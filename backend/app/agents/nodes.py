import ast
import json
import logging
import re
from typing import Any, Dict, List


from app.core.config import settings
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

CLAUSE_TYPES = [
    "Definitions",
    "Scope of Work",
    "Payment Terms",
    "Confidentiality",
    "Termination",
    "Intellectual Property",
    "Warranties",
    "Indemnification",
    "Limitation of Liability",
    "Force Majeure",
    "Governing Law",
    "Dispute Resolution",
    "Assignment",
    "Data Protection",
    "Non-Compete",
    "Non-Solicitation",
    "Audit Rights",
    "Insurance",
    "Entire Agreement",
    "Severability"
]

CLAUSE_SYNONYMS = {
    "Termination": ["termination", "terminate", "early termination", "terminat"],
    "Payment Terms": ["payment terms", "pay", "compensation", "fees", "invoice", "due date"],
    "Confidentiality": ["confidentiality", "confidential information", "non-disclosure", "nda"],
    "Governing Law": ["governing law", "laws of", "jurisdiction", "venue"],
    "Indemnification": ["indemnification", "indemnify", "hold harmless"],
    "Limitation of Liability": ["limitation of liability", "liability cap", "cap on liability", "limited liability"],
    "Intellectual Property": ["intellectual property", "ownership", "copyright", "patent", "trademark"],
    "Dispute Resolution": ["dispute resolution", "arbitration", "mediation", "court", "lawsuit"],
    "Definitions": ["definition", "definitions", "means"],
"Scope of Work": ["scope of work", "services", "deliverables"],
"Warranties": ["warranty", "warranties", "represents and warrants"],
"Force Majeure": ["force majeure", "act of god"],
"Assignment": ["assignment", "assign"],
"Data Protection": ["data protection", "privacy", "gdpr"],
"Non-Compete": ["non compete", "non-compete"],
"Non-Solicitation": ["non solicitation", "non-solicitation"],
"Audit Rights": ["audit", "inspection rights"],
"Insurance": ["insurance", "coverage"],
"Entire Agreement": ["entire agreement"],
"Severability": ["severability", "severable"]
}

RISK_WEIGHTS = {
    "High": 25,
    "Medium": 15,
    "Low": 5,
}







def extract_first_json_block(text: str) -> str | None:
    if not text:
        return None

    idx_brace = text.find("{")
    idx_bracket = text.find("[")

    if idx_brace == -1 and idx_bracket == -1:
        return None

    if idx_brace != -1 and idx_bracket != -1:
        start_idx = min(idx_brace, idx_bracket)
    elif idx_brace != -1:
        start_idx = idx_brace
    else:
        start_idx = idx_bracket

    stack = []
    in_string = False
    escape = False

    for idx in range(start_idx, len(text)):
        char = text[idx]
        if escape:
            escape = False
            continue
        if char == '\\':
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if not in_string:
            if char in "{[":
                stack.append(char)
            elif char in "]}":
                if not stack:
                    continue
                last = stack[-1]
                if (last == "{" and char == "}") or (last == "[" and char == "]"):
                    stack.pop()
                    if not stack:
                        return text[start_idx:idx+1]
    return None


def remove_trailing_commas(json_str: str) -> str:
    return re.sub(r',(\s*[}\]])', r'\1', json_str)


def remove_malformed_commas(json_str: str) -> str:
    # Trailing commas before } or ]
    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
    # Double commas
    json_str = re.sub(r',(\s*,)+', ',', json_str)
    return json_str


def repair_truncated_json(s: str) -> str:
    s = s.strip()
    if not s:
        return s

    stack = []
    in_string = False
    escape = False

    repaired = []
    for idx, char in enumerate(s):
        if escape:
            escape = False
            repaired.append(char)
            continue
        if char == '\\':
            escape = True
            repaired.append(char)
            continue
        if char == '"':
            in_string = not in_string
            repaired.append(char)
            continue

        if not in_string:
            if char in "{[":
                stack.append(char)
            elif char in "]}":
                if stack:
                    last = stack[-1]
                    if (last == "{" and char == "}") or (last == "[" and char == "]"):
                        stack.pop()
        repaired.append(char)

    if in_string:
        if escape:
            repaired.pop()
        repaired.append('"')

    while stack:
        last = stack.pop()
        if last == "{":
            repaired.append("}")
        elif last == "[":
            repaired.append("]")

    return "".join(repaired)


