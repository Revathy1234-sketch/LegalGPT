import os
import sys
import uuid
import logging
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

# Add backend to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.main import app
from app.core.database import SessionLocal
from app.models.models import Contract, User

client = TestClient(app)

def test_endpoints():
    db = SessionLocal()
    contract = db.query(Contract).first()
    if not contract:
        print("No contract found to test.")
        return
    
    contract_id = str(contract.id)
    print(f"Testing with contract: {contract_id}")

    user = db.query(User).filter(User.id == contract.uploaded_by).first()
    if user:
        # Mock auth by overriding dependency or just creating a token
        from app.auth.jwt_handler import create_access_token
        token = create_access_token(subject=str(user.id))
        headers = {"Authorization": f"Bearer {token}"}
    else:
        # Override dependency if no user
        headers = {}
        def override_get_current_user():
            return User(id=contract.uploaded_by, email="test@test.com")
        from app.api.v1.auth import get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user

    # 1. Contract Overview (Stored Results)
    print("\n--- Testing /stored/{contract_id} ---")
    resp = client.get(f"/api/v1/analysis/stored/{contract_id}", headers=headers)
    print("Status:", resp.status_code)
    if resp.status_code == 200:
        print("Success!")
    else:
        print(resp.json())

    # 2. Negotiation
    print("\n--- Testing /negotiation/{contract_id} ---")
    # Forcing execution
    resp = client.post(f"/api/v1/analysis/negotiation/{contract_id}?force=true", headers=headers)
    print("Status:", resp.status_code)
    if resp.status_code == 200:
        data = resp.json()
        suggs = data.get("negotiation_suggestions")
        print("negotiation_suggestions type:", type(suggs))
        print("Length:", len(suggs) if suggs else 0)
        if suggs and isinstance(suggs, list):
            print("First item:", type(suggs[0]))
    else:
        print(resp.json())

    # 3. Knowledge Graph
    print("\n--- Testing /knowledge-graph/{contract_id} ---")
    resp = client.post(f"/api/v1/analysis/knowledge-graph/{contract_id}?force=true", headers=headers)
    print("Status:", resp.status_code)
    if resp.status_code == 200:
        data = resp.json()
        print("Success:", data.get("success"))
        result = data.get("result", {})
        print("Entities length:", len(result.get("entities", [])))
        print("Relationships length:", len(result.get("relationships", [])))
    else:
        print(resp.json())
        
    print("\nDone testing.")

if __name__ == "__main__":
    test_endpoints()
