from typing import Dict, Any, Optional
import time
import uuid
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

def is_valid_uuid(val: str) -> bool:
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, TypeError):
        return False

from langchain.prompts import PromptTemplate
from app.services.llm_service import LLMService

from app.agents.agent_utils import safe_parse_json
from app.agents.prompts.comparison_prompt import COMPARISON_PROMPT
from app.agents.retrieval_agent import retrieve as retrieve_contract_context
from app.schemas.enterprise_schemas import AgentType, ErrorCode
from app.utils.agent_wrapper import enterprise_agent_wrapper, AgentResponseBuilder
from app.utils.enterprise_utils import sanitize_reasoning_summary, sanitize_warning_message, log_exception_context


def _run_comparison_internal(
    contract_a_id: str,
    contract_b_id: str,
    top_k: int = 6,
) -> Dict[str, Any]:
    """Internal comparison logic."""
    # Retrieve Contract A
    retrieval_a_start = time.time()
    try:
        retrieval_a = retrieve_contract_context(contract_a_id, "*", top_k=top_k)
    except Exception as e:
        logger.warning("Failed to retrieve contract A context: %s", e)
        retrieval_a = {"chunks": [], "context": "", "sources": [], "metadata": {}}
    retrieval_a_time_ms = int((time.time() - retrieval_a_start) * 1000)

    contract_a_text = retrieval_a.get("context", "")
    sources_a = retrieval_a.get("sources", [])
    metadata_a = retrieval_a.get("metadata", {})

    # Retrieve Contract B
    retrieval_b_start = time.time()
    try:
        retrieval_b = retrieve_contract_context(contract_b_id, "*", top_k=top_k)
    except Exception as e:
        logger.warning("Failed to retrieve contract B context: %s", e)
        retrieval_b = {"chunks": [], "context": "", "sources": [], "metadata": {}}
    retrieval_b_time_ms = int((time.time() - retrieval_b_start) * 1000)

    contract_b_text = retrieval_b.get("context", "")
    sources_b = retrieval_b.get("sources", [])
    # Combined retrieval metadata (use max times and combine results)
    combined_retrieval = {
        'chunks': retrieval_a.get('chunks', []) + retrieval_b.get('chunks', []),
        "context": contract_a_text + "\n" + contract_b_text,
        "sources": sources_a + sources_b,
        "metadata": metadata_a,
        "retrieval_time_ms": max(retrieval_a_time_ms, retrieval_b_time_ms),
        "total_chunks": retrieval_a.get("total_chunks", 0) + retrieval_b.get("total_chunks", 0),
        "total_chunks_deduplicated": (
            retrieval_a.get("total_chunks_deduplicated", 0) +
            retrieval_b.get("total_chunks_deduplicated", 0)
        ),
        "semantic_match_count": (
            retrieval_a.get("semantic_match_count", 0) +
            retrieval_b.get("semantic_match_count", 0)
        ),
        "bm25_match_count": (
            retrieval_a.get("bm25_match_count", 0) +
            retrieval_b.get("bm25_match_count", 0)
        ),
        "top_retrieval_score": max(
            retrieval_a.get("top_retrieval_score", 0.0),
            retrieval_b.get("top_retrieval_score", 0.0)
        ),
    }

    # If either contract is empty
    if not contract_a_text.strip() or not contract_b_text.strip():
        return {
            'result': {
                "similarities": [],
                "differences": [],
                "missing_clauses": [],
                "risk_differences": [],
                "summary": "One or both contracts could not be retrieved."
            },
            'retrieval_result': combined_retrieval,
            'reasoning_summary': "Retrieval returned empty context",
            'retrieval_time_ms': combined_retrieval['retrieval_time_ms'],
        }

    combined = "\n".join([
        "--- CONTRACT A ---",
        contract_a_text,
        "--- CONTRACT B ---",
        contract_b_text,
    ])

    prompt = PromptTemplate(
        input_variables=["contract_text"],
        template=COMPARISON_PROMPT,
    )

    llm_start = time.time()
    try:
        raw, token_usage = LLMService.invoke(prompt, {"contract_text": combined})
    except Exception as exc:
        log_exception_context("comparison", exc)
        return {
            'result': {"similarities": [], "differences": [], "missing_clauses": [], "risk_differences": [], "summary": ""},
            'retrieval_result': combined_retrieval,
            'reasoning_summary': sanitize_reasoning_summary(str(exc)),
            'retrieval_time_ms': combined_retrieval['retrieval_time_ms'],
            'llm_time_ms': int((time.time() - llm_start) * 1000),
            'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0,
            'warnings': [sanitize_warning_message(str(exc))],
        }
    llm_time_ms = int((time.time() - llm_start) * 1000)

    parsed = safe_parse_json(raw, {})

    if isinstance(parsed, dict) and parsed:
        # Ensure required fields exist
        if "similarities" not in parsed:
            parsed["similarities"] = []
        if "differences" not in parsed:
            parsed["differences"] = []
        if "missing_clauses" not in parsed:
            parsed["missing_clauses"] = []
        if "risk_differences" not in parsed:
            parsed["risk_differences"] = []
        if "summary" not in parsed:
            parsed["summary"] = ""
        
        return {
            'result': parsed,
            'retrieval_result': combined_retrieval,
            'reasoning_summary': "Comparison extracted from both contracts",
            'retrieval_time_ms': combined_retrieval['retrieval_time_ms'],
            'llm_time_ms': llm_time_ms,
            **token_usage,
        }

    # Fallback
    return {
        'result': {
            "similarities": [],
            "differences": [],
            "missing_clauses": [],
            "risk_differences": [],
            "summary": raw.strip() if raw else ""
        },
        'retrieval_result': combined_retrieval,
        'reasoning_summary': "Comparison returned structure",
        'retrieval_time_ms': combined_retrieval['retrieval_time_ms'],
        'llm_time_ms': llm_time_ms,
        **token_usage,
        'warnings': ["Response parsing returned fallback structure"],
    }