def parse_json_recursive(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: parse_json_recursive(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [parse_json_recursive(v) for v in data]
    elif isinstance(data, str):
        cleaned = data.strip()
        if (cleaned.startswith("{") and cleaned.endswith("}")) or (cleaned.startswith("[") and cleaned.endswith("]")):
            try:
                parsed = json.loads(cleaned)
                return parse_json_recursive(parsed)
            except Exception:
                try:
                    parsed = ast.literal_eval(cleaned)
                    return parse_json_recursive(parsed)
                except Exception:
                    pass
    return data


def parse_json_safe(raw_text: str, default: Any = None) -> Any:
    logger = logging.getLogger(__name__)
    if not raw_text:
        return default

    # 1. Clean fences and whitespace
    text = raw_text.strip()
    # Remove Markdown code fences (e.g. ```json ... ``` or just ```)
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    else:
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text, flags=re.IGNORECASE)
    text = text.strip()
    if not text:
        return default

    def balance_brackets(sub: str) -> str:
        sub = sub.strip()
        # Strip trailing commas or colons before balancing
        while sub and sub[-1] in ",:":
            sub = sub[:-1].strip()
        if not sub:
            return ""

        stack = []
        in_string = False
        escape = False
        repaired = []

        for char in sub:
            if escape:
                escape = False
                repaired.append(char)
                continue
            if char == '\\':
                escape = True
                repaired.append(char)
                continue
            if char == '"':
                in_string = not in_string
                repaired.append(char)
                continue
            if not in_string:
                if char in "{[":
                    stack.append(char)
                elif char in "]}":
                    if stack:
                        last = stack[-1]
                        if (last == "{" and char == "}") or (last == "[" and char == "]"):
                            stack.pop()
            repaired.append(char)

        if in_string:
            repaired.append('"')

        # Close open brackets in reverse order
        while stack:
            last = stack.pop()
            if last == "{":
                repaired.append("}")
            elif last == "[":
                repaired.append("]")
        return "".join(repaired)

    # 2. Try parsing direct text and clean comma variants first
    candidates = [text, re.sub(r',(\s*[}\]])', r'\1', text)]
    for cand in candidates:
        try:
            res = json.loads(cand)
            res_parsed = parse_json_recursive(res)
            if isinstance(res_parsed, (dict, list)):
                return res_parsed
        except Exception:
            pass

        try:
            res = ast.literal_eval(cand)
            if isinstance(res, (dict, list)):
                res_parsed = parse_json_recursive(res)
                if isinstance(res_parsed, (dict, list)):
                    return res_parsed
        except Exception:
            pass

    # 3. Progressive backtracking tail-trimming and balancing
    # Only balance if the JSON is truncated (i.e. it does NOT end with a matching closing bracket/brace)
    if text and not (text.endswith('}') or text.endswith(']')):
        max_backtrack = min(2000, len(text))
        if (text.startswith('{') or text.startswith('[')):
            for offset in range(max_backtrack):
                sub = text[:len(text) - offset]
                if '{' not in sub and '[' not in sub:
                    continue
                balanced = balance_brackets(sub)
                if not balanced:
                    continue

                # Clean potential malformed commas in the balanced version
                balanced_clean = re.sub(r',(\s*[}\]])', r'\1', balanced)

                for cand in (balanced, balanced_clean):
                    try:
                        res = json.loads(cand)
                        res_parsed = parse_json_recursive(res)
                        if isinstance(res_parsed, (dict, list)):
                            return res_parsed
                    except Exception:
                        pass

                    try:
                        res = ast.literal_eval(cand)
                        if isinstance(res, (dict, list)):
                            res_parsed = parse_json_recursive(res)
                            if isinstance(res_parsed, (dict, list)):
                                return res_parsed
                    except Exception:
                        pass

    # If we fall through, we capture the exception exactly to know why json.loads failed on the cleaned text
    try:
        json.loads(text)
        error_msg = "Unknown error"
    except Exception as e:
        error_msg = str(e)

    logger.error(f"Failed to parse JSON from response. Reason: {error_msg}. Raw Text:\n{raw_text}")

    # Return explicit structured error state instead of swallowing it with default
    return {"error": "JSON parsing failed", "reason": error_msg, "raw_response": raw_text}


def snippet_for_clause(contract_text: str, clause_type: str) -> str:
    normalized = contract_text.lower()
    for synonym in CLAUSE_SYNONYMS.get(clause_type, []):
        idx = normalized.find(synonym)
        if idx != -1:
            start = max(idx - 120, 0)
            end = min(idx + 260, len(contract_text))
            return contract_text[start:end].strip()
    return ""





def get_workflow_next_agent(state: AgentState, default: str) -> str:
    """
    Route based on query type. Ensures proper workflow sequencing:
    - clauses_only: extraction → end
    - risk_only: extraction → risk → end
    - compliance_only: extraction → compliance → end
    - negotiation_only: extraction → risk → negotiation → end
    """
    query = (state.get("query") or "").lower()
    if "clauses_only" in query:
        return "end"
    if "risk_only" in query:
        return "end"
    if "compliance_only" in query:
        return "end"
    if "negotiation_only" in query:
        return "risk"
    return default


def contract_analysis_node(state: AgentState) -> Dict[str, Any]:
    text = state.get("contract_text", "") or ""
    query = state.get("query", "")
    normalized_query = query.lower()
    if "summary" in normalized_query or "general summary" in normalized_query:
        next_agent = "end"
    elif "full_workflow" in normalized_query:
        next_agent = "extraction"
    else:
        next_agent = "end"

    prompt = f"""
You are a Contract Analysis Agent. Your task is to analyze the following contract in relation to this query: "{query}".
Provide a comprehensive analysis detailing the contract type, key parties, duration, and summary.

Contract Text:
{text}
"""

    try:
        from app.services.llm_service import LLMService
        final_response, _ = LLMService.invoke(prompt, {})
    except Exception as e:
        final_response = f"Analysis Error: {str(e)}"

    logger.info("Current Node: contract_analysis_node | Next Node: %s", next_agent)
    logger.debug("Clause Count: 0 | Risk Count: 0 | Compliance Count: 0 | Negotiation Count: 0")

    return {**state, "final_response": final_response, "next_agent": next_agent}


def clause_extraction_node(state: AgentState) -> Dict[str, Any]:
    text = state.get("contract_text", "") or ""
    query = state.get("query", "")
    next_agent = get_workflow_next_agent(state, "risk")

    logger.debug("=" * 50)
    logger.info("Current Node: clause_extraction_node")
    logger.debug("TEXT LENGTH: %d", len(text))
    logger.debug("=" * 50)

    prompt = """
You are a Clause Extraction Agent.
Extract the exact full text of each required clause from the contract.
Required clauses:
- Termination
- Confidentiality
- Payment Terms
- Governing Law
- Indemnification
- Limitation of Liability
- Force Majeure
- Data Protection
- Intellectual Property
- Dispute Resolution

Rules:
- Return complete clause text only.
- Never return partial text.
- Never merge multiple clauses.
- Return exact clause text as found in the contract.
- Omit clauses that are not present.
- Return JSON only, with no markdown or explanatory text.

Output format:
{{
  "clauses": [
    {{
      "clause_type":"Termination",
      "original_text":"...",
      "confidence_score":0.95
    }}
  ]
}}

Contract Text:
{text}
"""

    extracted: List[Dict[str, Any]] = []
    try:
        from app.services.llm_service import LLMService
        res_text, _ = LLMService.invoke(prompt, {"text": text}, require_json=True)
        logger.debug("\nRAW LLM RESPONSE:\n%s", res_text)
        parsed = parse_json_safe(res_text, {})

        clause_list = parsed.get("clauses", []) if isinstance(parsed, dict) else []
        if isinstance(clause_list, list):
            extracted = [
                {
                    "clause_type": item.get("clause_type", "Unknown"),
                    "original_text": item.get("original_text", ""),
                    "confidence_score": float(item.get("confidence_score", 0.0)) if item.get("confidence_score") is not None else 0.0,
                }
                for item in clause_list
                if isinstance(item, dict)
            ]
    except Exception as e:
        logger.error("CLAUSE EXTRACTION ERROR: %s", str(e))



    logger.info("clause_extraction_node | Next Node: %s", next_agent)
    logger.info("Clause Count: %d | Risk Count: 0 | Compliance Count: 0 | Negotiation Count: 0", len(extracted))

    return {**state, "extracted_clauses": extracted, "next_agent": next_agent}





def risk_analysis_node(state: AgentState) -> Dict[str, Any]:
    clauses = state.get("extracted_clauses", [])
    if not clauses:
        extracted_result = clause_extraction_node(state)
        clauses = extracted_result.get("extracted_clauses", [])

    query = (state.get("query") or "").lower()
    # Route based on query type
    if "risk_only" in query:
        next_agent = "end"
    elif "compliance_only" in query:
        next_agent = "end"
    elif "negotiation_only" in query:
        next_agent = "negotiation"
    else:
        next_agent = "end"

    prompt = """
You are a senior Legal Risk Analysis Agent.

Analyze the following extracted contract clauses.

For each risk return:
{{
  "risks": [
    {{
      "risk_level": "Low|Medium|High",
      "clause_type": "...",
      "issue": "...",
      "impact": "...",
      "mitigation": "..."
    }}
  ]
}}

Assess risk severity objectively based on actual contract evidence. Do not fabricate risk findings.
Do not assume missing clauses are automatically high risk.
Distinguish PRESENT, ABSENT, or UNCLEAR provisions based on the provided text.
Clauses:
{clauses}
"""

    risk_matrix: List[Dict[str, Any]] = []
    try:
        from app.services.llm_service import LLMService
        res_text, _ = LLMService.invoke(prompt, {"clauses": json.dumps(clauses, indent=2)}, require_json=True)
        logger.debug("\nRAW RISK RESPONSE:\n%s", res_text)
        parsed = parse_json_safe(res_text, {})
        if isinstance(parsed, dict) and "error" in parsed:
            raise ValueError(f"JSON Parsing Failed in Risk: {parsed['reason']}\nRaw Output:\n{parsed['raw_response']}")

        risk_list = parsed.get("risks", []) if isinstance(parsed, dict) else []
        if isinstance(risk_list, list):
            risk_matrix = [
                {
                    "risk_level": item.get("risk_level", "Low"),
                    "clause_type": item.get("clause_type", "Unknown"),
                    "issue": item.get("issue", ""),
                    "impact": item.get("impact", ""),
                    "mitigation": item.get("mitigation", ""),
                }
                for item in parsed.get("risks", [])
                if isinstance(item, dict)
            ]
    except Exception as e:
        logger.exception("RISK ANALYSIS ERROR: %s", str(e))



    overall_score = 100
    for risk in risk_matrix:
        overall_score -= RISK_WEIGHTS.get(risk.get("risk_level", "Low"), 5)
    overall_score = max(overall_score, 0)

    logger.info("Current Node: risk_analysis_node | Next Node: %s", next_agent)
    logger.info("Clause Count: %d | Risk Count: %d | Compliance Count: 0 | Negotiation Count: 0", len(clauses), len(risk_matrix))

    return {**state, "risk_matrix": risk_matrix, "overall_score": overall_score, "next_agent": next_agent}


def evaluate_compliance(clauses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    report: List[Dict[str, Any]] = []
    if not clauses:
        return report

    try:
        from app.services.llm_service import LLMService
        from app.agents.agent_utils import safe_parse_json

        prompt = """
You are a Compliance Analyst. Review the following contract clauses and determine if GDPR, HIPAA, or SOC2 are applicable based on the contract language.
For each regulation, return:
- framework: "GDPR", "HIPAA", or "SOC2"
- status: "APPLICABLE", "NOT APPLICABLE", "MENTIONED", "NOT FOUND", or "INSUFFICIENT INFORMATION"
- gap_analysis: Explanation based strictly on provided text.

Clauses:
{clauses}

Output JSON as a list of dicts.
"""
        res_text, _ = LLMService.invoke(prompt, {"clauses": json.dumps(clauses, indent=2)}, require_json=True)
        parsed = safe_parse_json(res_text, [])
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    report.append({
                        "framework": item.get("framework", "Unknown"),
                        "clause_type": "Compliance",
                        "status": item.get("status", "NOT FOUND"),
                        "gap_analysis": item.get("gap_analysis", "No information found.")
                    })
    except Exception as e:
        pass

    return report


def compliance_node(state: AgentState) -> Dict[str, Any]:
    clauses = state.get("extracted_clauses", [])
    if not clauses:
        extracted_result = clause_extraction_node(state)
        clauses = extracted_result.get("extracted_clauses", [])

    query = (state.get("query") or "").lower()
    next_agent = "end" if "compliance_only" in query else "negotiation"

    prompt = """
You are a Compliance Agent. Cross-reference the following clauses with compliance requirements (e.g. GDPR, HIPAA, SOC2).
Format your response strictly as a JSON object containing a "compliance" array:
{{
  "compliance": [
    {{
      "framework": "...",
      "clause_type": "...",
      "status": "Compliant|Non-Compliant",
      "gap_analysis": "..."
    }}
  ]
}}
Do not add markdown formatting or anything outside the JSON block.

Clauses:
{clauses}
"""

    compliance_report: List[Dict[str, Any]] = []
    try:
        from app.services.llm_service import LLMService
        res_text, _ = LLMService.invoke(prompt, {"clauses": json.dumps(clauses, indent=2)}, require_json=True)
        logger.debug("\nRAW COMPLIANCE RESPONSE:\n%s", res_text)
        parsed = parse_json_safe(res_text, {})
        if isinstance(parsed, dict) and "error" in parsed:
            raise ValueError(f"JSON Parsing Failed in Compliance: {parsed['reason']}\nRaw Output:\n{parsed['raw_response']}")

        compliance_list = parsed.get("compliance", []) if isinstance(parsed, dict) else []
        if isinstance(compliance_list, list):
            compliance_report = [
                {
                    "framework": item.get("framework", "Unknown"),
                    "clause_type": item.get("clause_type", "Unknown"),
                    "status": item.get("status", "Non-Compliant"),
                    "gap_analysis": item.get("gap_analysis", ""),
                }
                for item in compliance_list
                if isinstance(item, dict)
            ]
    except Exception as e:
        logger.error("COMPLIANCE ANALYSIS ERROR: %s", str(e))

    if not compliance_report:
        compliance_report = evaluate_compliance(clauses)

    logger.info("Current Node: compliance_node | Next Node: %s", next_agent)
    logger.info("Clause Count: %d | Risk Count: %d | Compliance Count: %d | Negotiation Count: 0",
                len(clauses), len(state.get('risk_matrix', [])), len(compliance_report))

    return {**state, "compliance_report": compliance_report, "next_agent": next_agent}


def build_negotiation_suggestions(
    risk_matrix: List[Dict[str, Any]],
    compliance_report: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    suggestions: List[Dict[str, Any]] = []
    seen = set()

    for risk in risk_matrix:
        clause_type = risk.get("clause_type", "General")
        clause_lower = clause_type.strip().lower()
        if "payment" in clause_lower:
            tactic = "Request clearer payment milestones and net terms."
            text = "Payment shall be made within 30 days of invoice receipt, and invoices shall include itemized fees."
        elif "indemn" in clause_lower:
            tactic = "Seek reciprocal indemnification to balance risk exposure."
            text = "Each party shall indemnify the other for losses arising from its own negligence or breach."
        elif "limitation" in clause_lower or "liability" in clause_lower:
            tactic = "Negotiate a reasonable mutual cap on damages."
            text = "The parties’ aggregate liability under this agreement shall be limited to the greater of the fees paid in the prior 12 months or $100,000."
        elif "governing" in clause_lower or "law" in clause_lower:
            tactic = "Establish a neutral and predictable jurisdiction."
            text = "This agreement shall be governed by the laws of the State of New York, without regard to conflict of law principles."
        elif "confidential" in clause_lower:
            tactic = "Strengthen data protection and permitted disclosure language."
            text = "Confidential information may only be disclosed to third parties with prior written consent and under comparable confidentiality obligations."
        elif "termination" in clause_lower:
            tactic = "Convert unilateral termination rights into mutual rights or conditional notice requirements."
            text = "Either party may terminate upon 30 days’ written notice if the other party materially breaches and fails to cure the breach within 15 days."
        else:
            tactic = "Propose standard balanced contract language to reduce ambiguity."
            text = "The contract terms shall be clarified to ensure obligations are mutual, risks are limited, and obligations are enforceable."

        if clause_type not in seen:
            suggestions.append(
                {
                    "clause_type": clause_type,
                    "proposed_text": text,
                    "negotiation_tactic": tactic,
                }
            )
            seen.add(clause_type)

    for issue in compliance_report:
        status = issue.get("status", "Non-Compliant")
        clause_type = issue.get("clause_type", "Compliance")
        if status.lower() != "compliant" and clause_type not in seen:
            suggestions.append(
                {
                    "clause_type": clause_type,
                    "proposed_text": "Update the clause to address compliance gaps and align with the applicable framework.",
                    "negotiation_tactic": f"Address the {clause_type} gap by incorporating compliant language and controls.",
                }
            )
            seen.add(clause_type)

    if not suggestions:
        suggestions.append(
            {
                "clause_type": "General",
                "proposed_text": "Add or improve the clauses that are missing or present the highest risk.",
                "negotiation_tactic": "Focus on balancing contractual obligations and reducing liability exposure.",
            }
        )
    return suggestions


def negotiation_node(state: AgentState) -> Dict[str, Any]:
    risk_matrix = state.get("risk_matrix", [])
    compliance_report = state.get("compliance_report", [])
    if not risk_matrix:
        risk_result = risk_analysis_node(state)
        risk_matrix = risk_result.get("risk_matrix", [])

    next_agent = "end"
    prompt = """
You are a Negotiation Agent. Review these risks and the compliance report, then provide concrete counter-party draft redline sentences to mitigate them.
Format your response strictly as a JSON object containing a "negotiations" array:
{{
  "negotiations": [
    {{
      "clause_type": "...",
      "proposed_text": "...",
      "negotiation_tactic": "..."
    }}
  ]
}}
Do not add markdown formatting or anything outside the JSON block.

Risk Matrix:
{risk_matrix}

Compliance Report:
{compliance_report}
"""

    negotiation_suggestions: List[Dict[str, Any]] = []
    try:
        from app.services.llm_service import LLMService
        res_text, _ = LLMService.invoke(
            prompt,
            {
                "risk_matrix": json.dumps(risk_matrix, indent=2),
                "compliance_report": json.dumps(compliance_report, indent=2)
            },
            require_json=True
        )
        logger.debug("\nRAW NEGOTIATION RESPONSE:\n%s", res_text)
        parsed = parse_json_safe(res_text, {})
        if isinstance(parsed, dict) and "error" in parsed:
            raise ValueError(f"JSON Parsing Failed in Negotiation: {parsed['reason']}\nRaw Output:\n{parsed['raw_response']}")

        negotiation_list = parsed.get("negotiations", []) if isinstance(parsed, dict) else []
        if isinstance(negotiation_list, list):
            for item in negotiation_list:
                if isinstance(item, dict):
                    negotiation_suggestions.append(
                        {
                            "clause_type": item.get("clause_type", "Unknown"),
                            "proposed_text": item.get("proposed_text", ""),
                            "negotiation_tactic": item.get("negotiation_tactic", ""),
                        }
                    )
    except Exception as e:
        logger.exception("NEGOTIATION ANALYSIS ERROR: %s", str(e))

    if not negotiation_suggestions:
        negotiation_suggestions = build_negotiation_suggestions(risk_matrix, compliance_report)

    logger.info("Current Node: negotiation_node | Next Node: %s", next_agent)
    logger.info("Clause Count: %d | Risk Count: %d | Compliance Count: %d | Negotiation Count: %d",
                len(state.get('extracted_clauses', [])), len(risk_matrix), len(compliance_report), len(negotiation_suggestions))

    return {**state, "negotiation_suggestions": negotiation_suggestions, "next_agent": next_agent}


def judge_node(state: AgentState) -> Dict[str, Any]:
    iterations = state.get("iterations", 0) or 0
    iterations += 1

    next_agent = state.get("next_agent", "end")
    if next_agent is None:
        next_agent = "end"
    else:
        next_agent = str(next_agent).lower().strip()

    if iterations > 10:
        logger.warning("Max supervisor iterations (10) exceeded. Terminating to prevent infinite loop.")
        next_agent = "end"

    valid_agents = ["analysis", "extraction", "risk", "compliance", "negotiation", "end"]
    if next_agent not in valid_agents:
        logger.warning("Invalid next_agent routed: '%s'. Forcing destination 'end'.", next_agent)
        next_agent = "end"

    logger.info("Current Node: judge_node | Next Node: %s | Iterations: %d", next_agent, iterations)
    return {**state, "next_agent": next_agent, "iterations": iterations}
