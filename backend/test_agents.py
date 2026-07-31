import json
import os
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(ROOT / ".env")

from app.core.config import settings
from app.services.vector_service import vector_service


class AgentTestResult:
    def __init__(self, name: str, display_name: str) -> None:
        self.name = name
        self.display_name = display_name
        self.success = False
        self.execution_time_ms = 0.0
        self.input_tokens: Optional[int] = None
        self.output_tokens: Optional[int] = None
        self.error: Optional[str] = None
        self.output: Any = None

    @property
    def status_mark(self) -> str:
        return "✓ PASS" if self.success else "✗ FAIL"

    def to_report_lines(self) -> List[str]:
        return [
            f"Agent: {self.display_name}",
            f"Status: {'PASS' if self.success else 'FAIL'}",
            f"Execution Time: {self.execution_time_ms:.1f} ms",
            f"Input Tokens: {self.input_tokens if self.input_tokens is not None else 'Not Available'}",
            f"Output Tokens: {self.output_tokens if self.output_tokens is not None else 'Not Available'}",
            f"Error: {self.error or 'None'}",
            f"Output: {json.dumps(self.output, ensure_ascii=False, default=str)[:3000]}",
            "",
        ]


def print_status(label: str, ok: bool, detail: str = "") -> None:
    marker = "✓" if ok else "✗"
    if detail:
        print(f"{marker} {label}: {detail}")
    else:
        print(f"{marker} {label}")


def check_configuration() -> List[Tuple[str, bool]]:
    print("\n--------------------------------------------------")
    print("1. Load Configuration")
    print("--------------------------------------------------")

    required_keys = [
        ("GEMINI_API_KEY", settings.GEMINI_API_KEY),
        ("OPENROUTER_API_KEY", settings.OPENROUTER_API_KEY),
        ("GEMINI_MODEL", settings.GEMINI_MODEL),
        ("OPENROUTER_MODEL", settings.OPENROUTER_MODEL),
    ]

    results: List[Tuple[str, bool]] = []
    for key, value in required_keys:
        ok = bool(str(value or "").strip())
        status_text = "Loaded" if ok else "Missing"
        print_status(key, ok, status_text)
        results.append((key, ok))

    return results


def verify_database() -> Tuple[bool, Optional[str]]:
    print("\n--------------------------------------------------")
    print("2. Database")
    print("--------------------------------------------------")

    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("✓ Database Connected")
        return True, None
    except Exception as exc:  # pragma: no cover
        print("✗ Database Connection Failed")
        print(str(exc))
        return False, str(exc)


def build_sample_contract() -> str:
    return """
SERVICE AGREEMENT

This agreement is entered between ABC Pvt Ltd and XYZ Solutions.

Payment shall be made within 30 days.

The agreement may be terminated with 60 days written notice.

Both parties agree to maintain confidentiality.

This agreement shall be governed by Indian law.
""".strip()


def build_comparison_contract() -> str:
    return """
SERVICE AGREEMENT

This agreement is entered between ABC Pvt Ltd and XYZ Solutions.

Payment shall be made within 15 days.

The agreement may be terminated with 30 days written notice.

Both parties agree to maintain confidentiality.

This agreement shall be governed by Indian law.
""".strip()


def chunk_text(text: str) -> List[Dict[str, Any]]:
    paragraphs = [segment.strip() for segment in text.split("\n\n") if segment.strip()]
    chunks: List[Dict[str, Any]] = []
    for index, paragraph in enumerate(paragraphs, start=1):
        chunk_id = f"chunk_{index}"
        parent_id = f"parent_{index}"
        chunks.append(
            {
                "child_id": chunk_id,
                "parent_id": parent_id,
                "child_text": paragraph,
                "parent_text": paragraph,
            }
        )
    return chunks


def prepare_contract_storage(contract_text: str, contract_id: str) -> None:
    os.makedirs(settings.FAISS_INDEX_PATH, exist_ok=True)
    chunks = chunk_text(contract_text)
    metadata_path = Path(settings.FAISS_INDEX_PATH) / f"{contract_id}_metadata.json"
    metadata_path.write_text(json.dumps(chunks, indent=2), encoding="utf-8")
    try:
        vector_service.index_contract_chunks(contract_id, chunks, db=None)
    except Exception:
        pass


def extract_result_payload(response: Any) -> Any:
    if response is None:
        return {}
    if hasattr(response, "result"):
        result = getattr(response, "result")
        if isinstance(result, dict):
            return result
    if isinstance(response, dict):
        return response
    return response


