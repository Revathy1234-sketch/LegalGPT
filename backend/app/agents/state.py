from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):
    contract_id: str
    query: str
    messages: List[Dict[str, str]]  # History: [{"role": "user", "content": "..."}, ...]
    contract_text: Optional[str]
    extracted_clauses: List[Dict[str, Any]]
    risk_matrix: List[Dict[str, Any]]
    compliance_report: List[Dict[str, Any]]
    negotiation_suggestions: List[Dict[str, Any]]
    comparison_data: Optional[Dict[str, Any]]
    knowledge_graph_data: Dict[str, Any]
    next_agent: str
    evaluation_feedback: Optional[str]
    final_response: str
    iterations: Optional[int]
