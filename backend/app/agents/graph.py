from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.nodes import (
    contract_analysis_node,
    clause_extraction_node,
    risk_analysis_node,
    compliance_node,
    negotiation_node,
    judge_node
)

# Initialize graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("analysis", contract_analysis_node)
workflow.add_node("extraction", clause_extraction_node)
workflow.add_node("risk", risk_analysis_node)
workflow.add_node("compliance", compliance_node)
workflow.add_node("negotiation", negotiation_node)
workflow.add_node("judge", judge_node)

# Start the graph based on the requested next_agent

def route_start(state: AgentState):
    return state.get("next_agent", "analysis")

# Define routing conditional logic
def route_judge(state: AgentState):
    return state.get("next_agent", "end")

workflow.set_conditional_entry_point(
    route_start,
    {
        "analysis": "analysis",
        "extraction": "extraction",
        "risk": "risk",
        "compliance": "compliance",
        "negotiation": "negotiation",
    },
)

# Connect edges to the central judge node
workflow.add_edge("analysis", "judge")
workflow.add_edge("extraction", "judge")
workflow.add_edge("risk", "judge")
workflow.add_edge("compliance", "judge")
workflow.add_edge("negotiation", "judge")

# Judge routes back to agents or finishes execution
workflow.add_conditional_edges(
    "judge",
    route_judge,
    {
        "analysis": "analysis",
        "extraction": "extraction",
        "risk": "risk",
        "compliance": "compliance",
        "negotiation": "negotiation",
        "end": END,
    },
)
agent_graph = workflow.compile()