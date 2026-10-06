import os
import sys

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.models import ContractEmbedding
from app.services.vector_service import vector_service

def migrate_embeddings():
    db = SessionLocal()
    try:
        query = db.query(ContractEmbedding)
        count = query.count()
        if count == 0:
            print("No existing embeddings to migrate.")
            return

        print(f"Migrating {count} embeddings...")
        
        # We need to re-embed all chunk texts
        for row in query.yield_per(100):
            child_text = row.child_text
            # Use vector_service's new model which uses Gemini
            try:
                embeddings = vector_service._get_embeddings_batch([child_text])
                if len(embeddings) != 1:
                    print(f"Failed to embed chunk {row.chunk_id}: Expected 1 embedding, got {len(embeddings)}")
                    continue
                embedding = embeddings[0]
                if len(embedding) != 384:
                    print(f"Failed to embed chunk {row.chunk_id}: Expected 384 dimensions, got {len(embedding)}")
                    continue
                row.embedding = embedding
                print(f"Re-embedded chunk {row.chunk_id} for contract {row.contract_id}")
            except Exception as embed_e:
                print(f"Failed to embed chunk {row.chunk_id}: {embed_e}")
            
        db.commit()
        print("Migration complete. All existing vectors have been updated to Gemini.")
    except Exception as e:
        db.rollback()
        print(f"Error during migration: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_embeddings()
