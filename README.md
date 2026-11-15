# Library Catalog API (Project 05)

A robust RESTful API and relational database layer for managing a public library's catalog of books and authors. Built with **FastAPI**, **PostgreSQL**, and raw parameterized SQL queries using **psycopg2** without an ORM.

---

## Technical Stack

- **Language:** Python 3.11+
- **Framework:** FastAPI
- **Database:** PostgreSQL (local)
- **Database Driver:** `psycopg2` / `psycopg2-binary` (raw SQL queries, **no ORM**)
- **Environment Management:** `python-dotenv`
- **Testing:** `pytest`, `httpx`

---

## Database Migrations & Indexes

Migrations are executed sequentially as raw SQL scripts located in `app/database/migrations/`:

1. `001_create_authors.sql` — Creates `authors` table
2. `002_create_books.sql` — Creates `books` table
3. `003_create_book_authors.sql` — Creates `book_authors` junction table (many-to-many)
4. `004_add_indexes.sql` — Creates performance indexes:
   - `idx_books_genre` on `books(genre)`
   - `idx_books_available` on `books(available)`
   - `idx_book_authors_author_id` on `book_authors(author_id)`

### Database Index Analysis

#### 1. Why do these specific columns benefit from an index?
- **`books.genre`**: The API provides filtering by genre (`GET /books?genre=Fiction`). Without an index, PostgreSQL must perform a full sequential scan across all book records. A B-tree index allows logarithmic lookups ($O(\log N)$).
- **`books.available`**: Availability is queried frequently when patrons search for borrowable books (`GET /books?available=true`) and during checkouts.
- **`book_authors.author_id`**: The junction table has a composite primary key `(book_id, author_id)`. PostgreSQL automatically indexes composite primary keys starting with the leading column (`book_id`). Queries that join from authors or search by author (`WHERE author_id = %s`) cannot utilize the leading `book_id` index. An explicit index on `author_id` ensures efficient joins.

#### 2. What is the trade-off of adding indexes?
- **Write Performance Overhead:** Every `INSERT`, `UPDATE`, or `DELETE` operation on indexed tables must update the index structures in addition to the base table rows.
- **Storage and Memory Consumption:** Indexes occupy disk space and consume database buffer pool memory (RAM), reducing cache space available for other operations if overused.

---

## Environment Variables & Security Configuration

All database connection strings and sensitive credentials are fully externalized to environment variables and loaded via `python-dotenv`.

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection URL for development / runtime | `postgresql://user:password@localhost:5432/library_catalog` |
| `TEST_DATABASE_URL` | Separate PostgreSQL connection URL for automated integration tests | `postgresql://user:password@localhost:5432/library_catalog_test` |

### Security Guarantees:
- `.env` is listed in `.gitignore` and is **never committed** to source control.
- `.env.example` provides a sanitized template with placeholder values.
- Direct parameterized SQL queries (`%s`) are enforced throughout the repository layer to prevent SQL injection vulnerabilities.
- Password and host information are never hardcoded in application logic or tests.

---

## Setup & Running

### 1. Environment Configuration
Copy `.env.example` to `.env` and fill in your PostgreSQL credentials:
```bash
DATABASE_URL=postgresql://<username>:<password>@localhost:5432/library_catalog
TEST_DATABASE_URL=postgresql://<username>:<password>@localhost:5432/library_catalog_test
```

### 2. Run Database Migrations
```bash
python run_migrations.py
```

### 3. Run the Development Server
```bash
uvicorn app.main:app --reload
```
Interactive API docs will be available at: `http://127.0.0.1:8000/docs`  
Interactive React Web UI will be available at: `http://127.0.0.1:8000/app`

---

## React Frontend

A responsive Single-Page Application (SPA) built with React 18 and Tailwind CSS is located in `frontend/index.html`. It is served directly by FastAPI at `/app` or can be opened standalone in any browser:
- **Catalog Browsing:** Card grid showing book details, publication year, genres, authors, and real-time availability badges.
- **Full-Text Search:** Instant keyword search across book titles and author names via `/books/search?q=...`.
- **Filtering & Pagination:** Filter by genre or availability, with Previous/Next pagination controls.
- **Direct Actions:** One-click book checkout and return with atomic status updates.
- **Modals:** Forms to add new books and authors with multi-author selection.

---

## API Endpoints

### Authors
- `POST /authors` — Create an author (201 Created)
- `GET /authors?limit=50&offset=0` — List all authors with pagination (200 OK)
- `GET /authors/{id}` — Get author details (200 OK / 404 Not Found)
- `PUT /authors/{id}` — Update author details (200 OK / 404 Not Found)
- `DELETE /authors/{id}` — Delete an author (204 No Content / 400 Bad Request if author has books / 404 Not Found)

### Books
- `POST /books` — Create a book with author associations (201 Created / 400 Bad Request / 409 Conflict)
- `GET /books?author_id=...&genre=...&available=...&limit=50&offset=0` — List books with filtering and pagination (200 OK)
- `GET /books/search?q=keyword&limit=50&offset=0` — Search books by keyword in title and author names (200 OK)
- `GET /books/{id}` — Get book details with its authors (200 OK / 404 Not Found)
- `PUT /books/{id}` — Update book details (200 OK / 404 Not Found / 409 Conflict)
- `DELETE /books/{id}` — Delete a book (204 No Content / 404 Not Found)
- `POST /books/{id}/checkout` — Check out a book with row-level transaction lock (200 OK / 409 Conflict / 404 Not Found)
- `POST /books/{id}/return` — Return a checked-out book (200 OK / 404 Not Found)
- `DELETE /books/{id}` — Delete a book (204 No Content / 404 Not Found)
- `POST /books/{id}/checkout` — Check out a book with row-level transaction lock (200 OK / 409 Conflict / 404 Not Found)
- `POST /books/{id}/return` — Return a checked-out book (200 OK / 404 Not Found)
