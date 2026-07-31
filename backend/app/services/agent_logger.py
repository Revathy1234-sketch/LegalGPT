import time
from sqlalchemy.orm import Session
from app.models.models import AgentExecutionLog
from typing import Optional, Any


def log_agent_execution(
    db: Session,
    agent_name: str,
    contract_id: Optional[str],
    task_type: str,
    input_payload: Any,
    output_payload: Any,
    status: str,
    start_time: float,
    end_time: float,
    metadata_json: Optional[dict] = None,
):
    latency_ms = (end_time - start_time) * 1000.0
    log = AgentExecutionLog(
        contract_id=contract_id,
        agent_name=agent_name,
        task_type=task_type,
        input_payload=input_payload,
        output_payload=output_payload,
        metadata_json=metadata_json or {},
        latency_ms=latency_ms,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
