import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["JWT_SECRET"] = "test-secret"

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

import uuid
from app.main import app
from app.core.database import Base, get_db
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.vector_service import vector_service

engine = create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def run():
    db = TestingSessionLocal()
    from app.models.models import User, Contract
    
    email_a = f"usera_rag_{uuid.uuid4()}@example.com"
    email_b = f"userb_rag_{uuid.uuid4()}@example.com"
    
    # 1. Register users
    client.post("/api/v1/auth/register", json={"email": email_a, "password": "Password123!", "full_name": "User A"})
    client.post("/api/v1/auth/register", json={"email": email_b, "password": "Password123!", "full_name": "User B"})
    
    tk_a = client.post("/api/v1/auth/login", data={"username": email_a, "password": "Password123!"}).json()["access_token"]
    tk_b = client.post("/api/v1/auth/login", data={"username": email_b, "password": "Password123!"}).json()["access_token"]
    
    user_a = db.query(User).filter_by(email=email_a).first()
    user_b = db.query(User).filter_by(email=email_b).first()
    
    # 2. Seed contracts and vector indexes
    cid_a = str(uuid.uuid4())
    cid_b = str(uuid.uuid4())
    
    db.add(Contract(id=uuid.UUID(cid_a), uploaded_by=user_a.id, file_name="A.txt", status="Processed"))
    db.add(Contract(id=uuid.UUID(cid_b), uploaded_by=user_b.id, file_name="B.txt", status="Processed"))
    db.commit()
    
    # Create chunks
    chunks_a = [
        {"child_id": "chunk_A1", "parent_id": "A", "child_text": "COMPANY_A_SECRET_TERM. Contract value: $111,111. Governing law: California. Indemnification period: 11 days.", "parent_text": ""}
    ]
    chunks_b = [
        {"child_id": "chunk_B1", "parent_id": "B", "child_text": "COMPANY_B_SECRET_TERM. Contract value: $999,999. Governing law: New York. Indemnification period: 99 days.", "parent_text": ""}
    ]
    
    try:
        vector_service.index_contract_chunks(cid_a, chunks_a, db=db)
        vector_service.index_contract_chunks(cid_b, chunks_b, db=db)
    except Exception as e:
        print(f"Error indexing: {e}")
    
    results = []
    
    def log(test, expected, actual, pf):
        results.append(f"TEST: {test}\nEXPECTED: {expected}\nACTUAL: {actual}\nPASS/FAIL: {pf}\n")

    # 3. Test Vector Retrieval Directly
    res_a = vector_service.search_contract(cid_a, "Contract value?", top_k=5)
    has_111 = any("111,111" in c["child_text"] for c in res_a)
    has_999 = any("999,999" in c["child_text"] for c in res_a)
    log("Vector Search A for Value", "$111,111 only", f"Found 111:{has_111}, Found 999:{has_999}", "PASS" if has_111 and not has_999 else "FAIL")
    
    # Test cross contamination via agent (Chat)
    resp_chat_a = client.post(f"/api/v1/analysis/chat/{cid_a}", headers={"Authorization": f"Bearer {tk_a}"}, json={"question": "Does this contain COMPANY_B_SECRET_TERM?"})
    if resp_chat_a.status_code == 200:
        ans = resp_chat_a.json().get("answer", "")
        fail = "COMPANY_B_SECRET_TERM" in ans and ("yes" in ans.lower() or "contain" in ans.lower())
        log("Chat A for B's Secret", "No / not found", ans[:100].replace("\n"," "), "FAIL" if fail else "PASS")
    else:
        log("Chat A for B's Secret", "200 OK", str(resp_chat_a.status_code), "FAIL")

    for r in results:
        print(r)
        
run()
