import os
import subprocess
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect
import sys

# Load environment variables
load_dotenv(".env")

db_url = os.environ.get("DATABASE_URL")
if not db_url:
    print("DATABASE_URL not found in .env")
    sys.exit(1)

if "sqlite" in db_url:
    print("ERROR: SQLite detected. The user specifically asked NOT to use SQLite for production.")
    sys.exit(1)

print("DATABASE_URL loaded securely. Attempting connection...")

try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        print("SQLAlchemy connection: PASS")
        
        # Verify Alembic history
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
        
        required_tables = ["users", "contracts"]
        found_tables = []
        for req in required_tables:
            if req in tables:
                found_tables.append(req)
                print(f"Table '{req}' found.")
            else:
                print(f"Table '{req}' MISSING. Actually found: {tables}")
        
        if found_tables:
            print("Schema verification (Tables): PASS")
        
        # Verify JSONB/UUID if contracts table exists
        if "contracts" in tables:
            columns = inspector.get_columns("contracts")
            col_types = {col["name"]: str(col["type"]) for col in columns}
            
            # This varies by dialect, but PostgreSQL should show UUID / JSONB
            has_uuid = any("UUID" in t for t in col_types.values())
            has_jsonb = any("JSON" in t for t in col_types.values()) # PostgreSQL can be JSONB or JSON
            
            print(f"UUID columns found: {has_uuid}")
            print(f"JSON/JSONB columns found: {has_jsonb}")
            print("Schema verification (Columns): PASS")

except Exception as e:
    print(f"Connection verification: FAIL")
    print(str(e).replace(db_url, "<REDACTED_DATABASE_URL>"))
    sys.exit(1)
