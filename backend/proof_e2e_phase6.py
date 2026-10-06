"""
proof_e2e_phase6.py — Canonical End-to-End Test Suite (Phase 6.1)

Tests the full LegalGPT production API including:
- Authentication (register, login, JWT)
- Contract upload + RAG pipeline
- All 6 analysis agents via HTTP
- Chat grounding (positive + negative)
- Cross-tenant security (403 isolation)
- API error boundaries (422, 404)
- PostgreSQL execution telemetry
- History endpoint
- Comparison endpoint

SECURITY: DB credentials are read from .env / environment only.
No secrets are hardcoded or printed.

Run from: backend/ directory (where .env lives)
  python proof_e2e_phase6.py
"""

import os
import sys
import time
import requests
import uuid
from pathlib import Path
from fpdf import FPDF
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Load .env so DATABASE_URL is available
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # Already set in environment

BASE_URL = "http://localhost:8000/api/v1"
DB_URL = os.environ.get("DATABASE_URL")

if not DB_URL:
    print("ERROR: DATABASE_URL not set in environment or .env file.")
    sys.exit(1)

# PostgreSQL connection (credentials come from DATABASE_URL only)
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_synthetic_pdf(filename: str, text_content: str) -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 10, text_content)
    pdf.output(filename)


def _post_with_retry(url: str, retries: int = 3, **kwargs) -> requests.Response:
    """POST with retry on transient connection reset errors (WinError 10054)."""
    for attempt in range(retries):
        try:
            return requests.post(url, **kwargs)
        except requests.exceptions.ConnectionError as exc:
            if attempt < retries - 1:
                wait = 2 ** attempt
                print(f"  [RETRY] Connection error on attempt {attempt + 1}, waiting {wait}s: {exc}")
                time.sleep(wait)
            else:
                raise


def register_and_login(email: str, password: str, full_name: str) -> str:
    res = _post_with_retry(f"{BASE_URL}/auth/register", json={
        "email": email, "password": password, "full_name": full_name
    })
    if res.status_code not in (200, 201, 400):
        raise Exception(f"Registration failed [{res.status_code}]")

    res = _post_with_retry(f"{BASE_URL}/auth/login", data={
        "username": email, "password": password
    })
    if res.status_code != 200:
        raise Exception(f"Login failed [{res.status_code}]: {res.text}")
    return res.json()["access_token"]


def upload_contract(token: str, filepath: str) -> str:
    headers = {"Authorization": f"Bearer {token}"}
    with open(filepath, "rb") as f:
        files = {"file": (os.path.basename(filepath), f, "application/pdf")}
        res = _post_with_retry(f"{BASE_URL}/contracts/upload", headers=headers, files=files)
    if res.status_code not in (200, 201):
        raise Exception(f"Upload failed [{res.status_code}]: {res.text}")
    return res.json()["id"]


