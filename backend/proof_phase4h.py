import requests
import json
import uuid
import time
import sys
import os
from reportlab.pdfgen import canvas

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://localhost:8000/api/v1"

def create_user_and_login(email, password="Password123!"):
    # Register
    res = requests.post(f"{BASE_URL}/auth/register", json={
        "email": email,
        "password": password,
        "full_name": email.split("@")[0]
    })
    if res.status_code != 201:
        print("Registration failed:", res.status_code, res.text)
    
    # Login
    res = requests.post(f"{BASE_URL}/auth/login", data={
        "username": email,
        "password": password
    })
    token = res.json().get("access_token")
    if not token:
        print("Login failed:", res.status_code, res.text)
    return token

def create_contract(token, title, text):
    headers = {"Authorization": f"Bearer {token}"}
    pdf_path = f"{title.replace(' ', '_')}.pdf"
    
    # Create PDF
    c = canvas.Canvas(pdf_path)
    textobject = c.beginText(50, 800)
    for line in text.split('\n'):
        textobject.textLine(line.strip())
    c.drawText(textobject)
    c.save()
    
    with open(pdf_path, "rb") as f:
        res = requests.post(f"{BASE_URL}/contracts/upload", headers=headers, files={"file": (f"{title}.pdf", f, "application/pdf")})
    
    os.remove(pdf_path)
    if res.status_code != 201:
        print("Upload failed:", res.status_code, res.text)
    return res.json().get("id")

def run_tests():
    print("=== PHASE 4H PROOF ===")
    
    run_id = str(uuid.uuid4())[:8]
    token_a = create_user_and_login(f"usera_{run_id}@example.com")
    token_b = create_user_and_login(f"userb_{run_id}@example.com")
    
    print("Tokens acquired.")
    
    contract_a_text = """
    Governing Law: California
    Contract Value: $111,111
    Term: 12 months
    Indemnification: Supplier shall indemnify Customer against third-party claims arising from intellectual property infringement.
    Liability: Liability shall not exceed the fees paid during the preceding 12 months.
    Privacy: The parties acknowledge compliance obligations under the California Consumer Privacy Act (CCPA).
    Payment: Late payments accrue interest at 2% per month.
    Termination: Either party may terminate with 30 days written notice.
    """
    
    contract_b_text = """
    Governing Law: New York
    Contract Value: $999,999
    Term: 24 months
    Indemnification: Supplier shall indemnify Customer against all third-party claims.
    Liability: Liability shall not exceed the fees paid during the preceding 24 months.
    Privacy: The parties acknowledge compliance obligations under the General Data Protection Regulation (GDPR).
    Payment: Late payments accrue interest at 5% per month.
    Termination: Either party may terminate with 60 days written notice.
    """
    
    print("Uploading Contract A (User A)...")
    cid_a = create_contract(token_a, "Contract A", contract_a_text)
    print(f"Contract A ID: {cid_a}")
    
    print("Uploading Contract B (User B)...")
    cid_b = create_contract(token_b, "Contract B", contract_b_text)
    print(f"Contract B ID: {cid_b}")
    
    print("Waiting for chunking/indexing (5s)...")
    time.sleep(5)
    
    print("\n--- 1. KNOWLEDGE GRAPH TEST ---")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    res = requests.post(f"{BASE_URL}/analysis/knowledge-graph/{cid_a}", headers=headers_a)
    print("KG Status:", res.status_code, res.text)
    kg = res.json()
    print("KG Result Keys:", kg.keys())
    print("Entities:", len(kg.get("result", {}).get("entities", [])))
    print("Relationships:", len(kg.get("result", {}).get("relationships", [])))
    
    print("\n--- 2. COMPARISON TEST ---")
    # Both contracts need to be accessible. Since cid_b belongs to user B, user A shouldn't be able to access it.
    res_unauth = requests.post(f"{BASE_URL}/analysis/compare", headers=headers_a, json={
        "contract_a_id": cid_a,
        "contract_b_id": cid_b
    })
    print("Cross-tenant compare (User A compares with B's contract):", res_unauth.status_code, res_unauth.text)
    
    print("Uploading Contract B2 (User A)...")
    cid_b2 = create_contract(token_a, "Contract B2", contract_b_text)
    time.sleep(5)
    
    res_comp = requests.post(f"{BASE_URL}/analysis/compare", headers=headers_a, json={
        "contract_a_id": cid_a,
        "contract_b_id": cid_b2
    })
    print("Comparison Status:", res_comp.status_code)
    comp_result = res_comp.json()
    print("Similarities:", len(comp_result.get("similarities", [])))
    print("Differences:", len(comp_result.get("differences", [])))
    print("Summary:", comp_result.get("summary"))

if __name__ == "__main__":
    run_tests()
