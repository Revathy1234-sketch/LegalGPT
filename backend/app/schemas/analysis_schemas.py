from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID

class ClauseExtractionItem(BaseModel):
    title: str
    category: str
    content: str
    confidence_score: Optional[float] = 1.0

class ClauseExtractionResponse(BaseModel):
    clauses: List[ClauseExtractionItem]

class ComplianceIssue(BaseModel):
    framework: str
    clause_type: str
    status: str
    gap_analysis: Optional[str] = None

class ComplianceResponse(BaseModel):
    compliant: bool
    issues: List[ComplianceIssue]
    recommendations: List[str]

class CompareRequest(BaseModel):
    contract_a_id: UUID
    contract_b_id: UUID

class CompareResponse(BaseModel):
    similarities: List[str]
    differences: List[str]
    missing_clauses: List[str]
    risk_differences: List[str]
    summary: str

class ContractSummaryResponse(BaseModel):
    contract_id: UUID
    summary_text: str
    key_obligations: Optional[List[str]] = []
    important_dates: Optional[List[str]] = []
    parties_involved: Optional[List[str]] = []
    confidence: float
    created_at: datetime

class RiskAssessmentResponse(BaseModel):
    id: UUID
    contract_id: UUID
    overall_score: int
    risk_matrix: Optional[List[dict]] = None
    mitigation_plan: Optional[str] = None
    confidence: Optional[float] = None
    evaluated_at: datetime

    model_config = {
        "from_attributes": True
    }

class NegotiationAnalysisResponse(BaseModel):
    clauses: Optional[List[dict]] = []
    risk_matrix: Optional[List[dict]] = []
    compliance_report: Optional[List[dict]] = []
    negotiation_suggestions: List[dict]

class KnowledgeGraphEntity(BaseModel):
    id: str
    type: str
    name: Optional[str] = None
    label: Optional[str] = None
    description: Optional[str] = None

class KnowledgeGraphRelationship(BaseModel):
    source: str
    target: str
    type: Optional[str] = None
    relationship: Optional[str] = None

class KnowledgeGraphResult(BaseModel):
    entities: List[KnowledgeGraphEntity]
    relationships: List[KnowledgeGraphRelationship]

class KnowledgeGraphResponse(BaseModel):
    success: bool
    result: KnowledgeGraphResult
