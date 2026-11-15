"""
conftest.py
Sets up the test database, runs migrations, and provides an HTTP client
for integration tests against the FastAPI application.
"""

import os
from pathlib import Path
import pytest
import psycopg2
from dotenv import load_dotenv
import httpx

load_dotenv()

# Point DATABASE_URL to TEST_DATABASE_URL for the duration of tests
TEST_DB_URL = os.getenv("TEST_DATABASE_URL")
if TEST_DB_URL:
    os.environ["DATABASE_URL"] = TEST_DB_URL

from app.main import app

MIGRATIONS_DIR = Path(__file__).parent.parent / "database" / "migrations"


def run_test_migrations():
    """Ensure all migrations are applied to the test database."""
    if not TEST_DB_URL:
        return
    try:
        conn = psycopg2.connect(TEST_DB_URL)
        conn.autocommit = False
        with conn.cursor() as cur:
            for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
                cur.execute(sql_file.read_text(encoding="utf-8"))
        conn.commit()
        conn.close()
    except psycopg2.OperationalError:
        pass


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Run migrations once before running the test suite."""
    run_test_migrations()


def get_test_connection():
    """Return a connection to the TEST database."""
    test_db_url = os.getenv("TEST_DATABASE_URL")
    if not test_db_url:
        raise ValueError("TEST_DATABASE_URL environment variable is not set.")
    return psycopg2.connect(test_db_url)


@pytest.fixture(autouse=True)
def clean_database():
    """
    Truncate all tables before every test.
    RESTART IDENTITY resets serial counters so IDs start from 1 each test.
    CASCADE truncates dependent tables (book_authors) automatically.
    """
    try:
        conn = get_test_connection()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE TABLE book_authors, books, authors RESTART IDENTITY CASCADE"
            )
        conn.close()
    except psycopg2.OperationalError:
        pass
    yield


@pytest.fixture
def client():
    """HTTP client for testing the FastAPI endpoints."""
    transport = httpx.ASGITransport(app=app)
    with httpx.Client(transport=transport, base_url="http://testserver") as c:
        yield c
