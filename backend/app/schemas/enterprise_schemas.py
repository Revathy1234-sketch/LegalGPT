"""
Enterprise Response Standardization Schemas

Provides standardized response formats for all agents across LegalGPT.
Ensures consistent structure, validation, and metadata tracking.
"""

from typing import Any, Dict, List, Optional, Generic, TypeVar
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class AgentType(str, Enum):
    """Enumeration of all available agents."""
    SUMMARY = "summary"
    CLAUSE_EXTRACTION = "clause_extraction"
    RISK_ANALYSIS = "risk_analysis"
    COMPLIANCE = "compliance"
    NEGOTIATION = "negotiation"
    COMPARISON = "comparison"
    CHAT = "chat"
    KNOWLEDGE_GRAPH = "knowledge_graph"


class ConfidenceLevel(str, Enum):
    """Confidence level classifications."""
    VERY_LOW = "very_low"      # < 0.30
    LOW = "low"                # 0.30 - 0.50
    MEDIUM = "medium"          # 0.50 - 0.70
    HIGH = "high"              # 0.70 - 0.85
    VERY_HIGH = "very_high"    # > 0.85


class ErrorCode(str, Enum):
    """Standard error codes for enterprise responses."""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RETRIEVAL_ERROR = "RETRIEVAL_ERROR"
    MODEL_ERROR = "MODEL_ERROR"
    PARSING_ERROR = "PARSING_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    UNAUTHORIZED_ERROR = "UNAUTHORIZED_ERROR"
    NOT_FOUND_ERROR = "NOT_FOUND_ERROR"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"


# ============================================================================
# RETRIEVAL & CITATION MODELS
# ============================================================================

class Citation(BaseModel):
    """Represents a citation to source material."""
    chunk_id: str = Field(..., description="FAISS chunk ID")
    parent_id: str = Field(..., description="Parent document ID")
    content_preview: str = Field(..., description="First 200 chars of source")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Semantic relevance score")
    retrieval_method: str = Field(..., description="semantic | bm25 | hybrid")


class RetrievalMetadata(BaseModel):
    """Metadata about the retrieval process."""
    retrieval_time_ms: int = Field(..., ge=0, description="Time taken for retrieval")
    total_chunks_retrieved: int = Field(..., ge=0, description="Total chunks returned")
    total_chunks_deduplicated: int = Field(
        ..., ge=0, description="After parent deduplication"
    )
    semantic_match_count: int = Field(..., ge=0, description="Semantic matches")
    bm25_match_count: int = Field(..., ge=0, description="BM25 matches")
    top_retrieval_score: float = Field(..., ge=0.0, le=1.0, description="Best chunk score")
    contract_id: Optional[str] = Field(None, description="Source contract")