def looks_meaningful(payload: Any, display_name: str) -> bool:
    if isinstance(payload, dict):
        if not payload:
            return False
        if display_name == "Summary Agent":
            return bool(payload.get("summary")) or bool(payload.get("key_obligations")) or bool(payload.get("critical_clauses"))
        if display_name == "Clause Agent":
            return bool(payload.get("clauses"))
        if display_name == "Risk Agent":
            return "overall_score" in payload or bool(payload.get("risk_matrix"))
        if display_name == "Compliance Agent":
            return "compliant" in payload or bool(payload.get("recommendations")) or bool(payload.get("issues"))
        if display_name == "Negotiation Agent":
            return bool(payload.get("negotiation_suggestions")) or bool(payload.get("priority_actions"))
        if display_name == "Comparison Agent":
            return bool(payload.get("similarities")) or bool(payload.get("differences")) or bool(payload.get("summary"))
        if display_name == "Retrieval Agent":
            return bool(payload.get("context")) or bool(payload.get("chunks")) or bool(payload.get("sources"))
        if display_name == "QA Agent":
            return bool(payload.get("final_response"))
        if display_name == "Knowledge Graph":
            return bool(payload.get("statistics")) or bool(payload.get("entities")) or bool(payload.get("relationships"))
        if display_name == "Chat Agent":
            return bool(payload.get("answer"))
        return any(
            isinstance(value, (str, list, dict)) and value not in ({}, [])
            for value in payload.values()
        )
    if isinstance(payload, list):
        return len(payload) > 0
    if isinstance(payload, str):
        return bool(payload.strip())
    return bool(payload)


def run_agent_case(name: str, display_name: str, runner: Any, contract_id: str, comparison_contract_id: Optional[str] = None) -> AgentTestResult:
    result = AgentTestResult(name, display_name)
    start = time.perf_counter()
    try:
        if name == "comparison_agent":
            response = runner(contract_id, comparison_contract_id or str(uuid.uuid4()))
        else:
            response = runner(contract_id)
        elapsed_ms = (time.perf_counter() - start) * 1000
        result.execution_time_ms = round(elapsed_ms, 1)

        payload = extract_result_payload(response)
        success = bool(getattr(response, "success", True))
        if isinstance(response, dict) and "success" in response:
            success = bool(response.get("success", True))
        if success and looks_meaningful(payload, display_name):
            result.success = True
        else:
            result.success = False

        if hasattr(response, "processing_metrics"):
            metrics = response.processing_metrics
            result.input_tokens = getattr(metrics, "input_tokens", None)
            result.output_tokens = getattr(metrics, "output_tokens", None)
        result.output = payload
        if not result.success:
            result.error = "Agent returned an empty or unsuccessful response"
    except Exception as exc:  # pragma: no cover
        result.execution_time_ms = round((time.perf_counter() - start) * 1000, 1)
        result.error = str(exc)
        result.output = {"exception": traceback.format_exc()}
    return result


def run_summary_case(contract_id: str, *_args: Any) -> Any:
    from app.agents.summary_agent import run_summary_agent

    return run_summary_agent(contract_id, query="summary", top_k=5)


def run_clause_case(contract_id: str, *_args: Any) -> Any:
    from app.agents.clause_agent import run_clause_agent

    return run_clause_agent(contract_id, query="clauses", top_k=5)


def run_risk_case(contract_id: str, *_args: Any) -> Any:
    from app.agents.risk_agent import run_risk_analysis

    return run_risk_analysis(contract_id, top_k=5)


def run_compliance_case(contract_id: str, *_args: Any) -> Any:
    from app.agents.compliance_agent import run_compliance_agent

    return run_compliance_agent(contract_id, top_k=5)


def run_negotiation_case(contract_id: str, *_args: Any) -> Any:
    from app.agents.negotiation_agent import run_negotiation_agent

    return run_negotiation_agent(contract_id, top_k=5)


def run_comparison_case(contract_id: str, comparison_contract_id: Optional[str] = None, *_args: Any) -> Any:
    from app.agents.comparison_agent import run_comparison_agent

    return run_comparison_agent(contract_id, comparison_contract_id or str(uuid.uuid4()), top_k=5)


def run_retrieval_case(contract_id: str, *_args: Any) -> Any:
    from app.agents.retrieval_agent import retrieve

    return retrieve(contract_id, "What is the payment clause?", top_k=5)


def run_qa_case(contract_id: str, *_args: Any) -> Any:
    from app.agents.qa_agent import call_gemini, return_structured_output

    state = {"contract_text": build_sample_contract(), "query": "When can the agreement be terminated?"}
    return return_structured_output(call_gemini(state))


def run_knowledge_graph_case(contract_id: str, *_args: Any) -> Any:
    from app.agents.knowledge_graph_agent import run_knowledge_graph_agent

    return run_knowledge_graph_agent(contract_id, top_k=5)


def run_chat_case(contract_id: str, *_args: Any) -> Any:
    from app.agents.chat_agent import run_chat_agent

    questions = [
        "What is this agreement about?",
        "What is the payment term?",
        "Can either party terminate?",
    ]

    last_response = None
    for question in questions:
        last_response = run_chat_agent(contract_id, question, top_k=5)
        if not getattr(last_response, "success", False):
            raise RuntimeError("chat agent did not return a successful response")
        payload = extract_result_payload(last_response)
        if not isinstance(payload, dict) or not str(payload.get("answer", "")).strip():
            raise RuntimeError("chat agent returned an empty answer")
    return last_response


