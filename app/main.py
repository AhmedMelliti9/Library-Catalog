from fastapi import FastAPI
from app.routes.authors import router as authors_router
from app.routes.books import router as books_router

app = FastAPI(
    title="Library Catalog API",
    description="API for managing books and authors in a library catalog",
    version="1.0.0",
)

app.include_router(authors_router)
app.include_router(books_router)


@app.get("/")
def root():
    return {"message": "Welcome to Library Catalog API"}
