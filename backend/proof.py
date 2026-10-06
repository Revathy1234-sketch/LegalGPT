import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["JWT_SECRET"] = "test-secret"

import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import Base, get_db

# Setup test DB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

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

def run_proof():
    results = []

    # 1. Register User A and User B
    user_a_email = f"usera_{uuid.uuid4()}@example.com"
    user_b_email = f"userb_{uuid.uuid4()}@example.com"
    password = "Password123!"

    resp_a = client.post("/api/v1/auth/register", json={"email": user_a_email, "password": password, "full_name": "User A"})
    resp_b = client.post("/api/v1/auth/register", json={"email": user_b_email, "password": password, "full_name": "User B"})

    # 2. Login
    login_a = client.post("/api/v1/auth/login", data={"username": user_a_email, "password": password})
    login_b = client.post("/api/v1/auth/login", data={"username": user_b_email, "password": password})

    token_a = login_a.json()["access_token"]
    token_b = login_b.json()["access_token"]

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # /users/me
    me_a = client.get("/api/v1/auth/me", headers=headers_a) # Assuming /users/me or /auth/me
    # Let's just create dummy contracts directly in the DB to avoid uploading PDFs
    
    db = TestingSessionLocal()
    from app.models.models import User, Contract
    user_a_db = db.query(User).filter_by(email=user_a_email).first()
    user_b_db = db.query(User).filter_by(email=user_b_email).first()

    contract_a_id = uuid.uuid4()
    contract_b_id = uuid.uuid4()
    
    db.add(Contract(id=contract_a_id, uploaded_by=user_a_db.id, file_name="A.pdf", status="Processed"))
    db.add(Contract(id=contract_b_id, uploaded_by=user_b_db.id, file_name="B.pdf", status="Processed"))
    db.commit()

    def test_access(method, endpoint_template, contract_id, headers, expected_status):
        endpoint = endpoint_template.format(id=contract_id)
        if method == "GET":
            resp = client.get(endpoint, headers=headers)
        else:
            resp = client.post(endpoint, headers=headers, json={})
        
        status = resp.status_code
        pass_fail = "PASS" if status == expected_status else f"FAIL (Got {status})"
        results.append(f"{method} {endpoint} -> EXPECTED: {expected_status}, ACTUAL: {status} [{pass_fail}]")

    # Tests for User A accessing User A's contract
    test_access("GET", "/api/v1/contracts/{id}", contract_a_id, headers_a, 200)
    
    # Tests for User A accessing User B's contract (Should be 403 or 404)
    # The actual implementation in contracts.py and analysis.py returns 403 or 404. Let's accept both as isolation success.
    # We will just print the actual status.
    
    endpoints = [
        ("GET", "/api/v1/contracts/{id}"),
        ("POST", "/api/v1/analysis/summarize/{id}"),
        ("POST", "/api/v1/analysis/risk/{id}"),
        ("POST", "/api/v1/analysis/clauses/{id}"),
        ("POST", "/api/v1/analysis/compliance/{id}"),
        ("POST", "/api/v1/analysis/negotiation/{id}"),
        ("POST", "/api/v1/analysis/knowledge-graph/{id}")
    ]

    for method, template in endpoints:
        test_access(method, template, contract_b_id, headers_a, 403) # We expect 403 based on validate_contract_access

    # Search Isolation (Assume GET /api/v1/contracts returns only own contracts)
    resp = client.get("/api/v1/contracts", headers=headers_a)
    if resp.status_code == 200:
        c_ids = [c["id"] for c in resp.json()]
        if str(contract_b_id) in c_ids:
            results.append("GET /api/v1/contracts -> User A saw User B's contract [FAIL]")
        else:
            results.append("GET /api/v1/contracts -> Isolation successful [PASS]")

    for r in results:
        print(r)

if __name__ == "__main__":
    run_proof()
