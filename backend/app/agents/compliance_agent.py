from typing import Dict, Any, Optional
import time

from langchain.prompts import PromptTemplate
from app.services.llm_service import LLMService

from app.agents.agent_utils import safe_parse_json
from app.agents.prompts.compliance_prompt import COMPLIANCE_PROMPT
from app.agents.retrieval_agent import retrieve as retrieve_contract_context
from app.schemas.enterprise_schemas import AgentType
from app.utils.agent_wrapper import enterprise_agent_wrapper, AgentResponseBuilder
from app.utils.enterprise_utils import sanitize_reasoning_summary, sanitize_warning_message, log_exception_context


def _derive_applicable_frameworks(contract_text: str, contract_type: str) -> list:
    """Return only frameworks supported by the contract content and contract type."""
    lower = contract_text.lower()
    frameworks = []
    if any(term in lower for term in ["gdpr", "personal data", "data processing", "data subject", "uk gdpr"]):
        frameworks.append("GDPR")
    if any(term in lower for term in ["hipaa", "phi", "protected health information", "health information"]):
        frameworks.append("HIPAA")
    if any(term in lower for term in ["pci", "payment card", "cardholder data", "credit card"]):
        frameworks.append("PCI DSS")
    if any(term in lower for term in ["soc 2", "iso 27001", "information security", "cybersecurity", "security controls"]):
        frameworks.append("SOC 2")
        frameworks.append("ISO 27001")
    if contract_type in {"Legal Services Agreement", "Estate Planning Agreement"} or any(
        term in lower for term in ["attorney-client", "client privilege", "bar council", "professional ethics"]
    ):
        frameworks.append("Professional Ethics")
    if contract_type == "Employment Contract" or any(term in lower for term in ["wage", "labor", "anti-discrimination", "worker safety"]):
        frameworks.append("Labor Law")
    if contract_type == "NDA" or "confidentiality" in lower:
        frameworks.append("Confidentiality")
    return frameworks


@enterprise_agent_wrapper(AgentType.COMPLIANCE)
def run_compliance_agent(
    contract_id: str,
    top_k: int = 6,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze contract for regulatory compliance.

    Args:
        contract_id: Contract identifier
        top_k: Number of top chunks to retrieve
        request_id: Optional request ID for tracing

    Returns:
        Enterprise response with compliance analysis
    """
    retrieval_start = time.time()
    retrieval = retrieve_contract_context(contract_id, "*", top_k=top_k)
    retrieval_time_ms = int((time.time() - retrieval_start) * 1000)

    total_chunks = retrieval.get("total_chunks", 0)
    contract_text = retrieval.get("context", "")

    if total_chunks == 0 or not contract_text.strip():
        return AgentResponseBuilder.success(
            result={
                "compliant": False,
                "issues": [],
                "recommendations": [],
                "applicable_frameworks": [],
                "contract_type": "Unknown",
            },
            retrieval_result=retrieval,
            reasoning_summary="Insufficient contract context was retrieved to provide a reliable answer.",
            retrieval_time_ms=retrieval_time_ms,
        )

    prompt = PromptTemplate(
        input_variables=["contract_text"],
        template=COMPLIANCE_PROMPT,
    )

    llm_start = time.time()
    try:
        raw, token_usage = LLMService.invoke(prompt, {"contract_text": contract_text})
    except Exception as exc:
        log_exception_context("compliance", exc)
        return AgentResponseBuilder.success(
            result={
                "compliant": False,
                "issues": [],
                "recommendations": [],
                "applicable_frameworks": [],
                "contract_type": "Unknown",
            },
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
        if "compliant" not in parsed:
            parsed["compliant"] = False
        if "issues" not in parsed:
            parsed["issues"] = []
        if "recommendations" not in parsed:
            parsed["recommendations"] = []
        if "applicable_frameworks" not in parsed:
            parsed["applicable_frameworks"] = []
        if "contract_type" not in parsed:
            parsed["contract_type"] = "Unknown"

        contract_type = parsed.get("contract_type") or "Unknown"
        applicable_frameworks = parsed.get("applicable_frameworks") or []
        if not isinstance(applicable_frameworks, list):
            applicable_frameworks = [applicable_frameworks] if applicable_frameworks else []
        applicable_frameworks = [framework for framework in applicable_frameworks if isinstance(framework, str) and framework.strip()]
        if not applicable_frameworks:
            applicable_frameworks = _derive_applicable_frameworks(contract_text, contract_type)
        parsed["applicable_frameworks"] = applicable_frameworks

        # Ensure each issue has a retrieval-based confidence score
        if isinstance(parsed["issues"], list):
            for issue in parsed["issues"]:
                if isinstance(issue, dict):
                    raw_confidence = issue.get("confidence_score")
                    try:
                        llm_confidence = float(raw_confidence) if raw_confidence is not None else retrieval_score
                    except (ValueError, TypeError):
                        llm_confidence = retrieval_score
                    issue["confidence_score"] = round(min(max(0.6 * retrieval_score + 0.4 * llm_confidence, 0.0), 1.0), 2)

        # Build extended result with compliance mapping
        extended_result = {
            **parsed,
            "framework": parsed.get("applicable_frameworks", ["LegalGPT Compliance Framework"]),
            "clause_type": "Compliance",
            "status": "Compliant" if parsed.get("compliant") else "Non-Compliant",
            "gap_analysis": parsed.get("issues", []),
        }
        return AgentResponseBuilder.success(
            result=extended_result,
            retrieval_result=retrieval,
            reasoning_summary=f"Compliance analysis for {parsed.get('contract_type', 'Unknown')} contract",
            retrieval_time_ms=retrieval_time_ms,
            llm_time_ms=llm_time_ms,
            **token_usage,
        )

    # Fallback with extended compliance mapping
    extended_fallback_result = {
        "compliant": False,
        "issues": [],
        "recommendations": [],
        "applicable_frameworks": [],
        "contract_type": "Unknown",
        "framework": "LegalGPT Compliance Framework",
        "clause_type": "Compliance",
        "status": "Non-Compliant",
        "gap_analysis": []
    }
    return AgentResponseBuilder.success(
        result=extended_fallback_result,
        retrieval_result=retrieval,
        reasoning_summary="Compliance analysis returned default structure",
        retrieval_time_ms=retrieval_time_ms,
        llm_time_ms=llm_time_ms,
        **token_usage,
        warnings=["Response parsing returned fallback structure"],
    )
