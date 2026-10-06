import os
import subprocess
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
import sys
import uuid
from datetime import datetime

# Import models
from app.models.models import Organization, AgentExecutionLog

load_dotenv(".env")

db_url = os.environ.get("DATABASE_URL")
if not db_url:
    print("DATABASE_URL not found in .env")
    sys.exit(1)

if "sqlite" in db_url:
    print("ERROR: SQLite detected. Need PostgreSQL for production.")
    sys.exit(1)

print("DATABASE_URL loaded securely. Attempting connection...")

engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

try:
    with engine.connect() as conn:
        print("SQLAlchemy connection: PASS")
        
        # Verify it's PostgreSQL
        version_result = conn.execute(text("SELECT version();")).scalar()
        if "PostgreSQL" in version_result:
            print(f"Connected Database: PASS ({version_result[:30]}...)")
        else:
            print(f"Connected Database Warning: Not explicitly PostgreSQL? Got {version_result}")

        # Check Alembic history
        print("\nChecking Alembic history...")
        result = subprocess.run(["alembic", "history"], capture_output=True, text=True)
        if result.returncode == 0:
            print("Alembic history: PASS")
        else:
            print(f"Alembic history: FAIL - {result.stderr}")
            sys.exit(1)

        # Run Alembic upgrade head
        print("\nRunning Alembic upgrade head...")
        result = subprocess.run(["alembic", "upgrade", "head"], capture_output=True, text=True)
        if result.returncode == 0:
            print("Alembic migration: PASS")
        else:
            print(f"Alembic migration: FAIL - {result.stderr}")
            sys.exit(1)

        # Inspect schema
        print("\nVerifying required tables and columns...")
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        required_tables = ["users", "contracts", "organizations", "agent_execution_logs"]
        missing_tables = [req for req in required_tables if req not in tables]
        
        if missing_tables:
            print(f"Schema verification (Tables): FAIL - Missing: {missing_tables}")
        else:
            print("Schema verification (Tables): PASS")
            
            # Verify JSONB/UUID in agent_execution_logs
            columns = inspector.get_columns("agent_execution_logs")
            col_types = {col["name"]: str(col["type"]) for col in columns}
            
            has_uuid = any("UUID" in t for t in col_types.values())
            has_jsonb = any("JSONB" in t for t in col_types.values())
            
            if has_uuid and has_jsonb:
                print("UUID/JSONB schema types: PASS")
            else:
                print(f"UUID/JSONB schema types: FAIL - Types found: {col_types}")

        # Basic Read/Write Test
        print("\nTesting Database Read/Write operations...")
        session = SessionLocal()
        
        # 1. Write an organization
        test_org_id = uuid.uuid4()
        test_org = Organization(id=test_org_id, name="Test Neon Org")
        session.add(test_org)
        session.commit()
        
        # 2. Write an agent execution log (to test JSONB and UUID)
        test_log_id = uuid.uuid4()
        test_log = AgentExecutionLog(
            id=test_log_id,
            agent_name="TestAgent",
            task_type="Testing DB",
            input_payload={"test_key": "test_value"}
        )
        session.add(test_log)
        session.commit()
        
        # 3. Read back
        read_org = session.query(Organization).filter_by(id=test_org_id).first()
        read_log = session.query(AgentExecutionLog).filter_by(id=test_log_id).first()
        
        if read_org and read_org.name == "Test Neon Org" and read_log and read_log.input_payload.get("test_key") == "test_value":
            print("Database Read/Write: PASS")
        else:
            print("Database Read/Write: FAIL - Values did not match on read")
            
        # 4. Clean up
        session.delete(read_log)
        session.delete(read_org)
        session.commit()
        
        print("Database Cleanup: PASS")

except Exception as e:
    print(f"Connection verification: FAIL")
    print(str(e).replace(db_url, "<REDACTED_DATABASE_URL>"))
    sys.exit(1)
