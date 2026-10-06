import os
import json
import re
import math
import logging
import psutil
from typing import List, Dict, Any, Optional
import threading

def log_memory(stage: str):
    try:
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        logger.info(f"MEMORY [{stage}]: {mem_info.rss / 1024 / 1024:.2f} MB")
    except Exception:
        pass

try:
    import numpy as np
except Exception:
    np = None

SentenceTransformer = None

from app.core.config import settings

logger = logging.getLogger(__name__)

class SimpleBM25:
    def __init__(self, documents: List[str]):
        self.documents = [self._tokenize(doc) for doc in documents]
        self.N = len(self.documents)
        self.avgdl = sum(len(doc) for doc in self.documents) / max(1, self.N)
        self.k1 = 1.5
        self.b = 0.75
        self.df = {}
        for doc in self.documents:
            for term in set(doc):
                self.df[term] = self.df.get(term, 0) + 1
        self.idf = {
            term: math.log((self.N - freq + 0.5) / (freq + 0.5) + 1)
            for term, freq in self.df.items()
        }

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return [tok for tok in re.findall(r"\w+", text.lower()) if len(tok) > 1]

    def score(self, query: str) -> List[float]:
        query_terms = self._tokenize(query)
        scores = [0.0] * self.N
        for term in query_terms:
            if term not in self.idf:
                continue
            idf = self.idf[term]
            for i, doc in enumerate(self.documents):
                freq = doc.count(term)
                if freq == 0:
                    continue
                denominator = freq + self.k1 * (1 - self.b + self.b * len(doc) / max(1, self.avgdl))
                scores[i] += idf * ((freq * (self.k1 + 1)) / denominator)
        return scores

from cachetools import LRUCache

