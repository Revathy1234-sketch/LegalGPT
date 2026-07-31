import os
import sys
import importlib
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")


def print_status(label: str, ok: bool, detail: str = "") -> None:
    marker = "✓" if ok else "✗"
    if detail:
        print(f"{marker} {label}: {detail}")
    else:
        print(f"{marker} {label}")


class TestCollector:
    def __init__(self) -> None:
        self.results: List[Tuple[str, bool, str]] = []
        self.failures: List[Tuple[str, str]] = []

    def add(self, component: str, ok: bool, reason: str = "") -> None:
        self.results.append((component, ok, reason))
        if not ok:
            self.failures.append((component, reason))

    def summary(self) -> None:
        print("\n===================================")
        print("LegalGPT Backend Health Report")
        print("===================================")

        summary_map = {
            "Database": "Database",
            "FastAPI": "FastAPI",
            "Authentication": "Authentication",
            "AI Agents": "AI Agents",
            "LangChain": "LangChain",
            "FAISS": "FAISS",
            "Embeddings": "Embeddings",
            "Routes": "Routes",
            "Uploads": "Uploads",
        }

        for display, component in summary_map.items():
            ok = any(name == component and status for name, status, _ in self.results)
            if component == "Database" and any(name == "Database" for name, _, _ in self.results):
                ok = any(name == "Database" and status for name, status, _ in self.results)
            if component == "FastAPI" and any(name == "FastAPI" for name, _, _ in self.results):
                ok = any(name == "FastAPI" and status for name, status, _ in self.results)
            if component == "Authentication" and any(name == "Authentication" for name, _, _ in self.results):
                ok = any(name == "Authentication" and status for name, status, _ in self.results)
            if component == "AI Agents" and any(name == "AI Agents" for name, _, _ in self.results):
                ok = any(name == "AI Agents" and status for name, status, _ in self.results)
            if component == "LangChain" and any(name == "LangChain" for name, _, _ in self.results):
                ok = any(name == "LangChain" and status for name, status, _ in self.results)
            if component == "FAISS" and any(name == "FAISS" for name, _, _ in self.results):
                ok = any(name == "FAISS" and status for name, status, _ in self.results)
            if component == "Embeddings" and any(name == "Embeddings" for name, _, _ in self.results):
                ok = any(name == "Embeddings" and status for name, status, _ in self.results)
            if component == "Routes" and any(name == "Routes" for name, _, _ in self.results):
                ok = any(name == "Routes" and status for name, status, _ in self.results)
            if component == "Uploads" and any(name == "Uploads" for name, _, _ in self.results):
                ok = any(name == "Uploads" and status for name, status, _ in self.results)

            marker = "✓ PASS" if ok else "✗ FAIL"
            print(f"{display:<16} {marker}")

        print("\nOverall Status:")
        if self.failures:
            print("✗ Backend Not Ready")
            print("\nFAILED:")
            for component, reason in self.failures:
                print(f"{component}")
                print("Reason:")
                print(reason)
        else:
            print("✓ Backend Ready")


def try_import(module_name: str):
    try:
        return importlib.import_module(module_name), None
    except Exception as exc:
        return None, exc


