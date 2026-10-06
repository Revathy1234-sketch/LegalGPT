"""End-to-end test of every LegalGPT agent via the running API.

Usage: python test_all_agents_e2e.py [email] [password]
"""
import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://localhost:8000/api/v1"


def req(method, path, token=None, payload=None, timeout=600):
    url = BASE + path
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    start = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            body = resp.read().decode(errors="replace")
            return resp.status, body, time.time() - start
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        return exc.code, body, time.time() - start
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc), time.time() - start


def main():
    email = sys.argv[1] if len(sys.argv) > 1 else "bufftest@test.com"
    password = sys.argv[2] if len(sys.argv) > 2 else "Test1234"

    status, body, _ = req(
        "POST", "/auth/login",
        payload=None,
    ) if False else (0, "", 0)

    # login (form encoded)
    request = urllib.request.Request(
        BASE + "/auth/login",
        data=f"username={email}&password={password}".encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as resp:
        token = json.load(resp)["access_token"]
    print(f"login: OK")

    status, body, _ = req("GET", "/contracts/", token)
    contracts = json.loads(body)
    if not contracts:
        print("No contracts available - upload one first.")
        sys.exit(1)
    # Prefer a substantive contract (real MSA) over tiny synthetic test docs.
    preferred = (
        [c for c in contracts if "real" in c["file_name"].lower()]
        or [c for c in contracts if "e2e" in c["file_name"].lower()]
        or contracts
    )
    target = preferred[0]
    cid = target["id"]
    print(f"contract: {target['file_name']} ({cid})")

    agents = [
        ("Summary", "POST", f"/analysis/summarize/{cid}", None),
        ("Clause Extraction", "POST", f"/analysis/clauses/{cid}", None),
        ("Risk Analysis", "POST", f"/analysis/risk/{cid}", None),
        ("Compliance", "POST", f"/analysis/compliance/{cid}", None),
        ("Negotiation", "POST", f"/analysis/negotiation/{cid}", None),
        ("Knowledge Graph", "POST", f"/analysis/knowledge-graph/{cid}?force=true", None),
        ("Contract Chat", "POST", f"/analysis/chat/{cid}", {"question": "What are the key obligations in this contract?"}),
        ("Dashboard Stats", "GET", "/dashboard/stats", None),
        ("Agent Status", "GET", "/dashboard/agent-status", None),
        ("History", "GET", "/history/", None),
        ("Workspace Sessions", "GET", "/chat/workspace/sessions", None),
    ]
    if len(contracts) >= 2:
        other = next((c for c in contracts if c["id"] != cid), None)
        if other:
            agents.append(
                ("Contract Comparison", "POST", "/analysis/compare",
                 {"contract_a_id": cid, "contract_b_id": other["id"]})
            )

    results = []
    for name, method, path, payload in agents:
        status, body, elapsed = req(method, path, token, payload)
        ok = 200 <= status < 300
        snippet = body[:160].replace("\n", " ")
        results.append((name, status, elapsed, ok))
        print(f"{'PASS' if ok else 'FAIL'} | {name:22} | HTTP {status} | {elapsed:6.1f}s | {snippet}")

    passed = sum(1 for r in results if r[3])
    print(f"\n{passed}/{len(results)} agents/endpoints passed")


if __name__ == "__main__":
    main()
