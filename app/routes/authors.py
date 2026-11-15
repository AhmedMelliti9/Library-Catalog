from fastapi import APIRouter, HTTPException, status, Query
from app.models.author import AuthorCreate, AuthorUpdate, AuthorResponse
from app.services import author_service
from app.exceptions import AuthorNotFoundError, AuthorHasBooksError

router = APIRouter(prefix="/authors", tags=["authors"])


@router.post("", response_model=AuthorResponse, status_code=status.HTTP_201_CREATED)
def create_author(data: AuthorCreate):
    return author_service.create_author(data)


@router.get("", response_model=list[AuthorResponse])
def get_all_authors(
    limit: int = Query(50, ge=1, le=100, description="Number of authors to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    return author_service.get_all_authors(limit=limit, offset=offset)


@router.get("/{author_id}", response_model=AuthorResponse)
def get_author(author_id: int):
    try:
        return author_service.get_author(author_id)
    except AuthorNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/{author_id}", response_model=AuthorResponse)
def update_author(author_id: int, data: AuthorUpdate):
    try:
        return author_service.update_author(author_id, data)
    except AuthorNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{author_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_author(author_id: int):
    try:
        author_service.delete_author(author_id)
    except AuthorNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AuthorHasBooksError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
