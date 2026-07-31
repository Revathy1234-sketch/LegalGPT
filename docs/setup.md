# LegalGPT Setup Guide

## Project structure created
- `frontend/`
- `backend/`
- `database/`
- `uploads/`
- `vectorstore/`
- `reports/`
- `datasets/`
- `docs/`

## Backend structure
- `backend/app/main.py`
- `backend/app/config.py`
- `backend/app/database.py`
- `backend/app/auth/`
- `backend/app/api/v1/`
- `backend/app/models/`
- `backend/app/schemas/`
- `backend/app/services/`
- `backend/app/rag/`
- `backend/app/utils/`

## PostgreSQL setup
Use the following commands to create the database and user:

```sql
CREATE DATABASE legalgpt;
CREATE USER legalgpt_user WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE legalgpt TO legalgpt_user;
```

## Environment variables
Create or update `backend/.env` with:

```env
DATABASE_URL=postgresql://legalgpt_user:password@localhost/legalgpt
GEMINI_API_KEY=YOUR_GEMINI_KEY
SECRET_KEY=legalgpt_secret_key
JWT_SECRET=legalgpt_secret_key
```

## Run backend
1. `cd backend`
2. `python -m venv venv`
3. `venv\Scripts\activate`
4. `pip install -r requirements.txt`
5. `uvicorn app.main:app --reload`

Access docs at `http://127.0.0.1:8000/docs`.
