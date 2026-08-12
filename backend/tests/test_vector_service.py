import os
import shutil
import tempfile
import pytest
from unittest.mock import patch

from app.core.config import settings
from app.services.vector_service import VectorService


def test_sentence_transformer_lazy_import_and_embedding():
    # Create a fresh VectorService instance
    service = VectorService()
    
    # a. SentenceTransformer can be lazily imported and model initialized
    # Initially service.model should be None (startup safety)
    assert service.model is None
    
    # Force _ensure_model to execute
    success = service._ensure_model()
    assert success is True
    assert service.model is not None
    
    # Verify module-level SentenceTransformer is not None now
    from app.services.vector_service import SentenceTransformer
    assert SentenceTransformer is not None

    # b. The embedding model can be initialized (it is done in _ensure_model)
    # c. A sample text produces a 384-dimensional embedding
    text = "This is a legal contract."
    emb = service._get_embedding(text)
    
    # d. VectorService._get_embedding() returns a non-empty list of 384 dimensions
    assert isinstance(emb, list)
    assert len(emb) == 384
    
    # Batch embeddings test
    batch_emb = service._get_embeddings_batch([text, "Another contract clause."])
    assert len(batch_emb) == 2
    assert len(batch_emb[0]) == 384


def test_faiss_indexing_and_search():
    # Use a temporary directory for FAISS index files to keep the environment clean
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Patch FAISS_INDEX_PATH
        with patch.object(settings, "FAISS_INDEX_PATH", temp_dir):
            service = VectorService()
            
            # Create a mock contract chunks list
            contract_id = "test_contract_123"
            chunks = [
                {
                    "child_id": "c1",
                    "parent_id": "p1",
                    "child_text": "The Buyer shall pay the Seller the purchase price.",
                    "parent_text": "Section 1: Purchase Price. The Buyer shall pay the Seller the purchase price."
                },
                {
                    "child_id": "c2",
                    "parent_id": "p2",
                    "child_text": "This Agreement shall terminate on December 31, 2026.",
                    "parent_text": "Section 2: Term. This Agreement shall terminate on December 31, 2026."
                }
            ]
            
            # Index the contract chunks
            service.index_contract_chunks(contract_id, chunks, db=None)
            
            # Verify files were created
            index_path = service._index_file_path(contract_id)
            metadata_path = service._metadata_file_path(contract_id)
            
            assert os.path.exists(index_path)
            assert os.path.exists(metadata_path)
            
            # e. Existing FAISS indexing/search behavior remains intact
            # Perform search
            results = service.search_contract(contract_id, "purchase price", top_k=2)
            
            assert len(results) > 0
            # The top hit should be about the purchase price (child_id: c1)
            assert results[0]["child_id"] == "c1"
            assert "score" in results[0]
            assert "relevance_source" in results[0]
            assert results[0]["relevance_source"] in ["semantic", "bm25"]
            
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
