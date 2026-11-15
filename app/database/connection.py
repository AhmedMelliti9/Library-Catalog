import os
import psycopg2
from psycopg2 import OperationalError
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """
    Returns a new psycopg2 database connection using DATABASE_URL from environment variables.
    Raises a clear error if the database cannot be reached.
    """
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set.")

    try:
        connection = psycopg2.connect(database_url)
        return connection
    except OperationalError as e:
        raise ConnectionError(
            f"Could not connect to the database. "
            f"Please verify that PostgreSQL is running and DATABASE_URL is correct.\n"
            f"Details: {e}"
        )
