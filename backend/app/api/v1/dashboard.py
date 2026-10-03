from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from pydantic import BaseModel
from typing import List
from datetime import datetime
import uuid

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.models import User, Contract, ContractRiskAssessment, AgentExecutionLog

router = APIRouter()

class DashboardStats(BaseModel):
    total_contracts: int
    high_risk: int
    pending_analysis: int
    completed_analyses: int

class RecentActivity(BaseModel):
    id: str
    title: str
    target: str
    time: str
    type: str

class RecentContract(BaseModel):
    id: str
    name: str
    type: str
    date: str
    status: str
    risk: str
    lastAnalysis: str

class RiskDistribution(BaseModel):
    name: str
    value: int
    color: str
    findings: List[dict] = []

class ContractTypeStats(BaseModel):
    type: str
    count: int

class StatusDistribution(BaseModel):
    name: str
    value: int
    color: str

class RiskRadar(BaseModel):
    category: str
    score: int

class AgentUsage(BaseModel):
    name: str
    count: int

class DashboardData(BaseModel):
    stats: DashboardStats
    recent_activity: List[RecentActivity]
    recent_contracts: List[RecentContract]
    risk_distribution: List[RiskDistribution]
    contract_types: List[ContractTypeStats] = []
    status_distribution: List[StatusDistribution] = []
    risk_radar: List[RiskRadar] = []
    agent_usage: List[AgentUsage] = []

def _time_ago(dt: datetime) -> str:
    if not dt:
        return "Unknown"
    now = datetime.utcnow()
    diff = now - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        return f"{int(seconds // 60)} mins ago"
    elif seconds < 86400:
        return f"{int(seconds // 3600)} hrs ago"
    else:
        return f"{int(seconds // 86400)} days ago"

