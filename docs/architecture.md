# LegalGPT architecture

## Overview

LegalGPT is a layered FastAPI application. Route modules expose the public API, services provide document/LLM/retrieval capabilities, and agents compose those capabilities into legal workflows. PostgreSQL stores application data; FAISS stores local vector indexes generated from contract chunks.

```text
HTTP / WebSocket clients
          |
          v
FastAPI route layer
(auth, contracts, analysis, chat)
          |
          +------------------+---------------------+
          |                  |                     |
          v                  v                     v
  SQLAlchemy models    Agent modules         Service layer
          |            (specialized)    parser / LLM / retrieval / vector
          |                  |                     |
          +------------------+---------------------+
                             |
                PostgreSQL / FAISS / LLM providers
```

## Layers

- `app/api/v1`: request validation, authorization, and stable API routes.
- `app/auth`: password and JWT helpers used by the API layer.
- `app/agents`: summary, clause, risk, compliance, negotiation, comparison, retrieval, Q&A, knowledge graph, and chat workflows.
- `app/services`: reusable document parsing, retrieval, embedding, LLM, and execution-log services.
- `app/models` and `app/schemas`: database entities and API data contracts.
- `app/core`: application configuration, security, database session management, and retrieval configuration.

## Retrieval flow

1. A PDF is uploaded and validated.
2. PyMuPDF extracts text and the parser creates parent/child chunks.
3. The vector service creates embeddings and a per-contract FAISS index.
4. Hybrid retrieval combines semantic matches and BM25 matches.
5. Agents consume retrieved context and return structured results with metadata.

## Boundaries

The FastAPI endpoints are the public contract. Agent implementations, providers, and local storage are internal details behind those endpoints. Environment-specific values belong only in `backend/.env` or deployment secrets.