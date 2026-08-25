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


