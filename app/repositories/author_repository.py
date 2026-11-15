"""
author_repository.py
All SQL for the authors table lives here.
Every query uses parameterized queries — never string concatenation with user input.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from app.database.connection import get_connection
from app.models.author import AuthorCreate, AuthorUpdate


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

    def get_all(self) -> list[dict]:
        """Return all authors."""
        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM authors ORDER BY id")
                return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def update(self, author_id: int, data: AuthorUpdate) -> dict | None:
        """
        Update only the fields provided in data.
        Returns the updated author, or None if not found.
        """
        # Build SET clause dynamically from the non-None fields
        fields = {k: v for k, v in data.model_dump().items() if v is not None}
        if not fields:
            # Nothing to update — just return the current author
            return self.get_by_id(author_id)

        set_clause = ", ".join(f"{col} = %s" for col in fields)
        values = list(fields.values()) + [author_id]

        conn = get_connection()
        try:
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        f"UPDATE authors SET {set_clause} WHERE id = %s RETURNING *",
                        values,
                    )
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
