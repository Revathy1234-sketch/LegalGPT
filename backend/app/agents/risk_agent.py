from typing import Dict, Any, Optional
import time

from langchain.prompts import PromptTemplate
from app.services.llm_service import LLMService

from app.agents.agent_utils import safe_parse_json
from app.agents.prompts.risk_prompt import RISK_PROMPT
from app.agents.retrieval_agent import retrieve as retrieve_contract_context
from app.schemas.enterprise_schemas import AgentType
from app.utils.agent_wrapper import enterprise_agent_wrapper, AgentResponseBuilder
from app.utils.enterprise_utils import sanitize_reasoning_summary, sanitize_warning_message, log_exception_context

# ---------------------------------------------------------------------------
# Lightweight contract-type detector (keyword heuristics)
# ---------------------------------------------------------------------------
CONTRACT_TYPE_KEYWORDS: Dict[str, list] = {
    "Estate Planning Agreement": ["estate planning", "will", "trust", "executor", "beneficiary", "probate", "testamentary"],
    "Legal Services Agreement": ["attorney", "law firm", "legal services", "legal representation", "retainer"],
    "Employment Contract": ["employment", "employee", "employer", "salary", "benefits", "working hours", "probation"],
    "NDA": ["non-disclosure", "nda", "confidential information", "disclosing party", "receiving party"],
    "Non-Compete Agreement": ["non-compete", "non compete", "restrictive covenant", "competition"],
    "Lease Agreement": ["lease", "landlord", "tenant", "rent", "premises", "leasehold"],
    "Software License Agreement": ["software license", "license agreement", "end user", "eula"],
    "SaaS Agreement": ["saas", "software as a service", "subscription", "cloud service"],
    "Service Agreement": ["service agreement", "services", "scope of work", "deliverables", "service provider"],
    "Consulting Agreement": ["consulting", "consultant", "advisory", "engagement"],
    "Purchase Agreement": ["purchase", "buyer", "seller", "purchase price", "bill of sale"],
    "Vendor Agreement": ["vendor", "supplier", "procurement"],
    "Partnership Agreement": ["partnership", "partners", "profit sharing", "joint venture"],
    "Maintenance Agreement": ["maintenance", "support services", "service level"],
    "Distribution Agreement": ["distribution", "distributor", "territory", "reseller"],
    "Franchise Agreement": ["franchise", "franchisee", "franchisor", "royalty"],
    "Loan Agreement": ["loan", "lender", "borrower", "interest rate", "repayment"],
    "Shareholder Agreement": ["shareholder", "stockholder", "shares", "equity", "voting rights"],
    "Memorandum of Understanding (MoU)": ["memorandum of understanding", "mou", "letter of intent"],
}


def detect_contract_type(text: str) -> str:
    """Detect contract type from text using weighted keyword scoring."""
    lower = text.lower()
    scores: Dict[str, int] = {}
    for ctype, keywords in CONTRACT_TYPE_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw in lower:
                score += 3
            else:
                words = [word for word in kw.split() if len(word) > 2]
                if words and sum(1 for word in words if word in lower) == len(words):
                    score += 2
                elif any(word in lower for word in words):
                    score += 1
        if score > 0:
            scores[ctype] = score
    if scores:
        return max(scores, key=scores.get)
    return "General Contract"


@enterprise_agent_wrapper(AgentType.RISK_ANALYSIS)
def run_risk_analysis(
    contract_id: str,
    top_k: int = 6,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze contract risks and generate risk scores.

    Args:
        contract_id: Contract identifier
        top_k: Number of top chunks to retrieve
        request_id: Optional request ID for tracing

    Returns:
        Enterprise response with risk analysis
    """
    retrieval_start = time.time()
    retrieval = retrieve_contract_context(contract_id, "*", top_k=top_k)
    retrieval_time_ms = int((time.time() - retrieval_start) * 1000)

    total_chunks = retrieval.get("total_chunks", 0)
    contract_text = retrieval.get("context", "")

    if total_chunks == 0 or not contract_text.strip():
        return AgentResponseBuilder.success(
            result={
                "contract_type": "Unknown",
                "overall_score": 0,
                "risk_matrix": [],
                "mitigation_plan": []
            },
            retrieval_result=retrieval,
            reasoning_summary="Insufficient contract context was retrieved to provide a reliable answer.",
            retrieval_time_ms=retrieval_time_ms,
        )

    # Detect contract type before LLM call (for fallback and context)
    detected_type = detect_contract_type(contract_text)

    prompt = PromptTemplate(
        input_variables=["contract_text"],
        template=RISK_PROMPT,
    )

    llm_start = time.time()
    try:
        raw, token_usage = LLMService.invoke(prompt, {"contract_text": contract_text})
    except Exception as exc:
        log_exception_context("risk", exc)
        return AgentResponseBuilder.success(
            result={"contract_type": detected_type, "overall_score": 0, "risk_matrix": [], "mitigation_plan": []},
            retrieval_result=retrieval, reasoning_summary=sanitize_reasoning_summary(str(exc)),
            retrieval_time_ms=retrieval_time_ms,
            llm_time_ms=int((time.time() - llm_start) * 1000), warnings=[sanitize_warning_message(str(exc))],
        )
    llm_time_ms = int((time.time() - llm_start) * 1000)

    parsed = safe_parse_json(raw, {})
    if isinstance(parsed, dict) and parsed:
        retrieval_score = 0.0
        chunk_scores = [
            float(chunk.get("score") or chunk.get("similarity") or 0.0)
            for chunk in retrieval.get("chunks", [])
            if chunk.get("score") or chunk.get("similarity")
        ]
        if chunk_scores:
            retrieval_score = min(max(sum(chunk_scores) / len(chunk_scores), 0.0), 1.0)
        else:
            retrieval_score = 0.85

        # Ensure required fields exist
        if "contract_type" not in parsed:
            parsed["contract_type"] = detected_type
        if "overall_score" not in parsed:
            parsed["overall_score"] = 0
        if "risk_matrix" not in parsed:
            parsed["risk_matrix"] = []
        if "mitigation_plan" not in parsed:
            parsed["mitigation_plan"] = []

        # Ensure each risk item has a retrieval-based confidence score
        if isinstance(parsed["risk_matrix"], list):
            for risk_item in parsed["risk_matrix"]:
                if isinstance(risk_item, dict):
                    raw_confidence = risk_item.get("confidence_score")
                    try:
                        llm_confidence = float(raw_confidence) if raw_confidence is not None else retrieval_score
                    except (ValueError, TypeError):
                        llm_confidence = retrieval_score
                    risk_item["confidence_score"] = round(min(max(0.6 * retrieval_score + 0.4 * llm_confidence, 0.0), 1.0), 2)

        return AgentResponseBuilder.success(
            result=parsed,
            retrieval_result=retrieval,
            reasoning_summary=f"Risk analysis extracted for {parsed.get('contract_type', detected_type)} contract",
            retrieval_time_ms=retrieval_time_ms,
            llm_time_ms=llm_time_ms,
            **token_usage,
        )

    # Fallback
    return AgentResponseBuilder.success(
        result={
            "contract_type": detected_type,
            "overall_score": 0,
            "risk_matrix": [],
            "mitigation_plan": []
        },
        retrieval_result=retrieval,
        reasoning_summary="Risk analysis returned default structure",
        retrieval_time_ms=retrieval_time_ms,
        llm_time_ms=llm_time_ms,
        **token_usage,
        warnings=["Response parsing returned fallback structure"],
    )
