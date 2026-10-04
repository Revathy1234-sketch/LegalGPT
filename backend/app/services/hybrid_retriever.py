"""
Production Hybrid Retriever Service

Orchestrates the complete retrieval pipeline:
Query → Expansion → Semantic → BM25 → Merge → Ranking → Dedup → Results
"""

import logging
import time
from typing import List, Dict, Any, Tuple, Optional
from app.core.retrieval_config import RETRIEVAL_CONFIG, PERFORMANCE_TARGETS
from app.services.query_expander import QueryExpander
from app.services.bm25_retriever import BM25Retriever
from app.services.context_ranker import ContextRanker
from app.services.context_assembler import  ContextAssembler, DeduplicationMetrics

logger = logging.getLogger("legalgpt.retrieval.hybrid")


class RetrievalMetrics:
    def __init__(self, values=None):
        self.values = dict(values or {})
    def update(self, **values):
        self.values.update(values)
    def to_dict(self):
        return dict(self.values)


class HybridRetriever:
    """
    Hybrid retrieval combining semantic and keyword-based search.
    
    Pipeline:
    1. Query Cleaning & Expansion (deterministic legal synonym expansion)
    2. Semantic Retrieval (FAISS semantic search)
    3. Keyword Retrieval (BM25 keyword search)
    4. Score Merging (weighted combination)
    5. Context Ranking (multi-factor ranking)
    6. Deduplication (parent chunk assembly)
    7. Final Selection (top-k results)
    """

    def __init__(self, semantic_retriever=None):
        """
        Initialize hybrid retriever.
        
        Args:
            semantic_retriever: Existing semantic retriever (FAISS)
        """
        self.semantic_retriever = semantic_retriever
        self.query_expander = QueryExpander()
        self.bm25_retriever = BM25Retriever()
        self.ranker = ContextRanker()
        self.assembler = ContextAssembler()
        
        # Configuration
        self.semantic_weight = 0.6
        self.keyword_weight = 0.4
        self.min_combined_score = RETRIEVAL_CONFIG["min_combined_score"]

    @staticmethod
    def _is_browse_query(query: str) -> bool:
        """Wildcard/empty queries mean "give me the whole document"."""
        return (query or "").strip().lower() in {"", "*", "**", "all", "document"}

    def _browse_retrieve(
        self,
        contract_id: str,
        top_k: int,
        retrieval_metadata: Dict[str, Any],
        total_start: float,
    ) -> Dict[str, Any]:
        """Full-document coverage mode.

        Analysis agents (risk, clauses, compliance, negotiation) ask for "*"
        because they need the whole contract, not a semantic match. Scoring a
        wildcard like a normal query drops almost everything below the ranking
        thresholds, leaving agents with a single chunk and empty results.
        This mode returns parent chunks evenly spread across the document.
        """
        from app.core.config import settings

        raw_chunks: List[Dict[str, Any]] = []
        if self.semantic_retriever and hasattr(self.semantic_retriever, "_load_chunks"):
            try:
                raw_chunks = self.semantic_retriever._load_chunks(str(contract_id)) or []
            except Exception as exc:  # noqa: BLE001
                logger.error("Browse-mode chunk loading failed: %s", exc)
                raw_chunks = []

        # Deduplicate children into parents, preserving document order.
        parents: List[Dict[str, Any]] = []
        seen: set = set()
        for chunk in raw_chunks:
            parent_id = chunk.get("parent_id") or chunk.get("child_id")
            if parent_id in seen:
                continue
            seen.add(parent_id)
            parents.append(chunk)

        target = max(int(top_k), 12)
        if len(parents) > target:
            step = (len(parents) - 1) / max(target - 1, 1)
            indexes = sorted({round(i * step) for i in range(target)})
            parents = [parents[i] for i in indexes]

        final_chunks: List[Dict[str, Any]] = []
        for idx, parent in enumerate(parents):
            final_chunks.append({
                "id": parent.get("child_id") or f"browse_{idx}",
                "child_id": parent.get("child_id"),
                "parent_id": parent.get("parent_id"),
                "child_text": parent.get("child_text"),
                "parent_text": parent.get("parent_text"),
                "content": parent.get("parent_text") or parent.get("child_text") or "",
                "metadata": {},
                "_scoring": {
                    "semantic_score": 0.0,
                    "keyword_score": 0.0,
                    "combined_score": 1.0,
                },
                "retrieval_method": "browse",
            })

        context = self._assemble_context(final_chunks)
        if len(context) > settings.MAX_SUMMARY_CHARS:
            context = context[: settings.MAX_SUMMARY_CHARS]

        total_time_ms = int((time.time() - total_start) * 1000)
        retrieval_metadata.update({
            "mode": "browse",
            "total_retrieval_time_ms": total_time_ms,
            "returned_chunks": len(final_chunks),
            "parent_ids": [c.get("parent_id") for c in final_chunks],
        })
        logger.info(
            "retrieval pipeline (browse) | contract=%s | parents=%s | ms=%s",
            contract_id, len(final_chunks), total_time_ms,
        )

        return {
            "metadata": retrieval_metadata,
            "parent_chunks": final_chunks,
            "child_chunks": final_chunks,
            "retrieval_time_ms": total_time_ms,
            "total_chunks": len(final_chunks),
            "total_chunks_deduplicated": len(final_chunks),
            "semantic_match_count": 0,
            "bm25_match_count": 0,
            "top_retrieval_score": 1.0,
            "context": context,
            "chunks": final_chunks,
            "retrieval_metadata": retrieval_metadata,
            "sources": [
                {
                    "parent_id": c.get("parent_id"),
                    "child_id": c.get("child_id"),
                    "score": 1.0,
                    "section": c.get("metadata", {}).get("section_number"),
                }
                for c in final_chunks
            ],
        }

    def retrieve(
        self,
        query: str,
        contract_id: str,
        top_k: int = 10,
        use_query_expansion: bool = True,
        use_bm25: bool = True,
        deduplicate: bool = True,
        return_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieve context using hybrid retrieval pipeline.
        
        Args:
            query: User query
            contract_id: Contract identifier
            top_k: Number of top results
            use_query_expansion: Whether to expand query with synonyms
            use_bm25: Whether to use BM25 keyword retrieval
            deduplicate: Whether to deduplicate parent chunks
            return_metadata: Whether to return retrieval metadata
            
        Returns:
            Dictionary with context and metadata
        """
        total_start = time.time()
        retrieval_metadata = {
            "query": query,
            "contract_id": str(contract_id),
            "requested_top_k": top_k,
        }

        # Wildcard / empty queries are browse requests from analysis agents:
        # return document-wide coverage instead of scoring a meaningless query.
        if self._is_browse_query(query):
            try:
                return self._browse_retrieve(contract_id, top_k, retrieval_metadata, total_start)
            except Exception as browse_exc:  # noqa: BLE001
                logger.error("Browse retrieval failed: %s", browse_exc, exc_info=True)
        
        try:
            # Step 1: Query Expansion
            expansion_start = time.time()
            if use_query_expansion:
                _cleaned_query, expansions = self.query_expander.expand_query(query)
                expanded_query = self.query_expander.build_expanded_query(query)
                retrieval_metadata["query_expansions"] = expansions
            else:
                expanded_query = query
            
            expansion_time_ms = int((time.time() - expansion_start) * 1000)
            retrieval_metadata["expansion_time_ms"] = expansion_time_ms
            
            # Step 2: Semantic Retrieval (FAISS)
            semantic_start = time.time()
            semantic_results, semantic_chunks = self._semantic_retrieve(
                query if not use_query_expansion else expanded_query,
                contract_id,
                top_k * 2  # Retrieve more for better merging
            )
            semantic_time_ms = int((time.time() - semantic_start) * 1000)
            retrieval_metadata["semantic_time_ms"] = semantic_time_ms
            retrieval_metadata["semantic_results_count"] = len(semantic_results)
            
            # Step 3: Keyword Retrieval (BM25)
            keyword_results = {}
            keyword_time_ms = 0
            if use_bm25:
                keyword_start = time.time()
                keyword_results = self._keyword_retrieve(
                    query if not use_query_expansion else expanded_query,
                    semantic_chunks,
                    top_k * 2
                )
                keyword_time_ms = int((time.time() - keyword_start) * 1000)
                retrieval_metadata["keyword_time_ms"] = keyword_time_ms
                retrieval_metadata["keyword_results_count"] = len(keyword_results)
            
            # Step 4: Merge Results
            merged_scores = self._merge_scores(
                semantic_results,
                keyword_results,
                self.semantic_weight,
                self.keyword_weight
            )
            
            # Step 5: Context Ranking
            ranking_start = time.time()
            ranked_chunks = self.ranker.rank_chunks(
                semantic_chunks,
                query,
                semantic_results,
                keyword_results,
                top_k * 2
            )
            ranking_time_ms = int((time.time() - ranking_start) * 1000)
            retrieval_metadata["ranking_time_ms"] = ranking_time_ms
            
            # Step 6: Deduplication
            dedupe_start = time.time()
            if deduplicate:
                deduplicated_chunks, parent_mapping = self.assembler.deduplicate_by_parent(
                    ranked_chunks,
                    self.min_combined_score
                )
                retrieval_metadata["parent_mapping"] = parent_mapping
            else:
                deduplicated_chunks = ranked_chunks
            
            dedupe_time_ms = int((time.time() - dedupe_start) * 1000)
            retrieval_metadata["deduplication_time_ms"] = dedupe_time_ms
            
            # Step 7: Final Selection
            final_chunks = deduplicated_chunks[:top_k]

            # Preserve how each returned chunk was actually matched so citation
            # metadata and retrieval metadata describe the same result set.
            for chunk in final_chunks:
                scoring = chunk.get('_scoring', {})
                has_semantic = scoring.get('semantic_score', 0.0) > 0
                has_bm25 = scoring.get('keyword_score', 0.0) > 0
                chunk['retrieval_method'] = (
                    'hybrid' if has_semantic and has_bm25
                    else 'semantic' if has_semantic
                    else 'bm25' if has_bm25
                    else 'hybrid'
                )
            
            # Step 8: Assemble Context
            context = self._assemble_context(final_chunks)
            
            # Step 9: Build Metadata
            total_time_ms = int((time.time() - total_start) * 1000)
            retrieval_metadata["total_retrieval_time_ms"] = total_time_ms
            retrieval_metadata["total_chunks_retrieved"] = len(semantic_chunks)
            retrieval_metadata["total_chunks_deduplicated"] = len(deduplicated_chunks)
            retrieval_metadata["returned_chunks"] = len(final_chunks)
            retrieval_metadata["semantic_match_count"] = len(semantic_results)
            retrieval_metadata["bm25_match_count"] = len(keyword_results)
            retrieval_metadata["top_retrieval_score"] = (
                final_chunks[0]["_scoring"]["combined_score"]
                if final_chunks and "_scoring" in final_chunks[0]
                else 0.0
            )
            retrieval_metadata.update({
                'retrieval_time_ms': total_time_ms,
                'semantic_matches': len(semantic_results),
                'bm25_matches': len(keyword_results),
                'retrieval_score': retrieval_metadata['top_retrieval_score'],
                'chunk_scores': [c.get('_scoring', {}) for c in final_chunks],
                'parent_ids': [c.get('parent_id') for c in final_chunks],
                'child_ids': [c.get('child_id') or c.get('id') for c in final_chunks],
                'retrieved_chunk_count': len(semantic_chunks),
                'deduplicated_chunk_count': len(final_chunks),
                'faiss_latency_ms': semantic_time_ms,
                'bm25_latency_ms': keyword_time_ms,
            })

            # Log timing
            self._log_retrieval_timing(retrieval_metadata)
            logger.info('retrieval_scores scores=%s', retrieval_metadata['chunk_scores'])
            
            return {
                'metadata': retrieval_metadata if return_metadata else {},
                # Canonical result collections and metrics are exposed alongside
                # the detailed metadata mapping for enterprise-wrapper consumers.
                'parent_chunks': final_chunks if return_metadata else [],
                'child_chunks': semantic_chunks if return_metadata else [],
                'retrieval_time_ms': total_time_ms,
                'total_chunks': len(semantic_chunks),
                'total_chunks_deduplicated': len(final_chunks),
                'semantic_match_count': len(semantic_results),
                'bm25_match_count': len(keyword_results),
                'top_retrieval_score': retrieval_metadata['top_retrieval_score'],
                "context": context,
                "chunks": final_chunks if return_metadata else [],
                "retrieval_metadata": retrieval_metadata if return_metadata else {},
                "sources": [  {
        "parent_id": c.get("parent_id"),
        "child_id": c.get("child_id"),
        "score": c.get("_scoring", {}).get("combined_score", 0),
        "section": c.get("metadata", {}).get("section_number")
    }
    for c in final_chunks],
            }
        
        except Exception as e:
            logger.error(f"Hybrid retrieval failed: {str(e)}", exc_info=True)
            return {
                "context": "",
                "chunks": [],
                "retrieval_metadata": {
                    **retrieval_metadata,
                    "error": str(e),
                    "total_retrieval_time_ms": int((time.time() - total_start) * 1000)
                },
                "sources": [],
            }

    def _semantic_retrieve(
        self,
        query: str,
        contract_id: str,
        top_k: int
    ) -> Tuple[Dict[int, float], List[Dict[str, Any]]]:
        """
        Perform semantic retrieval using FAISS.
        
        Args:
            query: Query string
            contract_id: Contract ID
            top_k: Number of results
            
        Returns:
            Tuple of (scores_dict, chunks_list)
        """
        if not self.semantic_retriever:
            logger.warning("Semantic retriever not configured")
            return {}, []
        
        try:
            # Call existing semantic retriever
            # This integrates with the current FAISS-based retrieval
            results = self.semantic_retriever.search_contract(
                str(contract_id),
                query,
                top_k=top_k
            )
            
            # Convert to internal format
            chunks = []
            scores = {}
            
            for idx, result in enumerate(results):
                chunk_id = result.get("id", f"chunk_{idx}")
                score = result.get("score", 0.0)
                
                scores[chunk_id] = max(0.0, min(score, 1.0))  # Normalize to 0-1
                
                chunk = {
                    "id": chunk_id,
    "child_id": result.get("child_id"),
    "parent_id": result.get("parent_id"),
    "child_text": result.get("child_text"),
    "parent_text": result.get("parent_text"),
    "content": result.get("parent_text") or result.get("child_text"),
    "metadata": result,
                }
                chunks.append(chunk)
            
            return scores, chunks
        
        except Exception as e:
            logger.error(f"Semantic retrieval error: {str(e)}")
            return {}, []

    def _keyword_retrieve(
        self,
        query: str,
        semantic_chunks: List[Dict[str, Any]],
        top_k: int
    ) -> Dict[int, float]:
        """
        Perform keyword retrieval using BM25.
        
        Args:
            query: Query string
            semantic_chunks: Chunks from semantic retrieval
            top_k: Number of results
            
        Returns:
            Dictionary of chunk_id -> BM25 score
        """
        if not semantic_chunks:
            return {}
        
        try:
            # Index chunks if not already indexed
            contents = [c.get("content", "") for c in semantic_chunks]
            self.bm25_retriever.index(contents)
            
            # Retrieve using BM25
            results = self.bm25_retriever.retrieve(query, top_k)
            
            # Convert to dictionary
            scores = {}
            for doc_idx, score in results:
                if doc_idx < len(semantic_chunks):
                    chunk_id = semantic_chunks[doc_idx].get("id", f"chunk_{doc_idx}")
                    scores[chunk_id] = max(0.0, min(score, 1.0))  # Normalize
            
            return scores
        
        except Exception as e:
            logger.error(f"BM25 retrieval error: {str(e)}")
            return {}

    def _merge_scores(
        self,
        semantic_scores: Dict[int, float],
        keyword_scores: Dict[int, float],
        semantic_weight: float,
        keyword_weight: float
    ) -> Dict[int, float]:
        """
        Merge semantic and keyword scores.
        
        Args:
            semantic_scores: Semantic similarity scores
            keyword_scores: BM25 keyword scores
            semantic_weight: Weight for semantic scores
            keyword_weight: Weight for keyword scores
            
        Returns:
            Merged scores dictionary
        """
        all_ids = set(semantic_scores.keys()) | set(keyword_scores.keys())
        merged = {}
        
        for chunk_id in all_ids:
            semantic = semantic_scores.get(chunk_id, 0.0)
            keyword = keyword_scores.get(chunk_id, 0.0)
            
            merged[chunk_id] = (
                semantic_weight * semantic +
                keyword_weight * keyword
            )
        
        return merged

    def _assemble_context(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Assemble final context string from chunks.
        
        Args:
            chunks: Final ranked chunks
            
        Returns:
            Combined context string
        """
        if not chunks:
            return ""
        
        # Combine content with separators
        content_parts = []
        for chunk in chunks:
            content = chunk.get("content", "")
            if content.strip():
                content_parts.append(content)
        
        return "\n\n".join(content_parts)

    def _log_retrieval_timing(self, metadata: Dict[str, Any]) -> None:
        """Log retrieval timing statistics."""
        logger.info(
            f"Retrieval pipeline | "
            f"query_len={len(metadata.get('query', ''))} | "
            f"expansion_ms={metadata.get('expansion_time_ms', 0)} | "
            f"semantic_ms={metadata.get('semantic_time_ms', 0)} | "
            f"keyword_ms={metadata.get('keyword_time_ms', 0)} | "
            f"ranking_ms={metadata.get('ranking_time_ms', 0)} | "
            f"dedup_ms={metadata.get('deduplication_time_ms', 0)} | "
            f"total_ms={metadata.get('total_retrieval_time_ms', 0)} | "
            f"chunks={metadata.get('returned_chunks', 0)}"
        )


def get_hybrid_retriever(semantic_retriever=None) -> HybridRetriever:
    """
    Get or create hybrid retriever singleton.
    
    Args:
        semantic_retriever: Semantic retriever instance
        
    Returns:
        HybridRetriever instance
    """
    if not hasattr(get_hybrid_retriever, "_instance"):
        get_hybrid_retriever._instance = HybridRetriever(semantic_retriever)
    return get_hybrid_retriever._instance
