from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from pydantic import BaseModel
from typing import List
from datetime import datetime
import os
import uuid

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.models import User, Contract, ContractRiskAssessment, AgentExecutionLog, RiskAnalysis
from app.services.evidence_grounding import ground_and_persist

router = APIRouter()

# overall_score is 0-100 where higher = riskier (see risk prompt contract)
HIGH_RISK_THRESHOLD = 70
MEDIUM_RISK_THRESHOLD = 40

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

    # Latest real risk assessment per contract (0-100 scale, higher = riskier)
    latest_risk: dict = {}
    if contract_ids:
        risk_rows = (
            db.query(RiskAnalysis)
            .filter(RiskAnalysis.contract_id.in_(contract_ids))
            .order_by(RiskAnalysis.evaluated_at.asc())
            .all()
        )
        for row in risk_rows:
            latest_risk[row.contract_id] = row  # ascending order => last wins

    # Make sure every finding carries verbatim PDF proof (ground + persist once)
    for cid, row in list(latest_risk.items()):
        ground_and_persist(db, cid, row)

    # 2. High Risk count (contracts with score >= 70)
    high_risk_count = sum(
        1 for row in latest_risk.values()
        if (row.overall_score or 0) >= HIGH_RISK_THRESHOLD
    )

    # 3. Statuses
    pending_count = sum(1 for c in contracts if c.status.lower() in ["pending", "processing"])

    # 4. Completed Analyses Log Count
    completed_analyses = 0
    if contract_ids:
        completed_analyses = db.query(AgentExecutionLog).filter(
            AgentExecutionLog.contract_id.in_(contract_ids)
        ).count()

    # 5. Risk Distribution - built from the real risk_matrix (with PDF evidence)
    low_risk = 0
    medium_risk = 0
    high_risk = 0

    high_findings = []
    medium_findings = []
    low_findings = []

    for row in latest_risk.values():
        matrix = row.risk_matrix if isinstance(row.risk_matrix, list) else []
        for finding in matrix:
            if not isinstance(finding, dict):
                continue
            severity = (
                finding.get("severity")
                or finding.get("risk_level")
                or finding.get("likelihood")
                or "Medium"
            )
            sev_lower = str(severity).lower()

            finding_data = {
                "category": finding.get("category", "General"),
                "description": finding.get("issue")
                or finding.get("description")
                or finding.get("title")
                or "No description",
                "impact": finding.get("financial_impact")
                or finding.get("impact")
                or finding.get("business_impact")
                or "",
                "evidence": finding.get("clause_reference")
                or finding.get("evidence")
                or "",
                "page": finding.get("page", ""),
                "section": finding.get("section", ""),
                "source_text": finding.get("source_text", ""),
                "mitigation": finding.get("mitigation", ""),
                "severity": str(severity),
            }

            if "high" in sev_lower or "critical" in sev_lower or "non-compliant" in sev_lower:
                high_risk += 1
                high_findings.append(finding_data)
            elif "low" in sev_lower or "info" in sev_lower or "compliant" in sev_lower:
                low_risk += 1
                low_findings.append(finding_data)
            else:
                medium_risk += 1
                medium_findings.append(finding_data)

    # Contracts assessed but with an empty matrix: bucket by overall score
    for row in latest_risk.values():
        if isinstance(row.risk_matrix, list) and len(row.risk_matrix) == 0:
            score = row.overall_score or 0
            if score >= HIGH_RISK_THRESHOLD:
                high_risk += 1
            elif score >= MEDIUM_RISK_THRESHOLD:
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

        # get risk label from the latest real risk analysis (0-100 scale)
        risk_label = "Unknown"
        c_risk = latest_risk.get(c.id)
        if c_risk:
            score = c_risk.overall_score or 0
            risk_label = (
                "High" if score >= HIGH_RISK_THRESHOLD
                else "Medium" if score >= MEDIUM_RISK_THRESHOLD
                else "Low"
            )

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
    
    # Contract Types (derived from file extension; Contract has no `type` column)
    type_counts = {}
    for c in contracts:
        ext = (os.path.splitext(c.file_name or "")[1] or ".pdf").lstrip(".").upper()
        type_counts[ext] = type_counts.get(ext, 0) + 1
    contract_types = [{"type": k, "count": v} for k, v in type_counts.items()]
    
    # Risk Radar - derived from real findings categories
    category_scores = {}
    for row in latest_risk.values():
        matrix = row.risk_matrix if isinstance(row.risk_matrix, list) else []
        for finding in matrix:
            if not isinstance(finding, dict): continue
            cat = finding.get("category", "General")
            sev = str(finding.get("severity", "Medium")).lower()
            val = 20 if "high" in sev or "critical" in sev else 10 if "medium" in sev else 5
            category_scores[cat] = category_scores.get(cat, 0) + val
            
    risk_radar = []
    for cat, score in category_scores.items():
        risk_radar.append({"category": cat, "score": min(score, 100)})
        
    if not risk_radar:
        risk_radar = [{"category": "No Risks Found", "score": 0}]
    
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
    from app.models.models import ChatMessage
    
    agents = [
        {"name": "SummaryAgent", "label": "Summary", "task": "summarize"},
        {"name": "ClauseAgent", "label": "Clauses", "task": "clause_extraction"},
        {"name": "RiskAgent", "label": "Risk", "task": "risk_analysis"},
        {"name": "ComplianceAgent", "label": "Compliance", "task": "compliance_check"},
        {"name": "NegotiationAgent", "label": "Negotiation", "task": "negotiation_analysis"},
        {"name": "ComparisonAgent", "label": "Comparison", "task": "comparison"},
        {"name": "KnowledgeGraphAgent", "label": "Knowledge Graph", "task": "knowledge_graph"},
        {"name": "Retrieval", "label": "Retrieval", "task": "retrieval"},
        {"name": "Chat", "label": "Chat", "task": "chat"}
    ]
    status = []
    
    from app.models.models import ChatSession
    
    for a in agents:
        if a["task"] == "chat":
            count = db.query(ChatSession).count()
        else:
            count = db.query(AgentExecutionLog).filter(AgentExecutionLog.task_type == a["task"]).count()
            
        status.append({
            "name": a["label"],
            "status": "Active" if count > 0 else "Ready",
            "executions": count
        })
    return status
