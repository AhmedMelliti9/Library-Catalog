"""
test_books.py
Integration tests for books:
- Repository unit tests
- FastAPI endpoint HTTP integration tests (using client fixture)
"""

import os
import pytest
from dotenv import load_dotenv

load_dotenv()

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
# REPOSITORY UNIT TESTS
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


def test_get_by_id_returns_book_with_authors():
    book = make_book()
    fetched = book_repo.get_by_id(book["id"])
    assert fetched is not None
    assert fetched["id"] == book["id"]
    assert len(fetched["authors"]) >= 1


def test_get_by_id_returns_none_for_missing_book():
    result = book_repo.get_by_id(99999)
    assert result is None


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


def test_update_book_returns_updated_record():
    book = make_book()
    updated = book_repo.update(book["id"], BookUpdate(title="Updated Title", genre="Sci-Fi"))
    assert updated["title"] == "Updated Title"
    assert updated["genre"] == "Sci-Fi"
    assert updated["isbn"] == book["isbn"]


def test_update_book_returns_none_for_missing_book():
    result = book_repo.update(99999, BookUpdate(title="Ghost"))
    assert result is None


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


def test_delete_book_returns_true_when_found():
    book = make_book()
    result = book_repo.delete(book["id"])
    assert result is True
    assert book_repo.get_by_id(book["id"]) is None


def test_delete_book_returns_false_when_not_found():
    result = book_repo.delete(99999)
    assert result is False


def test_delete_book_cascades_book_authors():
    author = make_author()
    book = make_book(author_ids=[author["id"]])

    book_repo.delete(book["id"])

    still_there = author_repo.get_by_id(author["id"])
    assert still_there is not None


# ---------------------------------------------------------------------------
# API ENDPOINT INTEGRATION TESTS (Task 8 Required Scenarios)
# ---------------------------------------------------------------------------

