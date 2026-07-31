# Deployment guide

## Docker Compose

1. Copy `backend/.env.example` to `backend/.env`.
2. Supply strong JWT secrets and LLM provider credentials.
3. Build and start the services:

   ```bash
   docker compose up --build -d
   ```

4. Apply migrations:

   ```bash
   docker compose exec api alembic upgrade head
   ```

The API is exposed on port `8000` and PostgreSQL on port `5432` for local development.

## Production checklist

- Store secrets in your hosting platform's secrets manager, never Git.
- Use strong unique `SECRET_KEY` and `JWT_SECRET` values.
- Restrict CORS origins for the deployed frontend.
- Put the API behind TLS termination and a reverse proxy.
- Use managed PostgreSQL with backups and network restrictions.
- Move uploads and FAISS indexes to persistent volumes or managed storage.
- Run Alembic migrations as a controlled deployment step.
- Add monitoring, log aggregation, request limits, and health checks.

## Image build

The root `Dockerfile` runs the API from `backend/`. Runtime data is mounted through named volumes in `docker-compose.yml`, keeping generated PDFs and indexes outside the Git repository.