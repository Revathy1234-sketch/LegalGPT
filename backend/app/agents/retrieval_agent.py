"""Reusable retrieval layer for agent workflows.

This module centralizes hybrid retrieval behavior so agents can consume a
consistent, structured retrieval payload without reimplementing the same logic.
"""
from time import perf_counter
from app.services.hybrid_retriever import HybridRetriever
from typing import Any, Dict, List

from app.services.vector_service import vector_service


class RetrievalAgent:
    """Encapsulates retrieval, deduplication, context assembly, and metrics."""

    def __init__(self):
        self._retriever = HybridRetriever(vector_service)

    def retrieve(self, contract_id: str, query: str, top_k: int = 10) -> Dict[str, Any]:
        return self._retriever.retrieve(query=query, contract_id=contract_id, top_k=top_k)

    def _legacy_retrieve(self, contract_id: str, query: str, top_k: int = 10) -> Dict[str, Any]:
        """Execute hybrid retrieval and return a normalized retrieval payload."""
        started_at = perf_counter()
        sources = vector_service.search_contract(contract_id, query, top_k=top_k)
        elapsed_ms = int(round((perf_counter() - started_at) * 1000))

        chunks = self._deduplicate_parent_chunks(sources)
        context = self._assemble_context(chunks)

        metadata = {
            "retrieved_chunks": len(sources),
            "semantic_matches": sum(1 for chunk in sources if chunk.get("relevance_source") == "semantic"),
            "bm25_matches": sum(1 for chunk in sources if chunk.get("relevance_source") == "bm25"),
            "retrieval_time_ms": elapsed_ms,
            "total_parent_chunks": len({chunk.get("parent_id") for chunk in chunks if chunk.get("parent_id")}),
            "total_child_chunks": len(chunks),
        }

        return {
            "context": context,
            "chunks": chunks,
            "sources": sources,
            "metadata": metadata,
        }

    @staticmethod
    def _deduplicate_parent_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Keep the highest-scoring chunk for each parent while preserving order."""
        selected: List[Dict[str, Any]] = []
        seen_parents: set[str] = set()

        for chunk in chunks:
            parent_id = chunk.get("parent_id")
            if parent_id and parent_id in seen_parents:
                continue
            if parent_id:
                seen_parents.add(parent_id)
            selected.append(chunk)

        return selected

    @staticmethod
    def _assemble_context(chunks: List[Dict[str, Any]]) -> str:
        """Assemble a readable context string from deduplicated chunks."""
        parts: List[str] = []
        for chunk in chunks:
            text = chunk.get("parent_text") or chunk.get("child_text") or ""
            if text and text not in parts:
                parts.append(text)
        return "\n\n".join(parts)


def retrieve(contract_id: str, query: str, top_k: int = 10) -> Dict[str, Any]:
    """Module-level entry point for retrieval workflows."""
    return retrieval_agent.retrieve(contract_id=contract_id, query=query, top_k=top_k)


def retrieve_context(contract_id: str, top_k: int = 10) -> List[Dict[str, Any]]:
    """Backward-compatible helper for callers expecting a chunk list."""
    return retrieve(contract_id=contract_id, query="*", top_k=top_k).get("chunks", [])


retrieval_agent = RetrievalAgent()
