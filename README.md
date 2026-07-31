# LegalGPT Enterprise

An AI-powered multi-user contract intelligence platform that helps organizations review, analyze, compare, and understand legal contracts using Generative AI.

---

## Technical Stack
- **Frontend**: Next.js 14 (App Router), React, Tailwind CSS, Lucide React, Zustand, Web Audio API
- **Backend**: FastAPI, Python 3.10+, SQLAlchemy
- **Database**: PostgreSQL (Auto-generates schemas on boot)
- **AI Stack**: Google Gemini 1.5 API, LangGraph (Multi-Agent State Graph), FAISS (Local Vector Indexes)

---

## Getting Started

### 1. Database Configuration
Ensure a local PostgreSQL instance is running with a database named `legalgpt`.
If needed, you can modify the connection string inside `backend/.env`:
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/legalgpt
```

Alternatively, you can run PostgreSQL via Docker Compose:
```yaml
# docker-compose.yml (in root folder)
version: '3.8'
services:
  db:
    image: postgres:15
    restart: always
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: legalgpt
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### 2. Backend Startup
1. Open a terminal and navigate to the backend folder:
   ```powershell
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
4. Run the development server:
   ```powershell
   uvicorn app.main:app --reload
   ```
The Swagger UI API documentation will be available at `http://localhost:8000/docs`.

### 3. Frontend Startup
1. Open a new terminal and navigate to the frontend folder:
   ```powershell
   cd frontend
   ```
2. Run the development server:
   ```powershell
   npm run dev
   ```
The user interface will be active at `http://localhost:3000`.

---

## Multi-Agent System Diagram

The LangGraph coordinator manages state transitions across five specialized legal agent nodes:
1. **Contract Analysis Agent**: Provides executive text summarization.
2. **Clause Extraction Agent**: Scans for specific legal obligations.
3. **Risk Analysis Agent**: Evaluates liability vectors and calculates risk safety indexes.
4. **Compliance Agent**: Audits clauses against GDPR constraints.
5. **Negotiation Agent**: Produces counter-party suggestion drafts.
6. **Judge Agent**: Verifies output data structures before finalizing executions.
