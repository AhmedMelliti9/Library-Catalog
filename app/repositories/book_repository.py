"""
book_repository.py
All SQL for the books and book_authors tables lives here.
Every query uses parameterized queries and psycopg2.sql identifier escaping
to strictly eliminate SQL injection vulnerabilities.

Key rule from project.md:
  - create() uses a transaction (INSERT book + INSERT book_authors atomically)
  - checkout() uses a transaction with SELECT ... FOR UPDATE to prevent race conditions
"""

from typing import Optional
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from app.database.connection import get_connection
from app.models.book import BookCreate, BookUpdate
from app.exceptions import (
    BookNotFoundError,
    BookAlreadyCheckedOutError,
    DuplicateISBNError,
    InvalidAuthorError,
)

ALLOWED_BOOK_COLUMNS = {"title", "isbn", "genre", "publication_year"}


def _row_to_book(book_row: dict, author_rows: list[dict]) -> dict:
    """Combine a book row and its author rows into a single response dict."""
    book = dict(book_row)
    book["authors"] = [dict(a) for a in author_rows]
    return book


def _fetch_authors_for_book(cursor, book_id: int) -> list[dict]:
    """Fetch all authors linked to a book via book_authors."""
    cursor.execute(
        """
        SELECT a.*
        FROM authors a
        JOIN book_authors ba ON a.id = ba.author_id
        WHERE ba.book_id = %s
        ORDER BY a.id
        """,
        (book_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


class BookRepository:

    # ------------------------------------------------------------------
    # CREATE — inserts book + author links in one transaction
    # ------------------------------------------------------------------

    def create(self, data: BookCreate) -> dict:
        """
        Insert a new book and its author relationships inside a single transaction.
        Rolls back entirely if any author_id is invalid or the ISBN is duplicate.
        """
        conn = get_connection()
        try:
            conn.autocommit = False
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # 1. Insert the book
                try:
                    cursor.execute(
                        """
                        INSERT INTO books (title, isbn, genre, publication_year)
                        VALUES (%s, %s, %s, %s)
                        RETURNING *
                        """,
                        (data.title, data.isbn, data.genre, data.publication_year),
                    )
                except psycopg2.errors.UniqueViolation:
                    conn.rollback()
                    raise DuplicateISBNError(
                        f"A book with ISBN '{data.isbn}' already exists."
                    )

                book_row = dict(cursor.fetchone())
                book_id = book_row["id"]

                # 2. Insert book_authors links
                for author_id in data.author_ids:
                    try:
                        cursor.execute(
                            """
                            INSERT INTO book_authors (book_id, author_id)
                            VALUES (%s, %s)
                            """,
                            (book_id, author_id),
                        )
                    except psycopg2.errors.ForeignKeyViolation:
                        conn.rollback()
                        raise InvalidAuthorError(
                            f"Author with id {author_id} does not exist."
                        )

                # 3. Fetch the linked authors to include in the response
                author_rows = _fetch_authors_for_book(cursor, book_id)

            conn.commit()
            return _row_to_book(book_row, author_rows)

        except (DuplicateISBNError, InvalidAuthorError):
            raise
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # GET BY ID — returns book with its authors
    # ------------------------------------------------------------------

    def get_by_id(self, book_id: int) -> dict | None:
        """Return a book and its authors, or None if not found."""
        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT * FROM books WHERE id = %s",
                    (book_id,),
                )
                book_row = cursor.fetchone()
                if book_row is None:
                    return None
                author_rows = _fetch_authors_for_book(cursor, book_id)
                return _row_to_book(book_row, author_rows)
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # GET ALL — supports filtering and pagination
    # ------------------------------------------------------------------

    def get_all(
        self,
        author_id: int | None = None,
        genre: str | None = None,
        available: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """
        Return all books, with optional filters and pagination.
        Builds a parameterized WHERE clause dynamically from provided filters.
        """
        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                conditions = []
                params = []

                if genre is not None:
                    conditions.append("b.genre = %s")
                    params.append(genre)

                if available is not None:
                    conditions.append("b.available = %s")
                    params.append(available)

                if author_id is not None:
                    conditions.append(
                        "EXISTS (SELECT 1 FROM book_authors ba WHERE ba.book_id = b.id AND ba.author_id = %s)"
                    )
                    params.append(author_id)

                where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

                query = f"SELECT * FROM books b {where_clause} ORDER BY b.id LIMIT %s OFFSET %s"
                params.extend([limit, offset])

                cursor.execute(query, params)
                book_rows = cursor.fetchall()

                books = []
                for book_row in book_rows:
                    author_rows = _fetch_authors_for_book(cursor, book_row["id"])
                    books.append(_row_to_book(book_row, author_rows))
                return books
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # SEARCH — keyword search on title and author names (Parameterized)
    # ------------------------------------------------------------------

    def search(self, keyword: str, limit: int = 50, offset: int = 0) -> list[dict]:
        """
        Search books by keyword across book title and author first/last name.
        Uses 100% parameterized ILIKE queries to prevent SQL injection.
        """
        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                pattern = f"%{keyword}%"
                query = """
                    SELECT DISTINCT b.*
                    FROM books b
                    LEFT JOIN book_authors ba ON b.id = ba.book_id
                    LEFT JOIN authors a ON ba.author_id = a.id
                    WHERE b.title ILIKE %s
                       OR a.first_name ILIKE %s
                       OR a.last_name ILIKE %s
                       OR (a.first_name || ' ' || a.last_name) ILIKE %s
                    ORDER BY b.id
                    LIMIT %s OFFSET %s
                """
                cursor.execute(
                    query,
                    (pattern, pattern, pattern, pattern, limit, offset),
                )
                book_rows = cursor.fetchall()

                books = []
                for book_row in book_rows:
                    author_rows = _fetch_authors_for_book(cursor, book_row["id"])
                    books.append(_row_to_book(book_row, author_rows))
                return books
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update(self, book_id: int, data: BookUpdate) -> dict | None:
        """
        Update only the provided fields.
        Uses psycopg2.sql.Identifier to strictly escape column names against a whitelist.
        Also updates updated_at timestamp.
        Returns the updated book or None if not found.
        """
        raw_fields = data.model_dump(exclude_unset=True)
        valid_fields = {k: v for k, v in raw_fields.items() if k in ALLOWED_BOOK_COLUMNS and v is not None}

        if not valid_fields:
            return self.get_by_id(book_id)

        set_parts = [
            sql.SQL("{} = %s").format(sql.Identifier(col))
            for col in valid_fields.keys()
        ]
        set_parts.append(sql.SQL("updated_at = NOW()"))
        set_clause = sql.SQL(", ").join(set_parts)

        query = sql.SQL("UPDATE books SET {} WHERE id = %s RETURNING *").format(set_clause)
        values = list(valid_fields.values()) + [book_id]

        conn = get_connection()
        try:
            conn.autocommit = False
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                try:
                    cursor.execute(query, values)
                except psycopg2.errors.UniqueViolation:
                    conn.rollback()
                    raise DuplicateISBNError(
                        f"A book with that ISBN already exists."
                    )

                book_row = cursor.fetchone()
                if book_row is None:
                    conn.rollback()
                    return None

                author_rows = _fetch_authors_for_book(cursor, book_id)

            conn.commit()
            return _row_to_book(book_row, author_rows)

        except DuplicateISBNError:
            raise
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # CHECKOUT — atomic transaction with row-level lock (FOR UPDATE)
    # ------------------------------------------------------------------

    def checkout(self, book_id: int) -> dict:
        """
        Mark a book as unavailable (checked out).
        Uses a transaction with SELECT ... FOR UPDATE to lock the row.
        """
        conn = get_connection()
        try:
            conn.autocommit = False
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT id, available FROM books WHERE id = %s FOR UPDATE",
                    (book_id,),
                )
                row = cursor.fetchone()

                if row is None:
                    conn.rollback()
                    raise BookNotFoundError(f"Book with id {book_id} not found.")

                if not row["available"]:
                    conn.rollback()
                    raise BookAlreadyCheckedOutError(
                        f"Book with id {book_id} is already checked out."
                    )

                cursor.execute(
                    "UPDATE books SET available = false, updated_at = NOW() WHERE id = %s RETURNING *",
                    (book_id,),
                )
                book_row = cursor.fetchone()
                author_rows = _fetch_authors_for_book(cursor, book_id)

            conn.commit()
            return _row_to_book(book_row, author_rows)

        except (BookNotFoundError, BookAlreadyCheckedOutError):
            raise
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # RETURN BOOK
    # ------------------------------------------------------------------

    def return_book(self, book_id: int) -> dict:
        """
        Mark a book as available (returned).
        """
        conn = get_connection()
        try:
            conn.autocommit = False
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "UPDATE books SET available = true, updated_at = NOW() WHERE id = %s RETURNING *",
                    (book_id,),
                )
                book_row = cursor.fetchone()

                if book_row is None:
                    conn.rollback()
                    raise BookNotFoundError(f"Book with id {book_id} not found.")

                author_rows = _fetch_authors_for_book(cursor, book_id)

            conn.commit()
            return _row_to_book(book_row, author_rows)

        except BookNotFoundError:
            raise
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    def delete(self, book_id: int) -> bool:
        """
        Delete a book by ID.
        book_authors rows are deleted automatically via ON DELETE CASCADE.
        """
        conn = get_connection()
        try:
            conn.autocommit = False
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM books WHERE id = %s",
                    (book_id,),
                )
                deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
