from typing import Dict, Any, Optional
import time

from langchain.prompts import PromptTemplate
from app.services.llm_service import LLMService

from app.agents.agent_utils import safe_parse_json
from app.agents.prompts.summary_prompt import SUMMARY_PROMPT
from app.agents.retrieval_agent import retrieve as retrieve_contract_context
from app.schemas.enterprise_schemas import AgentType
from app.utils.agent_wrapper import enterprise_agent_wrapper, AgentResponseBuilder
from app.utils.enterprise_utils import sanitize_reasoning_summary, sanitize_warning_message, log_exception_context


@enterprise_agent_wrapper(AgentType.SUMMARY)
def run_summary_agent(
    contract_id: str,
    query: str = "summary",
    top_k: int = 6,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extract executive summary from contract.

    Args:
        contract_id: Contract identifier
        query: Search query (default: "summary")
        top_k: Number of top chunks to retrieve
        request_id: Optional request ID for tracing

    Returns:
        Enterprise response with summary, obligations, dates, risks,
        critical_clauses, and business_impact
    """
    retrieval_start = time.time()
    # Use a targeted semantic query instead of a wildcard to ensure relevant chunks are pulled
    effective_query = "contract term, contract value, governing law, jurisdiction, parties" if query == "*" or query == "summary" else query
    retrieval = retrieve_contract_context(contract_id, effective_query, top_k=top_k)
    retrieval_time_ms = int((time.time() - retrieval_start) * 1000)

    total_chunks = retrieval.get("total_chunks", 0)
    contract_text = retrieval.get("context", "")

    if total_chunks == 0 or not contract_text.strip():
        return AgentResponseBuilder.success(
            result={
                "summary": "Insufficient contract context was retrieved to provide a reliable answer.",
                "key_obligations": [],
                "important_dates": [],
                "key_risks": [],
                "critical_clauses": [],
                "business_impact": "Not explicitly stated in the contract.",
            },
            retrieval_result=retrieval,
            reasoning_summary="Insufficient contract context was retrieved to provide a reliable answer.",
            retrieval_time_ms=retrieval_time_ms,
        )

    prompt = PromptTemplate(
        input_variables=["contract_text", "query"],
        template=SUMMARY_PROMPT,
    )

    llm_start = time.time()
    try:
        raw, token_usage = LLMService.invoke(prompt, {
            "contract_text": contract_text,
            "query": query
        }, require_json=True)
    except Exception as exc:
        log_exception_context("summary", exc)
        return AgentResponseBuilder.success(
            result={
                "summary": contract_text[:500],
                "key_obligations": [],
                "important_dates": [],
                "key_risks": [],
                "critical_clauses": [],
                "business_impact": "Not explicitly stated in the contract.",
            },
            retrieval_result=retrieval,
            reasoning_summary=sanitize_reasoning_summary(str(exc)),
            retrieval_time_ms=retrieval_time_ms,
            llm_time_ms=int((time.time() - llm_start) * 1000),
            warnings=[sanitize_warning_message(str(exc))],
        )
    llm_time_ms = int((time.time() - llm_start) * 1000)

    parsed = safe_parse_json(raw, {})
    if isinstance(parsed, str):
        parsed = safe_parse_json(parsed, {})

    if isinstance(parsed, dict) and parsed:
        def _normalize_list(value: Any) -> list:
            if isinstance(value, str):
                parsed_value = safe_parse_json(value, [])
                if isinstance(parsed_value, list):
                    return parsed_value
                if parsed_value:
                    return [parsed_value]
                return []
            if isinstance(value, list):
                return value
            if value is None:
                return []
            return [value]

        summary = parsed.get("summary") or (raw.strip() or contract_text[:500])
        if isinstance(summary, str):
            words = [word for word in summary.split() if word]
            if len(words) > 300:
                summary = " ".join(words[:300])

        result = {
            "summary": summary if isinstance(summary, str) else str(summary),
            "key_obligations": _normalize_list(parsed.get("key_obligations")),
            "important_dates": _normalize_list(parsed.get("important_dates")),
            "key_risks": _normalize_list(parsed.get("key_risks")),
            "critical_clauses": _normalize_list(parsed.get("critical_clauses")),
            "business_impact": parsed.get("business_impact") or "Not explicitly stated in the contract.",
        }

        reasoning_summary = parsed.get("reasoning_summary") or ""
        if not isinstance(reasoning_summary, str) or not reasoning_summary.strip():
            reasoning_summary = (
                f"Extracted an executive summary with {len(result['key_obligations'])} obligations, "
                f"{len(result['important_dates'])} dates, and {len(result['key_risks'])} risks."
            )

        return AgentResponseBuilder.success(
            result=result,
            retrieval_result=retrieval,
            reasoning_summary=reasoning_summary,
            retrieval_time_ms=retrieval_time_ms,
            llm_time_ms=llm_time_ms,
            **token_usage,
        )

    # Fallback: wrap raw text in expected structure
    return AgentResponseBuilder.success(
        result={
            "summary": raw.strip() if raw else contract_text[:500],
            "key_obligations": [],
            "important_dates": [],
            "key_risks": [],
            "critical_clauses": [],
            "business_impact": "Not explicitly stated in the contract.",
        },
        retrieval_result=retrieval,
        reasoning_summary="Summary extracted from LLM response",
        retrieval_time_ms=retrieval_time_ms,
        llm_time_ms=llm_time_ms,
        **token_usage,
        warnings=["Response parsing returned fallback structure"],
    )