def test_api_create_book_with_valid_author(client):
    """Required: Create a book with valid author -> 201"""
    author = client.post("/authors", json={"first_name": "Frank", "last_name": "Herbert"}).json()
    response = client.post(
        "/books",
        json={
            "title": "Dune",
            "isbn": "9780441172719",
            "genre": "Sci-Fi",
            "publication_year": 1965,
            "author_ids": [author["id"]],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Dune"
    assert data["available"] is True
    assert len(data["authors"]) == 1
    assert data["authors"][0]["id"] == author["id"]


def test_api_create_book_with_nonexistent_author(client):
    """Required: Create a book with non-existent author -> 400"""
    response = client.post(
        "/books",
        json={
            "title": "Ghost Book",
            "isbn": "9999999999999",
            "genre": "Mystery",
            "author_ids": [99999],
        },
    )
    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"].lower()


def test_api_create_book_with_duplicate_isbn(client):
    """Required: Create a book with duplicate ISBN -> 409"""
    author = client.post("/authors", json={"first_name": "Ray", "last_name": "Bradbury"}).json()
    payload = {
        "title": "Fahrenheit 451",
        "isbn": "9781451673319",
        "genre": "Dystopian",
        "author_ids": [author["id"]],
    }
    first_res = client.post("/books", json=payload)
    assert first_res.status_code == 201

    duplicate_res = client.post("/books", json=payload)
    assert duplicate_res.status_code == 409
    assert "already exists" in duplicate_res.json()["detail"].lower()


def test_api_checkout_available_book(client):
    """Required: Check out an available book -> 200"""
    author = client.post("/authors", json={"first_name": "Isaac", "last_name": "Asimov"}).json()
    book = client.post(
        "/books",
        json={
            "title": "Foundation",
            "isbn": "9780553293357",
            "genre": "Sci-Fi",
            "author_ids": [author["id"]],
        },
    ).json()

    checkout_res = client.post(f"/books/{book['id']}/checkout")
    assert checkout_res.status_code == 200
    assert checkout_res.json()["available"] is False


def test_api_checkout_already_checked_out_book(client):
    """Required: Check out an already checked-out book -> 409"""
    author = client.post("/authors", json={"first_name": "Isaac", "last_name": "Asimov"}).json()
    book = client.post(
        "/books",
        json={
            "title": "Foundation",
            "isbn": "9780553293357",
            "genre": "Sci-Fi",
            "author_ids": [author["id"]],
        },
    ).json()

    # First checkout -> 200
    client.post(f"/books/{book['id']}/checkout")

    # Second checkout -> 409
    second_res = client.post(f"/books/{book['id']}/checkout")
    assert second_res.status_code == 409
    assert "already checked out" in second_res.json()["detail"].lower()


def test_api_checkout_nonexistent_book(client):
    response = client.post("/books/99999/checkout")
    assert response.status_code == 404


def test_api_return_book(client):
    author = client.post("/authors", json={"first_name": "C.S.", "last_name": "Lewis"}).json()
    book = client.post(
        "/books",
        json={
            "title": "Narnia",
            "isbn": "9780064404990",
            "genre": "Fantasy",
            "author_ids": [author["id"]],
        },
    ).json()

    client.post(f"/books/{book['id']}/checkout")
    return_res = client.post(f"/books/{book['id']}/return")
    assert return_res.status_code == 200
    assert return_res.json()["available"] is True


def test_api_filter_books_by_genre(client):
    """Required: Filter books by genre -> returns only matching books"""
    author = client.post("/authors", json={"first_name": "Genre", "last_name": "Author"}).json()
    client.post("/books", json={"title": "SciFi 1", "isbn": "0000000000001", "genre": "Sci-Fi", "author_ids": [author["id"]]})
    client.post("/books", json={"title": "History 1", "isbn": "0000000000002", "genre": "History", "author_ids": [author["id"]]})
    client.post("/books", json={"title": "SciFi 2", "isbn": "0000000000003", "genre": "Sci-Fi", "author_ids": [author["id"]]})

    res = client.get("/books?genre=Sci-Fi")
    assert res.status_code == 200
    books = res.json()
    assert len(books) == 2
    assert all(b["genre"] == "Sci-Fi" for b in books)


def test_api_filter_books_by_availability(client):
    author = client.post("/authors", json={"first_name": "Avail", "last_name": "Author"}).json()
    b1 = client.post("/books", json={"title": "Avail Book", "isbn": "1111111111101", "genre": "General", "author_ids": [author["id"]]}).json()
    b2 = client.post("/books", json={"title": "Busy Book", "isbn": "1111111111102", "genre": "General", "author_ids": [author["id"]]}).json()
    client.post(f"/books/{b2['id']}/checkout")

    avail_res = client.get("/books?available=true")
    assert avail_res.status_code == 200
    assert any(b["id"] == b1["id"] for b in avail_res.json())
    assert not any(b["id"] == b2["id"] for b in avail_res.json())


def test_api_filter_books_by_author_id(client):
    a1 = client.post("/authors", json={"first_name": "A1", "last_name": "One"}).json()
    a2 = client.post("/authors", json={"first_name": "A2", "last_name": "Two"}).json()
    client.post("/books", json={"title": "A1's Book", "isbn": "2222222222201", "genre": "Fiction", "author_ids": [a1["id"]]})
    client.post("/books", json={"title": "A2's Book", "isbn": "2222222222202", "genre": "Fiction", "author_ids": [a2["id"]]})

    res = client.get(f"/books?author_id={a1['id']}")
    assert res.status_code == 200
    books = res.json()
    assert len(books) == 1
    assert books[0]["title"] == "A1's Book"


def test_api_get_book_by_id(client):
    author = client.post("/authors", json={"first_name": "J.R.R.", "last_name": "Tolkien"}).json()
    book = client.post("/books", json={"title": "The Hobbit", "isbn": "9780547928227", "genre": "Fantasy", "author_ids": [author["id"]]}).json()

    res = client.get(f"/books/{book['id']}")
    assert res.status_code == 200
    assert res.json()["title"] == "The Hobbit"


def test_api_get_book_not_found(client):
    res = client.get("/books/99999")
    assert res.status_code == 404


def test_api_update_book(client):
    author = client.post("/authors", json={"first_name": "Ernest", "last_name": "Hemingway"}).json()
    book = client.post("/books", json={"title": "Old Man", "isbn": "9780684801223", "genre": "Classic", "author_ids": [author["id"]]}).json()

    res = client.put(f"/books/{book['id']}", json={"title": "The Old Man and the Sea"})
    assert res.status_code == 200
    assert res.json()["title"] == "The Old Man and the Sea"


def test_api_delete_book(client):
    author = client.post("/authors", json={"first_name": "Mark", "last_name": "Twain"}).json()
    book = client.post("/books", json={"title": "Tom Sawyer", "isbn": "9780143039563", "genre": "Classic", "author_ids": [author["id"]]}).json()

    del_res = client.delete(f"/books/{book['id']}")
    assert del_res.status_code == 204

    # Verify deleted
    assert client.get(f"/books/{book['id']}").status_code == 404
