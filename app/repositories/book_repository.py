"""
book_repository.py
All SQL for the books and book_authors tables lives here.
Every query uses parameterized queries — never string concatenation with user input.

Key rule from project.md:
  - create() uses a transaction (INSERT book + INSERT book_authors atomically)
  - checkout() uses a transaction with SELECT ... FOR UPDATE to prevent race conditions
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from app.database.connection import get_connection
from app.models.book import BookCreate, BookUpdate
from app.exceptions import (
    BookNotFoundError,
    BookAlreadyCheckedOutError,
    DuplicateISBNError,
    InvalidAuthorError,
)


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
    # GET ALL — supports filtering by author_id, genre, available
    # ------------------------------------------------------------------

    def get_all(self, author_id: int | None = None, genre: str | None = None, available: bool | None = None) -> list[dict]:
        """
        Return all books, with optional filters.
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

                cursor.execute(
                    f"SELECT * FROM books b {where_clause} ORDER BY b.id",
                    params,
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
        Also updates updated_at timestamp.
        Returns the updated book or None if not found.
        """
        fields = {k: v for k, v in data.model_dump().items() if v is not None}
        if not fields:
            return self.get_by_id(book_id)

        # Always update updated_at
        set_parts = [f"{col} = %s" for col in fields] + ["updated_at = NOW()"]
        set_clause = ", ".join(set_parts)
        values = list(fields.values()) + [book_id]

        conn = get_connection()
        try:
            conn.autocommit = False
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                try:
                    cursor.execute(
                        f"UPDATE books SET {set_clause} WHERE id = %s RETURNING *",
                        values,
                    )
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

        Uses a transaction with SELECT ... FOR UPDATE to lock the row,
        preventing two simultaneous checkouts from both seeing available=true
        (race condition).

        Raises:
            BookNotFoundError: if the book does not exist.
            BookAlreadyCheckedOutError: if the book is already checked out.
        """
        conn = get_connection()
        try:
            conn.autocommit = False
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Lock the row for the duration of this transaction
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

                # Safe to mark as unavailable
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
        Raises BookNotFoundError if the book does not exist.
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
        Returns True if deleted, False if not found.
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
