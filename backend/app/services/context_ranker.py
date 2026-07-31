"""
Context Ranker Service

Ranks retrieved chunks based on multiple relevance factors including
semantic similarity, keyword overlap, parent relevance, and chunk quality.
"""

import logging
import time
import re
from typing import List, Dict, Any, Tuple
from app.core.retrieval_config import RANKING_WEIGHTS, CHUNK_QUALITY_FACTORS

logger = logging.getLogger("legalgpt.retrieval.ranking")


class ContextRanker:
    """Ranks context chunks based on multiple relevance factors."""

    def __init__(self):
        """Initialize context ranker."""
        self.weights = RANKING_WEIGHTS
        self.quality_factors = CHUNK_QUALITY_FACTORS

    def rank_chunks(
        self,
        chunks: List[Dict[str, Any]],
        query: str,
        semantic_scores: Dict[int, float],
        keyword_scores: Dict[int, float],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Rank chunks based on multiple factors.
        
        Args:
            chunks: List of chunk dictionaries
            query: Original query
            semantic_scores: Semantic similarity scores (chunk_id -> score)
            keyword_scores: BM25 keyword scores (chunk_id -> score)
            top_k: Number of top chunks to return
            
        Returns:
            Ranked list of chunks with scores
        """
        start_time = time.time()
        
        ranked_chunks = []
        
        for chunk_idx, chunk in enumerate(chunks):
            chunk = chunk.copy()
            chunk['id'] = chunk.get('child_id') or chunk.get('id') or str(chunk_idx)
            chunk['content'] = chunk.get('content') or chunk.get('child_text') or ''
            chunk_id = chunk.get("id", str(chunk_idx))
            
            # Get component scores
            semantic_score = semantic_scores.get(chunk_id, 0.0)
            keyword_score = keyword_scores.get(chunk_id, 0.0)
            parent_score = self._calculate_parent_relevance(chunk)
            position_score = self._calculate_position_score(chunk)
            citation_score = self._calculate_citation_score(chunk)
            length_score = self._calculate_length_score(chunk)
            
            # Calculate weighted combined score
            combined_score = (
                self.weights["semantic_similarity"] * semantic_score +
                self.weights["keyword_overlap"] * keyword_score +
                self.weights["parent_relevance"] * parent_score +
                self.weights["chunk_position"] * position_score +
                self.weights["citation_density"] * citation_score +
                self.weights["length_normalization"] * length_score
            )
            
            # Add scoring metadata to chunk
            ranked_chunk = chunk.copy()
            ranked_chunk["_scoring"] = {
                "combined_score": combined_score,
                "semantic_score": semantic_score,
                "keyword_score": keyword_score,
                "parent_relevance": parent_score,
                "position_score": position_score,
                "citation_score": citation_score,
                "length_score": length_score,
            }
            
            ranked_chunks.append(ranked_chunk)
        
        # Sort by combined score descending
        ranked_chunks.sort(
            key=lambda x: x["_scoring"]["combined_score"],
            reverse=True
        )
        
        # Return top-k
        result = ranked_chunks[:top_k]
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.debug(
            f"Context ranking | total_chunks={len(chunks)} | "
            f"ranked={len(result)} | latency_ms={elapsed_ms}"
        )
        
        return result

    def _calculate_parent_relevance(self, chunk: Dict[str, Any]) -> float:
        """
        Calculate relevance boost based on parent chunk context.
        
        Args:
            chunk: Chunk dictionary
            
        Returns:
            Score 0.0-1.0
        """
        # Check if chunk has parent metadata
        if chunk.get("parent_id") or chunk.get("parent_content"):
            return 0.8
        
        # Chunks that are part of a series get boost
        if chunk.get("chunk_number") and chunk.get("total_chunks"):
            # Middle chunks (not first or last) are often most relevant
            if chunk.get("chunk_number") > 1 and chunk.get("chunk_number") < chunk.get("total_chunks", 0):
                return 0.6
        
        return 0.4

    def _calculate_position_score(self, chunk: Dict[str, Any]) -> float:
        """
        Calculate score based on position in document.
        
        Earlier chunks (closer to document start) often contain more relevant context.
        
        Args:
            chunk: Chunk dictionary
            
        Returns:
            Score 0.0-1.0
        """
        # Get position information
        chunk_number = chunk.get("chunk_number", 1)
        total_chunks = chunk.get("total_chunks", 1)
        
        # Calculate position ratio (0 = first, 1 = last)
        position_ratio = (chunk_number - 1) / max(total_chunks - 1, 1)
        
        # Prefer earlier chunks (negative exponential decay)
        score = 1.0 - (position_ratio ** 0.5)
        
        return max(0.0, min(score, 1.0))

    def _calculate_citation_score(self, chunk: Dict[str, Any]) -> float:
        """
        Calculate score based on citation/reference density.
        
        Chunks with more citations tend to be authoritative.
        
        Args:
            chunk: Chunk dictionary
            
        Returns:
            Score 0.0-1.0
        """
        content = chunk.get("content", "")
        
        # Count citations/references (common patterns)
        citation_patterns = [
            r'\d+\.\d+\.\d+',      # Section references (3.2.1)
            r'Article\s+\d+',       # Article references
            r'Section\s+\d+',       # Section references
            r'\[Exhibit [A-Z]\]',   # Exhibit references
            r'\(hereinafter.*?\)',  # Hereinafter references
        ]
        
        citation_count = 0
        for pattern in citation_patterns:
            citation_count += len(re.findall(pattern, content, re.IGNORECASE))
        
        # Normalize by content length
        content_words = len(content.split())
        if content_words == 0:
            return 0.0
        
        citations_per_1000_words = (citation_count / content_words) * 1000
        
        # Score based on citation density (optimal ~5 per 1000 words)
        if citations_per_1000_words > 10:
            return 1.0
        elif citations_per_1000_words > 5:
            return 0.8
        elif citations_per_1000_words > 2:
            return 0.6
        elif citations_per_1000_words > 0:
            return 0.4
        else:
            return 0.2

    def _calculate_length_score(self, chunk: Dict[str, Any]) -> float:
        """
        Calculate score based on chunk length quality.
        
        Optimal length chunks score highest.
        
        Args:
            chunk: Chunk dictionary
            
        Returns:
            Score 0.0-1.0
        """
        content = chunk.get("content", "")
        content_length = len(content)
        
        min_len = self.quality_factors["min_length"]
        max_len = self.quality_factors["max_length"]
        optimal_len = self.quality_factors["optimal_length"]
        
        # Too short or too long gets penalized
        if content_length < min_len or content_length > max_len:
            return 0.3
        
        # Optimal length gets highest score
        if abs(content_length - optimal_len) < optimal_len * 0.2:
            return 1.0
        
        # Linear falloff from optimal
        distance_from_optimal = abs(content_length - optimal_len)
        max_distance = max(optimal_len - min_len, max_len - optimal_len)
        
        score = 1.0 - (distance_from_optimal / max_distance)
        
        return max(0.3, min(score, 1.0))

    def get_ranking_breakdown(self, chunk: Dict[str, Any]) -> Dict[str, float]:
        """
        Get detailed ranking score breakdown for a chunk.
        
        Args:
            chunk: Ranked chunk with _scoring metadata
            
        Returns:
            Dictionary of component scores
        """
        if "_scoring" not in chunk:
            return {}
        
        return chunk["_scoring"]


class RankingOptimizer:
    """Optimizes ranking weights based on query characteristics."""

    def __init__(self):
        """Initialize ranking optimizer."""
        self.ranker = ContextRanker()

    def adjust_weights_for_query(self, query: str) -> Dict[str, float]:
        """
        Adjust ranking weights based on query type.
        
        Args:
            query: Query string
            
        Returns:
            Adjusted weights dictionary
        """
        adjusted = self.ranker.weights.copy()
        
        query_lower = query.lower()
        
        # Keyword-heavy queries (e.g., "what is", "define")
        if any(kw in query_lower for kw in ["what is", "define", "definition"]):
            adjusted["keyword_overlap"] = 0.35
            adjusted["semantic_similarity"] = 0.35
        
        # Clause/provision queries
        elif any(kw in query_lower for kw in ["clause", "provision", "section", "article"]):
            adjusted["parent_relevance"] = 0.25
            adjusted["semantic_similarity"] = 0.35
        
        # Obligation/requirement queries
        elif any(kw in query_lower for kw in ["must", "require", "obligation", "must"]):
            adjusted["keyword_overlap"] = 0.30
            adjusted["semantic_similarity"] = 0.40
        
        return adjusted


def get_context_ranker() -> ContextRanker:
    """
    Get or create context ranker singleton.
    
    Returns:
        ContextRanker instance
    """
    if not hasattr(get_context_ranker, "_instance"):
        get_context_ranker._instance = ContextRanker()
    return get_context_ranker._instance
