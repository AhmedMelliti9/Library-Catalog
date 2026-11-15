from typing import Optional
from fastapi import APIRouter, HTTPException, status, Query
from app.models.book import BookCreate, BookUpdate, BookResponse
from app.services import book_service
from app.exceptions import (
    BookNotFoundError,
    BookAlreadyCheckedOutError,
    DuplicateISBNError,
    InvalidAuthorError,
)

router = APIRouter(prefix="/books", tags=["books"])


@router.post("", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
def create_book(data: BookCreate):
    try:
        return book_service.create_book(data)
    except DuplicateISBNError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except InvalidAuthorError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=list[BookResponse])
def get_all_books(
    author_id: Optional[int] = Query(None, description="Filter by author ID"),
    genre: Optional[str] = Query(None, description="Filter by genre"),
    available: Optional[bool] = Query(None, description="Filter by availability"),
):
    return book_service.get_all_books(author_id=author_id, genre=genre, available=available)


@router.get("/{book_id}", response_model=BookResponse)
def get_book(book_id: int):
    try:
        return book_service.get_book(book_id)
    except BookNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/{book_id}", response_model=BookResponse)
def update_book(book_id: int, data: BookUpdate):
    try:
        return book_service.update_book(book_id, data)
    except BookNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DuplicateISBNError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int):
    try:
        book_service.delete_book(book_id)
    except BookNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{book_id}/checkout", response_model=BookResponse)
def checkout_book(book_id: int):
    try:
        return book_service.checkout_book(book_id)
    except BookNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BookAlreadyCheckedOutError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/{book_id}/return", response_model=BookResponse)
def return_book(book_id: int):
    try:
        return book_service.return_book(book_id)
    except BookNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
