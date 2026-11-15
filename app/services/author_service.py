"""
author_service.py
Business logic layer for authors.
Calls the AuthorRepository — never writes SQL directly.
Raises domain exceptions that routes convert to HTTP responses.
"""

from app.repositories.author_repository import AuthorRepository
from app.models.author import AuthorCreate, AuthorUpdate
from app.exceptions import AuthorNotFoundError

_repo = AuthorRepository()


def create_author(data: AuthorCreate) -> dict:
    return _repo.create(data)


def get_author(author_id: int) -> dict:
    author = _repo.get_by_id(author_id)
    if author is None:
        raise AuthorNotFoundError(f"Author with id {author_id} not found.")
    return author


def get_all_authors() -> list[dict]:
    return _repo.get_all()


def update_author(author_id: int, data: AuthorUpdate) -> dict:
    author = _repo.update(author_id, data)
    if author is None:
        raise AuthorNotFoundError(f"Author with id {author_id} not found.")
    return author


def delete_author(author_id: int) -> None:
    deleted = _repo.delete(author_id)
    if not deleted:
        raise AuthorNotFoundError(f"Author with id {author_id} not found.")

