"""Reproduce the /analysis/risk force=true 500 and print the traceback."""
import os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv(".env")

from fastapi.testclient import TestClient
from app.main import app

client_auth = TestClient(app, raise_server_exceptions=False)
r = client_auth.post("/api/v1/auth/login", data={"username": "bufftest@test.com", "password": "Test1234"})
token = r.json()["access_token"]
H = {"Authorization": f"Bearer {token}"}
CID = "e0aa2c34-b846-4b9d-9ad2-ec655142c0f6"

client = TestClient(app, raise_server_exceptions=True)
print("running force risk (may take several minutes)...", flush=True)
try:
    resp = client.post(f"/api/v1/analysis/risk/{CID}?force=true", headers=H)
    print("status:", resp.status_code)
    data = resp.json()
    print("score:", data.get("overall_score"), "findings:", len(data.get("risk_matrix") or []))
except Exception:
    traceback.print_exc()
