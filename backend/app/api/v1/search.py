from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel
from typing import List

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.models import User, Contract, Clause

router = APIRouter()

class SearchResult(BaseModel):
    id: str
    type: str # 'contract' or 'clause'
    title: str
    subtitle: str
    contract_id: str

@router.get("/", response_model=List[SearchResult])
def search(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    contracts_query = db.query(Contract).filter(Contract.uploaded_by == current_user.id)
    if current_user.organization_id:
        contracts_query = db.query(Contract).join(User).filter(User.organization_id == current_user.organization_id)

    user_contracts = contracts_query.all()
    contract_ids = [c.id for c in user_contracts]

    if not contract_ids:
        return []

    results = []

    # 1. Search Contracts by filename
    matching_contracts = [c for c in user_contracts if q.lower() in c.file_name.lower()]
    for c in matching_contracts:
        results.append(SearchResult(
            id=str(c.id),
            type="contract",
            title=c.file_name,
            subtitle=f"Status: {c.status}",
            contract_id=str(c.id)
        ))

    # 2. Search Clauses by text
    clauses = db.query(Clause).filter(
        Clause.contract_id.in_(contract_ids),
        or_(
            Clause.original_text.ilike(f"%{q}%"),
            Clause.clause_type.ilike(f"%{q}%")
        )
    ).limit(10).all()

    for clause in clauses:
        contract_name = next((c.file_name for c in user_contracts if c.id == clause.contract_id), "Contract")
        # create a snippet
        text = clause.original_text
        snippet = text
        idx = text.lower().find(q.lower())
        if idx != -1:
            start = max(0, idx - 30)
            end = min(len(text), idx + len(q) + 30)
            snippet = ("..." if start > 0 else "") + text[start:end] + ("..." if end < len(text) else "")

        results.append(SearchResult(
            id=str(clause.id),
            type="clause",
            title=f"{clause.clause_type} in {contract_name}",
            subtitle=snippet,
            contract_id=str(clause.contract_id)
        ))

    return results
