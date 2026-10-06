# LegalGPT

> Production-oriented contract intelligence API powered by FastAPI, PostgreSQL, retrieval-augmented generation, and specialized legal AI agents.

[![Python CI](https://github.com/Revathy1234-sketch/LegalGPT/actions/workflows/python.yml/badge.svg)](https://github.com/Revathy1234-sketch/LegalGPT/actions/workflows/python.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

LegalGPT is an AI-powered contract intelligence platform that helps users analyze, understand, compare, and interact with legal contracts using retrieval-augmented generation, specialized AI agents, hybrid search, and evidence-grounded language models.

*Disclaimer: LegalGPT is intended for contract intelligence and analysis and does not replace qualified legal counsel.*

## Project Links

- **Live Application**: [https://legalgpt-delta.vercel.app](https://legalgpt-delta.vercel.app)
- **GitHub Repository**: [https://github.com/Revathy1234-sketch/LegalGPT](https://github.com/Revathy1234-sketch/LegalGPT)

## Key Features

- **Secure Authentication**: JWT-based user registration and authentication.
- **Contract Processing**: PDF contract upload, text extraction (via PyMuPDF), and semantic parent/child chunking.
- **Advanced Hybrid Retrieval**: Semantic search (pgvector) combined with keyword search (BM25) and intelligent deduplication.
- **Specialized AI Agents**: Dedicated agents for summarization, clause extraction, risk assessment, compliance, negotiation, comparison, Q&A, and knowledge graphs.
- **LLM Provider Fallback**: Automatic failover hierarchy (NVIDIA NIM → OpenRouter → Google Gemini) for high availability.
- **Explainability**: Agents provide confidence scores, source references, and parent/child context.
- **Audit Logging**: Comprehensive tracking of agent executions, latency, and payloads.

## System Architecture

```mermaid
flowchart TB

    U[User]

    FE[Next.js / React Frontend]

    API[FastAPI Backend]

    AUTH[Authentication and Authorization]

    INGEST[Contract Ingestion]
    PDF[PDF Extraction]
    CHUNK[Document Chunking]
    EMBED[Gemini Embeddings]

    DB[(PostgreSQL / Neon)]
    VECTOR[(pgvector)]
    BM25[BM25 Keyword Retrieval]

    RETRIEVAL[Hybrid Retrieval]
    CONTEXT[Contract-Grounded Context]

    ORCH[LangChain + LangGraph]

    SUMMARY[Summary Agent]
    CLAUSE[Clause Agent]
    RISK[Risk Agent]
    COMPLIANCE[Compliance Agent]
    NEGOTIATION[Negotiation Agent]
    CHAT[Contract Chat Agent]
    COMPARISON[Comparison Agent]
    GRAPH[Knowledge Graph Agent]

    LLM[NVIDIA NIM]
    OPENROUTER[OpenRouter]
    GEMINI[Google Gemini]

    EVIDENCE[Evidence and Explainability]
    KG[Knowledge Graph]
    UI[Analysis Results and Visualization]

    U --> FE
    FE --> API
    API --> AUTH

    API --> INGEST
    INGEST --> PDF
    PDF --> CHUNK
    CHUNK --> EMBED

    EMBED --> VECTOR
    CHUNK --> BM25

    VECTOR --> RETRIEVAL
    BM25 --> RETRIEVAL
    RETRIEVAL --> CONTEXT

    API --> ORCH
    CONTEXT --> ORCH

    ORCH --> SUMMARY
    ORCH --> CLAUSE
    ORCH --> RISK
    ORCH --> COMPLIANCE
    ORCH --> NEGOTIATION
    ORCH --> CHAT
    ORCH --> COMPARISON
    ORCH --> GRAPH

    SUMMARY --> LLM
    CLAUSE --> LLM
    RISK --> LLM
    COMPLIANCE --> LLM
    NEGOTIATION --> LLM
    CHAT --> LLM
    COMPARISON --> LLM
    GRAPH --> LLM

    LLM --> OPENROUTER
    OPENROUTER --> GEMINI

    API --> DB
    DB --> EVIDENCE
    GRAPH --> KG
    EVIDENCE --> UI
    KG --> UI
```

## RAG Pipeline

Our Retrieval-Augmented Generation (RAG) architecture follows a precise pipeline:

1. **PDF Upload & Text Extraction**: PyMuPDF extracts raw text from uploaded contracts.
2. **Parent/Child Chunking**: The text is split into small semantic chunks (children) mapped to larger contextual windows (parents).
3. **Embeddings**: Generates vector embeddings for indexing in PostgreSQL.
4. **Hybrid Retrieval**: The user query triggers both pgvector (semantic) and BM25 (keyword) retrieval.
5. **Context Ranking & Deduplication**: Results are merged, ranked by a combined score, and parent chunks are deduplicated.
6. **Agent Processing**: The curated context is passed to the specialized LangGraph agent.
7. **Explainable Output**: The LLM generates a structured response citing specific chunk IDs and parent text.

## Multi-Agent Architecture

The system orchestrates multiple specialized LangChain/LangGraph agents to handle distinct tasks:

| Agent | Responsibility | Input | Output | Status |
|------|----------------|-------|--------|--------|
| **Summary Agent** | Contract overview | Retrieved contract context | Executive summary | Implemented |
| **Clause Agent** | Clause extraction | Contract text/context | Categorized clauses + confidence | Implemented |
| **Risk Agent** | Risk identification | Contract context | Risk score + risk matrix + mitigation | Implemented |
| **Compliance Agent** | Compliance analysis | Contract context | Compliance status + issues | Implemented |
| **Negotiation Agent** | Negotiation recommendations | Risk/clause context | Recommended wording + priority | Implemented |
| **Chat Agent** | Contract Q&A | User question + retrieved chunks | Grounded answer + sources | Implemented |
| **Comparison Agent** | Contract comparison | Two contracts | Differences, missing clauses, risk delta | Implemented |
| **Knowledge Graph Agent** | Relationship extraction | Contract entities/clauses | Relationships/graph data | Implemented |
| **Retrieval Agent** | Context retrieval | User query | Ranked, deduplicated chunks | Implemented |

## Explainability

Explainability is a core feature of LegalGPT. To improve trust and traceability:
- Responses are grounded in **retrieved contract chunks**.
- The system returns **source references** and **relevance scores** for cited text.
- Agents provide **confidence scores** for their analysis.
- **Parent/child context** ensures the LLM understands the broader context of a retrieved clause.
This RAG-based grounding significantly reduces the risk of hallucination and improves traceability.

## Technology Stack

**Backend & API**:
- Python 3.12+
- FastAPI, Uvicorn
- SQLAlchemy, Alembic (Migrations)
- PostgreSQL (Neon), pgvector

**AI & Orchestration**:
- LangChain, LangGraph
- NVIDIA NIM, OpenRouter, Google Gemini (Fallback hierarchy)

**Retrieval & Vector Search**:
- pgvector
- BM25
- Custom Hybrid Retrieval Pipeline

**Document Processing**:
- PyMuPDF (`pymupdf`), `pypdf`

## Project Structure

```text
.
├── backend/
│   ├── alembic/                 # Database migrations
│   ├── app/
│   │   ├── agents/              # Legal AI agents (LangGraph/LangChain)
│   │   ├── api/v1/              # FastAPI HTTP routes
│   │   ├── auth/                # JWT authentication logic
│   │   ├── core/                # Configuration and database setup
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic validation schemas
│   │   ├── services/            # LLM, Hybrid RAG, parsing services
│   │   └── utils/               # Shared utilities
│   ├── tests/                   # Pytest suite
│   ├── requirements.txt         # Python dependencies
│   └── .env.example             # Environment variables template
├── database/                    # Reference schema
├── docs/                        # Additional documentation
├── docker-compose.yml           # Docker deployment
└── Dockerfile                   # Docker image definition
```

## Database Architecture

The PostgreSQL database persists all critical state and agent execution logs.

```mermaid
flowchart TD
    User --> Organization
    User --> Contracts
    Contracts --> Clauses
    Contracts --> Contract_Embeddings
    Contracts --> Risk_Analysis
    Contracts --> Contract_Summary
    Contracts --> Chat_Sessions
    Chat_Sessions --> Chat_Messages
    Contracts --> Agent_Execution_Logs
```

## Installation

### Prerequisites
- Python 3.12+
- PostgreSQL 15+ (with pgvector)
- API Keys for NVIDIA NIM (Primary), OpenRouter, or Google Gemini

### Local Setup

1. **Clone the repository** (or navigate to the project directory):
   ```bash
   git clone https://github.com/Revathy1234-sketch/LegalGPT.git
   cd LegalGPT
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Windows
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # Linux/macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your PostgreSQL database URL and API keys
   ```

5. **Run database migrations**:
   ```bash
   alembic upgrade head
   ```

6. **Start the FastAPI server**:
   ```bash
   uvicorn app.main:app --reload
   ```

## Environment Variables

Copy `backend/.env.example` to `backend/.env`. **Never commit `.env` or secret credentials to Git.**

| Variable | Purpose | Example |
| --- | --- | --- |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@localhost:5432/legalgpt` |
| `SECRET_KEY` | JWT signing secret | `<your_strong_secret>` |
| `JWT_SECRET` | JWT signing secret | `<your_strong_secret>` |
| `NVIDIA_API_KEY` | Primary LLM Provider Key | `nvapi-...` |
| `OPENROUTER_API_KEY` | Fallback LLM Provider Key | `sk-or-v1-...` |
| `GEMINI_API_KEY` | Final Fallback LLM Provider Key | `AIzaSy...` |
| `UPLOAD_DIR` | Directory for PDF storage | `./uploads` |

## Running the Application

Once started, the API is accessible at `http://127.0.0.1:8000`.
Interactive Swagger documentation is available at `http://127.0.0.1:8000/docs`.

## Security

- **Environment Secrets**: Never commit `.env` files or expose API keys/JWT secrets.
- **Authentication**: JWT authentication is required for all contract and analysis routes.
- **Passwords**: Hashed securely via `pwdlib` and Argon2.
- **Authorization**: Strict role and organization-based access control (RBAC) implemented at the route level.
- **File Handling**: PDF validation and size limits are strictly enforced on upload.

## Limitations

- **Not Legal Counsel**: AI-generated analysis should always be reviewed by qualified legal professionals. The software does not provide legally binding advice.
- **Hallucinations**: While RAG significantly reduces hallucinations, model output can still contain errors.
- **Compliance Context**: Compliance analysis strictly depends on the predefined framework rules provided to the agent.
- **Confidence Scores**: These are statistical indicators of model certainty, not measures of legal validity.

## License

This project is licensed under the [MIT License](LICENSE).
