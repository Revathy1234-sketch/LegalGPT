"""
Enterprise Response Utilities

Provides utilities for response wrapping, validation, confidence scoring,
and processing time tracking.
"""

import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from decimal import Decimal

from app.core.config import settings
from app.schemas.enterprise_schemas import (
    AgentType,
    Citation,
    ConfidenceLevel,
    ConfidenceMetadata,
    EnterpriseResponse,
    ErrorCode,
    ErrorDetail,
    EnterpriseErrorResponse,
    ProcessingMetrics,
    RetrievalMetadata,
)


# ============================================================================
# RESPONSE VALIDATION
# ============================================================================

def sanitize_reasoning_summary(
    reasoning_summary: Optional[str],
    fallback: str = "LLM request failed.",
) -> str:
    """Return a concise reasoning summary that never exposes raw LLM errors."""
    if reasoning_summary is None:
        return fallback

    text = str(reasoning_summary).strip()
    if not text:
        return fallback

    lowered = text.lower()
    if any(token in lowered for token in ["quota", "resourceexhausted", "429", "rate limit", "per minute"]):
        return "Gemini API quota exceeded."
    if any(token in lowered for token in ["timeout", "timed out", "deadline"]):
        return "LLM request timed out."
    if any(token in lowered for token in ["unavailable", "service unavailable", "connection", "network", "temporarily unavailable"]):
        return "LLM service unavailable."
    if any(token in lowered for token in ["error", "failed", "exception", "traceback"]):
        return fallback

    if len(text) > 200:
        return text[:197].rstrip() + "..."
    return text


def sanitize_warning_message(warning: Optional[str], fallback: str = "LLM request failed.") -> str:
    """Return a concise warning that avoids leaking raw exception payloads."""
    if warning is None:
        return ""

    text = str(warning).strip()
    if not text:
        return ""

    lowered = text.lower()
    if any(token in lowered for token in ["quota", "resourceexhausted", "429", "rate limit", "per minute", "timeout", "timed out", "deadline", "exception", "traceback", "error"]):
        return fallback

    if len(text) > 120:
        return text[:117].rstrip() + "..."
    return text


def log_exception_context(agent_name: str, exc: Exception) -> None:
    """Log the full exception context without exposing it in API payloads."""
    logger = logging.getLogger(f"legalgpt.agent.{agent_name}")
    logger.exception("[%s] LLM request failed", agent_name, exc_info=exc)


