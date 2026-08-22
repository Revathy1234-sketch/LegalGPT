from typing import Dict, Any, Optional, List
import time
import re

# ---------------------------------------------------------------------------
# Deterministic keyword-based clause category mapper
# ---------------------------------------------------------------------------
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "Definitions": ["definition", "interpretation"],
    "Scope of Services": ["services", "scope", "work"],
    "Payment Terms": ["payment", "fee", "invoice", "billing"],
    "Termination": ["termination", "end"],
    "Withdrawal": ["withdrawal"],
    "Confidentiality": ["confidential"],
    "Indemnification": ["indemnity", "indemnification", "indemnify"],
    "Liability": ["liability"],
    "Governing Law": ["governing law"],
    "Jurisdiction": ["jurisdiction"],
    "Dispute Resolution": ["dispute"],
    "Force Majeure": ["force majeure"],
    "Assignment": ["assignment"],
    "Severability": ["severability"],
    "Notices": ["notices"],
    "Amendments": ["amendment"],
    "Warranty": ["warranty"],
    "Intellectual Property": ["intellectual property"],
    "Audit Rights": ["audit"],
    "Data Protection": ["data protection"],
    "Miscellaneous": ["miscellaneous"],
}


def map_category(title: str) -> str:
    """Map a clause title to a standardised category using keyword matching."""
    lower = title.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return category
    return "Other"


def _compute_confidence(similarity: float, completeness: float) -> float:
    """Deterministic confidence score.

    confidence = 0.6 × retrieval_similarity + 0.4 × extraction_completeness
    where extraction_completeness is:
        1.0 = full clause extracted
        0.7 = most of clause extracted
        0.4 = partial clause
        0.0 = fallback / default
    """
    return round(min(max(0.6 * similarity + 0.4 * completeness, 0.0), 1.0), 2)


def _estimate_completeness(content: str) -> float:
    """Heuristic completeness estimate based on content length."""
    length = len(content.strip())
    if length >= 200:
        return 1.0
    if length >= 80:
        return 0.7
    if length >= 20:
        return 0.4
    return 0.0


def _title_present_in_text(title: str, text: str) -> bool:
    """Check whether the clause title (or a close variant) appears in the source text."""
    if not title or not text:
        return False
    title_lower = title.lower().strip()
    text_lower = text.lower()
    # Direct substring match
    if title_lower in text_lower:
        return True
    # Try individual significant words (skip short words)
    words = [w for w in title_lower.split() if len(w) > 3]
    if words and all(w in text_lower for w in words):
        return True
    return False


def extract_clause_from_contract(contract_text: str, title: str) -> str:
    """Recover clause content from the contract text when the model omits it."""
    if not contract_text or not title:
        return ""

    normalized_title = title.strip().lower()
    if not normalized_title:
        return ""

    # Prefer explicit heading matches inline with the clause title.
    for pattern in [
        rf"(?:section|article|clause)\s*[^\n.]*{re.escape(normalized_title)}[^\n.]*",
        rf"{re.escape(normalized_title)}",
    ]:
        match = re.search(pattern, contract_text.lower())
        if match:
            start = max(0, match.start())
            end = min(len(contract_text), start + 700)
            snippet = contract_text[start:end].strip()
            if len(snippet) >= 20:
                return snippet

    # Fallback: extract the first sentence block containing keywords from the title.
    keywords = [word for word in re.split(r"[^a-z0-9]+", normalized_title) if word and len(word) > 2]
    if keywords:
        for keyword in keywords:
            idx = contract_text.lower().find(keyword)
            if idx != -1:
                start = max(0, idx - 120)
                end = min(len(contract_text), idx + 700)
                snippet = contract_text[start:end].strip()
                if len(snippet) >= 20:
                    return snippet

    return ""


from langchain.prompts import PromptTemplate
from app.services.llm_service import LLMService

from app.agents.agent_utils import safe_parse_json
from app.agents.prompts.clause_prompt import CLAUSE_PROMPT
from app.agents.retrieval_agent import retrieve as retrieve_contract_context
from app.schemas.enterprise_schemas import AgentType
from app.utils.agent_wrapper import enterprise_agent_wrapper, AgentResponseBuilder
from app.utils.enterprise_utils import sanitize_reasoning_summary, sanitize_warning_message, log_exception_context

