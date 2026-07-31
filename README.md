# LegalGPT Enterprise

> Production-oriented contract intelligence API powered by FastAPI, PostgreSQL, retrieval-augmented generation, and specialized legal AI agents.

[![Python CI](https://github.com/your-org/legalgpt/actions/workflows/python.yml/badge.svg)](https://github.com/your-org/legalgpt/actions/workflows/python.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

LegalGPT Enterprise helps teams upload, search, analyze, compare, and discuss legal contracts. It combines deterministic retrieval with specialized AI agents while keeping the backend API suitable for a web frontend or other clients.

## Features

- Secure user registration and JWT-based authentication
- PDF contract upload, text extraction, and local FAISS indexing
- Hybrid semantic and BM25 retrieval with source citations
- Contract summary, clause extraction, risk, compliance, negotiation, comparison, chat, and knowledge-graph agents
- PostgreSQL persistence with Alembic migrations
- OpenAPI documentation at `/docs`
- Docker Compose deployment and GitHub Actions validation

## Architecture

```text
Client / Frontend
       |
       v
FastAPI API (`/api/v1`)
       |
       +--> Authentication and authorization
       +--> Contract upload and document parsing
       +--> Agent orchestration and API responses
                  |
                  +--> Hybrid retrieval --> FAISS indexes
                  +--> Specialized AI agents --> Gemini / OpenRouter
                  +--> SQLAlchemy --> PostgreSQL
```

See [architecture documentation](docs/architecture.md) for details.

## Repository structure

```text
.
+-- backend/
¦   +-- alembic/                 # Database migrations
¦   +-- app/
¦   ¦   +-- agents/              # Legal AI agents and prompts
¦   ¦   +-- api/v1/              # Stable HTTP and WebSocket routes
¦   ¦   +-- auth/                # Authentication helpers
¦   ¦   +-- core/                # Settings, database, security, retrieval config
¦   ¦   +-- models/              # SQLAlchemy models
¦   ¦   +-- schemas/             # Pydantic request/response contracts
¦   ¦   +-- services/            # LLM, retrieval, parsing, vector services
¦   ¦   +-- utils/               # Shared agent utilities
¦   +-- tests/                   # Automated tests
¦   +-- requirements.txt
+-- database/                    # Reference PostgreSQL schema
+-- docs/                        # Architecture, API, database, deployment docs
+-- Dockerfile
+-- docker-compose.yml
+-- README.md
```

## Tech stack

- Python 3.12, FastAPI, Uvicorn
- PostgreSQL, SQLAlchemy, Alembic
- LangChain, LangGraph, Google Gemini, OpenRouter
- FAISS, sentence-transformers, BM25 retrieval
- PyMuPDF for PDF extraction

## AI agent architecture

The application retains all existing agents:

- Summary
- Clause extraction
- Risk analysis
- Compliance
- Negotiation
- Contract comparison
- Retrieval
- Q&A
- Knowledge graph
- Contract chat

Each agent receives retrieved contract context and returns structured output for its corresponding API operation. See [docs/architecture.md](docs/architecture.md).

## Database design

Core entities are organizations, users, contracts, clauses, risk analyses, contract summaries, embeddings, agent execution logs, chat sessions, and chat messages. Read [database documentation](docs/database.md) before running migrations.

## Installation

### Prerequisites

- Python 3.12+
- PostgreSQL 15+
- A Gemini API key (OpenRouter is optional fallback)

### Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
```

Set your local values in `backend/.env`, then start PostgreSQL and run:

```powershell
cd backend
alembic upgrade head
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive OpenAPI documentation is at `http://127.0.0.1:8000/docs`.

## API documentation

All endpoints retain the `/api/v1` prefix. Key route groups:

- `/api/v1/auth` — registration and token login
- `/api/v1/contracts` — upload, list, retrieve, and ask questions
- `/api/v1/analysis` — AI-assisted contract analysis
- `/api/v1/chat` — authenticated WebSocket chat

See [docs/api.md](docs/api.md) for the route reference.

## Environment variables

Copy `backend/.env.example` to `backend/.env`. Do not commit the resulting file.

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` / `JWT_SECRET` | Token-signing secrets; use strong unique production values |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | Primary LLM provider |
| `OPENROUTER_API_KEY` / `OPENROUTER_MODEL` | Optional fallback LLM provider |
| `UPLOAD_DIR` | Local PDF storage directory |
| `FAISS_INDEX_PATH` | Local vector-index directory |

## Docker deployment

```bash
docker compose up --build
```

Configure `backend/.env` first, then run migrations:

```bash
docker compose exec api alembic upgrade head
```

See [deployment documentation](docs/deployment.md) for production guidance.

## Screenshots

> Add product screenshots or a short demo GIF here when the frontend is available.

## Future enhancements

- Frontend application and end-to-end tests
- Object storage for contract files
- Background job processing for long-running analysis
- Role-based administration and audit dashboards
- Observability, rate limiting, and production secrets management

## License

This project is licensed under the [MIT License](LICENSE).