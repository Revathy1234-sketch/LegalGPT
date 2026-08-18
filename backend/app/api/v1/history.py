from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.models import User, Contract, AgentExecutionLog

router = APIRouter()

class HistoryItem(BaseModel):
    id: str
    contract_id: str
    contract_name: str
    task_type: str
    status: str
    created_at: datetime
    latency_ms: Optional[float]

@router.get("/", response_model=List[HistoryItem])
def get_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Base Query for User's Contracts
    contracts_query = db.query(Contract).filter(Contract.uploaded_by == current_user.id)
    if current_user.organization_id:
        contracts_query = db.query(Contract).join(User).filter(User.organization_id == current_user.organization_id)

    contract_map = {c.id: c.file_name for c in contracts_query.all()}
    contract_ids = list(contract_map.keys())

    if not contract_ids:
        return []

    logs = db.query(AgentExecutionLog).filter(
        AgentExecutionLog.contract_id.in_(contract_ids)
    ).order_by(AgentExecutionLog.created_at.desc()).limit(50).all()

    history = []
    for log in logs:
        history.append(HistoryItem(
            id=str(log.id),
            contract_id=str(log.contract_id),
            contract_name=contract_map.get(log.contract_id, "Unknown Contract"),
            task_type=log.task_type,
            status="Completed" if log.output_payload else "Failed/Pending",
            created_at=log.created_at,
            latency_ms=log.latency_ms
        ))

    return history
