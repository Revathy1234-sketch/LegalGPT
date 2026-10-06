from typing import Dict, Any, Optional
import time

from langchain.prompts import PromptTemplate
from app.services.llm_service import LLMService

from app.agents.agent_utils import safe_parse_json
from app.agents.prompts.negotiation_prompt import NEGOTIATION_PROMPT
from app.agents.retrieval_agent import retrieve as retrieve_contract_context
from app.schemas.enterprise_schemas import AgentType
from app.utils.agent_wrapper import enterprise_agent_wrapper, AgentResponseBuilder
from app.utils.enterprise_utils import sanitize_reasoning_summary, sanitize_warning_message, log_exception_context


@enterprise_agent_wrapper(AgentType.NEGOTIATION)
def run_negotiation_agent(
    contract_id: str,
    top_k: int = 6,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate negotiation strategies and recommendations.

    Args:
        contract_id: Contract identifier
        top_k: Number of top chunks to retrieve
        request_id: Optional request ID for tracing

    Returns:
        Enterprise response with negotiation analysis
    """
    retrieval_start = time.time()
    retrieval = retrieve_contract_context(contract_id, "*", top_k=top_k)
    retrieval_time_ms = int((time.time() - retrieval_start) * 1000)

    total_chunks = retrieval.get("total_chunks", 0)
    contract_text = retrieval.get("context", "")

    if total_chunks == 0 or not contract_text.strip():
        return AgentResponseBuilder.success(
            result={
                "overall_risk_score": 0,
                "overall_risk_level": "unknown",
                "executive_summary": "Insufficient contract context was retrieved to provide a reliable answer.",
                "negotiation_suggestions": [],
                "priority_actions": []
            },
            retrieval_result=retrieval,
            reasoning_summary="Insufficient contract context was retrieved to provide a reliable answer.",
            retrieval_time_ms=retrieval_time_ms,
        )

    prompt = PromptTemplate(
        input_variables=["contract_text"],
        template=NEGOTIATION_PROMPT,
    )

    llm_start = time.time()
    try:
        raw, token_usage = LLMService.invoke(prompt, {"contract_text": contract_text}, require_json=True)
    except Exception as exc:
        log_exception_context("negotiation", exc)
        return AgentResponseBuilder.success(
            result={"overall_risk_score": 0, "overall_risk_level": "unknown", "executive_summary": "", "negotiation_suggestions": [], "priority_actions": []},
            retrieval_result=retrieval, reasoning_summary=sanitize_reasoning_summary(str(exc)),
            retrieval_time_ms=retrieval_time_ms,
            llm_time_ms=int((time.time() - llm_start) * 1000), warnings=[sanitize_warning_message(str(exc))],
        )
    llm_time_ms = int((time.time() - llm_start) * 1000)

    parsed = safe_parse_json(raw, {})
    if not isinstance(parsed, dict) or not parsed:
        parsed = {
            "overall_risk_score": 0,
            "overall_risk_level": "unknown",
            "executive_summary": raw.strip() if raw else "",
            "negotiation_suggestions": [],
            "priority_actions": []
        }

    # Ensure required fields exist
    if "overall_risk_score" not in parsed:
        parsed["overall_risk_score"] = 0
    if "overall_risk_level" not in parsed:
        parsed["overall_risk_level"] = "unknown"
    if "executive_summary" not in parsed:
        parsed["executive_summary"] = ""
    if "negotiation_suggestions" not in parsed:
        parsed["negotiation_suggestions"] = []
    if "priority_actions" not in parsed:
        parsed["priority_actions"] = []

    if isinstance(parsed["negotiation_suggestions"], str):
        parsed["negotiation_suggestions"] = [{"suggestion": parsed["negotiation_suggestions"]}] if parsed["negotiation_suggestions"].strip() else []
    elif isinstance(parsed["negotiation_suggestions"], list):
        parsed["negotiation_suggestions"] = [
            {"suggestion": item} if isinstance(item, str) else item
            for item in parsed["negotiation_suggestions"]
        ]
    else:
        parsed["negotiation_suggestions"] = []

    if isinstance(parsed["priority_actions"], str):
        parsed["priority_actions"] = [parsed["priority_actions"]] if parsed["priority_actions"].strip() else []
    elif not isinstance(parsed["priority_actions"], list):
        parsed["priority_actions"] = []

    # NOTE: We intentionally do NOT generate hardcoded fallback suggestions.
    # If the LLM returns empty suggestions, we return an empty list rather
    # than fabricating generic advice that is not grounded in the contract text.
    # This follows the "prefer omission over hallucination" principle.

    warnings = []
    if "warnings" in parsed:
        warnings = parsed.get("warnings", [])
    elif not parsed.get("negotiation_suggestions"):
        warnings = ["No negotiation suggestions were generated from the contract text"]

    return AgentResponseBuilder.success(
        result=parsed,
        retrieval_result=retrieval,
        reasoning_summary="Negotiation analysis processed successfully",
        retrieval_time_ms=retrieval_time_ms,
        llm_time_ms=llm_time_ms,
        **token_usage,
        warnings=warnings,
    )