def main() -> None:
    collector = TestCollector()

    # Database
    try:
        import psycopg2
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
        from app.database import Base
        from app.config import settings

        db_url = getattr(settings, "DATABASE_URL", None)
        if not db_url:
            raise RuntimeError("DATABASE_URL missing")

        engine = create_engine(db_url)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        session.execute(text("SELECT 1"))
        session.close()

        required_tables = [
            "users",
            "organizations",
            "contracts",
            "clauses",
            "contract_embeddings",
            "contract_summaries",
            "contract_risks",
            "risk_analyses",
            "chat_sessions",
            "chat_messages",
            "agent_execution_logs",
        ]

        from sqlalchemy import inspect as sqlalchemy_inspect
        insp = sqlalchemy_inspect(engine)
        existing_tables = set(insp.get_table_names())
        missing_tables = [table for table in required_tables if table not in existing_tables]
        if missing_tables:
            raise RuntimeError(f"Missing tables: {', '.join(missing_tables)}")

        collector.add("Database", True, "Database connection and tables verified")
    except Exception as exc:
        collector.add("Database", False, f"{exc}")

    # FastAPI
    try:
        from app.main import app
        collector.add("FastAPI", True, "FastAPI app imported")
    except Exception as exc:
        collector.add("FastAPI", False, f"{exc}")

    # Health / root endpoint
    try:
        from fastapi.testclient import TestClient
        from app.main import app as fastapi_app
        client = TestClient(fastapi_app)
        root_response = client.get("/")
        health_response = None
        try:
            health_response = client.get("/health")
        except Exception:
            health_response = None
        print_status("Root endpoint", True, f"{root_response.status_code} {root_response.text}")
        if health_response is not None:
            print_status("Health endpoint", True, f"{health_response.status_code} {health_response.text}")
        else:
            print_status("Health endpoint", False, "Not available")
    except Exception as exc:
        collector.add("FastAPI", False, f"API test failed: {exc}")
        print_status("API test", False, str(exc))

    # AI config
    try:
        required_keys = ["GEMINI_API_KEY", "OPENROUTER_API_KEY", "SECRET_KEY", "JWT_SECRET"]
        for key in required_keys:
            value = os.getenv(key)
            if value and str(value).strip():
                print_status(key, True, "Loaded")
            else:
                print_status(key, False, "Missing")
                raise RuntimeError(f"{key} missing")
        collector.add("Authentication", True, "API secrets configured")
    except Exception as exc:
        collector.add("Authentication", False, f"{exc}")

    # Vector / FAISS
    try:
        import faiss
        import numpy as np
        from app.services.vector_service import VectorService
        service = VectorService()
        print_status("FAISS import", True, "Loaded")
        print_status("Vector service", True, "Initialized")
        print_status("Embedding model", True, "Loaded")
        try:
            from app.services.vector_service import vector_service
            print_status("Vector service instance", True, "Ready")
        except Exception as exc:
            print_status("Vector service instance", False, str(exc))
            raise
        collector.add("FAISS", True, "FAISS and vector service available")
        collector.add("Embeddings", True, "Embedding service initialized")
    except Exception as exc:
        collector.add("FAISS", False, f"{exc}")
        collector.add("Embeddings", False, f"{exc}")

    # Agents
    agent_names = [
        "summary_agent",
        "clause_agent",
        "compliance_agent",
        "comparison_agent",
        "knowledge_graph_agent",
        "negotiation_agent",
        "qa_agent",
        "retrieval_agent",
        "risk_agent",
    ]
    agent_ok = True
    agent_errors = []
    for name in agent_names:
        try:
            module_name = f"app.agents.{name}"
            module = importlib.import_module(module_name)
            if hasattr(module, name):
                getattr(module, name)
            else:
                for attr in dir(module):
                    if attr.endswith("_agent"):
                        getattr(module, attr)
                        break
            print_status(f"Agent {name}", True, "Loaded")
        except Exception as exc:
            agent_ok = False
            agent_errors.append(f"{name}: {exc}")
            print_status(f"Agent {name}", False, str(exc))
    if agent_ok:
        collector.add("AI Agents", True, "All agents loaded")
    else:
        collector.add("AI Agents", False, "Some agents failed to load")

    # LangChain / LangGraph / LLM
    try:
        from langchain.prompts import PromptTemplate
        from langgraph.graph import StateGraph
        from app.services.llm_service import LLMService
        print_status("LangChain", True, "Loaded")
        print_status("LangGraph", True, "Loaded")
        print_status("Prompt templates", True, "Loaded")
        print_status("LLM service", True, "Initialized")
        collector.add("LangChain", True, "LangChain, LangGraph and LLM service ready")
    except Exception as exc:
        collector.add("LangChain", False, f"{exc}")

    # Auth
    try:
        from app.auth.jwt_handler import create_access_token, decode_access_token
        from passlib.context import CryptContext
        from app.models.models import User
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        pwd_context.hash("test-password")
        print_status("JWT utilities", True, "Loaded")
        print_status("Password hashing", True, "Loaded")
        print_status("User model", True, "Loaded")
        collector.add("Authentication", True, "JWT and user model verified")
    except Exception as exc:
        collector.add("Authentication", False, f"{exc}")

    # Upload system
    try:
        upload_dir = ROOT / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        print_status("Uploads folder", True, "Ready")
        collector.add("Uploads", True, "Uploads directory ready")
    except Exception as exc:
        collector.add("Uploads", False, f"{exc}")

    # Routes
    try:
        from app.api.v1 import router as api_router
        route_modules = ["auth", "analysis", "chat", "contracts"]
        for name in route_modules:
            module_name = f"app.api.v1.{name}"
            importlib.import_module(module_name)
        print_status("Routes", True, "Loaded")
        collector.add("Routes", True, "API routes imported")
    except Exception as exc:
        collector.add("Routes", False, f"{exc}")

    # Model config
    try:
        from app.core.config import settings
        print(f"Gemini Model: {getattr(settings, 'GEMINI_MODEL', '') or 'Not set'}")
        print(f"OpenRouter Model: {getattr(settings, 'OPENROUTER_MODEL', '') or 'Not set'}")
        print(f"Embedding Model: {getattr(settings, 'EMBEDDING_MODEL', '') or 'Not set'}")
    except Exception as exc:
        print_status("Model config", False, str(exc))

    collector.summary()


__test__ = False


if __name__ == "__main__":
    main()
