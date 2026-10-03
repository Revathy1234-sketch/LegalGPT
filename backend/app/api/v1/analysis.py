import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.chat_agent import run_chat_agent
from app.agents.clause_agent import run_clause_agent
from app.agents.comparison_agent import run_comparison_agent
from app.agents.compliance_agent import run_compliance_agent
from app.agents.knowledge_graph_agent import run_knowledge_graph_agent
from app.agents.negotiation_agent import run_negotiation_agent
from app.agents.risk_agent import run_risk_analysis as run_risk_agent
from app.agents.summary_agent import run_summary_agent
from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.models import (
    Clause,
    Contract,
    ContractClauseExtraction,
    ContractRiskAssessment,
    RiskAnalysis,
    User,
)
from app.schemas.analysis_schemas import (
    ClauseExtractionResponse,
    CompareRequest,
    CompareResponse,
    ComplianceResponse,
    NegotiationAnalysisResponse,
    KnowledgeGraphResponse,
)
from app.schemas.schemas import (
    ContractQuestionRequest,
    ContractResponse,
    RiskAnalysisResponse,
)
from app.services.agent_logger import log_agent_execution


logger = logging.getLogger(__name__)
router = APIRouter()


def log_endpoint_call(endpoint: str, contract_id: str, status_: str = 'START') -> None:
    logger.info('[%s] %s | Contract: %s', status_, endpoint, contract_id)


def validate_contract_access(contract: Contract, current_user: User) -> None:
    if current_user.organization_id:
        uploader = contract.uploader
        if not uploader or uploader.organization_id != current_user.organization_id:
            raise HTTPException(status_code=403, detail='Unauthorized')
    elif contract.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail='Unauthorized')


def _agent_payload(response: Any) -> Dict[str, Any]:
    if not getattr(response, 'success', False):
        error = getattr(response, 'error', None)
        detail = getattr(error, 'message', 'Enterprise agent execution failed')
        raise HTTPException(status_code=500, detail=detail)

    result = getattr(response, 'result', None)
    if not isinstance(result, dict):
        raise HTTPException(status_code=500, detail='Enterprise agent returned an invalid result')
    return result


def _serialized_response(response: Any) -> Dict[str, Any]:
    if isinstance(response, dict):
        return response
    if hasattr(response, 'model_dump'):
        return response.model_dump(mode='json')
    return {'result': _agent_payload(response)}


def _log_execution(
    db: Session,
    agent_name: str,
    contract_id: str,
    task_type: str,
    response: Any,
    start_time: float,
    end_time: float,
) -> None:
    try:
        with db.begin_nested():
            log_agent_execution(
                db=db,
                agent_name=agent_name,
                contract_id=contract_id,
                task_type=task_type,
                input_payload={'contract_id': contract_id},
                output_payload=_serialized_response(response),
                status='SUCCESS',
                start_time=start_time,
                end_time=end_time,
            )
    except Exception as exc:
        logger.warning('Failed to persist %s execution log: %s', agent_name, exc)


