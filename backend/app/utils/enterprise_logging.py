"""
Enterprise Logging System

Provides structured logging for all agent executions with comprehensive
tracking of metrics, performance, and events.
"""

import logging
import json
from typing import Any, Dict, Optional
from datetime import datetime
from enum import Enum

from app.schemas.enterprise_schemas import AgentType, ConfidenceLevel


class LogLevel(str, Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AgentExecutionLogger:
    """Specialized logger for agent executions."""

    def __init__(self, agent_name: str):
        """
        Initialize agent logger.
        
        Args:
            agent_name: Name of the agent being logged
        """
        self.agent_name = agent_name
        self.logger = logging.getLogger(f"legalgpt.agent.{agent_name}")
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Configure logging if not already configured."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG)

    def log_execution_start(
        self,
        contract_id: str,
        model: str,
        request_id: Optional[str] = None,
    ) -> None:
        """
        Log the start of agent execution.
        
        Args:
            contract_id: Contract being processed
            model: LLM model being used
            request_id: Optional request ID for tracing
        """
        message = (
            f"[{self.agent_name}] Execution started | "
            f"contract_id={contract_id} | "
            f"model={model}"
        )
        if request_id:
            message += f" | request_id={request_id}"
        self.logger.info(message)

    def log_retrieval(
        self,
        retrieval_time_ms: int,
        total_chunks: int,
        top_score: float,
    ) -> None:
        """
        Log retrieval completion.
        
        Args:
            retrieval_time_ms: Time taken for retrieval
            total_chunks: Number of chunks retrieved
            top_score: Best retrieval score
        """
        message = (
            f"[{self.agent_name}] Retrieval completed | "
            f"retrieval_time_ms={retrieval_time_ms} | "
            f"total_chunks={total_chunks} | "
            f"top_score={top_score:.4f}"
        )
        self.logger.info(message)

    def log_llm_call(
        self,
        llm_time_ms: int,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
    ) -> None:
        """
        Log LLM model call.
        
        Args:
            llm_time_ms: Time taken for LLM inference
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        """
        message = f"[{self.agent_name}] LLM call completed | llm_time_ms={llm_time_ms}"
        if input_tokens:
            message += f" | input_tokens={input_tokens}"
        if output_tokens:
            message += f" | output_tokens={output_tokens}"
        self.logger.info(message)

    def log_execution_complete(
        self,
        total_time_ms: int,
        confidence_score: float,
        confidence_level: ConfidenceLevel,
        success: bool = True,
    ) -> None:
        """
        Log successful execution completion.
        
        Args:
            total_time_ms: Total processing time
            confidence_score: Final confidence score
            confidence_level: Confidence classification
            success: Whether execution was successful
        """
        status = "SUCCESS" if success else "PARTIAL"
        message = (
            f"[{self.agent_name}] Execution {status} | "
            f"total_time_ms={total_time_ms} | "
            f"confidence_score={confidence_score:.4f} | "
            f"confidence_level={confidence_level.value}"
        )
        self.logger.info(message)

    def log_error(
        self,
        error_message: str,
        error_type: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an error during execution.
        
        Args:
            error_message: Error message
            error_type: Type of error
            details: Optional error details dictionary
        """
        message = (
            f"[{self.agent_name}] ERROR | "
            f"error_type={error_type} | "
            f"message={error_message}"
        )
        if details:
            message += f" | details={json.dumps(details)}"
        self.logger.error(message)

    def log_warning(self, warning_message: str) -> None:
        """
        Log a non-fatal warning.
        
        Args:
            warning_message: Warning message
        """
        message = f"[{self.agent_name}] WARNING | message={warning_message}"
        self.logger.warning(message)

    def log_validation_failure(
        self,
        validation_errors: list,
    ) -> None:
        """
        Log validation failures.
        
        Args:
            validation_errors: List of validation error messages
        """
        message = (
            f"[{self.agent_name}] Validation failed | "
            f"errors={json.dumps(validation_errors)}"
        )
        self.logger.warning(message)


class ExecutionMetricsLogger:
    """Logs comprehensive execution metrics."""

    @staticmethod
    def log_agent_metrics(
        agent: AgentType,
        contract_id: str,
        model: str,
        total_latency_ms: int,
        retrieved_chunks: int,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        confidence: float = 0.0,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """
        Log comprehensive agent execution metrics.
        
        Args:
            agent: Agent that executed
            contract_id: Contract processed
            model: LLM model used
            total_latency_ms: Total latency
            retrieved_chunks: Number of chunks retrieved
            input_tokens: Input tokens used
            output_tokens: Output tokens used
            confidence: Confidence score
            success: Whether execution succeeded
            error: Error message if failed
        """
        logger = logging.getLogger("legalgpt.metrics")
        
        metrics = {
            "agent": agent.value,
            "contract_id": contract_id,
            "model": model,
            "timestamp": datetime.utcnow().isoformat(),
            "latency_ms": total_latency_ms,
            "retrieved_chunks": retrieved_chunks,
            "confidence": confidence,
            "success": success,
        }
        
        if input_tokens:
            metrics["input_tokens"] = input_tokens
        if output_tokens:
            metrics["output_tokens"] = output_tokens
        if error:
            metrics["error"] = error
        
        logger.info(f"AGENT_METRICS: {json.dumps(metrics)}")


def get_agent_logger(agent_name: str) -> AgentExecutionLogger:
    """
    Get or create an agent logger.
    
    Args:
        agent_name: Name of the agent
        
    Returns:
        AgentExecutionLogger instance
    """
    return AgentExecutionLogger(agent_name)
