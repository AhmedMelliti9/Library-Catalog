"""
book_service.py
Business logic layer for books.
Calls the BookRepository — never writes SQL directly.
Raises domain exceptions that routes convert to HTTP responses.
"""

from typing import Optional
from app.repositories.book_repository import BookRepository
from app.models.book import BookCreate, BookUpdate
from app.exceptions import BookNotFoundError

_repo = BookRepository()


def create_book(data: BookCreate) -> dict:
    return _repo.create(data)


def get_book(book_id: int) -> dict:
    book = _repo.get_by_id(book_id)
    if book is None:
        raise BookNotFoundError(f"Book with id {book_id} not found.")
    return book


def get_all_books(
    author_id: Optional[int] = None,
    genre: Optional[str] = None,
    available: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    return _repo.get_all(
        author_id=author_id,
        genre=genre,
        available=available,
        limit=limit,
        offset=offset,
    )


def search_books(keyword: str, limit: int = 50, offset: int = 0) -> list[dict]:
    return _repo.search(keyword=keyword, limit=limit, offset=offset)


def update_book(book_id: int, data: BookUpdate) -> dict:
    book = _repo.update(book_id, data)
    if book is None:
        raise BookNotFoundError(f"Book with id {book_id} not found.")
    return book


def delete_book(book_id: int) -> None:
    deleted = _repo.delete(book_id)
    if not deleted:
        raise BookNotFoundError(f"Book with id {book_id} not found.")


def checkout_book(book_id: int) -> dict:
    return _repo.checkout(book_id)


def return_book(book_id: int) -> dict:
    return _repo.return_book(book_id)