def run_tests() -> None:
    print("=== PHASE 6.1 CANONICAL E2E AUDIT START ===")
    failures = []

    # --------------------------------------------------------------------------
    # 1. Synthetic Contracts (distinct facts for RAG isolation testing)
    # --------------------------------------------------------------------------
    pdf_a = "contract_e2e_ny.pdf"
    pdf_b = "contract_e2e_ca.pdf"
    create_synthetic_pdf(pdf_a,
        "This SaaS Agreement is governed by the laws of New York. "
        "The contract value is $999,999. The term is 24 months. "
        "The supplier is liable up to the contract value.")
    create_synthetic_pdf(pdf_b,
        "This Master Service Agreement is governed by the laws of California. "
        "The contract value is $111,111. The term is 12 months. "
        "Late payments accrue interest at 2% per month.")

    # --------------------------------------------------------------------------
    # 2. Auth
    # --------------------------------------------------------------------------
    email_a = f"e2e_usera_{uuid.uuid4()}@example.com"
    email_b = f"e2e_userb_{uuid.uuid4()}@example.com"
    token_a = register_and_login(email_a, "Password123!", "E2E User A")
    token_b = register_and_login(email_b, "Password123!", "E2E User B")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    cid_a = upload_contract(token_a, pdf_a)
    cid_b = upload_contract(token_b, pdf_b)
    cid_a2 = upload_contract(token_a, pdf_b)  # User A uploads a second contract for comparison

    print(f"Contract A (User A): {cid_a}")
    print("Waiting 10s for chunking/embedding pipeline...")
    time.sleep(10)

    # --------------------------------------------------------------------------
    # 3. Core Agent Endpoints
    # --------------------------------------------------------------------------
    print("\n--- A. CORE AGENT ENDPOINTS ---")
    for ep in ["summarize", "clauses", "risk", "compliance", "negotiation"]:
        res = requests.post(f"{BASE_URL}/analysis/{ep}/{cid_a}", headers=headers_a)
        status = "PASS" if res.status_code == 200 else "FAIL"
        print(f"  {ep.capitalize():15s}: HTTP {res.status_code} [{status}]")
        if res.status_code != 200:
            failures.append(f"{ep}: HTTP {res.status_code}")

    res = requests.post(f"{BASE_URL}/analysis/knowledge-graph/{cid_a}", headers=headers_a)
    status = "PASS" if res.status_code == 200 else "FAIL"
    print(f"  {'KnowledgeGraph':15s}: HTTP {res.status_code} [{status}]")
    if res.status_code != 200:
        failures.append(f"knowledge-graph: HTTP {res.status_code}")

    # Comparison (both contracts belong to User A)
    res = requests.post(f"{BASE_URL}/analysis/compare", headers=headers_a,
                        json={"contract_a_id": cid_a, "contract_b_id": cid_a2})
    status = "PASS" if res.status_code == 200 else "FAIL"
    print(f"  {'Compare':15s}: HTTP {res.status_code} [{status}]")
    if res.status_code != 200:
        failures.append(f"compare: HTTP {res.status_code}")

    # History
    res = requests.get(f"{BASE_URL}/history/", headers=headers_a)
    status = "PASS" if res.status_code == 200 else "FAIL"
    print(f"  {'History':15s}: HTTP {res.status_code} [{status}]")
    if res.status_code != 200:
        failures.append(f"history: HTTP {res.status_code}")

    # --------------------------------------------------------------------------
    # 4. Cross-Tenant Isolation
    # --------------------------------------------------------------------------
    print("\n--- B. CROSS-TENANT ISOLATION ---")
    res = requests.post(f"{BASE_URL}/analysis/summarize/{cid_b}", headers=headers_a)
    expected_403 = res.status_code in (401, 403)
    print(f"  User A -> User B's contract: HTTP {res.status_code} [{'PASS' if expected_403 else 'FAIL'}]")
    if not expected_403:
        failures.append(f"Cross-tenant isolation FAILED: HTTP {res.status_code}")

    # --------------------------------------------------------------------------
    # 5. RAG Chat Grounding
    # --------------------------------------------------------------------------
    print("\n--- C. RAG CHAT GROUNDING ---")

    def chat(question: str) -> dict:
        r = requests.post(f"{BASE_URL}/analysis/chat/{cid_a}", headers=headers_a,
                          json={"question": question})
        assert r.status_code == 200, f"Chat failed: {r.status_code}"
        return r.json().get("result", {})

    term_ans = chat("What is the contract term?")
    safe_term = str(term_ans.get("answer", "")).encode("ascii", errors="replace").decode("ascii")
    print(f"  [Positive] Term: {safe_term[:80]}")
    if "24" not in str(term_ans.get("answer", "")):
        failures.append("RAG: Positive term query did not return 24 months")

    hipaa_ans = chat("What are the HIPAA requirements?")
    safe_hipaa = str(hipaa_ans.get("answer", "")).encode("ascii", errors="replace").decode("ascii")
    print(f"  [Negative] HIPAA: {safe_hipaa[:80]}")
    answer_text = str(hipaa_ans.get("answer", "")).lower()
    if "not find" not in answer_text and "no information" not in answer_text and "no hipaa" not in answer_text and "not available" not in answer_text:
        failures.append(f"RAG: Negative HIPAA query may have hallucinated: {hipaa_ans.get('answer', '')[:100]}")

    rag_sep = chat("Is the governing law California?")
    safe_ans = str(rag_sep.get("answer", "")).encode("ascii", errors="replace").decode("ascii")
    print(f"  [RAG Sep] Cal law: {safe_ans[:80]}")
    if "california" in str(rag_sep.get("answer", "")).lower() and "no" not in str(rag_sep.get("answer", "")).lower():
        failures.append("RAG separation failure: Contract A returned California as governing law")

    # --------------------------------------------------------------------------
    # 6. API Error Boundaries
    # --------------------------------------------------------------------------
    print("\n--- D. ERROR BOUNDARIES ---")
    res = requests.post(f"{BASE_URL}/analysis/summarize/not-a-uuid", headers=headers_a)
    print(f"  Malformed UUID:    HTTP {res.status_code} [{'PASS' if res.status_code == 422 else 'FAIL'}]")
    if res.status_code != 422:
        failures.append(f"Malformed UUID: expected 422, got {res.status_code}")

    res = requests.post(f"{BASE_URL}/analysis/summarize/{uuid.uuid4()}", headers=headers_a)
    print(f"  Non-existent UUID: HTTP {res.status_code} [{'PASS' if res.status_code == 404 else 'FAIL'}]")
    if res.status_code != 404:
        failures.append(f"Non-existent UUID: expected 404, got {res.status_code}")

    res = requests.post(f"{BASE_URL}/analysis/summarize/{cid_a}")  # No auth
    print(f"  No auth header:    HTTP {res.status_code} [{'PASS' if res.status_code == 401 else 'FAIL'}]")
    if res.status_code != 401:
        failures.append(f"No-auth: expected 401, got {res.status_code}")

    # --------------------------------------------------------------------------
    # 7. PostgreSQL Telemetry
    # --------------------------------------------------------------------------
    print("\n--- E. POSTGRESQL TELEMETRY ---")
    db = SessionLocal()
    try:
        rows = db.execute(
            text("SELECT agent_name, task_type, latency_ms FROM agent_execution_logs "
                 "WHERE contract_id = :cid ORDER BY created_at"),
            {"cid": cid_a}
        ).fetchall()
        print(f"  Execution logs for Contract A: {len(rows)}")
        agents_logged = set()
        for row in rows:
            agents_logged.add(row[0])
            print(f"    - {row[0]:25s} | {row[1]:20s} | {round(row[2], 0)}ms")

        for required_agent in ["SummaryAgent", "KnowledgeGraphAgent"]:
            if required_agent not in agents_logged:
                failures.append(f"Telemetry: {required_agent} not in agent_execution_logs")
            else:
                print(f"  {required_agent} telemetry: PASS")
    finally:
        db.close()

    # --------------------------------------------------------------------------
    # 8. Final Summary
    # --------------------------------------------------------------------------
    print("\n=== PHASE 6.1 CANONICAL E2E AUDIT COMPLETE ===")
    if failures:
        print(f"\nFAILURES ({len(failures)}):")
        for f in failures:
            print(f"  ✗ {f}")
        sys.exit(1)
    else:
        print(f"\nALL CHECKS PASSED — Phase 6.1 PROVEN")


if __name__ == "__main__":
    run_tests()
