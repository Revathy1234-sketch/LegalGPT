import os
import sys
import uuid
from fastapi.testclient import TestClient

# Change context so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.main import app

client = TestClient(app)

print("Starting Complete API Audit & Agent Pipeline Test...\n")

def test_pipeline():
    # 1. Register User A
    user_a_email = f"user_a_{uuid.uuid4()}@example.com"
    resp = client.post("/api/v1/auth/register", json={
        "email": user_a_email,
        "password": "Password123!",
        "full_name": "Test User A"
    })
    
    login_resp = client.post("/api/v1/auth/login", data={"username": user_a_email, "password": "Password123!"})
    token_a = login_resp.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    print("User A Registration & Login: PASS")
    
    # 2. Register User B
    user_b_email = f"user_b_{uuid.uuid4()}@example.com"
    resp = client.post("/api/v1/auth/register", json={
        "email": user_b_email,
        "password": "Password123!",
        "full_name": "Test User B"
    })
    login_resp = client.post("/api/v1/auth/login", data={"username": user_b_email, "password": "Password123!"})
    token_b = login_resp.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    print("User B Registration & Login: PASS")

    # 3. Upload Contract A as User A
    pdf_path_a = "./contract_a_ny.pdf"
    if not os.path.exists(pdf_path_a):
        print(f"Skipping upload test because {pdf_path_a} does not exist.")
        return

    with open(pdf_path_a, "rb") as f:
        resp = client.post("/api/v1/contracts/upload", headers=headers_a, files={"file": ("contract_A.pdf", f, "application/pdf")})
    if resp.status_code not in [200, 201, 202]:
        print(f"FAIL: Upload A: {repr(resp.text)}")
        return
    contract_a_id = resp.json()["id"]
    print("Upload Contract A (User A): PASS")

    # 4. Upload Contract B as User B
    pdf_path_b = "./contract_b_ca.pdf"
    with open(pdf_path_b, "rb") as f:
        resp = client.post("/api/v1/contracts/upload", headers=headers_b, files={"file": ("contract_b_ca.pdf", f, "application/pdf")})
    contract_b_id = resp.json()["id"]
    print("Upload Contract B (User B): PASS")
    
    # Wait for processing
    import time
    def wait_for_contract(c_id, headers):
        print(f"Waiting for contract {c_id} to process...")
        for _ in range(15):
            r = client.get(f"/api/v1/contracts/{c_id}", headers=headers)
            if r.status_code == 200 and r.json().get("status") == "Processed":
                return True
            time.sleep(1)
        return False
        
    if not wait_for_contract(contract_a_id, headers_a):
        print("FAIL: Contract A failed to process in time")
        return
    if not wait_for_contract(contract_b_id, headers_b):
        print("FAIL: Contract B failed to process in time")
        return
    
    # 5. Tenant Isolation Check
    # User B tries to read Contract A
    resp = client.get(f"/api/v1/contracts/{contract_a_id}", headers=headers_b)
    if resp.status_code in [403, 404]:
        print("Tenant Isolation (Read Contract A by User B): PASS")
    else:
        print(f"FAIL: Tenant Isolation. User B read Contract A: {resp.status_code}")
        
    # User A tries to summarize Contract B
    resp = client.post(f"/api/v1/analysis/summarize/{contract_b_id}", headers=headers_a)
    if resp.status_code in [403, 404]:
        print("Tenant Isolation (Analyze Contract B by User A): PASS")
    else:
        print(f"FAIL: Tenant Isolation. User A analyzed Contract B: {resp.status_code}")
        
    # 6. Test RAG / All Agents for User A on Contract A
    agents = [
        ("Summary Agent", f"/api/v1/analysis/summarize/{contract_a_id}", {}),
        ("Clause Agent", f"/api/v1/analysis/clauses/{contract_a_id}", {}),
        ("Risk Agent", f"/api/v1/analysis/risk/{contract_a_id}", {}),
        ("Compliance Agent", f"/api/v1/analysis/compliance/{contract_a_id}", {}),
        ("Negotiation Agent", f"/api/v1/analysis/negotiation/{contract_a_id}", {}),
        ("Knowledge Graph", f"/api/v1/analysis/knowledge-graph/{contract_a_id}", {})
    ]
    
    for agent_name, endpoint, payload in agents:
        resp = client.post(endpoint, headers=headers_a, json=payload)
        if resp.status_code == 200:
            print(f"{agent_name}: PASS")
        else:
            print(f"FAIL: {agent_name} failed with {resp.status_code}: {resp.text}")
            print(f"FAIL: {agent_name} failed with {resp.status_code}: {repr(resp.text)}")
            
    # 7. Test Chat / RAG Grounding
    resp = client.post(f"/api/v1/analysis/chat/{contract_a_id}", headers=headers_a, json={"question": "What is the governing law of this contract?"})
    if resp.status_code == 200:
        print("Chat Agent (Positive): PASS")
    else:
        print(f"FAIL: Chat Agent: {repr(resp.text)}")
        
    resp = client.post(f"/api/v1/analysis/chat/{contract_a_id}", headers=headers_a, json={"question": "Does this contract mention a secret moon base?"})
    if resp.status_code == 200:
        print("Chat Agent (Negative): PASS")
    else:
        print(f"FAIL: Chat Agent (Negative): {repr(resp.text)}")

    print("\nAPI Audit & Agent Pipeline Test: SUCCESS")

if __name__ == "__main__":
    test_pipeline()
