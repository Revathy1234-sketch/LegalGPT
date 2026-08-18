from typing import Dict, Any, Optional, Tuple
import time
import math

def convert_to_react_flow(entities: list, relationships: list) -> Tuple[list, list]:
    nodes = []
    edges = []
    n = len(entities)
    r = 250 # layout radius

    for i, entity in enumerate(entities):
        if not isinstance(entity, dict):
            continue
        ent_id = entity.get("id") or f"entity_{i}"
        ent_type = entity.get("type", "UNKNOWN")
        name = entity.get("name") or entity.get("description") or ent_id

        # Calculate circular position
        angle = (2 * math.pi * i) / n if n > 0 else 0
        x = 400 + r * math.cos(angle)
        y = 300 + r * math.sin(angle)

        node = {
            "id": ent_id,
            "type": "custom" if ent_type in ["PARTY", "OBLIGATION"] else "default",
            "data": {
                "label": name,
                "type": ent_type,
                **{k: v for k, v in entity.items() if k not in ["id", "type"]}
            },
            "position": {"x": round(x, 1), "y": round(y, 1)}
        }
        nodes.append(node)

    for i, rel in enumerate(relationships):
        if not isinstance(rel, dict):
            continue
        source = rel.get("source")
        target = rel.get("target")
        rel_type = rel.get("type", "RELATED_TO")

        if not source or not target:
            continue

        edge_id = rel.get("id") or f"e_{source}_{target}_{i}"
        edge = {
            "id": edge_id,
            "source": source,
            "target": target,
            "label": rel_type,
            "animated": True,
            "data": {
                "type": rel_type,
                **{k: v for k, v in rel.items() if k not in ["source", "target", "type", "id"]}
            }
        }
        edges.append(edge)

    return nodes, edges


from langchain.prompts import PromptTemplate
from app.services.llm_service import LLMService

from app.agents.agent_utils import safe_parse_json
from app.agents.prompts.knowledge_graph_prompt import KNOWLEDGE_GRAPH_PROMPT
from app.agents.retrieval_agent import retrieve as retrieve_contract_context
from app.schemas.enterprise_schemas import AgentType
from app.utils.agent_wrapper import enterprise_agent_wrapper, AgentResponseBuilder
from app.utils.enterprise_utils import sanitize_reasoning_summary, sanitize_warning_message, log_exception_context


@enterprise_agent_wrapper(AgentType.KNOWLEDGE_GRAPH)
def run_knowledge_graph_agent(
    contract_id: str,
    top_k: int = 8,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extract entities and relationships from contract.

    Args:
        contract_id: Contract identifier
        top_k: Number of top chunks to retrieve
        request_id: Optional request ID for tracing

    Returns:
        Enterprise response with entities and relationships
    """
    retrieval_start = time.time()
    retrieval = retrieve_contract_context(contract_id, "*", top_k=top_k)
    retrieval_time_ms = int((time.time() - retrieval_start) * 1000)

    total_chunks = retrieval.get("total_chunks", 0)
    contract_text = retrieval.get("context", "")

    if total_chunks == 0 or not contract_text.strip():
        return AgentResponseBuilder.success(
            result={
                "entities": [],
                "relationships": [],
                "statistics": {"entity_count": 0, "relationship_count": 0}
            },
            retrieval_result=retrieval,
            reasoning_summary="Insufficient contract context was retrieved to provide a reliable answer.",
            retrieval_time_ms=retrieval_time_ms,
        )

    prompt = PromptTemplate(
        input_variables=["contract_text"],
        template=KNOWLEDGE_GRAPH_PROMPT,
    )

    llm_start = time.time()
    try:
        raw, token_usage = LLMService.invoke(prompt, {"contract_text": contract_text}, require_json=True)
    except Exception as exc:
        log_exception_context("knowledge_graph", exc)
        return AgentResponseBuilder.success(
            result={"entities": [], "relationships": [], "statistics": {"entity_count": 0, "relationship_count": 0}},
            retrieval_result=retrieval, reasoning_summary=sanitize_reasoning_summary(str(exc)),
            retrieval_time_ms=retrieval_time_ms,
            llm_time_ms=int((time.time() - llm_start) * 1000), warnings=[sanitize_warning_message(str(exc))],
        )
    llm_time_ms = int((time.time() - llm_start) * 1000)

    parsed = safe_parse_json(raw, {})
    if isinstance(parsed, str):
        parsed = safe_parse_json(parsed, {})

    if isinstance(parsed, dict) and parsed:
        if "entities" not in parsed or not isinstance(parsed["entities"], list):
            parsed["entities"] = []
        if "relationships" not in parsed or not isinstance(parsed["relationships"], list):
            parsed["relationships"] = []

        # Ensure each entity has a confidence score
        if isinstance(parsed["entities"], list):
            for entity in parsed["entities"]:
                if isinstance(entity, dict) and "confidence_score" not in entity:
                    entity["confidence_score"] = 0.85

        nodes, edges = convert_to_react_flow(parsed["entities"], parsed["relationships"])
        parsed["nodes"] = nodes
        parsed["edges"] = edges
        parsed["statistics"] = {
            "entity_count": len(parsed["entities"]),
            "relationship_count": len(parsed["relationships"]),
            "node_count": len(nodes),
            "edge_count": len(edges)
        }

        return AgentResponseBuilder.success(
            result=parsed,
            retrieval_result=retrieval,
            reasoning_summary="Entities and relationships extracted from contract",
            retrieval_time_ms=retrieval_time_ms,
            llm_time_ms=llm_time_ms,
            **token_usage,
        )

    # Fallback
    fallback_result = {
        "entities": [],
        "relationships": [],
        "nodes": [],
        "edges": [],
        "statistics": {"entity_count": 0, "relationship_count": 0, "node_count": 0, "edge_count": 0}
    }
    return AgentResponseBuilder.success(
        result=fallback_result,
        retrieval_result=retrieval,
        reasoning_summary="Knowledge graph returned default structure",
        retrieval_time_ms=retrieval_time_ms,
        llm_time_ms=llm_time_ms,
        **token_usage,
        warnings=["Response parsing returned fallback structure"],
    )
