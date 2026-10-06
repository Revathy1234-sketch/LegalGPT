"""Reproduce failing endpoints in-process and print tracebacks."""
import sys, os, json, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(".env")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

# login
r = client.post("/api/v1/auth/login", data={"username": "bufftest@test.com", "password": "Test1234"})
print("login:", r.status_code)
token = r.json()["access_token"]
H = {"Authorization": f"Bearer {token}"}

# contracts
r = client.get("/api/v1/contracts/", headers=H)
contracts = r.json()
cid = contracts[0]["id"]
print("contract:", cid)

print("\n=== /dashboard/stats ===")
r = client.get("/api/v1/dashboard/stats", headers=H)
print("status:", r.status_code)
print(r.text[:500])

print("\n=== /analysis/chat ===")
r = client.post(f"/api/v1/analysis/chat/{cid}", json={"question": "What is the contract value?"}, headers=H)
print("status:", r.status_code)
print(r.text[:500])

# With raise_server_exceptions=True to get tracebacks
client2 = TestClient(app, raise_server_exceptions=True)
print("\n=== traceback for /dashboard/stats ===")
try:
    client2.get("/api/v1/dashboard/stats", headers=H)
    print("no exception")
except Exception:
    traceback.print_exc()

print("\n=== traceback for /analysis/chat ===")
try:
    client2.post(f"/api/v1/analysis/chat/{cid}", json={"question": "What is the contract value?"}, headers=H)
    print("no exception")
except Exception:
    traceback.print_exc()
