import os
import json
import uuid
import numpy as np

os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from app.core.database import Base
from sqlalchemy import create_engine
from app.services.vector_service import vector_service

def run():
    cid = str(uuid.uuid4())
    
    contract_text = """
    Governing Law: California
    Contract Value: $111,111
    Term: 12 months
    
    Indemnification: Supplier shall indemnify Customer against third-party claims arising from intellectual property infringement.
    
    Liability: Liability shall not exceed the fees paid during the preceding 12 months.
    
    Privacy: The parties acknowledge compliance obligations under the California Consumer Privacy Act (CCPA).
    
    Payment: Late payments accrue interest at 2% per month.
    
    Termination: Either party may terminate with 30 days written notice.
    """
    
    chunks = []
    lines = [line.strip() for line in contract_text.split('\n') if line.strip()]
    for i, line in enumerate(lines):
        chunks.append({
            "child_id": f"chunk_{i}",
            "parent_id": f"parent_{i}",
            "child_text": line,
            "parent_text": line
        })
        
    vector_service.index_contract_chunks(cid, chunks, db=None)
    
    queries = [
        "What is the governing law?",
        "What is the contract term?",
        "What is the indemnification obligation?",
        "What is the liability cap?",
        "What privacy regulation is mentioned?",
        "What is the late payment interest?",
        "What is the termination period?",
        "What insurance coverage is required?"
    ]
    
    print("\n--- RETRIEVAL TEST DIRECT ---")
    for q in queries:
        print(f"\nQUERY: {q}")
        faiss_res = vector_service._semantic_results(cid, q, top_k=5)
        chunks = vector_service._load_chunks(cid)
        bm25_res = vector_service._bm25_results(q, chunks, top_k=5)
        
        merged = vector_service._merge_and_rerank(faiss_res, bm25_res, chunk_limit=3)
        
        for i, hit in enumerate(merged):
            print(f"  Rank {i+1}: Score={hit['score']:.4f} | Src={hit['relevance_source']} | Text='{hit['child_text']}'")

if __name__ == "__main__":
    run()
