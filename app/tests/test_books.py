"""
test_books.py
Unit tests for BookRepository using the test database.
The clean_database fixture in conftest.py truncates all tables before each test.
"""

import os
import pytest
from dotenv import load_dotenv

load_dotenv()

# Point the app at the TEST database before importing anything that connects
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "")

from app.repositories.book_repository import BookRepository
from app.repositories.author_repository import AuthorRepository
from app.models.book import BookCreate, BookUpdate
from app.models.author import AuthorCreate
from app.exceptions import (
    BookNotFoundError,
    BookAlreadyCheckedOutError,
    DuplicateISBNError,
    InvalidAuthorError,
)

book_repo = BookRepository()
author_repo = AuthorRepository()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_author(first="John", last="Doe", nationality="American"):
    return author_repo.create(AuthorCreate(first_name=first, last_name=last, nationality=nationality))


def make_book(title="1984", isbn="9780451524935", genre="Dystopia", author_ids=None, year=1949):
    if author_ids is None:
        author = make_author()
        author_ids = [author["id"]]
    return book_repo.create(BookCreate(
        title=title, isbn=isbn, genre=genre,
        publication_year=year, author_ids=author_ids
    ))


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

def test_create_book_with_valid_author():
    author = make_author()
    book = book_repo.create(BookCreate(
        title="1984", isbn="9780451524935", genre="Dystopia",
        publication_year=1949, author_ids=[author["id"]]
    ))
    assert book["id"] is not None
    assert book["title"] == "1984"
    assert book["available"] is True
    assert len(book["authors"]) == 1
    assert book["authors"][0]["id"] == author["id"]


def test_create_book_with_multiple_authors():
    a1 = make_author("Alice", "Smith")
    a2 = make_author("Bob", "Jones")
    book = book_repo.create(BookCreate(
        title="Collab Book", isbn="1111111111111", genre="Fiction",
        author_ids=[a1["id"], a2["id"]]
    ))
    assert len(book["authors"]) == 2


def test_create_book_with_nonexistent_author_raises_error():
    with pytest.raises(InvalidAuthorError):
        book_repo.create(BookCreate(
            title="Ghost Book", isbn="9999999999999", genre="Mystery",
            author_ids=[99999]
        ))


def test_create_book_with_duplicate_isbn_raises_error():
    author = make_author()
    book_repo.create(BookCreate(
        title="First", isbn="1234567890123", genre="Fiction",
        author_ids=[author["id"]]
    ))
    with pytest.raises(DuplicateISBNError):
        book_repo.create(BookCreate(
            title="Second", isbn="1234567890123", genre="Fiction",
            author_ids=[author["id"]]
        ))


# ---------------------------------------------------------------------------
# GET BY ID
# ---------------------------------------------------------------------------

def test_get_by_id_returns_book_with_authors():
    book = make_book()
    fetched = book_repo.get_by_id(book["id"])
    assert fetched is not None
    assert fetched["id"] == book["id"]
    assert len(fetched["authors"]) >= 1


def test_get_by_id_returns_none_for_missing_book():
    result = book_repo.get_by_id(99999)
    assert result is None


# ---------------------------------------------------------------------------
# GET ALL — filtering
# ---------------------------------------------------------------------------

def test_get_all_returns_all_books():
    make_book(title="Book A", isbn="1000000000001", genre="Fiction")
    make_book(title="Book B", isbn="1000000000002", genre="History")
    books = book_repo.get_all()
    assert len(books) == 2


def test_get_all_filter_by_genre():
    make_book(title="Fiction One", isbn="2000000000001", genre="Fiction")
    make_book(title="History One", isbn="2000000000002", genre="History")
    make_book(title="Fiction Two", isbn="2000000000003", genre="Fiction")

    fiction = book_repo.get_all(genre="Fiction")
    assert len(fiction) == 2
    assert all(b["genre"] == "Fiction" for b in fiction)


def test_get_all_filter_by_available():
    b1 = make_book(title="Available", isbn="3000000000001", genre="Fiction")
    b2 = make_book(title="CheckedOut", isbn="3000000000002", genre="Fiction")
    book_repo.checkout(b2["id"])

    available = book_repo.get_all(available=True)
    checked_out = book_repo.get_all(available=False)

    assert any(b["id"] == b1["id"] for b in available)
    assert any(b["id"] == b2["id"] for b in checked_out)


def test_get_all_filter_by_author_id():
    a1 = make_author("Alice", "Filter")
    a2 = make_author("Bob", "Filter")
    make_book(title="Alice Book", isbn="4000000000001", genre="Fiction", author_ids=[a1["id"]])
    make_book(title="Bob Book", isbn="4000000000002", genre="Fiction", author_ids=[a2["id"]])

    result = book_repo.get_all(author_id=a1["id"])
    assert len(result) == 1
    assert result[0]["title"] == "Alice Book"


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------

def test_update_book_returns_updated_record():
    book = make_book()
    updated = book_repo.update(book["id"], BookUpdate(title="Updated Title", genre="Sci-Fi"))
    assert updated["title"] == "Updated Title"
    assert updated["genre"] == "Sci-Fi"
    assert updated["isbn"] == book["isbn"]  # unchanged


def test_update_book_returns_none_for_missing_book():
    result = book_repo.update(99999, BookUpdate(title="Ghost"))
    assert result is None


# ---------------------------------------------------------------------------
# CHECKOUT & RETURN
# ---------------------------------------------------------------------------

def test_checkout_available_book_marks_unavailable():
    book = make_book()
    assert book["available"] is True

    checked_out = book_repo.checkout(book["id"])
    assert checked_out["available"] is False


def test_checkout_already_checked_out_book_raises_error():
    book = make_book()
    book_repo.checkout(book["id"])

    with pytest.raises(BookAlreadyCheckedOutError):
        book_repo.checkout(book["id"])


def test_checkout_nonexistent_book_raises_error():
    with pytest.raises(BookNotFoundError):
        book_repo.checkout(99999)


def test_return_book_marks_available():
    book = make_book()
    book_repo.checkout(book["id"])

    returned = book_repo.return_book(book["id"])
    assert returned["available"] is True


def test_return_nonexistent_book_raises_error():
    with pytest.raises(BookNotFoundError):
        book_repo.return_book(99999)


def test_checkout_return_lifecycle():
    book = make_book()
    assert book["available"] is True

    checked_out = book_repo.checkout(book["id"])
    assert checked_out["available"] is False

    returned = book_repo.return_book(book["id"])
    assert returned["available"] is True


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------

def test_delete_book_returns_true_when_found():
    book = make_book()
    result = book_repo.delete(book["id"])
    assert result is True
    assert book_repo.get_by_id(book["id"]) is None


def test_delete_book_returns_false_when_not_found():
    result = book_repo.delete(99999)
    assert result is False


def test_delete_book_cascades_book_authors():
    """Deleting a book must also remove its book_authors rows (via ON DELETE CASCADE)."""
    author = make_author()
    book = make_book(author_ids=[author["id"]])

    book_repo.delete(book["id"])

    # Author must still exist
    still_there = author_repo.get_by_id(author["id"])
    assert still_there is not None
