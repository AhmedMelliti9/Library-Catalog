"""
author_repository.py
All SQL for the authors table lives here.
Every query uses parameterized queries and psycopg2.sql identifier escaping
to strictly eliminate SQL injection vulnerabilities.
"""

from typing import Optional
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from app.database.connection import get_connection
from app.models.author import AuthorCreate, AuthorUpdate

ALLOWED_AUTHOR_COLUMNS = {"first_name", "last_name", "nationality"}


class AuthorRepository:

    def create(self, data: AuthorCreate) -> dict:
        """Insert a new author and return the created author."""
        conn = get_connection()
        try:
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        """
                        INSERT INTO authors (first_name, last_name, nationality)
                        VALUES (%s, %s, %s)
                        RETURNING *
                        """,
                        (data.first_name, data.last_name, data.nationality),
                    )
                    return dict(cursor.fetchone())
        finally:
            conn.close()

    def get_by_id(self, author_id: int) -> dict | None:
        """Return an author by ID, or None if not found."""
        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT * FROM authors WHERE id = %s",
                    (author_id,),
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        finally:
            conn.close()

    def get_all(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """Return authors with pagination."""
        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT * FROM authors ORDER BY id LIMIT %s OFFSET %s",
                    (limit, offset),
                )
                return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def update(self, author_id: int, data: AuthorUpdate) -> dict | None:
        """
        Update only the fields provided in data.
        Uses psycopg2.sql.Identifier to strictly escape column names against a whitelist.
        Returns the updated author, or None if not found.
        """
        # Validate columns against strict whitelist
        raw_fields = data.model_dump(exclude_unset=True)
        valid_fields = {k: v for k, v in raw_fields.items() if k in ALLOWED_AUTHOR_COLUMNS and v is not None}

        if not valid_fields:
            return self.get_by_id(author_id)

        set_parts = [
            sql.SQL("{} = %s").format(sql.Identifier(col))
            for col in valid_fields.keys()
        ]
        set_clause = sql.SQL(", ").join(set_parts)

        query = sql.SQL("UPDATE authors SET {} WHERE id = %s RETURNING *").format(set_clause)
        values = list(valid_fields.values()) + [author_id]

        conn = get_connection()
        try:
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, values)
                    row = cursor.fetchone()
                    return dict(row) if row else None
        finally:
            conn.close()

    def has_books(self, author_id: int) -> bool:
        """Check if an author has any associated books in book_authors."""
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM book_authors WHERE author_id = %s LIMIT 1",
                    (author_id,),
                )
                return cursor.fetchone() is not None
        finally:
            conn.close()

    def delete(self, author_id: int) -> bool:
        """Delete an author by ID. Returns True if deleted, False if not found."""
        conn = get_connection()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM authors WHERE id = %s",
                        (author_id,),
                    )
                    return cursor.rowcount > 0
        finally:
            conn.close()
