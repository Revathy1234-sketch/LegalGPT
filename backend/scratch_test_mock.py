import os
import sys
import uuid
from unittest.mock import patch
from fastapi.testclient import TestClient
import json

# Add backend to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.main import app
from app.core.database import SessionLocal
from app.models.models import Contract, User

client = TestClient(app)

def mock_invoke(*args, **kwargs):
    # Depending on prompt, return different mock JSON
    prompt = args[0]
    prompt_str = str(prompt).lower()
    if "negotiation" in prompt_str:
        # Test the string-to-dict coercion
        resp = {
            "negotiation_suggestions": "This is a string suggestion that should be converted to a list of dicts.",
            "priority_actions": "This is another string",
            "clauses": [],
            "risk_matrix": [],
            "compliance_report": [],
            "confidence_score": 0.9,
            "reasoning_summary": "Mock reasoning"
        }
    elif "knowledge graph" in prompt_str:
        # Test the entities/relationships mapping
        resp = {
            "entities": [{"id": "e1", "type": "PERSON", "name": "John", "confidence_score": 0.9}],
            "relationships": [{"source": "e1", "target": "e2", "type": "KNOWS"}]
        }
    else:
        resp = {"summary": "mock summary"}
    return json.dumps(resp), {"total_tokens": 100}

@patch("app.services.llm_service.LLMService.invoke", side_effect=mock_invoke)
def test_endpoints(mock_llm):
    db = SessionLocal()
    contract = db.query(Contract).first()
    if not contract:
        print("No contract found.")
        return
    
    contract_id = str(contract.id)
    user = db.query(User).filter(User.id == contract.uploaded_by).first()
    
    if user:
        from app.auth.jwt_handler import create_access_token
        token = create_access_token(subject=str(user.id))
        headers = {"Authorization": f"Bearer {token}"}
    else:
        headers = {}
        def override_get_current_user():
            return User(id=contract.uploaded_by, email="test@test.com")
        from app.api.v1.auth import get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user

    print("\n--- Testing Negotiation ---")
    resp = client.post(f"/api/v1/analysis/negotiation/{contract_id}?force=true", headers=headers)
    print("Status:", resp.status_code)
    if resp.status_code == 200:
        data = resp.json()
        print("negotiation_suggestions:", data.get("negotiation_suggestions"))
    else:
        print("Error:", resp.json())

    print("\n--- Testing Knowledge Graph ---")
    resp = client.post(f"/api/v1/analysis/knowledge-graph/{contract_id}?force=true", headers=headers)
    print("Status:", resp.status_code)
    if resp.status_code == 200:
        data = resp.json()
        result = data.get("result", {})
        print("result_dict raw:", data.get("result"))
        print("Entities:", result.get("entities"))
        print("Relationships:", result.get("relationships"))
    else:
        print("Error:", resp.json())

if __name__ == "__main__":
    test_endpoints()
