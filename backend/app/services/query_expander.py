"""
Deterministic Query Expansion Service

Expands user queries with legal synonyms to improve retrieval coverage.
Uses deterministic expansion without LLM calls.
"""

import logging
import time
import re
from typing import List, Set, Tuple
from app.core.retrieval_config import LEGAL_QUERY_SYNONYMS

logger = logging.getLogger("legalgpt.retrieval.query_expansion")


class QueryExpander:
    """Expands legal queries with domain-specific synonyms."""

    def __init__(self):
        """Initialize query expander."""
        self.synonyms = LEGAL_QUERY_SYNONYMS
        self._build_expansion_index()

    def _build_expansion_index(self) -> None:
        """Build reverse index for faster expansion lookup."""
        self.expansion_index = {}
        
        for primary, alternates in self.synonyms.items():
            # Add primary term
            self.expansion_index[primary.lower()] = set(alternates)
            
            # Add each alternate as a key pointing back to all synonyms
            for alt in alternates:
                alt_lower = alt.lower()
                if alt_lower not in self.expansion_index:
                    self.expansion_index[alt_lower] = set()
                # Add primary and all other alternates
                self.expansion_index[alt_lower].add(primary)
                for other_alt in alternates:
                    if other_alt.lower() != alt_lower:
                        self.expansion_index[alt_lower].add(other_alt)

    def expand_query(self, query: str, max_expansions: int = 10) -> Tuple[str, List[str]]:
        """
        Expand query with legal synonyms.
        
        Args:
            query: Original user query
            max_expansions: Maximum number of expansion terms to return
            
        Returns:
            Tuple of (original_query, list_of_expansion_terms)
        """
        start_time = time.time()
        
        # Normalize query
        query_normalized = re.sub(r'[^a-z0-9 -]+', ' ', query.lower()).strip()
        
        # Extract potential multi-word terms and single words
        terms_to_expand = self._extract_terms(query_normalized)
        
        # Expand each term
        expanded_terms = set()
        for term in terms_to_expand:
            if term in self.expansion_index:
                # Add the synonym set for this term
                expanded_terms.update(self.expansion_index[term])
        
        # Remove original query and duplicates
        expanded_terms.discard(query_normalized)
        
        # Sort by relevance and limit
        expansion_list = sorted(
            list(expanded_terms),
            key=lambda x: self._term_relevance_score(x, query_normalized),
            reverse=True
        )[:max_expansions]
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.debug(
            f"Query expansion | original='{query_normalized}' | "
            f"expansions={len(expansion_list)} | latency_ms={elapsed_ms}"
        )
        
        return query_normalized, expansion_list

    def _extract_terms(self, query: str) -> Set[str]:
        """
        Extract both multi-word and single-word terms from query.
        
        Args:
            query: Normalized query
            
        Returns:
            Set of terms to expand
        """
        terms = set()
        
        # Add the whole query first (multi-word phrase)
        terms.add(query)
        
        # Add individual words
        words = query.split()
        terms.update(words)
        # Deterministic legal morphology (terminated -> terminate).
        terms.update(word[:-1] for word in words if word.endswith('ed') and len(word) > 4)
        
        # Add common 2-word phrases
        for i in range(len(words) - 1):
            two_word = f"{words[i]} {words[i + 1]}"
            terms.add(two_word)
        
        # Add common 3-word phrases if query is long enough
        if len(words) >= 3:
            for i in range(len(words) - 2):
                three_word = f"{words[i]} {words[i + 1]} {words[i + 2]}"
                terms.add(three_word)
        
        return terms

    def _term_relevance_score(self, term: str, original_query: str) -> float:
        """
        Score how relevant an expansion term is to original query.
        
        Args:
            term: Expansion term
            original_query: Original query
            
        Returns:
            Relevance score (0.0-1.0)
        """
        score = 0.0
        
        # Longer terms are more specific
        term_length = len(term.split())
        score += min(term_length / 3, 0.3)  # Max 0.3 for term length
        
        # Terms that start with query words are more relevant
        query_words = original_query.split()
        term_words = term.split()
        
        for qword in query_words:
            for tword in term_words:
                if qword in tword or tword in qword:
                    score += 0.2  # Bonus for word overlap
        
        # Normalize score
        return min(score, 1.0)

    def build_expanded_query(
        self,
        query: str,
        max_expansions: int = 5,
        include_original: bool = True
    ) -> str:
        """
        Build a combined search query with expansions for retrieval.
        
        Args:
            query: Original query
            max_expansions: Max expansion terms
            include_original: Whether to include original in result
            
        Returns:
            Space-separated combination of query and expansions
        """
        original, expansions = self.expand_query(query, max_expansions)
        
        # Build combined query
        if include_original:
            combined = original
        else:
            combined = ""
        
        # Add top expansions
        for expansion in expansions[:max_expansions]:
            if combined:
                combined += " OR " + expansion
            else:
                combined = expansion
        
        return combined


def get_query_expander() -> QueryExpander:
    """
    Get or create query expander singleton.
    
    Returns:
        QueryExpander instance
    """
    if not hasattr(get_query_expander, "_instance"):
        get_query_expander._instance = QueryExpander()
    return get_query_expander._instance