def run_all_agents(contract_id: str, comparison_contract_id: str) -> List[AgentTestResult]:
    test_cases = [
        ("summary_agent", "Summary Agent", run_summary_case),
        ("clause_agent", "Clause Agent", run_clause_case),
        ("risk_agent", "Risk Agent", run_risk_case),
        ("compliance_agent", "Compliance Agent", run_compliance_case),
        ("negotiation_agent", "Negotiation Agent", run_negotiation_case),
        ("comparison_agent", "Comparison Agent", run_comparison_case),
        ("retrieval_agent", "Retrieval Agent", run_retrieval_case),
        ("qa_agent", "QA Agent", run_qa_case),
        ("knowledge_graph_agent", "Knowledge Graph", run_knowledge_graph_case),
        ("chat_agent", "Chat Agent", run_chat_case),
    ]

    results: List[AgentTestResult] = []
    for name, display_name, runner in test_cases:
        print(f"\nRunning {display_name}...")
        result = run_agent_case(name, display_name, runner, contract_id, comparison_contract_id)
        marker = "✓ PASS" if result.success else "✗ FAIL"
        print(marker)
        print(f"Execution Time: {result.execution_time_ms:.1f} ms")
        input_tokens_display = result.input_tokens if result.input_tokens is not None else "Not Available"
        output_tokens_display = result.output_tokens if result.output_tokens is not None else "Not Available"
        print(f"Input Tokens: {input_tokens_display}")
        print(f"Output Tokens: {output_tokens_display}")
        if result.error:
            print(f"Error: {result.error}")
        if display_name == "Knowledge Graph" and isinstance(result.output, dict):
            stats = result.output.get("statistics", {})
            if isinstance(stats, dict):
                print(f"Nodes: {stats.get('node_count', 0)}")
                print(f"Edges: {stats.get('edge_count', 0)}")
        results.append(result)
    return results


def write_report(results: List[AgentTestResult], started_at: datetime, completed_at: datetime, config_ok: bool, db_ok: bool, contract_id: str) -> None:
    report_path = ROOT / "agent_test_report.txt"
    passed = sum(1 for result in results if result.success)
    failed = [result.display_name for result in results if not result.success]

    lines: List[str] = []
    lines.append("LegalGPT Agent Test Report")
    lines.append("=" * 40)
    lines.append(f"Date: {completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Execution Time: {round((completed_at - started_at).total_seconds(), 2)} seconds")
    lines.append(f"Contract ID: {contract_id}")
    lines.append(f"Configuration: {'OK' if config_ok else 'FAILED'}")
    lines.append(f"Database: {'OK' if db_ok else 'FAILED'}")
    lines.append("")
    for result in results:
        lines.append(f"{result.display_name:<24} {result.status_mark}")
    lines.append("")
    lines.append(f"Agents Passed: {passed}/{len(results)}")
    lines.append("")
    lines.append("Overall Status:")
    if failed:
        lines.append("FAILED AGENTS")
        for name in failed:
            lines.append(f"- {name}")
    else:
        lines.append("✓ ALL AGENTS WORKING")
    lines.append("")
    lines.append("Errors:")
    for result in results:
        if result.error:
            lines.append(f"- {result.display_name}: {result.error}")
    lines.append("")
    lines.append("Agent Outputs:")
    for result in results:
        lines.append("-" * 40)
        lines.append(result.display_name)
        lines.append(json.dumps(result.output, ensure_ascii=False, default=str)[:4000])
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nSaved report to {report_path}")


def main() -> None:
    started_at = datetime.now(timezone.utc)
    print("=========================================")
    print("LegalGPT Agent Test Report")
    print("=========================================")

    config_results = check_configuration()
    config_ok = all(ok for _, ok in config_results)

    db_ok, db_error = verify_database()

    print("\n--------------------------------------------------")
    print("3. Create Sample Contract")
    print("--------------------------------------------------")
    contract_text = build_sample_contract()
    comparison_text = build_comparison_contract()
    print("Sample contract prepared for agent testing.")

    contract_id = str(uuid.uuid4())
    prepare_contract_storage(contract_text, contract_id)
    compare_contract_id = str(uuid.uuid4())
    prepare_contract_storage(comparison_text, compare_contract_id)

    print("\n--------------------------------------------------")
    print("4. Test Every Agent Individually")
    print("--------------------------------------------------")
    results = run_all_agents(contract_id, compare_contract_id)

    print("\n=========================================")
    print("LegalGPT Agent Test Report")
    print("=========================================")
    for result in results:
        print(f"{result.display_name:<24} {result.status_mark}")
    print("=========================================")
    passed = sum(1 for result in results if result.success)
    print(f"Agents Passed: {passed}/{len(results)}")
    print("\nOverall Status:")
    if passed == len(results):
        print("✓ ALL AGENTS WORKING")
    else:
        print("FAILED AGENTS")
        for result in results:
            if not result.success:
                print(f"- {result.display_name}")

    completed_at = datetime.now(timezone.utc)
    write_report(results, started_at, completed_at, config_ok, db_ok, contract_id)


if __name__ == "__main__":
    main()
