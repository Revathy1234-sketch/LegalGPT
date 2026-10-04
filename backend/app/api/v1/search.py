from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, String
from pydantic import BaseModel
from typing import List, Optional

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.models import User, Contract, Clause, AgentExecutionLog

router = APIRouter()

class SearchResultItem(BaseModel):
    id: str
    type: str # 'contract', 'clause', 'analysis', 'knowledge_graph', 'evidence'
    title: str
    subtitle: str
    contract_id: str
    link: Optional[str] = None

class SearchResultGroup(BaseModel):
    group: str
    items: List[SearchResultItem]

@router.get("/", response_model=List[SearchResultGroup])
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
    contract_map = {c.id: c.file_name for c in user_contracts}

    if not contract_ids:
        return []

    results_by_group = {
        "Contracts": [],
        "Clauses": [],
        "Analyses": [],
        "Knowledge Graph": [],
        "Evidence": []
    }

    q_lower = q.lower()

    # 1. Search Contracts
    matching_contracts = [c for c in user_contracts if q_lower in c.file_name.lower() or q_lower in str(c.id).lower() or q_lower in (c.status or "").lower()]
    for c in matching_contracts:
        results_by_group["Contracts"].append(SearchResultItem(
            id=str(c.id),
            type="contract",
            title=c.file_name,
            subtitle=f"Status: {c.status} | ID: {str(c.id)[:8]}...",
            contract_id=str(c.id),
            link=f"/contracts/{c.id}"
        ))

    # 2. Search Clauses
    clauses = db.query(Clause).filter(
        Clause.contract_id.in_(contract_ids),
        or_(
            Clause.original_text.ilike(f"%{q}%"),
            Clause.clause_type.ilike(f"%{q}%")
        )
    ).limit(10).all()

    for clause in clauses:
        contract_name = contract_map.get(clause.contract_id, "Contract")
        text = clause.original_text
        snippet = text
        idx = text.lower().find(q_lower)
        if idx != -1:
            start = max(0, idx - 30)
            end = min(len(text), idx + len(q) + 30)
            snippet = ("..." if start > 0 else "") + text[start:end] + ("..." if end < len(text) else "")

        results_by_group["Clauses"].append(SearchResultItem(
            id=str(clause.id),
            type="clause",
            title=f"{clause.clause_type}",
            subtitle=f"{contract_name} • {snippet}",
            contract_id=str(clause.contract_id),
            link=f"/agents/clauses"
        ))

    # 3. Search Agent Logs (Analyses, KG, Evidence)
    logs = db.query(AgentExecutionLog).filter(
        AgentExecutionLog.contract_id.in_(contract_ids),
        cast(AgentExecutionLog.output_payload, String).ilike(f"%{q}%")
    ).limit(20).all()

    for log in logs:
        contract_name = contract_map.get(log.contract_id, "Contract")
        agent = log.agent_name
        
        if agent == "knowledge_graph":
            results_by_group["Knowledge Graph"].append(SearchResultItem(
                id=str(log.id),
                type="knowledge_graph",
                title=f"Entity / Relationship Match",
                subtitle=f"{contract_name}",
                contract_id=str(log.contract_id),
                link=f"/agents/knowledge_graph"
            ))
        elif agent in ["risk", "compliance", "negotiation", "summary"]:
            results_by_group["Analyses"].append(SearchResultItem(
                id=str(log.id),
                type="analysis",
                title=f"{agent.capitalize()} Agent Result",
                subtitle=f"{contract_name} match found",
                contract_id=str(log.contract_id),
                link=f"/agents/{agent}"
            ))
            
            # Evidence could also be extracted if it matches specific patterns (rough approximation)
            if agent in ["risk", "compliance", "negotiation"]:
                 results_by_group["Evidence"].append(SearchResultItem(
                    id=f"{log.id}-evidence",
                    type="evidence",
                    title=f"Finding in {agent.capitalize()}",
                    subtitle=f"{contract_name}",
                    contract_id=str(log.contract_id),
                    link=f"/agents/{agent}"
                ))

    # Compile final result
    final_results = []
    for group_name, items in results_by_group.items():
        if items:
            # deduplicate
            unique_items = {item.id: item for item in items}.values()
            final_results.append(SearchResultGroup(
                group=group_name,
                items=list(unique_items)
            ))

    return final_results