class ConfidenceMetadata(BaseModel):
    """Detailed breakdown of confidence calculation."""
    retrieval_score_component: float = Field(..., ge=0.0, le=1.0)
    chunk_count_component: float = Field(..., ge=0.0, le=1.0)
    response_quality_component: float = Field(..., ge=0.0, le=1.0)
    citation_presence_component: float = Field(..., ge=0.0, le=1.0)
    final_confidence_score: float = Field(..., ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel


class ProcessingMetrics(BaseModel):
    """Execution metrics for the agent processing."""
    retrieval_time_ms: int = Field(..., ge=0)
    llm_time_ms: int = Field(..., ge=0)
    total_processing_time_ms: int = Field(..., ge=0)
    input_tokens: Optional[int] = Field(None, ge=0)
    output_tokens: Optional[int] = Field(None, ge=0)
    total_tokens: Optional[int] = Field(None, ge=0)


# ============================================================================
# ERROR MODELS
# ============================================================================

class ErrorDetail(BaseModel):
    """Structured error information."""
    code: ErrorCode = Field(..., description="Standard error code")
    message: str = Field(..., max_length=500, description="User-friendly message")
    details: Optional[str] = Field(None, max_length=1000, description="Additional context")
    field: Optional[str] = Field(None, description="Field that caused error (validation)")


class EnterpriseErrorResponse(BaseModel):
    """Standard error response for all agents."""
    success: bool = Field(False, description="Always false for errors")
    agent: AgentType = Field(..., description="Which agent failed")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error: ErrorDetail = Field(...)
    request_id: Optional[str] = Field(None, description="Unique request identifier")

    # Pydantic V2: use_enum_values serializes enums as their string values.
    model_config = ConfigDict(use_enum_values=True)


# ============================================================================
# AGENT-SPECIFIC RESULT MODELS
# ============================================================================

class SummaryResult(BaseModel):
    """Result model for Summary Agent."""
    summary: str = Field(..., description="Executive summary")
    key_obligations: List[Dict[str, Any]] = Field(
        default_factory=list, description="Extracted obligations"
    )
    important_dates: List[Dict[str, Any]] = Field(
        default_factory=list, description="Key dates"
    )
    key_risks: List[Dict[str, Any]] = Field(
        default_factory=list, description="Identified risks"
    )


class ClauseExtractionResult(BaseModel):
    """Result model for Clause Extraction Agent."""
    clauses: List[Dict[str, Any]] = Field(
        default_factory=list, description="Extracted clauses"
    )


class RiskAnalysisResult(BaseModel):
    """Result model for Risk Analysis Agent."""
    overall_score: float = Field(..., ge=0, le=100, description="Risk score 0-100")
    risk_matrix: List[Dict[str, Any]] = Field(
        default_factory=list, description="Risk categories and ratings"
    )
    mitigation_plan: List[Dict[str, Any]] = Field(
        default_factory=list, description="Recommended mitigations"
    )


class ComplianceResult(BaseModel):
    """Result model for Compliance Agent."""
    compliant: bool = Field(..., description="Overall compliance status")
    issues: List[Dict[str, Any]] = Field(
        default_factory=list, description="Identified compliance issues"
    )
    recommendations: List[Dict[str, Any]] = Field(
        default_factory=list, description="Compliance recommendations"
    )


class NegotiationResult(BaseModel):
    """Result model for Negotiation Agent."""
    overall_risk_score: float = Field(..., ge=0, le=100, description="Negotiation risk 0-100")
    overall_risk_level: str = Field(..., description="low | medium | high | critical")
    executive_summary: str = Field(..., description="Executive summary")
    negotiation_suggestions: List[Dict[str, Any]] = Field(
        default_factory=list, description="Negotiation tactics"
    )
    priority_actions: List[Dict[str, Any]] = Field(
        default_factory=list, description="Priority action items"
    )


class ComparisonResult(BaseModel):
    """Result model for Comparison Agent."""
    similarities: List[Dict[str, Any]] = Field(
        default_factory=list, description="Similarities between contracts"
    )
    differences: List[Dict[str, Any]] = Field(
        default_factory=list, description="Key differences"
    )
    missing_clauses: List[Dict[str, Any]] = Field(
        default_factory=list, description="Missing clauses in comparison"
    )
    risk_differences: List[Dict[str, Any]] = Field(
        default_factory=list, description="Risk profile differences"
    )
    summary: str = Field(..., description="Comparison summary")


class ChatResult(BaseModel):
    """Result model for Chat Agent."""
    answer: str = Field(..., description="Answer to question")
    sources: List[Dict[str, Any]] = Field(
        default_factory=list, description="Source references"
    )


class KnowledgeGraphResult(BaseModel):
    """Result model for Knowledge Graph Agent."""
    entities: List[Dict[str, Any]] = Field(
        default_factory=list, description="Extracted entities"
    )
    relationships: List[Dict[str, Any]] = Field(
        default_factory=list, description="Entity relationships"
    )
    statistics: Dict[str, int] = Field(
        default_factory=dict, description="Entity and relationship counts"
    )


# ============================================================================
# GENERIC ENTERPRISE RESPONSE WRAPPER
# ============================================================================

ResultType = TypeVar('ResultType', bound=BaseModel)


class EnterpriseResponse(BaseModel, Generic[ResultType]):
    """
    Standard enterprise response wrapper for all agents.

    Wraps all agent outputs in a consistent structure with metadata,
    citations, confidence scores, and processing metrics.
    """
    success: bool = Field(True, description="Operation success status")
    agent: AgentType = Field(..., description="Agent that processed request")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    model: str = Field(..., description="LLM model used (e.g., gemini-2.0-flash)")
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Overall confidence 0.0-1.0"
    )
    confidence_level: ConfidenceLevel = Field(..., description="Confidence classification")
    processing_time_ms: int = Field(..., ge=0, description="Total processing time")

    # Retrieval & citation tracking
    retrieval_metadata: RetrievalMetadata = Field(...)
    citations: List[Citation] = Field(default_factory=list)
    source_parent_ids: List[str] = Field(
        default_factory=list, description="Unique parent document IDs"
    )
    source_chunk_ids: List[str] = Field(
        default_factory=list, description="Unique chunk IDs"
    )

    # Analysis metadata
    confidence_breakdown: ConfidenceMetadata = Field(...)
    processing_metrics: ProcessingMetrics = Field(...)
    reasoning_summary: str = Field(
        ..., max_length=500, description="Brief explanation of reasoning"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Non-fatal warnings"
    )

    # Agent-specific result (polymorphic)
    result: Dict[str, Any] = Field(...)

    # Tracking & correlation
    request_id: Optional[str] = Field(None, description="Unique request ID for tracing")
    contract_id: Optional[str] = Field(None, description="Source contract ID")

    # Pydantic V2: use_enum_values serializes enums as their string values.
    model_config = ConfigDict(use_enum_values=True)


