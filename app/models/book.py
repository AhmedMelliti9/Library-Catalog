from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.author import AuthorResponse


class BookCreate(BaseModel):
    title: str
    isbn: str
    genre: str
    publication_year: Optional[int] = None
    author_ids: list[int]


class BookUpdate(BaseModel):
    title: Optional[str] = None
    isbn: Optional[str] = None
    genre: Optional[str] = None
    publication_year: Optional[int] = None


class BookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    isbn: str
    genre: str
    publication_year: Optional[int]
    available: bool
    created_at: datetime
    updated_at: datetime
    authors: list[AuthorResponse] = []
