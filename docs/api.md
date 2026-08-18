# API reference

The API is served under `/api/v1`. Interactive OpenAPI documentation is available from the running application at `/docs` and remains the source of truth for request and response schemas.

## Authentication

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/auth/register` | Create a user and optional organization |
| POST | `/auth/login` | Obtain a bearer token using OAuth2 form data |

Authenticated endpoints require `Authorization: Bearer <token>`.

## Contracts

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/contracts/upload` | Upload and index a PDF contract |
| GET | `/contracts/` | List contracts visible to the current user |
| GET | `/contracts/{contract_id}` | Retrieve a contract |

## Analysis agents

| Method | Path | Agent |
| --- | --- | --- |
| POST | `/analysis/summarize/{contract_id}` | Summary |
| POST | `/analysis/risk/{contract_id}` | Risk analysis |
| POST | `/analysis/clauses/{contract_id}` | Clause extraction |
| POST | `/analysis/compliance/{contract_id}` | Compliance |
| POST | `/analysis/negotiation/{contract_id}` | Negotiation |
| POST | `/analysis/compare` | Contract comparison |
| POST | `/analysis/chat/{contract_id}` | Contract chat |
| POST | `/analysis/knowledge-graph/{contract_id}` | Knowledge graph |

## WebSocket chat

`/chat/ws/{contract_id}` provides authenticated streaming chat for a contract. Consult the OpenAPI/route implementation for token and message requirements.

## Errors

The API uses standard HTTP status codes. Validation failures return 4xx responses; unexpected server failures return 500 responses. Clients should never rely on internal implementation details in error messages.