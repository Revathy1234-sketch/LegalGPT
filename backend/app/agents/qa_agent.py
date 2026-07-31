from typing import Dict, Any, List
from app.agents.nodes import contract_analysis_node
from app.agents.retrieval_agent import retrieve_context as fetch_context


def retrieve_context(contract_id: str, top_k: int = 10) -> List[Dict[str, Any]]:
    return fetch_context(contract_id, top_k)


def build_prompt(question: str, context: str) -> Dict[str, Any]:
    return {"contract_text": context, "query": question}


def call_gemini(state: Dict[str, Any]) -> Dict[str, Any]:
    return contract_analysis_node(state)


def return_structured_output(node_output: Dict[str, Any]) -> Dict[str, Any]:
    return {"final_response": node_output.get("final_response", "")}
