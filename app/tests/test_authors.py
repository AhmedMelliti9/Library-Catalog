"""
test_authors.py
Unit tests for AuthorRepository using the test database.
The clean_database fixture in conftest.py truncates all tables before each test.
"""

import os
import pytest
from dotenv import load_dotenv

load_dotenv()

# Point the app at the TEST database before importing anything that connects
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "")

from app.repositories.author_repository import AuthorRepository
from app.models.author import AuthorCreate, AuthorUpdate

repo = AuthorRepository()


# ---------------------------------------------------------------------------
# CREATE
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


# ---------------------------------------------------------------------------
# GET BY ID
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# GET ALL
# ---------------------------------------------------------------------------

def test_get_all_returns_empty_list_when_no_authors():
    authors = repo.get_all()
    assert authors == []


def test_get_all_returns_all_authors():
    repo.create(AuthorCreate(first_name="A", last_name="One"))
    repo.create(AuthorCreate(first_name="B", last_name="Two"))
    repo.create(AuthorCreate(first_name="C", last_name="Three"))

    authors = repo.get_all()
    assert len(authors) == 3


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------

def test_update_author_returns_updated_record():
    created = repo.create(AuthorCreate(first_name="Old", last_name="Name", nationality="French"))

    updated = repo.update(created["id"], AuthorUpdate(first_name="New", nationality="German"))

    assert updated is not None
    assert updated["first_name"] == "New"
    assert updated["last_name"] == "Name"       # unchanged
    assert updated["nationality"] == "German"


def test_update_author_returns_none_for_missing_author():
    result = repo.update(99999, AuthorUpdate(first_name="Ghost"))
    assert result is None


def test_update_with_no_fields_returns_existing_author():
    created = repo.create(AuthorCreate(first_name="Same", last_name="Person"))
    result = repo.update(created["id"], AuthorUpdate())

    assert result is not None
    assert result["first_name"] == "Same"


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------

def test_delete_author_returns_true_when_found():
    created = repo.create(AuthorCreate(first_name="Del", last_name="Author"))
    result = repo.delete(created["id"])

    assert result is True
    assert repo.get_by_id(created["id"]) is None


def test_delete_author_returns_false_when_not_found():
    result = repo.delete(99999)
    assert result is False