class VectorService:
    def __init__(self):
        self.model: Optional[Any] = None
        self.model_error: Optional[str] = None
        self.chunk_cache = LRUCache(maxsize=10)
        self._lock = threading.Lock()

    def _ensure_model(self) -> bool:
        if self.model is not None:
            return True
            
        with self._lock:
            # Double-checked locking
            if self.model is not None:
                return True

            if not settings.GEMINI_API_KEY:
                self.model_error = "GEMINI_API_KEY is not configured but is required for vector embeddings."
                logger.error(self.model_error)
                return False

            logger.info("Using cloud-safe Gemini embedding model (gemini-embedding-2) to avoid OOM")
            try:
                from google import genai
                from google.genai import types
                
                class GeminiEmbeddingModel:
                    def __init__(self):
                        self.model = "gemini-embedding-2"
                        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

                    def encode(self, texts, convert_to_numpy=True, show_progress_bar=False, batch_size=32):
                        if isinstance(texts, str):
                            texts = [texts]
                        embeddings = []
                        # Process sequentially to guarantee 1 vector per chunk and keep memory extremely low
                        for text in texts:
                            # Use asymmetric retrieval format for documents
                            formatted_doc = f"title: Contract | text: {text}"
                            res = self.client.models.embed_content(
                                model=self.model,
                                contents=formatted_doc,
                                config=types.EmbedContentConfig(
                                    output_dimensionality=384
                                )
                            )
                            embeddings.append(res.embeddings[0].values)
                        if convert_to_numpy:
                            import numpy as np
                            return np.array(embeddings)
                        return embeddings
                
                self.model = GeminiEmbeddingModel()
                logger.info("embedding model load completed (Gemini)")
                return True
            except Exception as exc:
                self.model_error = f"Failed to initialize Gemini embedding model: {exc}"
                logger.error(self.model_error)
                return False

    def _normalize_scores(self, scores: List[float]) -> List[float]:
        if not scores:
            return []
        max_score = max(scores)
        if max_score <= 0:
            return [0.0 for _ in scores]
        if max_score > 1.0:
            return [float(score) / float(max_score) for score in scores]
        return [max(float(score), 0.0) for score in scores]

    def _get_embedding(self, text: str) -> List[float]:
        if not self._ensure_model():
            raise RuntimeError(self.model_error or "Embedding model is unavailable.")
        
        # Use asymmetric retrieval format for query
        formatted_query = f"task: question answering | query: {text}"
        
        # Bypass the standard `encode` since it adds Document formatting
        from google.genai import types
        res = self.model.client.models.embed_content(
            model=self.model.model,
            contents=formatted_query,
            config=types.EmbedContentConfig(output_dimensionality=384)
        )
        return res.embeddings[0].values

    def _get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        if not self._ensure_model():
            raise RuntimeError(self.model_error or "Embedding model is unavailable.")
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
        )
        return embeddings.tolist()

    def _bm25_results(self, query: str, chunks: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        if not chunks:
            return []
        texts = [f"{chunk['child_text']} {chunk['parent_text']}" for chunk in chunks]
        ranker = SimpleBM25(texts)
        raw_scores = ranker.score(query)
        normalized_scores = self._normalize_scores(raw_scores)

        results = []
        for idx, score in enumerate(normalized_scores):
            results.append({
                "child_id": chunks[idx]["child_id"],
                "parent_id": chunks[idx]["parent_id"],
                "child_text": chunks[idx]["child_text"],
                "parent_text": chunks[idx]["parent_text"],
                "score": score,
                "relevance_source": "bm25"
            })
        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:top_k]

    def _load_chunks(self, contract_id: str, db=None) -> List[Dict[str, Any]]:
        if contract_id in self.chunk_cache:
            return self.chunk_cache[contract_id]
        
        if not db:
            from app.core.database import get_db
            db_generator = get_db()
            db = next(db_generator)
            
        from app.models.models import ContractEmbedding
        db_embeddings = (
            db.query(
                ContractEmbedding.chunk_id,
                ContractEmbedding.parent_id,
                ContractEmbedding.child_text,
                ContractEmbedding.parent_text
            )
            .filter(ContractEmbedding.contract_id == contract_id)
            .all()
        )
        chunks = []
        for chunk_id, parent_id, child_text, parent_text in db_embeddings:
            chunks.append({
                "child_id": chunk_id,
                "parent_id": parent_id,
                "child_text": child_text,
                "parent_text": parent_text
            })
            
        self.chunk_cache[contract_id] = chunks
        return chunks

    def index_contract_chunks(self, contract_id: str, chunks: List[Dict[str, Any]], db=None) -> None:
        if not chunks:
            raise ValueError("No chunks available for indexing.")
        if not self._ensure_model():
            raise RuntimeError(self.model_error or "Embedding model is unavailable.")

        child_texts = [chunk["child_text"] for chunk in chunks]
        embeddings = []
        
        # Use a reduced batch size to save memory in production
        batch_size = min(settings.EMBEDDING_BATCH_SIZE, 8) 
        
        for start in range(0, len(child_texts), batch_size):
            logger.info(f"each embedding batch started {start} to {start + batch_size}")
            log_memory(f"before embedding generation {start}")
            batch = child_texts[start:start + batch_size]
            embeddings.extend(self._get_embeddings_batch(batch))
            log_memory(f"after embedding generation {start}")
            logger.info(f"each embedding batch completed {start} to {start + batch_size}")

        self.chunk_cache[contract_id] = chunks

        if db is not None:
            logger.info("pgvector insert started")
            from app.models.models import ContractEmbedding
            db.query(ContractEmbedding).filter(ContractEmbedding.contract_id == contract_id).delete()
            for chunk, embedding in zip(chunks, embeddings):
                db_embedding = ContractEmbedding(
                    contract_id=contract_id,
                    chunk_id=chunk["child_id"],
                    parent_id=chunk["parent_id"],
                    child_text=chunk["child_text"],
                    parent_text=chunk["parent_text"],
                    embedding=list(embedding),
                    relevance_source="semantic"
                )
                db.add(db_embedding)
            db.flush()
            logger.info("pgvector insert completed")

        logger.info("Indexed %s chunks for contract_id=%s using pgvector", len(chunks), contract_id)

    def _semantic_results(self, contract_id: str, query: str, top_k: int, db=None) -> List[Dict[str, Any]]:
        if not db:
            from app.core.database import get_db
            db_generator = get_db()
            db = next(db_generator)

        try:
            query_embedding = self._get_embedding(query)
        except RuntimeError:
            return []

        from app.models.models import ContractEmbedding
        # Inner product via pgvector cosine distance: embedding.cosine_distance(query_embedding)
        results = (
            db.query(
                ContractEmbedding.chunk_id,
                ContractEmbedding.parent_id,
                ContractEmbedding.child_text,
                ContractEmbedding.parent_text,
                ContractEmbedding.embedding.cosine_distance(query_embedding).label("distance")
            )
            .filter(ContractEmbedding.contract_id == contract_id)
            .order_by("distance")
            .limit(top_k)
            .all()
        )

        formatted_results = []
        for chunk_id, parent_id, child_text, parent_text, distance in results:
            formatted_results.append({
                "child_id": chunk_id,
                "parent_id": parent_id,
                "child_text": child_text,
                "parent_text": parent_text,
                "score": 1.0 - float(distance or 0.0), # Normalize cosine distance to a similarity score
                "relevance_source": "semantic"
            })
            
        return formatted_results

    def search_contract(self, contract_id: str, query: str, top_k: int = settings.MAX_CHUNK_RESULTS) -> List[Dict[str, Any]]:
        logger.debug("Searching contract_id=%s; query_length=%s", contract_id, len(query))

        from app.core.database import get_db
        db_generator = get_db()
        db = next(db_generator)

        chunks = self._load_chunks(contract_id, db=db)
        if not chunks:
            return []

        semantic_hits = self._semantic_results(contract_id, query, settings.SEMANTIC_TOP_K, db=db)
        bm25_hits = self._bm25_results(query, chunks, settings.BM25_TOP_K)

        merged = {}
        for hit in semantic_hits + bm25_hits:
            key = f"{hit['parent_id']}::{hit['child_id']}"
            existing = merged.get(key)
            if existing is None or hit["score"] > existing["score"]:
                merged[key] = hit

        candidates = sorted(merged.values(), key=lambda item: item["score"], reverse=True)

        selected = []
        seen_parents = set()
        for candidate in candidates:
            if candidate["parent_id"] in seen_parents:
                continue
            seen_parents.add(candidate["parent_id"])
            selected.append(candidate)
            if len(selected) >= top_k:
                break

        return selected

vector_service = VectorService()