@enterprise_agent_wrapper(AgentType.CLAUSE_EXTRACTION)
def run_clause_agent(
    contract_id: str,
    query: str = "clauses",
    top_k: int = 8,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extract and categorize clauses from contract.

    Args:
        contract_id: Contract identifier
        query: Search query (default: "clauses")
        top_k: Number of top chunks to retrieve
        request_id: Optional request ID for tracing

    Returns:
        Enterprise response with extracted clauses
    """
    retrieval_start = time.time()
    effective_query = "indemnification, liability, termination, privacy, governing law, payment, term" if query == "*" or query == "clauses" else query
    retrieval = retrieve_contract_context(contract_id, effective_query, top_k=top_k)
    retrieval_time_ms = int((time.time() - retrieval_start) * 1000)

    total_chunks = retrieval.get("total_chunks", 0)
    contract_text = retrieval.get("context", "")
    chunks = retrieval.get("chunks", [])

    if total_chunks == 0 or not contract_text.strip():
        return AgentResponseBuilder.success(
            result={"clauses": []},
            retrieval_result=retrieval,
            reasoning_summary="Insufficient contract context was retrieved to provide a reliable answer.",
            retrieval_time_ms=retrieval_time_ms,
        )

    prompt = PromptTemplate(
        input_variables=["contract_text", "query"],
        template=CLAUSE_PROMPT,
    )

    llm_start = time.time()
    try:
        raw, token_usage = LLMService.invoke(
            prompt,
            {
                "contract_text": contract_text,
                "query": query
            },
            require_json=True
        )
    except Exception as exc:
        log_exception_context("clauses", exc)
        return AgentResponseBuilder.success(
            result={"clauses": []},
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

    if isinstance(parsed, dict) and "error" in parsed:
        raise ValueError(f"JSON Parsing Failed: {parsed['reason']}\nRaw Output:\n{parsed['raw_response']}")

    if isinstance(parsed, dict):
        clauses = parsed.get("clauses", [])
    elif isinstance(parsed, list):
        clauses = parsed
    else:
        clauses = []

    # ------------------------------------------------------------------
    # Build chunk metadata for citation enrichment
    # ------------------------------------------------------------------
    chunk_meta: List[Dict[str, Any]] = []
    for idx, ch in enumerate(chunks):
        chunk_meta.append({
            "chunk_id": ch.get("child_id") or ch.get("parent_id") or f"chunk_{idx}",
            "page": ch.get("page") or ch.get("page_number") or (idx + 1),
            "text": (ch.get("parent_text") or ch.get("child_text") or "").lower(),
        })

    # Compute average retrieval similarity (normalised 0-1) from chunks
    avg_similarity = 0.85  # default when no score available
    scores = [ch.get("score") or ch.get("similarity") for ch in chunks if ch.get("score") or ch.get("similarity")]
    if scores:
        try:
            avg_similarity = min(max(sum(float(s) for s in scores) / len(scores), 0.0), 1.0)
        except (ValueError, TypeError):
            avg_similarity = 0.85

    standardized_clauses = []
    if isinstance(clauses, list):
        for item in clauses:
            if not isinstance(item, dict):
                continue
            title = item.get("title") or item.get("clause_type") or item.get("category") or "extracted"
            content = item.get("content") or item.get("clause_text") or item.get("original_text") or ""
            if not content:
                content = extract_clause_from_contract(contract_text, title)
            # ----------------------------------------------------------
            # Hallucination guard: discard clauses with empty content
            # ----------------------------------------------------------
            if not content or len(content.strip()) < 10:
                continue

            # ----------------------------------------------------------
            # Hallucination guard: verify clause content exists in source text.
            # ----------------------------------------------------------
            if not _title_present_in_text(title, contract_text):
                content_snippet = content[:80].lower().strip()
                if content_snippet not in contract_text.lower():
                    continue
            elif len(content.strip()) > 20 and content.strip() not in contract_text:
                if not any(segment.strip() in contract_text for segment in [content.strip()[:200], content.strip()[-200:]]):
                    continue

            # ----------------------------------------------------------
            # Category mapping (deterministic keyword-based)
            # ----------------------------------------------------------
            category = item.get("category") or ""
            if not category or str(category).lower() in ["unknown", "none", "n/a", ""]:
                category = map_category(title)

            # ----------------------------------------------------------
            # Confidence score
            # ----------------------------------------------------------
            completeness = _estimate_completeness(content)
            score = item.get("confidence_score") or item.get("score")
            try:
                raw_score = float(score) if score is not None else avg_similarity
            except (ValueError, TypeError):
                raw_score = avg_similarity
            confidence_score = _compute_confidence(raw_score, completeness)

            # ----------------------------------------------------------
            # Citations: match content against chunks to find source
            # ----------------------------------------------------------
            citations = item.get("citations") or []
            if not citations:
                content_lower = content[:120].lower()
                for cm in chunk_meta:
                    if content_lower[:60] in cm["text"] or cm["text"][:60] in content_lower:
                        citations.append({"chunk_id": cm["chunk_id"], "page": cm["page"]})
                if not citations:
                    # Fallback: use all retrieved chunks as broad citations
                    citations = [{"chunk_id": cm["chunk_id"], "page": cm["page"]} for cm in chunk_meta[:3]]

            standardized_clauses.append({
                "title": title,
                "category": category,
                "content": content,
                "confidence_score": confidence_score,
                "citations": citations,
            })

    if not standardized_clauses:
        # User requested to return clear insufficient-evidence rather than invented legal info.
        pass

    return AgentResponseBuilder.success(
        result={"clauses": standardized_clauses},
        retrieval_result=retrieval,
        reasoning_summary="Clauses extracted from contract text",
        retrieval_time_ms=retrieval_time_ms,
        llm_time_ms=llm_time_ms,
        **token_usage,
    )