@router.get("/stats", response_model=DashboardData)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Base Query for User's Contracts
    contracts_query = db.query(Contract).filter(Contract.uploaded_by == current_user.id)
    if current_user.organization_id:
        contracts_query = db.query(Contract).join(User).filter(User.organization_id == current_user.organization_id)

    contracts = contracts_query.all()
    contract_ids = [c.id for c in contracts]

    total_contracts = len(contracts)

    # 2. High Risk count
    high_risk_count = 0
    if contract_ids:
        high_risk_count = db.query(ContractRiskAssessment).filter(
            ContractRiskAssessment.contract_id.in_(contract_ids),
            ContractRiskAssessment.overall_score < -1
        ).count()

    # 3. Statuses
    pending_count = sum(1 for c in contracts if c.status.lower() in ["pending", "processing"])

    # 4. Completed Analyses Log Count
    completed_analyses = 0
    if contract_ids:
        completed_analyses = db.query(AgentExecutionLog).filter(
            AgentExecutionLog.contract_id.in_(contract_ids)
        ).count()

    # 5. Risk Distribution
    low_risk = 0
    medium_risk = 0
    high_risk = 0

    high_findings = []
    medium_findings = []
    low_findings = []

    if contract_ids:
        assessments = db.query(ContractRiskAssessment).filter(
            ContractRiskAssessment.contract_id.in_(contract_ids)
        ).all()

        # Count findings from risk_matrix
        for a in assessments:
            if a.risk_matrix and isinstance(a.risk_matrix, list):
                for finding in a.risk_matrix:
                    # Depending on how it's stored, it might have a 'severity', 'level', or 'status'
                    # Or we just use the overall score of the assessment if finding level isn't specified
                    severity = finding.get('severity') or finding.get('status') or 'Medium'
                    sev_lower = str(severity).lower()
                    
                    finding_data = {
                        "category": finding.get("category", "General"),
                        "description": finding.get("issue") or finding.get("description", "No description"),
                        "impact": finding.get("financial_impact") or finding.get("impact", ""),
                        "evidence": finding.get("clause_reference") or finding.get("evidence", ""),
                        "page": finding.get("page", ""),
                        "section": finding.get("section", ""),
                        "source_text": finding.get("source_text", "")
                    }

                    if 'high' in sev_lower or 'critical' in sev_lower or 'non-compliant' in sev_lower:
                        high_risk += 1
                        high_findings.append(finding_data)
                    elif 'low' in sev_lower or 'info' in sev_lower:
                        low_risk += 1
                        low_findings.append(finding_data)
                    else:
                        medium_risk += 1
                        medium_findings.append(finding_data)
            else:
                # Fallback to contract-level score if no matrix
                score = a.overall_score if a.overall_score is not None else 0
                if score < -1:
                    high_risk += 1
                elif score < 0:
                    medium_risk += 1
                else:
                    low_risk += 1

    risk_distribution = [
        {"name": "High Risk", "value": high_risk, "color": "#f43f5e", "findings": high_findings},
        {"name": "Medium Risk", "value": medium_risk, "color": "#f59e0b", "findings": medium_findings},
        {"name": "Low Risk", "value": low_risk, "color": "#10b981", "findings": low_findings},
    ]

    # 6. Recent Contracts
    recent_contracts = []
    sorted_contracts = sorted(contracts, key=lambda c: c.created_at, reverse=True)[:5]
    for c in sorted_contracts:
        # get latest analysis
        latest_log = db.query(AgentExecutionLog).filter(AgentExecutionLog.contract_id == c.id).order_by(AgentExecutionLog.created_at.desc()).first()
        last_analysis = _time_ago(latest_log.created_at) if latest_log else "Never"

        # get risk
        risk_label = "Unknown"
        c_risk = db.query(ContractRiskAssessment).filter(ContractRiskAssessment.contract_id == c.id).order_by(ContractRiskAssessment.evaluated_at.desc()).first()
        if c_risk:
            risk_label = "High" if c_risk.overall_score < -1 else "Medium" if c_risk.overall_score < 0 else "Low"

        recent_contracts.append(RecentContract(
            id=str(c.id),
            name=c.file_name,
            type="PDF",
            date=c.created_at.strftime("%b %d, %Y"),
            status=c.status,
            risk=risk_label,
            lastAnalysis=last_analysis
        ))

    # 7. Recent Activity (Mix of uploads and analysis logs)
    activities = []
    for c in sorted_contracts:
        activities.append({
            "id": f"upload-{c.id}",
            "title": "Contract uploaded",
            "target": c.file_name,
            "dt": c.created_at,
            "type": "upload"
        })

    if contract_ids:
        logs = db.query(AgentExecutionLog).filter(AgentExecutionLog.contract_id.in_(contract_ids)).order_by(AgentExecutionLog.created_at.desc()).limit(10).all()
        for log in logs:
            c_name = next((c.file_name for c in contracts if c.id == log.contract_id), "Unknown Contract")
            activities.append({
                "id": str(log.id),
                "title": f"Analysis complete: {log.task_type}",
                "target": c_name,
                "dt": log.created_at,
                "type": "analysis"
            })

    activities.sort(key=lambda a: a["dt"], reverse=True)
    recent_activity = [
        RecentActivity(
            id=a["id"],
            title=a["title"],
            target=a["target"],
            time=_time_ago(a["dt"]),
            type=a["type"]
        )
        for a in activities[:10]
    ]

    # --- Additional Data for 6+ Charts ---
    # Status Distribution
    status_distribution = [
        {"name": "Completed", "value": total_contracts - pending_count, "color": "#10b981"},
        {"name": "Pending", "value": pending_count, "color": "#f59e0b"}
    ]
    
    # Contract Types
    type_counts = {}
    for c in contracts:
        ctype = c.type or "PDF"
        type_counts[ctype] = type_counts.get(ctype, 0) + 1
    contract_types = [{"type": k, "count": v} for k, v in type_counts.items()]
    
    # Risk Radar
    risk_radar = [
        {"category": "Financial", "score": min(high_risk_count * 20, 100)},
        {"category": "Operational", "score": min(medium_risk * 15, 100)},
        {"category": "Legal", "score": min(high_risk * 25, 100)},
        {"category": "Compliance", "score": min((high_risk + medium_risk) * 10, 100)},
        {"category": "Reputation", "score": min(low_risk * 5, 100)},
    ]
    
    # Agent Usage
    agent_counts = {}
    if contract_ids:
        logs = db.query(AgentExecutionLog).filter(AgentExecutionLog.contract_id.in_(contract_ids)).all()
        for log in logs:
            agent_counts[log.task_type] = agent_counts.get(log.task_type, 0) + 1
    agent_usage = [{"name": k, "count": v} for k, v in agent_counts.items()]

    return DashboardData(
        stats=DashboardStats(
            total_contracts=total_contracts,
            high_risk=high_risk_count,
            pending_analysis=pending_count,
            completed_analyses=completed_analyses
        ),
        recent_activity=recent_activity,
        recent_contracts=recent_contracts,
        risk_distribution=risk_distribution,
        contract_types=contract_types,
        status_distribution=status_distribution,
        risk_radar=risk_radar,
        agent_usage=agent_usage
    )

@router.get("/agent-status")
def get_agent_status(db: Session = Depends(get_db)):
    # Simple check for now: count recent successful executions per agent
    agents = [
        {"name": "SummaryAgent", "label": "Summary", "task": "summarize"},
        {"name": "ClauseAgent", "label": "Clauses", "task": "clause_extraction"},
        {"name": "RiskAgent", "label": "Risk", "task": "risk_analysis"},
        {"name": "ComplianceAgent", "label": "Compliance", "task": "compliance_check"},
        {"name": "NegotiationAgent", "label": "Negotiation", "task": "negotiation_analysis"},
        {"name": "KnowledgeGraphAgent", "label": "Knowledge Graph", "task": "knowledge_graph"}
    ]
    status = []
    for a in agents:
        count = db.query(AgentExecutionLog).filter(AgentExecutionLog.agent_name == a["name"]).count()
        status.append({
            "name": a["label"],
            "status": "Active" if count > 0 else "Ready",
            "executions": count
        })
    status.insert(0, {"name": "Retrieval", "status": "Active", "executions": -1})
    status.append({"name": "Chat", "status": "Ready", "executions": 0})
    return status