class ResponseValidator:
    """Validates enterprise responses for quality and consistency."""

    @staticmethod
    def validate_json_structure(data: Any) -> Tuple[bool, List[str]]:
        """
        Validate JSON structure and content.
        
        Args:
            data: Data to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        if not isinstance(data, dict):
            errors.append("Response must be a dictionary")
            return False, errors
        
        # Check for empty strings
        for key, value in data.items():
            if isinstance(value, str) and not value.strip():
                errors.append(f"Field '{key}' contains empty string")
            elif isinstance(value, list) and len(value) == 0:
                # Empty lists are allowed in this context
                pass
            elif isinstance(value, dict) and len(value) == 0:
                # Empty dicts are allowed in this context
                pass
        
        return len(errors) == 0, errors

    @staticmethod
    def validate_markdown_free(text: str) -> Tuple[bool, List[str]]:
        """
        Check if text contains markdown formatting.
        
        Args:
            text: Text to validate
            
        Returns:
            Tuple of (is_markdown_free, issues)
        """
        issues = []
        
        # Check for markdown patterns
        patterns = [
            (r'^#+\s+', "Heading marker"),
            (r'\*\*.*?\*\*', "Bold formatting"),
            (r'__.*?__', "Bold formatting"),
            (r'\*.*?\*', "Italic formatting"),
            (r'_.*?_', "Italic formatting"),
            (r'\[.*?\]\(.*?\)', "Link formatting"),
            (r'^-\s+', "Bullet list"),
            (r'^\d+\.\s+', "Numbered list"),
            (r'`.*?`', "Code formatting"),
            (r'```', "Code block"),
        ]
        
        for pattern, issue_type in patterns:
            if re.search(pattern, text, re.MULTILINE):
                issues.append(issue_type)
        
        return len(issues) == 0, issues

    @staticmethod
    def sanitize_response(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize response by removing markdown and normalizing text.
        
        Args:
            data: Response data to sanitize
            
        Returns:
            Sanitized response data
        """
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                # Remove markdown headers
                value = re.sub(r'^#+\s+', '', value, flags=re.MULTILINE)
                # Remove bold/italic markers
                value = re.sub(r'\*\*([^*]+)\*\*', r'\1', value)
                value = re.sub(r'__([^_]+)__', r'\1', value)
                value = re.sub(r'\*([^*]+)\*', r'\1', value)
                value = re.sub(r'_([^_]+)_', r'\1', value)
                # Remove code blocks
                value = re.sub(r'```[\s\S]*?```', '', value)
                value = re.sub(r'`([^`]+)`', r'\1', value)
                # Strip whitespace
                value = value.strip()
                sanitized[key] = value
            elif isinstance(value, dict):
                sanitized[key] = ResponseValidator.sanitize_response(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    ResponseValidator.sanitize_response(v) if isinstance(v, dict)
                    else v
                    for v in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized

    @staticmethod
    def validate_response(response_dict: Any) -> Tuple[bool, List[str]]:
        """
        Comprehensive response validation.
        
        Args:
            response_dict: Final EnterpriseResponse (or its dictionary form)
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Validation belongs at the enterprise boundary. Accept the model itself
        # so callers do not validate an intermediate agent payload that cannot
        # yet contain wrapper fields such as ``success`` and ``agent``.
        if isinstance(response_dict, EnterpriseResponse):
            response_dict = response_dict.model_dump(mode='python')
        
        # Validate JSON structure
        is_valid, structure_errors = ResponseValidator.validate_json_structure(response_dict)
        errors.extend(structure_errors)
        
        # Validate key fields
        if not isinstance(response_dict.get('result'), (dict, list)):
            errors.append("'result' field must be dict or list")
        
        if not isinstance(response_dict.get('success'), bool):
            errors.append("'success' field must be boolean")
        
        if 'agent' not in response_dict:
            errors.append("'agent' field is required")
        
        # Check for markdown in text fields
        for field in ['reasoning_summary']:
            if field in response_dict and isinstance(response_dict[field], str):
                is_clean, issues = ResponseValidator.validate_markdown_free(
                    response_dict[field]
                )
                if not is_clean:
                    errors.append(f"Field '{field}' contains markdown: {', '.join(issues)}")
        
        return len(errors) == 0, errors


# ============================================================================
# CONFIDENCE SCORING
# ============================================================================

class ConfidenceCalculator:
    """Calculates confidence scores based on multiple factors."""

    @staticmethod
    def calculate_confidence(
        retrieval_score: float,
        total_chunks: int,
        response_quality: float,
        has_citations: bool,
        retrieved_successfully: bool = True,
    ) -> Tuple[float, ConfidenceLevel, ConfidenceMetadata]:
        """
        Calculate overall confidence score from component factors.
        
        Weights:
        - Retrieval score: 40% (best chunk relevance)
        - Chunk count: 20% (normalized 0-1)
        - Response quality: 30% (inferred from LLM quality)
        - Citations: 10% (presence boost)
        
        Args:
            retrieval_score: Best retrieval score (0.0-1.0)
            total_chunks: Number of chunks retrieved
            response_quality: Quality assessment (0.0-1.0)
            has_citations: Whether citations were found
            retrieved_successfully: Whether retrieval succeeded
            
        Returns:
            Tuple of (confidence_score, confidence_level, metadata)
        """
        if not retrieved_successfully:
            return 0.2, ConfidenceLevel.VERY_LOW, ConfidenceMetadata(
                retrieval_score_component=0.0,
                chunk_count_component=0.0,
                response_quality_component=response_quality * 0.5,
                citation_presence_component=0.0,
                final_confidence_score=0.2,
                confidence_level=ConfidenceLevel.VERY_LOW,
            )
        
        # Normalize retrieval score (already 0-1)
        retrieval_component = retrieval_score * 0.40
        
        # Normalize chunk count (assume 5 is optimal, max out at 1.0)
        chunk_component = min(total_chunks / 10.0, 1.0) * 0.20
        
        # Response quality component
        quality_component = response_quality * 0.30
        
        # Citation presence bonus
        citation_component = (0.10 if has_citations else 0.0)
        
        # Calculate final score
        final_score = min(
            retrieval_component + chunk_component + quality_component + citation_component,
            1.0
        )
        
        # Determine confidence level
        if final_score < 0.30:
            level = ConfidenceLevel.VERY_LOW
        elif final_score < 0.50:
            level = ConfidenceLevel.LOW
        elif final_score < 0.70:
            level = ConfidenceLevel.MEDIUM
        elif final_score < 0.85:
            level = ConfidenceLevel.HIGH
        else:
            level = ConfidenceLevel.VERY_HIGH
        
        metadata = ConfidenceMetadata(
            retrieval_score_component=retrieval_component,
            chunk_count_component=chunk_component,
            response_quality_component=quality_component,
            citation_presence_component=citation_component,
            final_confidence_score=final_score,
            confidence_level=level,
        )
        
        return final_score, level, metadata

    @staticmethod
    def assess_response_quality(
        response_text: Optional[str],
        response_has_structure: bool = True,
    ) -> float:
        """
        Assess LLM response quality.
        
        Factors:
        - Non-empty response
        - Reasonable length
        - Proper structure
        
        Args:
            response_text: Response text to assess
            response_has_structure: Whether response has expected structure
            
        Returns:
            Quality score (0.0-1.0)
        """
        if not response_text:
            return 0.3
        
        text_length = len(response_text)
        
        # Score factors
        score = 0.0
        
        # Length assessment
        if text_length > 50:
            score += 0.4
        elif text_length > 20:
            score += 0.2
        
        # Structure assessment
        if response_has_structure:
            score += 0.4
        
        # Specificity check (presence of numbers, dates, etc.)
        if re.search(r'\d+', response_text):
            score += 0.2
        
        return min(score, 1.0)


# ============================================================================
# PROCESSING METRICS
# ============================================================================

class ProcessingTimeTracker:
    """Tracks and aggregates processing times."""

    def __init__(self):
        """Initialize tracker."""
        self.retrieval_time_ms: int = 0
        self.llm_time_ms: int = 0
        self.start_time: Optional[datetime] = None
        self.retrieval_start: Optional[datetime] = None

    def start_total(self) -> None:
        """Start total processing timer."""
        self.start_time = datetime.utcnow()

    def end_total(self) -> int:
        """End total processing timer and return elapsed ms."""
        if not self.start_time:
            return 0
        elapsed = (datetime.utcnow() - self.start_time).total_seconds() * 1000
        return int(elapsed)

    def add_retrieval_time(self, time_ms: int) -> None:
        """Add retrieval time."""
        self.retrieval_time_ms = max(self.retrieval_time_ms, time_ms)

    def add_llm_time(self, time_ms: int) -> None:
        """Add LLM execution time."""
        self.llm_time_ms = max(self.llm_time_ms, time_ms)

    def get_metrics(
        self,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
    ) -> ProcessingMetrics:
        """
        Get processing metrics.
        
        Args:
            input_tokens: LLM input tokens
            output_tokens: LLM output tokens
            
        Returns:
            ProcessingMetrics object
        """
        total_time = self.end_total()
        total_tokens = None
        if input_tokens is not None and output_tokens is not None:
            total_tokens = input_tokens + output_tokens
        
        return ProcessingMetrics(
            retrieval_time_ms=self.retrieval_time_ms,
            llm_time_ms=self.llm_time_ms,
            total_processing_time_ms=total_time,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )


# ============================================================================
# CITATION & RETRIEVAL METADATA BUILDERS
# ============================================================================

class CitationBuilder:
    """Builds citation objects from retrieval results."""

    @staticmethod
    def build_citation(
        chunk_id: str,
        parent_id: str,
        content: str,
        relevance_score: float,
        retrieval_method: str = "hybrid",
    ) -> Citation:
        """
        Build a Citation object.
        
        Args:
            chunk_id: FAISS chunk ID
            parent_id: Parent document ID
            content: Full chunk content
            relevance_score: Relevance score (0.0-1.0)
            retrieval_method: "semantic", "bm25", or "hybrid"
            
        Returns:
            Citation object
        """
        # Get first 200 chars as preview
        preview = content[:200] if content else ""
        
        return Citation(
            chunk_id=chunk_id,
            parent_id=parent_id,
            content_preview=preview,
            relevance_score=relevance_score,
            retrieval_method=retrieval_method,
        )

    @staticmethod
    def build_from_retrieval_result(
        retrieval_result: Dict[str, Any]
    ) -> List[Citation]:
        """
        Build citations from a retrieval result dictionary.
        
        Expected format from RetrievalAgent:
        {
            'chunks': [
                {
                    'chunk_id': '...',
                    'parent_id': '...',
                    'content': '...',
                    'relevance_score': 0.95,
                    'retrieval_method': 'semantic'
                }
            ]
        }
        
        Args:
            retrieval_result: Retrieval result dictionary
            
        Returns:
            List of Citation objects
        """
        citations = []
        
        chunks = retrieval_result.get('chunks', [])
        for chunk in chunks:
            chunk_metadata = chunk.get('metadata', {})
            scoring = chunk.get('_scoring', {})
            citation = CitationBuilder.build_citation(
                chunk_id=chunk.get('chunk_id') or chunk.get('child_id') or chunk.get('id', ''),
                parent_id=chunk.get('parent_id', ''),
                content=(
                    chunk.get('content') or chunk.get('parent_text') or
                    chunk_metadata.get('parent_text') or chunk.get('child_text', '')
                ),
                relevance_score=float(
                    chunk.get('relevance_score', scoring.get(
                        'combined_score', chunk_metadata.get('score', 0.0)
                    ))
                ),
                retrieval_method=chunk.get('retrieval_method', 'hybrid'),
            )
            citations.append(citation)
        
        return citations


class RetrievalMetadataBuilder:
    """Builds retrieval metadata objects."""

    @staticmethod
    def build_metadata(
        retrieval_time_ms: int,
        total_chunks: int,
        total_deduplicated: int,
        semantic_count: int,
        bm25_count: int,
        top_score: float,
        contract_id: Optional[str] = None,
    ) -> RetrievalMetadata:
        """
        Build RetrievalMetadata object.
        
        Args:
            retrieval_time_ms: Time taken for retrieval
            total_chunks: Total chunks before deduplication
            total_deduplicated: Total chunks after deduplication
            semantic_count: Number of semantic matches
            bm25_count: Number of BM25 matches
            top_score: Best retrieval score
            contract_id: Optional contract ID
            
        Returns:
            RetrievalMetadata object
        """
        return RetrievalMetadata(
            retrieval_time_ms=retrieval_time_ms,
            total_chunks_retrieved=total_chunks,
            total_chunks_deduplicated=total_deduplicated,
            semantic_match_count=semantic_count,
            bm25_match_count=bm25_count,
            top_retrieval_score=top_score,
            contract_id=contract_id,
        )

    @staticmethod
    def build_from_retrieval_result(
        retrieval_result: Dict[str, Any],
        contract_id: Optional[str] = None,
    ) -> RetrievalMetadata:
        """
        Build metadata from a retrieval result dictionary.
        
        Args:
            retrieval_result: Retrieval result from RetrievalAgent
            contract_id: Optional contract ID
            
        Returns:
            RetrievalMetadata object
        """
        nested_metadata = (
            retrieval_result.get('retrieval_metadata') or
            retrieval_result.get('metadata') or {}
        )
        chunks = retrieval_result.get('chunks', [])
        child_chunks = retrieval_result.get('child_chunks', [])

        total_chunks = retrieval_result.get(
            'total_chunks', nested_metadata.get(
                'total_chunks_retrieved', nested_metadata.get(
                    'retrieved_chunk_count', len(child_chunks) or len(chunks)
                )
            )
        )
        total_deduplicated = retrieval_result.get(
            'total_chunks_deduplicated', nested_metadata.get(
                'total_chunks_deduplicated', nested_metadata.get(
                    'deduplicated_chunk_count', len(chunks)
                )
            )
        )

        # A non-empty chunk list is direct retrieval evidence. This invariant
        # prevents zero chunk metadata while citations use those same chunks.
        if chunks:
            total_chunks = max(total_chunks, len(chunks))
            total_deduplicated = max(total_deduplicated, len(chunks))

        chunk_scores = [
            float(chunk.get('relevance_score', chunk.get('_scoring', {}).get(
                'combined_score', chunk.get('metadata', {}).get('score', 0.0)
            )))
            for chunk in chunks
        ]
        top_score = retrieval_result.get(
            'top_retrieval_score', nested_metadata.get(
                'top_retrieval_score', nested_metadata.get(
                    'retrieval_score', max(chunk_scores, default=0.0)
                )
            )
        )
        if chunk_scores:
            top_score = max(top_score, max(chunk_scores))

        semantic_count = retrieval_result.get(
            'semantic_match_count', nested_metadata.get(
                'semantic_match_count', nested_metadata.get('semantic_matches', 0)
            )
        )
        bm25_count = retrieval_result.get(
            'bm25_match_count', nested_metadata.get(
                'bm25_match_count', nested_metadata.get('bm25_matches', 0)
            )
        )
        semantic_count = max(semantic_count, sum(
            1 for chunk in chunks
            if chunk.get('_scoring', {}).get('semantic_score', 0.0) > 0
        ))
        bm25_count = max(bm25_count, sum(
            1 for chunk in chunks
            if chunk.get('_scoring', {}).get('keyword_score', 0.0) > 0
        ))

        return RetrievalMetadataBuilder.build_metadata(
            retrieval_time_ms=retrieval_result.get(
                'retrieval_time_ms', nested_metadata.get(
                    'retrieval_time_ms', nested_metadata.get('total_retrieval_time_ms', 0)
                )
            ),
            total_chunks=total_chunks,
            total_deduplicated=total_deduplicated,
            semantic_count=semantic_count,
            bm25_count=bm25_count,
            top_score=top_score,
            contract_id=contract_id,
        )


# ============================================================================
# RESPONSE WRAPPING & ERROR HANDLING
# ============================================================================

def create_error_response(
    agent: AgentType,
    error_code: ErrorCode,
    message: str,
    details: Optional[str] = None,
    field: Optional[str] = None,
    request_id: Optional[str] = None,
) -> EnterpriseErrorResponse:
    """
    Create a standardized error response.
    
    Args:
        agent: Which agent failed
        error_code: Standard error code
        message: User-friendly error message
        details: Additional error details
        field: Field that caused error (validation)
        request_id: Optional request ID for tracing
        
    Returns:
        EnterpriseErrorResponse object
    """
    return EnterpriseErrorResponse(
        agent=agent,
        timestamp=datetime.utcnow(),
        error=ErrorDetail(
            code=error_code,
            message=message,
            details=details,
            field=field,
        ),
        request_id=request_id or str(uuid.uuid4()),
    )


def wrap_agent_response(
    agent: AgentType,
    result: Dict[str, Any],
    retrieval_metadata: RetrievalMetadata,
    citations: List[Citation],
    confidence_score: float,
    confidence_level: ConfidenceLevel,
    confidence_breakdown: ConfidenceMetadata,
    processing_metrics: ProcessingMetrics,
    reasoning_summary: str,
    warnings: Optional[List[str]] = None,
    request_id: Optional[str] = None,
    contract_id: Optional[str] = None,
    model: str = settings.GEMINI_MODEL,
) -> EnterpriseResponse:
    """
    Wrap an agent response in the enterprise response format.
    
    Args:
        agent: Which agent produced the response
        result: Agent-specific result data
        retrieval_metadata: Metadata about retrieval
        citations: List of citations
        confidence_score: Overall confidence score
        confidence_level: Confidence classification
        confidence_breakdown: Detailed confidence breakdown
        processing_metrics: Processing time metrics
        reasoning_summary: Brief reasoning explanation
        warnings: Optional list of warnings
        request_id: Optional request ID for tracing
        contract_id: Optional source contract ID
        model: LLM model used
        
    Returns:
        EnterpriseResponse object
    """
    # Extract unique parent and chunk IDs
    source_parent_ids = list(set(c.parent_id for c in citations))
    source_chunk_ids = list(set(c.chunk_id for c in citations))
    
    return EnterpriseResponse(
        success=True,
        agent=agent,
        timestamp=datetime.utcnow(),
        model=model,
        confidence_score=confidence_score,
        confidence_level=confidence_level,
        processing_time_ms=processing_metrics.total_processing_time_ms,
        retrieval_metadata=retrieval_metadata,
        citations=citations,
        source_parent_ids=source_parent_ids,
        source_chunk_ids=source_chunk_ids,
        confidence_breakdown=confidence_breakdown,
        processing_metrics=processing_metrics,
        reasoning_summary=sanitize_reasoning_summary(reasoning_summary),
        warnings=[sanitize_warning_message(w) for w in (warnings or []) if sanitize_warning_message(w)],
        result=result,
        request_id=request_id or str(uuid.uuid4()),
        contract_id=contract_id,
    )