def run_comparison_agent(
    contract_a_id: str,
    contract_b_id: str,
    top_k: int = 6,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compare two contracts.
    
    Note: This function is wrapped separately from the enterprise wrapper
    because it takes two contract IDs rather than one.
    
    Args:
        contract_a_id: First contract identifier
        contract_b_id: Second contract identifier
        top_k: Number of top chunks to retrieve per contract
        request_id: Optional request ID for tracing
        
    Returns:
        Enterprise response with comparison analysis
    """
    # Import here to avoid circular imports
    from app.utils.enterprise_logging import AgentExecutionLogger, ExecutionMetricsLogger
    from app.utils.enterprise_utils import (
        CitationBuilder,
        ConfidenceCalculator,
        ProcessingTimeTracker,
        RetrievalMetadataBuilder,
        ResponseValidator,
        create_error_response,
        wrap_agent_response,
    )
    
    # Initialize tracking
    logger = AgentExecutionLogger(AgentType.COMPARISON.value)
    tracker = ProcessingTimeTracker()
    tracker.start_total()
    
    # Validate UUID format
    if not is_valid_uuid(contract_a_id) or not is_valid_uuid(contract_b_id):
        return create_error_response(
            agent=AgentType.COMPARISON,
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Invalid contract UUID format provided.",
            details="One or both contract IDs are not valid UUIDs.",
            request_id=request_id or 'unknown'
        )

    # Log start
    logger.log_execution_start(f"{contract_a_id} vs {contract_b_id}", settings.NVIDIA_MODEL, request_id)

    # Check if same contract
    if contract_a_id == contract_b_id:
        logger.info("[COMPARISON] Same contract supplied. Shortcut path.")
        result_data = {
            "similarities": ["Identical contract content."],
            "differences": [],
            "missing_clauses": [],
            "risk_differences": [],
            "summary": "Same contract supplied."
        }
        metrics = tracker.get_metrics()
        from app.schemas.enterprise_schemas import ConfidenceLevel, ProcessingMetrics, RetrievalMetadata, ConfidenceMetadata
        retrieval_metadata = RetrievalMetadata(
            retrieval_time_ms=0,
            total_chunks_retrieved=0,
            total_chunks_deduplicated=0,
            semantic_match_count=0,
            bm25_match_count=0,
            top_retrieval_score=1.0,
            contract_id=f"{contract_a_id},{contract_b_id}"
        )
        return wrap_agent_response(
            agent=AgentType.COMPARISON,
            result=result_data,
            retrieval_metadata=retrieval_metadata,
            citations=[],
            confidence_score=1.0,
            confidence_level=ConfidenceLevel.VERY_HIGH,
            confidence_breakdown=ConfidenceMetadata(
                retrieval_score_component=0.4,
                chunk_count_component=0.2,
                response_quality_component=0.3,
                citation_presence_component=0.1,
                final_confidence_score=1.0,
                confidence_level=ConfidenceLevel.VERY_HIGH
            ),
            processing_metrics=metrics,
            reasoning_summary="Same contract supplied shortcut validation.",
            warnings=[],
            request_id=request_id,
            contract_id=f"{contract_a_id},{contract_b_id}"
        )
    
    try:
        # Execute comparison
        agent_result = _run_comparison_internal(contract_a_id, contract_b_id, top_k)
        
        # Extract components
        result_data = agent_result.get('result', {})
        retrieval_data = agent_result.get('retrieval_result', {})
        reasoning = agent_result.get('reasoning_summary', '')
        retrieval_time_ms = agent_result.get('retrieval_time_ms', 0)
        llm_time_ms = agent_result.get('llm_time_ms', 0)
        warnings = agent_result.get('warnings', [])
        
        # Track times
        tracker.add_retrieval_time(retrieval_time_ms)
        tracker.add_llm_time(llm_time_ms)
        
        logger.log_retrieval(
            retrieval_time_ms,
            retrieval_data.get('total_chunks', 0),
            retrieval_data.get('top_retrieval_score', 0.0),
        )
        logger.log_llm_call(llm_time_ms)
        
        # Sanitize response
        result_data = ResponseValidator.sanitize_response(result_data)
        
        # Build citations
        citations = CitationBuilder.build_from_retrieval_result(retrieval_data)
        
        # Build retrieval metadata
        retrieval_metadata = RetrievalMetadataBuilder.build_from_retrieval_result(retrieval_data)
        
        # Calculate confidence
        confidence_score, confidence_level, confidence_breakdown = (
            ConfidenceCalculator.calculate_confidence(
                retrieval_score=retrieval_data.get('top_retrieval_score', 0.0),
                total_chunks=retrieval_data.get('total_chunks', 0),
                response_quality=ConfidenceCalculator.assess_response_quality(reasoning),
                has_citations=len(citations) > 0,
                retrieved_successfully=len(citations) > 0,
            )
        )
        
        # Get processing metrics
        metrics = tracker.get_metrics()
        
        # Create response
        response = wrap_agent_response(
            agent=AgentType.COMPARISON,
            result=result_data,
            retrieval_metadata=retrieval_metadata,
            citations=citations,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            confidence_breakdown=confidence_breakdown,
            processing_metrics=metrics,
            reasoning_summary=reasoning,
            warnings=warnings,
            request_id=request_id,
            contract_id=f"{contract_a_id},{contract_b_id}",
        )
        
        # Validate the completed enterprise wrapper, not the intermediate
        # comparison result dictionary.
        is_valid, validation_errors = ResponseValidator.validate_response(response)
        if not is_valid:
            logger.log_validation_failure(validation_errors)
            response.warnings.extend(validation_errors)

        # Log completion
        logger.log_execution_complete(
            metrics.total_processing_time_ms,
            confidence_score,
            confidence_level,
        )
        
        # Log metrics
        ExecutionMetricsLogger.log_agent_metrics(
            agent=AgentType.COMPARISON,
            contract_id=f"{contract_a_id},{contract_b_id}",
            model=settings.NVIDIA_MODEL,
            total_latency_ms=metrics.total_processing_time_ms,
            retrieved_chunks=retrieval_metadata.total_chunks_deduplicated,
            confidence=confidence_score,
            success=True,
        )
        
        return response
    
    except Exception as e:
        # Handle errors
        error_msg = str(e)
        error_type = type(e).__name__
        
        logger.log_error(error_msg, error_type)
        
        ExecutionMetricsLogger.log_agent_metrics(
            agent=AgentType.COMPARISON,
            contract_id=f"{contract_a_id},{contract_b_id}",
            model=settings.NVIDIA_MODEL,
            total_latency_ms=tracker.end_total(),
            retrieved_chunks=0,
            confidence=0.0,
            success=False,
            error=error_msg,
        )
        
        return create_error_response(
            agent=AgentType.COMPARISON,
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            message=f"Agent execution failed: {error_msg}",
            details=error_type,
            request_id=request_id or 'unknown',
        )