# ============================================================================
# RESPONSE FACTORY MODELS (for agent-specific wrapper types)
# ============================================================================

class EnterpriseSummaryResponse(EnterpriseResponse):
    """Typed response wrapper for Summary Agent."""
    agent: AgentType = AgentType.SUMMARY
    result: SummaryResult = Field(...)


class EnterpriseClauseExtractionResponse(EnterpriseResponse):
    """Typed response wrapper for Clause Extraction Agent."""
    agent: AgentType = AgentType.CLAUSE_EXTRACTION
    result: ClauseExtractionResult = Field(...)


class EnterpriseRiskAnalysisResponse(EnterpriseResponse):
    """Typed response wrapper for Risk Analysis Agent."""
    agent: AgentType = AgentType.RISK_ANALYSIS
    result: RiskAnalysisResult = Field(...)


class EnterpriseComplianceResponse(EnterpriseResponse):
    """Typed response wrapper for Compliance Agent."""
    agent: AgentType = AgentType.COMPLIANCE
    result: ComplianceResult = Field(...)


class EnterpriseNegotiationResponse(EnterpriseResponse):
    """Typed response wrapper for Negotiation Agent."""
    agent: AgentType = AgentType.NEGOTIATION
    result: NegotiationResult = Field(...)


class EnterpriseComparisonResponse(EnterpriseResponse):
    """Typed response wrapper for Comparison Agent."""
    agent: AgentType = AgentType.COMPARISON
    result: ComparisonResult = Field(...)


class EnterpriseChatResponse(EnterpriseResponse):
    """Typed response wrapper for Chat Agent."""
    agent: AgentType = AgentType.CHAT
    result: ChatResult = Field(...)


class EnterpriseKnowledgeGraphResponse(EnterpriseResponse):
    """Typed response wrapper for Knowledge Graph Agent."""
    agent: AgentType = AgentType.KNOWLEDGE_GRAPH
    result: KnowledgeGraphResult = Field(...)
