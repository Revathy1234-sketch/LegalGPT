"""
Agent Wrapper Utilities

Provides decorators and wrapper functions to standardize agent execution,
response formatting, and error handling.
"""

import time
from typing import Any, Callable, Dict, Optional, TypeVar
from functools import wraps

from app.core.config import settings
from app.schemas.enterprise_schemas import (
    AgentType,
    ConfidenceLevel,
    EnterpriseResponse,
    ErrorCode,
)
from app.utils.enterprise_utils import (
    CitationBuilder,
    ConfidenceCalculator,
    ProcessingTimeTracker,
    RetrievalMetadataBuilder,
    ResponseValidator,
    create_error_response,
    sanitize_reasoning_summary,
    sanitize_warning_message,
    wrap_agent_response,
)
from app.utils.enterprise_logging import (
    AgentExecutionLogger,
    ExecutionMetricsLogger,
)


# Type variables
T = TypeVar('T', bound=Callable)


def enterprise_agent_wrapper(
    agent_type: AgentType,
    model: str = settings.NVIDIA_MODEL,
) -> Callable:
    """
    Decorator to wrap agent functions with enterprise response standardization.
    
    Handles:
    - Response validation
    - Confidence scoring
    - Citation building
    - Metric tracking
    - Error handling
    - Logging
    
    Agent functions should return:
    {
        'result': {...},  # agent-specific result
        'retrieval_result': {...},  # from retrieve_contract_context
        'reasoning_summary': str,
    }
    
    Or on error, raise an exception.
    
    Args:
        agent_type: Which agent this is
        model: LLM model used
        
    Returns:
        Decorated function
    """
    def decorator(func: T) -> T:
        @wraps(func)
        def wrapper(
            *args,
            **kwargs
        ) -> EnterpriseResponse:
            # Initialize tracking
            logger = AgentExecutionLogger(agent_type.value)
            tracker = ProcessingTimeTracker()
            tracker.start_total()
            
            # Extract parameters
            contract_id = kwargs.get('contract_id') or (
                args[0] if args else 'unknown'
            )
            request_id = kwargs.get('request_id')
            
            logger.log_execution_start(contract_id, model, request_id)
            
            try:
                # Execute agent function
                agent_result = func(*args, **kwargs)
                
                # Extract components from result
                result_data = agent_result.get('result', {})
                retrieval_data = agent_result.get('retrieval_result', {})
                reasoning = sanitize_reasoning_summary(
                    agent_result.get('reasoning_summary', '')
                )
                retrieval_time_ms = agent_result.get('retrieval_time_ms', 0)
                llm_time_ms = agent_result.get('llm_time_ms', 0)
                input_tokens = agent_result.get('input_tokens')
                output_tokens = agent_result.get('output_tokens')
                warnings = [
                    sanitize_warning_message(warning)
                    for warning in agent_result.get('warnings', [])
                ]
                
                # Track times
                tracker.add_retrieval_time(retrieval_time_ms)
                tracker.add_llm_time(llm_time_ms)
                
                logger.log_retrieval(
                    retrieval_time_ms,
                    retrieval_data.get('total_chunks', 0),
                    retrieval_data.get('top_retrieval_score', 0.0),
                )
                logger.log_llm_call(llm_time_ms, input_tokens, output_tokens)
                
                # Sanitize response
                result_data = ResponseValidator.sanitize_response(result_data)
                
                # Build citations
                citations = CitationBuilder.build_from_retrieval_result(
                    retrieval_data
                )
                
                # Build retrieval metadata
                retrieval_metadata = RetrievalMetadataBuilder.build_from_retrieval_result(
                    retrieval_data,
                    contract_id=contract_id,
                )
                
                # Calculate confidence
                confidence_score, confidence_level, confidence_breakdown = (
                    ConfidenceCalculator.calculate_confidence(
                        retrieval_score=retrieval_data.get('top_retrieval_score', 0.0),
                        total_chunks=retrieval_data.get('total_chunks', 0),
                        response_quality=ConfidenceCalculator.assess_response_quality(
                            reasoning
                        ),
                        has_citations=len(citations) > 0,
                        retrieved_successfully=len(citations) > 0,
                    )
                )
                
                # Get processing metrics
                metrics = tracker.get_metrics(input_tokens, output_tokens)
                
                # Create response
                response = wrap_agent_response(
                    agent=agent_type,
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
                    contract_id=contract_id,
                    model=model,
                )

                # Validate the completed enterprise wrapper, not the intermediate
                # agent-specific result dictionary.
                is_valid, validation_errors = ResponseValidator.validate_response(
                    response
                )
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
                    agent=agent_type,
                    contract_id=contract_id,
                    model=model,
                    total_latency_ms=metrics.total_processing_time_ms,
                    retrieved_chunks=retrieval_metadata.total_chunks_deduplicated,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    confidence=confidence_score,
                    success=True,
                )
                
                return response
            
            except Exception as e:
                # Handle errors
                error_msg = str(e)
                error_type = type(e).__name__
                
                logger.log_error(error_msg, error_type)
                
                # Log failed metrics
                ExecutionMetricsLogger.log_agent_metrics(
                    agent=agent_type,
                    contract_id=contract_id,
                    model=model,
                    total_latency_ms=tracker.end_total(),
                    retrieved_chunks=0,
                    confidence=0.0,
                    success=False,
                    error=error_msg,
                )
                
                # Return error response
                return create_error_response(
                    agent=agent_type,
                    error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                    message=f"Agent execution failed: {error_msg}",
                    details=error_type,
                    request_id=request_id or 'unknown',
                )
        
        return wrapper  # type: ignore
    
    return decorator


class AgentResponseBuilder:
    """Helper to build standardized agent responses."""

    @staticmethod
    def success(
        result: Dict[str, Any],
        retrieval_result: Dict[str, Any],
        reasoning_summary: str,
        retrieval_time_ms: int = 0,
        llm_time_ms: int = 0,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        warnings: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Build a successful agent response.
        
        Args:
            result: Agent-specific result data
            retrieval_result: Result from retrieve_contract_context
            reasoning_summary: Explanation of reasoning
            retrieval_time_ms: Time taken for retrieval
            llm_time_ms: Time taken for LLM call
            input_tokens: Optional input token count
            output_tokens: Optional output token count
            total_tokens: Optional total token count
            warnings: Optional list of warnings
            
        Returns:
            Response dict for wrapper
        """
        return {
            'result': result,
            'retrieval_result': retrieval_result,
            'reasoning_summary': reasoning_summary,
            'retrieval_time_ms': retrieval_time_ms,
            'llm_time_ms': llm_time_ms,
            'input_tokens': input_tokens if input_tokens is not None else 0,
            'output_tokens': output_tokens if output_tokens is not None else 0,
            'total_tokens': total_tokens if total_tokens is not None else (
                input_tokens + output_tokens
                if input_tokens is not None and output_tokens is not None
                else 0
            ),
            'warnings': warnings or [],
        }
