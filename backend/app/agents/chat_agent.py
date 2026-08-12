from typing import Dict, Any, Optional
import time

from langchain.prompts import PromptTemplate
from app.services.llm_service import LLMService

from app.agents.agent_utils import safe_parse_json
from app.agents.prompts.chat_prompt import CHAT_PROMPT
from app.agents.retrieval_agent import retrieve as retrieve_contract_context
from app.schemas.enterprise_schemas import AgentType
from app.utils.agent_wrapper import enterprise_agent_wrapper, AgentResponseBuilder
from app.utils.enterprise_utils import sanitize_reasoning_summary, sanitize_warning_message, log_exception_context


def _source_references(sources):
    """Expose identifiers and score without leaking vector-store payloads."""
    return [
        {key: source.get(key) for key in ("parent_id", "child_id", "score")}
        for source in sources
    ]
@enterprise_agent_wrapper(AgentType.CHAT)
def run_chat_agent(
    contract_id: str,
    query: str,
    top_k: int = 5,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Answer questions about a contract using retrieval + generation.
    
    Args:
        contract_id: Contract identifier
        query: User question/query
        top_k: Number of top chunks to retrieve
        request_id: Optional request ID for tracing
        
    Returns:
        Enterprise response with answer and sources
    """
    retrieval_start = time.time()
    retrieval = retrieve_contract_context(contract_id, query, top_k=top_k)
    retrieval_time_ms = int((time.time() - retrieval_start) * 1000)
    
    contract_text = retrieval.get("context", "")
    sources = retrieval.get("sources", [])
    source_references = _source_references(sources)
    
    if not contract_text.strip():
        return AgentResponseBuilder.success(
            result={
                "answer": "Information not found in contract.",
                "sources": []
            },
            retrieval_result=retrieval,
            reasoning_summary="Retrieval returned empty context",
            retrieval_time_ms=retrieval_time_ms,
        )

    prompt = PromptTemplate(
        input_variables=["contract_text", "question"],
        template=CHAT_PROMPT,
    )

    llm_start = time.time()
    try:
        raw, token_usage = LLMService.invoke(prompt, {
            "contract_text": contract_text,
            "question": query
        })
    except Exception as exc:
        log_exception_context("chat", exc)
        return AgentResponseBuilder.success(
            result={"answer": "Model unavailable", "sources": source_references},
            retrieval_result=retrieval, reasoning_summary=sanitize_reasoning_summary(str(exc)),
            retrieval_time_ms=retrieval_time_ms,
            llm_time_ms=int((time.time() - llm_start) * 1000), warnings=[sanitize_warning_message(str(exc))],
        )
    llm_time_ms = int((time.time() - llm_start) * 1000)
    
    parsed = safe_parse_json(raw, {})
    if isinstance(parsed, str):
        parsed = safe_parse_json(parsed, {})

    def _extract_answer(parsed: Any, fallback: str) -> str:
        if isinstance(parsed, dict):
            for key in ("answer", "response", "text", "content"):
                value = parsed.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            nested_result = parsed.get("result")
            if isinstance(nested_result, dict):
                for key in ("answer", "response", "text", "content"):
                    value = nested_result.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
            nested_result_value = parsed.get("result")
            if isinstance(nested_result_value, str) and nested_result_value.strip():
                return nested_result_value.strip()
        if isinstance(parsed, str) and parsed.strip():
            return parsed.strip()
        return fallback.strip() if fallback else ""

    # Calculate confidence & citations
    top_score = max([float(src.get("score") or 0.0) for src in sources], default=0.0)
    similarity = min(max(top_score, 0.0), 1.0)
    answer_text = _extract_answer(parsed, raw)
    completeness = 0.0
    if answer_text:
        if len(answer_text) < 80:
            completeness = 0.25
        elif len(answer_text) < 250:
            completeness = 0.6
        else:
            completeness = 0.85
    confidence = round(min(max(0.6 * similarity + 0.4 * completeness, 0.0), 1.0), 2)

    result_citations = []
    for chunk in retrieval.get('chunks', []):
        scoring = chunk.get('_scoring', {})
        result_citations.append({
            "chunk_id": chunk.get('chunk_id') or chunk.get('child_id') or chunk.get('id', ''),
            "parent_id": chunk.get('parent_id', ''),
            "content_preview": (chunk.get('content') or chunk.get('parent_text') or chunk.get('child_text', ''))[:200],
            "relevance_score": float(chunk.get('relevance_score', scoring.get('combined_score', chunk.get('metadata', {}).get('score', 0.0)))),
            "retrieval_method": chunk.get('retrieval_method', 'hybrid'),
        })

    # Prepare standard result
    result_data = {
        "answer": "",
        "sources": source_references,
        "confidence": confidence,
        "citations": result_citations
    }

    if isinstance(parsed, dict) and parsed:
        result_data["answer"] = _extract_answer(parsed, raw)
    else:
        result_data["answer"] = raw.strip() if raw else ""

    return AgentResponseBuilder.success(
        result=result_data,
        retrieval_result=retrieval,
        reasoning_summary=f"Answered question: {query[:50]}",
        retrieval_time_ms=retrieval_time_ms,
        llm_time_ms=llm_time_ms,
        **token_usage,
    )