def _string_list(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    return [value if isinstance(value, str) else str(value) for value in values]

def _get_cached_result(db: Session, contract_id: uuid.UUID, task_type: str) -> Optional[Dict[str, Any]]:
    from app.models.models import AgentExecutionLog
    log = db.query(AgentExecutionLog).filter(
        AgentExecutionLog.contract_id == contract_id,
        AgentExecutionLog.task_type == task_type
    ).order_by(AgentExecutionLog.created_at.desc()).first()
    if log and log.output_payload:
        if isinstance(log.output_payload, dict):
            # Output payload could be the raw dict from _serialized_response
            if log.output_payload.get('success'):
                return log.output_payload.get('result')
            elif 'result' in log.output_payload:
                return log.output_payload['result']
            return log.output_payload
    return None


@router.post('/summarize/{contract_id}', response_model=ContractResponse)
def run_summarize(
    contract_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail='Contract not found')

    validate_contract_access(contract, current_user)
    log_endpoint_call('run_summarize', str(contract_id))

    # Return cached summary but still record telemetry for every API call.
    if contract.summary and contract.summary != "No summary generated.":
        start_time = time.perf_counter()
        end_time = time.perf_counter()
        _log_execution(
            db, 'SummaryAgent', str(contract_id), 'summarize',
            {'success': True, 'result': {'summary': contract.summary, 'cached': True}},
            start_time, end_time,
        )
        latest_risk = db.query(RiskAnalysis).filter(RiskAnalysis.contract_id == contract_id).order_by(RiskAnalysis.evaluated_at.desc()).first()
        return {
            "id": contract.id,
            "file_name": contract.file_name,
            "storage_url": contract.storage_url,
            "status": contract.status,
            "summary": contract.summary,
            "uploaded_by": contract.uploaded_by,
            "created_at": contract.created_at,
            "clauses": contract.clause_extractions if hasattr(contract, 'clause_extractions') else [],
            "risk_analysis": latest_risk
        }

    start_time = time.perf_counter()
    response = run_summary_agent(str(contract_id))
    end_time = time.perf_counter()
    result = _agent_payload(response)

    _log_execution(
        db, 'SummaryAgent', str(contract_id), 'summarize',
        response, start_time, end_time,
    )

    contract.summary = str(result.get('summary', ''))
    db.commit()
    db.refresh(contract)
    
    # Map the DB relationships to the Pydantic schema expected names
    latest_risk = db.query(RiskAnalysis).filter(RiskAnalysis.contract_id == contract_id).order_by(RiskAnalysis.evaluated_at.desc()).first()
    
    # Return as dict to satisfy ContractResponse
    response_data = {
        "id": contract.id,
        "file_name": contract.file_name,
        "storage_url": contract.storage_url,
        "status": contract.status,
        "summary": contract.summary,
        "uploaded_by": contract.uploaded_by,
        "created_at": contract.created_at,
        "clauses": contract.clause_extractions if hasattr(contract, 'clause_extractions') else [],
        "risk_analysis": latest_risk
    }
    
    return response_data


@router.post('/risk/{contract_id}', response_model=RiskAnalysisResponse)
def run_risk_analysis(
    contract_id: uuid.UUID,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail='Contract not found')

    validate_contract_access(contract, current_user)
    log_endpoint_call('run_risk_analysis', str(contract_id))

    if not force:
        cached = _get_cached_result(db, contract_id, 'risk_analysis')
        if cached:
            # We must also return the db_risk schema or at least a RiskAnalysisResponse compatible dict
            db_risk = db.query(RiskAnalysis).filter(RiskAnalysis.contract_id == contract_id).first()
            if db_risk:
                return db_risk

    start_time = time.perf_counter()
    response = run_risk_agent(str(contract_id))
    end_time = time.perf_counter()
    result = _agent_payload(response)

    _log_execution(
        db, 'RiskAgent', str(contract_id), 'risk_analysis',
        response, start_time, end_time,
    )

    risks = result.get('risk_matrix', [])
    mitigation_plan = result.get('mitigation_plan')
    if not isinstance(mitigation_plan, str):
        mitigation_plan = 'Mitigation suggestions compiled. Refer to negotiation suggestions.'

    db.query(RiskAnalysis).filter(RiskAnalysis.contract_id == contract_id).delete()
    try:
        raw_score = result.get('overall_score', 0)
        overall_score = int(float(raw_score))
    except (ValueError, TypeError):
        overall_score = 0

    db_risk = RiskAnalysis(
        contract_id=contract_id,
        overall_score=overall_score,
        risk_matrix=risks if isinstance(risks, list) else [],
        mitigation_plan=mitigation_plan,
    )
    db.add(db_risk)
    db.commit()
    db.refresh(db_risk)
    return db_risk


@router.post('/clauses/{contract_id}', response_model=ClauseExtractionResponse)
def extract_clauses(
    contract_id: uuid.UUID,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail='Contract not found')

    validate_contract_access(contract, current_user)
    log_endpoint_call('extract_clauses', str(contract_id))

    if not force:
        cached = _get_cached_result(db, contract_id, 'clause_extraction')
        if cached:
            return {'clauses': cached.get('clauses', [])}

    start_time = time.perf_counter()
    response = run_clause_agent(str(contract_id))
    end_time = time.perf_counter()
    result = _agent_payload(response)

    _log_execution(
        db, 'ClauseAgent', str(contract_id), 'clause_extraction',
        response, start_time, end_time,
    )

    extracted = result.get('clauses', [])
    if not isinstance(extracted, list):
        extracted = []

    db.query(Clause).filter(Clause.contract_id == contract_id).delete()
    db.query(ContractClauseExtraction).filter(
        ContractClauseExtraction.contract_id == contract_id
    ).delete()

    clauses_out = []
    for clause in extracted:
        if not isinstance(clause, dict):
            continue
        clause_type = (
            clause.get('clause_type') or clause.get('category') or
            clause.get('title') or 'Unknown'
        )
        original_text = clause.get('original_text') or clause.get('content') or ''
        confidence = float(clause.get('confidence_score', 1.0))

        db.add(Clause(
            contract_id=contract_id,
            clause_type=clause_type,
            original_text=original_text,
            confidence_score=confidence,
        ))
        db.add(ContractClauseExtraction(
            contract_id=contract_id,
            clause_type=clause_type,
            original_text=original_text,
            confidence_score=confidence,
            source_parent_id=clause.get('source_parent_id'),
            source_chunk_id=clause.get('source_chunk_id'),
        ))
        clauses_out.append({
            'title': clause.get('title') or clause_type,
            'category': clause.get('category') or clause_type,
            'content': original_text,
            'confidence_score': confidence,
        })

    db.commit()
    logger.info(
        'Clause extraction completed: %s clauses saved for contract %s',
        len(clauses_out), contract_id,
    )
    return {'clauses': clauses_out}


@router.post('/compliance/{contract_id}', response_model=ComplianceResponse)
def run_compliance_analysis(
    contract_id: uuid.UUID,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail='Contract not found')

    validate_contract_access(contract, current_user)
    log_endpoint_call('run_compliance_analysis', str(contract_id))

    if not force:
        cached = _get_cached_result(db, contract_id, 'compliance_check')
        if cached:
            return {
                'compliant': bool(cached.get('compliant', False)),
                'issues': cached.get('issues', []),
                'recommendations': _string_list(cached.get('recommendations', []))
            }

    start_time = time.perf_counter()
    response = run_compliance_agent(str(contract_id))
    end_time = time.perf_counter()
    result = _agent_payload(response)

    _log_execution(
        db, 'ComplianceAgent', str(contract_id), 'compliance_check',
        response, start_time, end_time,
    )

    issues = result.get('issues', [])
    recommendations = result.get('recommendations', [])
    if not isinstance(issues, list):
        issues = []
    if not isinstance(recommendations, list):
        recommendations = []
    compliant = bool(result.get('compliant', False))

    issues_mapped = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        framework = issue.get('framework') or result.get('framework') or 'Compliance Framework'
        clause_type = issue.get('clause_type') or result.get('clause_type') or 'Compliance'
        status = issue.get('status') or result.get('status') or 'Non-Compliant'
        gap_analysis = issue.get('gap_analysis') or issue.get('requirement') or issue.get('issue') or issue.get('description') or ''
        issues_mapped.append({
            'framework': str(framework),
            'clause_type': str(clause_type),
            'status': str(status),
            'gap_analysis': str(gap_analysis),
        })

    db.query(ContractRiskAssessment).filter(
        ContractRiskAssessment.contract_id == contract_id,
        ContractRiskAssessment.overall_score == -1,
    ).delete()
    db.add(ContractRiskAssessment(
        contract_id=contract_id,
        overall_score=-1,
        risk_matrix=issues_mapped,
        confidence=getattr(response, 'confidence_score', 1.0 if compliant else 0.5),
    ))
    db.commit()

    logger.info(
        'Compliance check completed: %s issues found for contract %s',
        len(issues_mapped), contract_id,
    )
    return {
        'compliant': compliant,
        'issues': issues_mapped,
        'recommendations': _string_list(recommendations),
    }


@router.post('/negotiation/{contract_id}', response_model=NegotiationAnalysisResponse)
def run_negotiation_analysis(
    contract_id: uuid.UUID,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail='Contract not found')

    validate_contract_access(contract, current_user)
    log_endpoint_call('run_negotiation_analysis', str(contract_id))

    if not force:
        cached = _get_cached_result(db, contract_id, 'negotiation_analysis')
        if cached:
            return {
                'overall_risk_score': int(float(cached.get('overall_risk_score', 0))),
                'overall_risk_level': str(cached.get('overall_risk_level', 'unknown')),
                'executive_summary': str(cached.get('executive_summary', '')),
                'negotiation_suggestions': _string_list(cached.get('negotiation_suggestions', [])),
                'priority_actions': _string_list(cached.get('priority_actions', []))
            }

    start_time = time.perf_counter()
    response = run_negotiation_agent(str(contract_id))
    end_time = time.perf_counter()
    result = _agent_payload(response)

    _log_execution(
        db, 'NegotiationAgent', str(contract_id), 'negotiation_analysis',
        response, start_time, end_time,
    )

    suggestions = result.get('negotiation_suggestions', [])
    if not isinstance(suggestions, list):
        suggestions = []

    db.query(ContractRiskAssessment).filter(
        ContractRiskAssessment.contract_id == contract_id,
        ContractRiskAssessment.overall_score == -2,
    ).delete()
    db.add(ContractRiskAssessment(
        contract_id=contract_id,
        overall_score=-2,
        risk_matrix=suggestions,
        confidence=getattr(response, 'confidence_score', 1.0),
    ))
    db.commit()

    logger.info(
        'Negotiation analysis completed: %s suggestions for contract %s',
        len(suggestions), contract_id,
    )
    return {
        'clauses': result.get('clauses', []),
        'risk_matrix': result.get('risk_matrix', []),
        'compliance_report': result.get('compliance_report', []),
        'negotiation_suggestions': suggestions,
    }


@router.post('/compare', response_model=CompareResponse)
def compare_contracts(
    payload: CompareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract_a = db.query(Contract).filter(Contract.id == payload.contract_a_id).first()
    contract_b = db.query(Contract).filter(Contract.id == payload.contract_b_id).first()
    if not contract_a or not contract_b:
        raise HTTPException(status_code=404, detail='One or both contracts not found')

    validate_contract_access(contract_a, current_user)
    validate_contract_access(contract_b, current_user)

    response = run_comparison_agent(
        str(payload.contract_a_id),
        str(payload.contract_b_id),
    )
    result = _agent_payload(response)
    return {
        'similarities': _string_list(result.get('similarities', [])),
        'differences': _string_list(result.get('differences', [])),
        'missing_clauses': _string_list(result.get('missing_clauses', [])),
        'risk_differences': _string_list(result.get('risk_differences', [])),
        'summary': str(result.get('summary', '')),
    }


@router.post('/chat/{contract_id}')
def chat_contract(
    contract_id: uuid.UUID,
    payload: ContractQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail='Contract not found')

    validate_contract_access(contract, current_user)
    from app.models.models import ChatSession, ChatMessage
    session = db.query(ChatSession).filter(ChatSession.user_id == current_user.id, ChatSession.contract_id == contract_id).first()
    if not session:
        session = ChatSession(user_id=current_user.id, contract_id=contract_id)
        db.add(session)
        db.commit()
        db.refresh(session)
        
    user_msg = ChatMessage(session_id=session.id, sender_role="user", content=payload.question)
    db.add(user_msg)
    db.commit()

    response = run_chat_agent(str(contract_id), payload.question)
    
    agent_msg = ChatMessage(
        session_id=session.id, 
        sender_role="assistant", 
        content=response.get("result", {}).get("answer", ""),
        metadata_json={"citations": response.get("result", {}).get("citations", [])}
    )
    db.add(agent_msg)
    db.commit()
    
    return response

@router.get('/chat/{contract_id}')
def get_chat_history(
    contract_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.models import ChatSession, ChatMessage
    session = db.query(ChatSession).filter(ChatSession.user_id == current_user.id, ChatSession.contract_id == contract_id).first()
    if not session:
        return []
    
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at.asc()).all()
    return [
        {
            "role": msg.sender_role,
            "content": msg.content,
            "metadata": msg.metadata_json,
            "created_at": msg.created_at.isoformat()
        } for msg in messages
    ]


@router.post('/knowledge-graph/{contract_id}', response_model=KnowledgeGraphResponse)
def knowledge_graph(
    contract_id: uuid.UUID,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail='Contract not found')

    validate_contract_access(contract, current_user)

    if not force:
        cached = _get_cached_result(db, contract_id, 'knowledge_graph')
        if cached:
            return {
                "success": True,
                "result": {
                    "entities": cached.get("nodes", []),
                    "relationships": cached.get("edges", [])
                }
            }

    start_time = time.perf_counter()
    agent_response = run_knowledge_graph_agent(str(contract_id))
    end_time = time.perf_counter()
    result_dict = _agent_payload(agent_response)

    _log_execution(
        db, 'KnowledgeGraphAgent', str(contract_id), 'knowledge_graph',
        agent_response, start_time, end_time,
    )

    return {
        "success": True,
        "result": {
            "entities": result_dict.get("nodes", []),
            "relationships": result_dict.get("edges", [])
        }
    }
