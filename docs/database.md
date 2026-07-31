# Database design

LegalGPT uses PostgreSQL through SQLAlchemy and Alembic. The canonical migration history is in `backend/alembic/versions`; `database/schema.sql` is a lightweight reference schema.

## Core entities

```text
Organization 1 --- * User 1 --- * Contract
                              |        |
                              |        +--- * Clause
                              |        +--- 1 RiskAnalysis
                              |        +--- 1 ContractSummary
                              |        +--- * ContractEmbedding
                              |        +--- * AgentExecutionLog
                              |        +--- * ChatSession --- * ChatMessage
```

- `organizations`: tenant boundary for users.
- `users`: authenticated identities and roles.
- `contracts`: uploaded file metadata and generated summary.
- `clauses`, `risk_analyses`, `contract_summaries`, `contract_clauses`, and `contract_risks`: persisted analytical results.
- `contract_embeddings`: chunk metadata and optional stored embeddings.
- `agent_execution_logs`: execution metadata for agents.
- `chat_sessions` and `chat_messages`: contract discussion history.

## Migrations

Run migrations from `backend/`:

```bash
alembic upgrade head
```

Create new migrations only for intentional schema changes:

```bash
alembic revision --autogenerate -m "describe change"
```

Review generated migrations before committing. Do not use the reference SQL file and Alembic migrations as competing migration mechanisms in the same environment.