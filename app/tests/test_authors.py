"""
test_authors.py
Integration tests for authors:
- Repository unit tests
- FastAPI endpoint HTTP integration tests (using client)
"""

import os
import pytest
from dotenv import load_dotenv

load_dotenv()

from app.repositories.author_repository import AuthorRepository
from app.repositories.book_repository import BookRepository
from app.models.author import AuthorCreate, AuthorUpdate
from app.models.book import BookCreate

repo = AuthorRepository()
book_repo = BookRepository()


# ---------------------------------------------------------------------------
# REPOSITORY TESTS
# ---------------------------------------------------------------------------

def test_create_author_returns_created_record():
    data = AuthorCreate(first_name="George", last_name="Orwell", nationality="British")
    author = repo.create(data)

    assert author["id"] is not None
    assert author["first_name"] == "George"
    assert author["last_name"] == "Orwell"
    assert author["nationality"] == "British"
    assert author["created_at"] is not None


def test_create_author_without_nationality():
    data = AuthorCreate(first_name="Homer", last_name="Unknown")
    author = repo.create(data)

    assert author["first_name"] == "Homer"
    assert author["nationality"] is None


def test_get_by_id_returns_correct_author():
    data = AuthorCreate(first_name="Jane", last_name="Austen", nationality="British")
    created = repo.create(data)

    fetched = repo.get_by_id(created["id"])

    assert fetched is not None
    assert fetched["id"] == created["id"]
    assert fetched["first_name"] == "Jane"
    assert fetched["last_name"] == "Austen"


def test_get_by_id_returns_none_for_missing_author():
    result = repo.get_by_id(99999)
    assert result is None


def test_get_all_returns_empty_list_when_no_authors():
    authors = repo.get_all()
    assert authors == []


def test_get_all_returns_all_authors():
    repo.create(AuthorCreate(first_name="A", last_name="One"))
    repo.create(AuthorCreate(first_name="B", last_name="Two"))
    repo.create(AuthorCreate(first_name="C", last_name="Three"))

    authors = repo.get_all()
    assert len(authors) == 3


def test_update_author_returns_updated_record():
    created = repo.create(AuthorCreate(first_name="Old", last_name="Name", nationality="French"))

    updated = repo.update(created["id"], AuthorUpdate(first_name="New", nationality="German"))

    assert updated is not None
    assert updated["first_name"] == "New"
    assert updated["last_name"] == "Name"
    assert updated["nationality"] == "German"


def test_update_author_returns_none_for_missing_author():
    result = repo.update(99999, AuthorUpdate(first_name="Ghost"))
    assert result is None


def test_update_with_no_fields_returns_existing_author():
    created = repo.create(AuthorCreate(first_name="Same", last_name="Person"))
    result = repo.update(created["id"], AuthorUpdate())

    assert result is not None
    assert result["first_name"] == "Same"


def test_delete_author_returns_true_when_found():
    created = repo.create(AuthorCreate(first_name="Del", last_name="Author"))
    result = repo.delete(created["id"])

    assert result is True
    assert repo.get_by_id(created["id"]) is None


def test_delete_author_returns_false_when_not_found():
    result = repo.delete(99999)
    assert result is False


# ---------------------------------------------------------------------------
# API ENDPOINT INTEGRATION TESTS (Task 8)
# ---------------------------------------------------------------------------

def test_api_create_author(client):
    response = client.post(
        "/authors",
        json={"first_name": "Arthur", "last_name": "Conan Doyle", "nationality": "British"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["first_name"] == "Arthur"
    assert data["last_name"] == "Conan Doyle"


def test_api_get_all_authors(client):
    client.post("/authors", json={"first_name": "Author", "last_name": "1"})
    client.post("/authors", json={"first_name": "Author", "last_name": "2"})

    response = client.get("/authors")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_api_get_author_by_id(client):
    created = client.post("/authors", json={"first_name": "Leo", "last_name": "Tolstoy"}).json()
    response = client.get(f"/authors/{created['id']}")
    assert response.status_code == 200
    assert response.json()["last_name"] == "Tolstoy"


def test_api_get_author_not_found(client):
    response = client.get("/authors/99999")
    assert response.status_code == 404
    assert "detail" in response.json()


def test_api_update_author(client):
    created = client.post("/authors", json={"first_name": "Jules", "last_name": "Verne"}).json()
    response = client.put(
        f"/authors/{created['id']}",
        json={"nationality": "French"},
    )
    assert response.status_code == 200
    assert response.json()["nationality"] == "French"


def test_api_delete_author_success(client):
    created = client.post("/authors", json={"first_name": "To Delete", "last_name": "Author"}).json()
    response = client.delete(f"/authors/{created['id']}")
    assert response.status_code == 204

    # Verify author is no longer found
    assert client.get(f"/authors/{created['id']}").status_code == 404


def test_api_delete_author_with_books_enforces_policy(client):
    """
    Task 8 / FR-09: Delete an author with books -> verify defined policy is enforced.
    Defined Policy: Rejects deletion with 400 Bad Request to protect catalog integrity.
    """
    # 1. Create author
    author = client.post("/authors", json={"first_name": "J.K.", "last_name": "Rowling"}).json()

    # 2. Create book linked to author
    client.post(
        "/books",
        json={
            "title": "Harry Potter",
            "isbn": "9780747532699",
            "genre": "Fantasy",
            "publication_year": 1997,
            "author_ids": [author["id"]],
        },
    )

    # 3. Attempt to delete author
    response = client.delete(f"/authors/{author['id']}")
    assert response.status_code == 400
    assert "associated books" in response.json()["detail"].lower()


def test_api_delete_author_not_found(client):
    response = client.delete("/authors/99999")
    assert response.status_code == 404
