"""
BM25 Retriever Service

Implements BM25 keyword-based retrieval to complement semantic search.
Ranks documents by term frequency and relevance.
"""

import logging
import time
import math
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict

logger = logging.getLogger("legalgpt.retrieval.bm25")


class BM25Retriever:
    """
    BM25 keyword retrieval using term frequency and inverse document frequency.
    
    BM25 formula: score = sum(IDF(qi) * (f(qi, D) * (k1 + 1)) / (f(qi, D) + k1 * (1 - b + b * (|D| / avgdl))))
    where:
    - qi = query term i
    - f(qi, D) = frequency of qi in document D
    - |D| = length of document D
    - avgdl = average document length
    - k1 = term frequency normalization parameter (default 1.5)
    - b = length normalization parameter (default 0.75)
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Initialize BM25 retriever.
        
        Args:
            k1: Term frequency normalization parameter (default 1.5)
            b: Length normalization parameter (default 0.75)
        """
        self.k1 = k1
        self.b = b
        self.corpus = []  # List of documents
        self.tokenized_corpus = []  # Tokenized documents
        self.doc_freqs = defaultdict(int)  # Term frequency per document
        self.idf = {}  # Inverse document frequency cache
        self.avg_doc_length = 0.0
        self.is_indexed = False

    def index(self, documents: List[str]) -> None:
        """
        Build BM25 index from documents.
        
        Args:
            documents: List of document strings to index
        """
        start_time = time.time()
        
        self.corpus = documents
        self.tokenized_corpus = []
        self.doc_freqs = defaultdict(int)
        
        total_length = 0
        
        # Tokenize and index
        for doc_idx, doc in enumerate(documents):
            tokens = self._tokenize(doc)
            self.tokenized_corpus.append(tokens)
            total_length += len(tokens)
            
            # Calculate term frequencies
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self.doc_freqs[(token, doc_idx)] = tokens.count(token)
        
        # Calculate average document length
        self.avg_doc_length = total_length / len(documents) if documents else 0.0
        
        # Calculate IDF values
        self._calculate_idf()
        
        self.is_indexed = True
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(
            f"BM25 index built | documents={len(documents)} | "
            f"avg_length={self.avg_doc_length:.1f} | latency_ms={elapsed_ms}"
        )

    def _tokenize(self, text: str) -> List[str]:
        """
        Simple tokenization: lowercase, split on whitespace/punctuation.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of tokens
        """
        # Lowercase
        text = text.lower()
        
        # Split on whitespace and common punctuation
        tokens = []
        current_token = ""
        
        for char in text:
            if char.isalnum():
                current_token += char
            else:
                if current_token:
                    tokens.append(current_token)
                    current_token = ""
        
        if current_token:
            tokens.append(current_token)
        
        return tokens

    def _calculate_idf(self) -> None:
        """
        Calculate IDF (Inverse Document Frequency) for all terms.
        
        IDF = log((N - df + 0.5) / (df + 0.5))
        where N = total documents, df = documents containing term
        """
        n_docs = len(self.corpus)
        
        # Count document frequency for each term
        doc_freq = defaultdict(int)
        for doc_idx, tokens in enumerate(self.tokenized_corpus):
            for token in set(tokens):
                doc_freq[token] += 1
        
        # Calculate IDF for each term
        for token, df in doc_freq.items():
            self.idf[token] = math.log((n_docs - df + 0.5) / (df + 0.5) + 1e-8)

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0
    ) -> List[Tuple[int, float]]:
        """
        Retrieve top-k documents for query using BM25.
        
        Args:
            query: Query string
            top_k: Number of top results to return
            min_score: Minimum score threshold
            
        Returns:
            List of (document_index, score) tuples sorted by score descending
        """
        if not self.is_indexed:
            logger.warning("BM25: Index not built. Indexing corpus first...")
            return []
        
        start_time = time.time()
        
        # Tokenize query
        query_tokens = self._tokenize(query)
        
        # Calculate scores for each document
        scores = {}
        for doc_idx in range(len(self.corpus)):
            score = self._calculate_score(query_tokens, doc_idx)
            if score >= min_score:
                scores[doc_idx] = score
        
        # Sort by score and return top-k
        sorted_results = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.debug(
            f"BM25 retrieval | query_len={len(query_tokens)} | "
            f"results={len(sorted_results)} | latency_ms={elapsed_ms}"
        )
        
        return sorted_results

    def _calculate_score(self, query_tokens: List[str], doc_idx: int) -> float:
        """
        Calculate BM25 score for document given query.
        
        Args:
            query_tokens: Tokenized query
            doc_idx: Document index
            
        Returns:
            BM25 score
        """
        score = 0.0
        doc_length = len(self.tokenized_corpus[doc_idx])
        
        for token in query_tokens:
            # Get term frequency in document
            freq = self.doc_freqs.get((token, doc_idx), 0)
            
            if freq > 0:
                # Get IDF
                idf_value = self.idf.get(token, 0.0)
                
                # Calculate BM25 component
                numerator = freq * (self.k1 + 1)
                denominator = freq + self.k1 * (1 - self.b + self.b * (doc_length / (self.avg_doc_length + 1e-8)))
                
                score += idf_value * (numerator / denominator)
        
        return score

    def batch_retrieve(
        self,
        queries: List[str],
        top_k: int = 10,
        min_score: float = 0.0
    ) -> List[List[Tuple[int, float]]]:
        """
        Retrieve results for multiple queries.
        
        Args:
            queries: List of query strings
            top_k: Number of results per query
            min_score: Minimum score threshold
            
        Returns:
            List of result lists
        """
        results = []
        for query in queries:
            results.append(self.retrieve(query, top_k, min_score))
        return results

    def get_term_frequencies(self, doc_idx: int) -> Dict[str, int]:
        """
        Get term frequencies for a document.
        
        Args:
            doc_idx: Document index
            
        Returns:
            Dictionary of term frequencies
        """
        freqs = {}
        for token in self.tokenized_corpus[doc_idx]:
            freqs[token] = freqs.get(token, 0) + 1
        return freqs


class BM25Index:
    """Manages BM25 indexes for different document collections."""

    def __init__(self):
        """Initialize BM25 index manager."""
        self.indexes = {}

    def create_index(self, collection_id: str, documents: List[str]) -> None:
        """
        Create or update BM25 index for collection.
        
        Args:
            collection_id: Collection identifier
            documents: List of documents to index
        """
        retriever = BM25Retriever()
        retriever.index(documents)
        self.indexes[collection_id] = retriever
        logger.info(f"BM25 index created for collection '{collection_id}'")

    def retrieve(
        self,
        collection_id: str,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0
    ) -> Optional[List[Tuple[int, float]]]:
        """
        Retrieve from indexed collection.
        
        Args:
            collection_id: Collection identifier
            query: Query string
            top_k: Number of results
            min_score: Minimum score
            
        Returns:
            Results or None if collection not indexed
        """
        if collection_id not in self.indexes:
            logger.warning(f"BM25 index not found for collection '{collection_id}'")
            return None
        
        return self.indexes[collection_id].retrieve(query, top_k, min_score)

    def has_index(self, collection_id: str) -> bool:
        """Check if collection has BM25 index."""
        return collection_id in self.indexes


def get_bm25_index() -> BM25Index:
    """
    Get or create BM25 index singleton.
    
    Returns:
        BM25Index instance
    """
    if not hasattr(get_bm25_index, "_instance"):
        get_bm25_index._instance = BM25Index()
    return get_bm25_index._instance
