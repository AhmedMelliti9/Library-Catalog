"""
conftest.py
Sets up the test database connection and truncates all tables before each test
to guarantee a clean slate.
"""

import os
import pytest
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()


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
    conn = get_test_connection()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "TRUNCATE TABLE book_authors, books, authors RESTART IDENTITY CASCADE"
        )
    conn.close()
    yield


@pytest.fixture
def test_conn():
    """Provide a live connection to the test database for direct SQL assertions."""
    conn = get_test_connection()
    yield conn
    conn.close()
