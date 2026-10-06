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
    classDef client fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0f172a
    classDef api fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#0f172a
    classDef llm fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#0f172a
    classDef data fill:#f3e8ff,stroke:#9333ea,stroke-width:2px,color:#0f172a
    classDef ops fill:#fee2e2,stroke:#dc2626,stroke-width:2px,color:#0f172a

    subgraph "Client Layer"
        U([User / Browser]):::client
        FE[Next.js React Frontend]:::client
        U <-->|HTTP/REST, WebSocket| FE
    end

    subgraph "API & Orchestration Layer (FastAPI)"
        API[FastAPI Gateway]:::api
        AUTH[JWT Auth Middleware]:::api
        WORKER[BackgroundTasks / Asyncio]:::api
        
        subgraph "LLM Orchestration & RAG Pipeline"
            ORCH[LangChain & LangGraph Orchestrator]:::api
            ROUTER{Semantic Router}:::api
            
            subgraph "Specialized Multi-Agents"
                SUMMARY[Executive Summary Agent]:::api
                CLAUSE[Clause Extraction Agent]:::api
                RISK[Risk Assessment Agent]:::api
                COMPLIANCE[Regulatory Compliance Agent]:::api
                NEGOTIATION[Negotiation Playbook Agent]:::api
                CHAT[Conversational Q&A Agent]:::api
                COMPARISON[Delta Comparison Agent]:::api
                GRAPH[Knowledge Graph Builder]:::api
            end
        end

        subgraph "Ingestion & Processing"
            INGEST[PDF Bytes Parser]:::api
            EXTRACT[PyMuPDF Text Extraction]:::api
            CHUNK[Recursive Parent/Child Chunker]:::api
            EMBED_API[Embedding Service]:::api
        end
    end

    subgraph "Data & Vector Storage"
        DB[(PostgreSQL / Neon)]:::data
        VECTOR[(pgvector HNSW Index)]:::data
        BM25[(BM25 Sparse Index)]:::data
        CACHE[(Redis Caching)]:::data
    end

    subgraph "External ML Models & Services"
        LLM_NIM[NVIDIA NIM - Primary LLM]:::llm
        LLM_OPENROUTER[OpenRouter - Fallback LLM]:::llm
        LLM_GEMINI[Google Gemini 1.5 - Vision & Embedding]:::llm
        EMBED_MODEL[gemini-embedding-2]:::llm
    end
    
    subgraph "Observability & LLMOps"
        LANGSMITH[LangSmith / Tracing]:::ops
        LOGGING[Winston / Datadog]:::ops
    end

    %% Client to API
    FE <-->|JSON Payloads| API
    API --> AUTH
    API --> WORKER

    %% Ingestion Flow
    WORKER --> INGEST
    INGEST --> EXTRACT
    EXTRACT --> CHUNK
    CHUNK --> EMBED_API
    EMBED_API -->|Batch API Calls| EMBED_MODEL
    EMBED_MODEL -->|Dense Vectors| VECTOR
    CHUNK -->|Tokenization| BM25

    %% RAG Retrieval Flow
    ORCH -->|Query Expansion| ROUTER
    ROUTER -->|Alpha=0.7| VECTOR
    ROUTER -->|Alpha=0.3| BM25
    VECTOR -->|Top-K Dense| RRF[Reciprocal Rank Fusion]
    BM25 -->|Top-K Sparse| RRF
    RRF -->|Ranked Context| ORCH
    
    %% Multi-Agent Routing
    ORCH --> SUMMARY & CLAUSE & RISK & COMPLIANCE & NEGOTIATION & CHAT & COMPARISON & GRAPH
    
    %% LLM Execution with Fallback
    SUMMARY & CLAUSE & RISK & COMPLIANCE & NEGOTIATION & CHAT & COMPARISON & GRAPH -->|Prompt + Context| LLM_NIM
    LLM_NIM -.->|Timeout / 503| LLM_OPENROUTER
    LLM_OPENROUTER -.->|Rate Limit| LLM_GEMINI
    
    %% Persistence
    API --> DB
    VECTOR --- DB
    
    %% Tracing
    ORCH -.->|Telemetery, Tokens, Latency| LANGSMITH
    LLM_NIM -.-> LANGSMITH
    API -.-> LOGGING
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
