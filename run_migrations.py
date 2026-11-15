"""
run_migrations.py
Reads and executes all SQL migration files in app/database/migrations/ in sorted order.
Uses CREATE TABLE IF NOT EXISTS so it is safe to run multiple times (idempotent).
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from app.database.connection import get_connection

load_dotenv()

MIGRATIONS_DIR = Path(__file__).parent / "app" / "database" / "migrations"


def run_migrations():
    # Collect all .sql files sorted by name (001, 002, 003 ...)
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    if not migration_files:
        print("No migration files found in", MIGRATIONS_DIR)
        return

    try:
        conn = get_connection()
        conn.autocommit = False
        cursor = conn.cursor()

        for migration_file in migration_files:
            print(f"Running migration: {migration_file.name} ...", end=" ")
            sql = migration_file.read_text(encoding="utf-8")
            cursor.execute(sql)
            print("OK")

        conn.commit()
        cursor.close()
        conn.close()
        print("\nAll migrations applied successfully.")

    except ConnectionError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        conn.rollback()
        print(f"\nERROR during migration: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    run_migrations()
