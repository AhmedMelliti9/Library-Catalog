from pathlib import Path
import logging
import psycopg2
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.routes.authors import router as authors_router
from app.routes.books import router as books_router
from app.exceptions import (
    BookNotFoundError,
    AuthorNotFoundError,
    BookAlreadyCheckedOutError,
    BookNotCheckedOutError,
    DuplicateISBNError,
    InvalidAuthorError,
    AuthorHasBooksError,
    DatabaseUnavailableError,
)

logger = logging.getLogger("library_catalog")

app = FastAPI(
    title="Library Catalog API",
    description="API for managing books and authors in a library catalog",
    version="1.0.0",
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(authors_router)
app.include_router(books_router)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/app", include_in_schema=False)
def serve_frontend():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Frontend not yet built."}


# ---------------------------------------------------------------------------
# Global Exception Handlers — Structured Error Responses
# ---------------------------------------------------------------------------

@app.exception_handler(AuthorNotFoundError)
async def author_not_found_handler(request: Request, exc: AuthorNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


@app.exception_handler(BookNotFoundError)
async def book_not_found_handler(request: Request, exc: BookNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


@app.exception_handler(DuplicateISBNError)
async def duplicate_isbn_handler(request: Request, exc: DuplicateISBNError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.exception_handler(BookAlreadyCheckedOutError)
async def book_already_checked_out_handler(request: Request, exc: BookAlreadyCheckedOutError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.exception_handler(InvalidAuthorError)
async def invalid_author_handler(request: Request, exc: InvalidAuthorError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


@app.exception_handler(AuthorHasBooksError)
async def author_has_books_handler(request: Request, exc: AuthorHasBooksError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


@app.exception_handler(ConnectionError)
async def db_connection_error_handler(request: Request, exc: ConnectionError):
    logger.error(f"Database connection error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Database is unavailable. Please try again later."},
    )


@app.exception_handler(DatabaseUnavailableError)
async def db_unavailable_handler(request: Request, exc: DatabaseUnavailableError):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Database is unavailable. Please try again later."},
    )


@app.exception_handler(psycopg2.OperationalError)
async def operational_error_handler(request: Request, exc: psycopg2.OperationalError):
    logger.error(f"Database operational error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Database is unavailable. Please try again later."},
    )


@app.exception_handler(psycopg2.Error)
async def database_error_handler(request: Request, exc: psycopg2.Error):
    logger.error(f"Database error occurred: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "A database error occurred."},
    )


@app.get("/")
def root():
    return {
        "message": "Welcome to Library Catalog API",
        "docs": "/docs",
        "frontend": "/app",
    }
