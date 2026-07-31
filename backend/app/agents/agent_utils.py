"""Shared utilities for agents: model loader, retrieval helpers, and parsing.

Agents should import these helpers to keep behavior consistent.
"""
from typing import List, Dict, Any, Optional
import json

from app.services import langchain_rag_service
from app.agents.nodes import parse_json_safe
from app.agents.retrieval_agent import retrieve as retrieve_contract_context


def assemble_text_from_chunks(chunks: List[Dict[str, Any]]) -> str:
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


def retrieve_via_vector(contract_id: str, query: str = "*", top_k: int = 50) -> List[Dict[str, Any]]:
    retrieval = retrieve_contract_context(contract_id, query, top_k=top_k)
    return retrieval.get("chunks", [])


def retrieve_via_langchain_rag(contract_id: str, question: str, top_k: int = 10) -> Any:
    # Wrap call to existing langchain rag service which may return richer content
    try:
        return langchain_rag_service.ask(contract_id=contract_id, question=question)
    except Exception:
        return []


def safe_parse_json(text: str, default: Any = None) -> Any:
    return parse_json_safe(text, default)
