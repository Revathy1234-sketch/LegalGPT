# LegalGPT

> Production-oriented contract intelligence API powered by FastAPI, PostgreSQL, retrieval-augmented generation, and specialized legal AI agents.

[![Python CI](https://github.com/your-org/legalgpt/actions/workflows/python.yml/badge.svg)](https://github.com/your-org/legalgpt/actions/workflows/python.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

LegalGPT Enterprise helps teams upload, search, analyze, compare, and discuss legal contracts. It combines deterministic retrieval with specialized AI agents while keeping the backend API highly scalable and secure.

## Overview

LegalGPT Enterprise uses a multi-agent RAG (Retrieval-Augmented Generation) architecture to provide explainable contract intelligence. The system leverages state-of-the-art hybrid retrieval (FAISS semantic + BM25 keyword) to ground LLM responses directly in the uploaded contract text, reducing hallucinations and providing traceable citations.

## Problem Statement

Reviewing contracts manually is time-consuming, prone to human error, and inconsistent. Existing generalized LLMs hallucinate legal facts and lack the context required for deep contract analysis. LegalGPT Enterprise solves this by coupling a robust RAG pipeline with specialized AI agents designed for specific legal tasks (Risk, Compliance, Negotiation).

## Key Features

- **Secure Authentication**: JWT-based user registration and authentication.
- **Contract Processing**: PDF contract upload, text extraction, and parent/child chunking.
- **Advanced Hybrid Retrieval**: Semantic search (FAISS) combined with keyword search (BM25) and intelligent deduplication.
- **Specialized AI Agents**: Dedicated agents for summarization, clause extraction, risk assessment, compliance, negotiation, comparison, Q&A, and knowledge graphs.
- **LLM Provider Fallback**: Automatic failover hierarchy (NVIDIA NIM → OpenRouter → Google Gemini) for high availability.
- **Explainability**: Agents provide confidence scores, source references, and parent/child context.
- **Audit Logging**: Comprehensive tracking of agent executions, latency, and payloads.

## System Architecture

```mermaid
flowchart TD
    A[Client Request] --> B[FastAPI Backend]
    B --> C[Authentication / JWT]
    C --> D[Contract Upload / Processing]
    D --> E[PyMuPDF Text Extraction]
    E --> F[Parent/Child Chunking]
    F --> G[Sentence Transformers Embeddings]
    G --> H[FAISS Index]
    F --> I[BM25 Index]
    H --> J[Hybrid Retrieval Engine]
    I --> J
    J --> K[Relevant Contract Context]
    K --> L[Agent Orchestration Layer]
    L --> M[LLM Provider Fallback Pipeline]
    M --> N[Structured Explainable Response]
    N --> O[(PostgreSQL Database)]
```

## RAG Pipeline

Our Retrieval-Augmented Generation (RAG) architecture follows a precise pipeline:

1. **PDF Upload & Text Extraction**: PyMuPDF extracts raw text from uploaded contracts.
2. **Parent/Child Chunking**: The text is split into small semantic chunks (children) mapped to larger contextual windows (parents).
3. **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` generates vector embeddings.
4. **Hybrid Retrieval**: The user query triggers both FAISS (semantic) and BM25 (keyword) retrieval.
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

Explainability is a core feature of LegalGPT Enterprise. To improve trust and traceability:
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
- PostgreSQL, psycopg2

**AI & Orchestration**:
- LangChain, LangGraph
- NVIDIA NIM, OpenRouter, Google Gemini (Fallback hierarchy)
- `sentence-transformers`

**Retrieval & Vector Search**:
- FAISS (CPU)
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
- PostgreSQL 15+
- API Keys for NVIDIA NIM (Primary), OpenRouter, or Google Gemini

### Local Setup

1. **Clone the repository** (or navigate to the project directory):
   ```bash
   cd LegalGPT
   ```

2. **Create and activate a virtual environment**:
   ```powershell
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
| `FAISS_INDEX_PATH` | Directory for local vector index | `./faiss_index` |
| `EMBEDDING_MODEL` | Local embedding model | `sentence-transformers/all-MiniLM-L6-v2` |

## Running the Application

Once started, the API is accessible at `http://127.0.0.1:8000`.
Interactive Swagger documentation is available at `http://127.0.0.1:8000/docs`.

## API Documentation

### Authentication
- `POST /api/v1/auth/register`: Register a new user.
- `POST /api/v1/auth/login`: Authenticate and receive a JWT Bearer token.

### Contracts
- `POST /api/v1/contracts/upload`: Upload a PDF contract, extract text, chunk, embed, and index it.
- `GET /api/v1/contracts/`: List user/organization contracts.
- `GET /api/v1/contracts/{contract_id}`: Retrieve contract details and metadata.

### Analysis (Agent Triggers)
- `POST /api/v1/analysis/summarize/{contract_id}`: Generate an executive summary.
- `POST /api/v1/analysis/clauses/{contract_id}`: Extract and categorize clauses.
- `POST /api/v1/analysis/risk/{contract_id}`: Generate a risk score and risk matrix.
- `POST /api/v1/analysis/compliance/{contract_id}`: Check against compliance frameworks.
- `POST /api/v1/analysis/negotiation/{contract_id}`: Provide actionable negotiation suggestions.
- `POST /api/v1/analysis/compare`: Compare two contracts and highlight differences.
- `POST /api/v1/analysis/chat/{contract_id}`: Conversational agent interaction.
- `POST /api/v1/analysis/knowledge-graph/{contract_id}`: Extract entity relationships.

## Demo Workflow

1. **User Authentication**: User registers and logs in to receive a JWT.
2. **Contract Upload**: User uploads a PDF Non-Disclosure Agreement via `POST /api/v1/contracts/upload`.
3. **Processing**: The backend parses the PDF, creates parent/child chunks, generates `sentence-transformers` embeddings, and indexes them in FAISS and BM25.
4. **Agent Analysis**: User calls `POST /api/v1/analysis/risk/{contract_id}`.
5. **Execution**: The Risk Agent retrieves context using hybrid search, identifies weaknesses, and calculates a risk score using the active LLM provider.
6. **Result Storage**: The structured analysis (risk matrix, mitigation plan) is saved to PostgreSQL and returned to the user.
7. **Q&A**: User calls `POST /api/v1/analysis/chat/{contract_id}` with a specific question. The system returns a grounded answer with citations to specific contract chunks.

## Example Analysis (Test Output)

*Note: The following represents output from internal testing and does not constitute universal behavior or legal advice.*

**Risk Agent Response**:
- **Overall Risk Score**: 70
- **Identified Concerns**:
  - Undefined scope of Confidential Information
  - Unspecified/indefinite confidentiality duration
  - Missing breach remedies/indemnification

**Negotiation Agent Response**:
- **Clause Title**: Duration of confidentiality obligations
- **Recommended Wording**: Suggests limiting the obligation to 2-3 years post-termination.
- **Priority**: High

## Security

- **Environment Secrets**: Never commit `.env` files or expose API keys/JWT secrets.
- **Authentication**: JWT authentication is required for all contract and analysis routes.
- **Passwords**: Hashed securely via `pwdlib` and Argon2.
- **Authorization**: Strict role and organization-based access control (RBAC) implemented at the route level.
- **File Handling**: PDF signature validation and size limits are strictly enforced on upload.

## Limitations

- **Not Legal Counsel**: AI-generated analysis should always be reviewed by qualified legal professionals. The software does not provide legally binding advice.
- **Hallucinations**: While RAG significantly reduces hallucinations, model output can still contain errors.
- **Compliance Context**: Compliance analysis strictly depends on the predefined framework rules provided to the agent.
- **Confidence Scores**: These are statistical indicators of model certainty, not measures of legal validity.

## Future Scope

The following features are planned for future iterations (currently **not implemented**):
- **Voice Interaction**: Speech-to-text contract querying.
- **Human-in-the-loop**: Features for lawyers to manually override or correct agent findings.
- **Cloud Object Storage**: Migrating from local file storage to AWS S3 / GCP Cloud Storage.
- **Advanced RBAC Dashboards**: UI for managing user roles and audit logs.

## License

This project is licensed under the [MIT License](LICENSE).
