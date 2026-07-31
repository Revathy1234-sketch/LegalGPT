"""LangGraph-style Supervisor for LegalGPT.

This supervisor orchestrates the existing agent nodes in `app.agents.nodes` using
simple sequential orchestration and returns structured JSON outputs per the
master prompts provided by the user.

Note: This is a non-blocking, local orchestrator that doesn't call an external
"LangGraph" runtime; it reuses the project's node functions.
"""
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END

from app.agents import (
    retrieval_agent,
    summary_agent,
    clause_agent,
    risk_agent,
    compliance_agent,
    negotiation_agent,
    comparison_agent,
    chat_agent,
    knowledge_graph_agent,
)
from app.agents.nodes import (
    clause_extraction_node,
    risk_analysis_node,
    compliance_node,
    negotiation_node,
    contract_analysis_node,
)

MASTER_PROMPT = """
You are LegalGPT Enterprise Supervisor.

Your responsibility is to orchestrate specialized legal AI agents.

Available Agents:

1. Clause Extraction Agent
2. Risk Analysis Agent
3. Compliance Agent
4. Negotiation Agent
5. Contract Comparison Agent
6. Executive Summary Agent
7. Contract Chat Agent
8. Compliance Engine Agent
9. Knowledge Graph Agent
Always retrieve contract context from the RAG retrieval layer before performing analysis.

Rules:

- Never invent contract content.
- Use only retrieved contract context.
- If information is unavailable, explicitly state that it is not found in the contract.
- Return structured JSON responses.
- Provide confidence scores whenever applicable.
- Highlight high-risk issues.
- Prioritize legal accuracy over verbosity.
- Preserve clause references whenever possible.
- Generate actionable recommendations.
- Ensure outputs are suitable for lawyers, compliance teams, procurement teams, and business executives.
The final response should be professional, structured, explainable, and auditable.
"""


def _assemble_contract_text(chunks: List[Dict[str, Any]]) -> str:
    # Prefer parent_text deduplicated by parent_id, else fall back to child_text
    seen = set()
    parts: List[str] = []
    for c in chunks:
        pid = c.get("parent_id") or c.get("child_id")
        if pid in seen:
            continue
        seen.add(pid)
        text = c.get("parent_text") or c.get("child_text") or ""
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def run_supervisor(contract_id: str, query: str = "full_workflow", top_k: int = 50) -> Dict[str, Any]:
    """Run the orchestrated workflow over a contract and return agent outputs.

    Args:
        contract_id: identifier of the indexed contract (matches vector_service)
        query: routing hint (e.g., "full_workflow", "risk_only", "clauses_only")
        top_k: number of chunks to retrieve from the RAG layer

    Returns:
        Dict containing structured outputs from Clause Extraction, Risk Analysis,
        Compliance, Negotiation, and an Executive Summary.
    """
    chunks = retrieval_agent.retrieve_context(contract_id, top_k=top_k)
    contract_text = _assemble_contract_text(chunks)

    base_state = {"contract_text": contract_text, "query": query}

    # Clause extraction
    extraction_out = clause_extraction_node(base_state)
    extracted_clauses = extraction_out.get("extracted_clauses", [])

    # Risk analysis (uses extracted clauses)
    risk_state = {**base_state, "extracted_clauses": extracted_clauses}
    risk_out = risk_analysis_node(risk_state)
    risk_matrix = risk_out.get("risk_matrix", [])
    overall_score = risk_out.get("overall_score", 0)

    # Compliance analysis
    compliance_state = {**risk_state, "risk_matrix": risk_matrix}
    compliance_out = compliance_node(compliance_state)
    compliance_report = compliance_out.get("compliance_report", [])

    # Negotiation suggestions
    negotiation_state = {**compliance_state, "compliance_report": compliance_report}
    negotiation_out = negotiation_node(negotiation_state)
    negotiation_suggestions = negotiation_out.get("negotiation_suggestions", [])

    # Executive summary / contract analysis
    analysis_state = {**base_state}
    analysis_out = contract_analysis_node(analysis_state)
    executive_summary_text = analysis_out.get("final_response", "")

    result = {
        "contract_id": contract_id,
        "query": query,
        "executive_summary": executive_summary_text,
        "clauses": extracted_clauses,
        "risk": {
            "overall_score": overall_score,
            "risk_matrix": risk_matrix,
        },
        "compliance": {
            "report": compliance_report,
        },
        "negotiation": {
            "suggestions": negotiation_suggestions,
        },
        "retrieved_chunks_count": len(chunks),
    }

    return result


if __name__ == "__main__":
    # quick local smoke test (won't run external LLMs during test)
    import json
    print(json.dumps(run_supervisor("example_contract", "full_workflow", top_k=3), indent=2))

