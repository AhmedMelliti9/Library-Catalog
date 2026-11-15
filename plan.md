# Plan — Library Catalog (Project 05)

---

## Overview

Build a backend API and database layer for a public library catalog system. The system stores books and authors, supports filtering by author or genre, tracks book availability (checked out / available), and persists data reliably using PostgreSQL with raw SQL (no ORM).

---

## Tech Stack (Mandatory)

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Framework | FastAPI |
| Database | PostgreSQL (local) |
| DB Driver | `psycopg2` or `psycopg` — **no ORM** |
| Env Config | `python-dotenv` |
| Testing | `pytest` + `httpx` |
| Version Control | Git with feature branches |

### Forbidden

- SQLAlchemy, Tortoise ORM, or any ORM
- Alembic or any migration framework — raw SQL migration files only
- Docker
- Authentication

---

## Data Model

### Table: `books`

| Column | Type | Constraints |
|---|---|---|
| `id` | `SERIAL` | `PRIMARY KEY` |
| `title` | `TEXT` | `NOT NULL` |
| `isbn` | `VARCHAR(13)` | `UNIQUE`, `NOT NULL` |
| `genre` | `TEXT` | `NOT NULL` |
| `publication_year` | `INTEGER` | |
| `available` | `BOOLEAN` | `DEFAULT true`, `NOT NULL` |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` |
| `updated_at` | `TIMESTAMP` | `DEFAULT NOW()` |

### Table: `authors`

| Column | Type | Constraints |
|---|---|---|
| `id` | `SERIAL` | `PRIMARY KEY` |
| `first_name` | `TEXT` | `NOT NULL` |
| `last_name` | `TEXT` | `NOT NULL` |
| `nationality` | `TEXT` | |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` |

### Table: `book_authors` (join table — many-to-many)

| Column | Type | Constraints |
|---|---|---|
| `book_id` | `INTEGER` | `FK → books.id`, `ON DELETE CASCADE` |
| `author_id` | `INTEGER` | `FK → authors.id`, `ON DELETE CASCADE` |
| | | `PRIMARY KEY (book_id, author_id)` |

### Design Decisions

- **When a book is deleted:** `book_authors` rows are automatically deleted via `ON DELETE CASCADE`.
- **When an author is deleted:** `book_authors` rows are automatically deleted via `ON DELETE CASCADE`. The defined policy is: deleting an author removes the author–book links but does **not** delete the books themselves. If an author is the **only** author of a book, the book remains but with no linked author. *(Alternative policy: reject deletion of an author who still has books — either approach is acceptable as long as it is defined and enforced.)*
- **ISBN uniqueness:** The `UNIQUE` constraint on `isbn` prevents duplicate ISBNs at the database level.
- **Why `book_authors` is a separate table:** Because a book can have multiple authors and an author can have multiple books — this is a many-to-many relationship that requires a join table.

---

## Project Structure

```
library_catalog/
├── README.md
├── requirements.txt
├── .env.example
├── .env                          ← never committed
├── .gitignore
├── run_migrations.py
└── app/
    ├── main.py
    ├── database/
    │   ├── connection.py
    │   └── migrations/
    │       ├── 001_create_authors.sql
    │       ├── 002_create_books.sql
    │       ├── 003_create_book_authors.sql
    │       └── 004_add_indexes.sql
    ├── models/
    │   ├── book.py
    │   └── author.py
    ├── repositories/
    │   ├── book_repository.py
    │   └── author_repository.py
    ├── services/
    │   ├── book_service.py
    │   └── author_service.py
    ├── routes/
    │   ├── books.py
    │   └── authors.py
    └── tests/
        ├── conftest.py
        ├── test_books.py
        └── test_authors.py
```

### Architecture Pattern: Repository Pattern

- **Routes** → call **Services** → call **Repositories** → execute **raw SQL**
- All SQL is isolated inside repository files. Services never write SQL.
- If the database engine changes later, only the repositories need to change.

---

## Environment Variables

```
DATABASE_URL=postgresql://user:postgresahmed@localhost:5432/library_catalog
TEST_DATABASE_URL=postgresql://user:postgresahmed@localhost:5432/library_catalog_test
```

- Loaded via `python-dotenv` from `.env`.
- `.env` is in `.gitignore` — **never committed**.
- `.env.example` is committed with placeholder values.

---

## Error Handling Policy

| Scenario | HTTP Status | Response Detail |
|---|---|---|
| Book not found | `404 Not Found` | Expected business error |
| Author not found | `404 Not Found` | Expected business error |
| Duplicate ISBN | `409 Conflict` | Unique constraint violation |
| Book already checked out | `409 Conflict` | Business rule violation |
| Invalid `author_id` in request | `400 Bad Request` | Foreign key violation / bad client input |
| Database unavailable | `503 Service Unavailable` | Infrastructure failure |
| Unhandled exception | `500 Internal Server Error` | Programming or infrastructure error |

- **Never** expose raw database error messages to the client.
- All error responses are structured JSON: `{ "detail": "<human-readable message>" }`.

---

## Security Rules

1. **SQL Injection Prevention:** Every query uses parameterized queries (`%s` placeholders). Never concatenate user input into SQL strings.
   ```python
   # WRONG
   query = f"SELECT * FROM books WHERE genre = '{genre}'"

   # CORRECT
   query = "SELECT * FROM books WHERE genre = %s"
   cursor.execute(query, (genre,))
   ```

2. **Environment Variables:** The database password must never appear in source code or in Git.

---

## Transaction Atomicity — Checkout Operation

The checkout must be atomic to prevent race conditions:

```
BEGIN
  SELECT available FROM books WHERE id = ? FOR UPDATE
  IF NOT available: RAISE error (409 Conflict)
  UPDATE books SET available = false WHERE id = ?
COMMIT
```

- `FOR UPDATE` locks the row, preventing concurrent checkouts from both seeing `available = true`.
- If `SELECT` and `UPDATE` are not in a transaction, two simultaneous checkouts could both succeed — a **race condition**.

---

## Git Rules

- Use **feature branches** for each task.
- Commit messages follow the specified format exactly.
- **Migration files are never modified after they are committed.** Schema changes require a new migration file.

---

## Implementation Tasks — Step-by-Step

---

### Task 1 — Set Up PostgreSQL Connection

**Branch:** `feature/postgresql-setup`

**What to do:**

1. PostgreSQL is already installed and the `library_catalog` database is already created.
2. Create `app/database/connection.py`:
   - Read `DATABASE_URL` from environment variables using `python-dotenv`.
   - Provide a function `get_connection()` that returns a `psycopg2` database connection.
   - Raise a clear, descriptive error if the database cannot be reached.
3. Create `.env` file with the actual `DATABASE_URL`.
4. Create `.env.example` file with a placeholder `DATABASE_URL`.
5. Add `.env` to `.gitignore`.
6. Create `requirements.txt` with all dependencies:
   ```
   fastapi
   uvicorn
   psycopg2-binary
   python-dotenv
   pytest
   httpx
   ```

**Verification:** Run the connection module standalone — it should connect to the database without error.

**Commit:** `"chore: set up PostgreSQL connection"`

---

### Task 2 — Write Migration Files

**Branch:** `feature/migrations`

**What to do:**

1. Create `app/database/migrations/001_create_authors.sql`:
   ```sql
   CREATE TABLE IF NOT EXISTS authors (
       id SERIAL PRIMARY KEY,
       first_name TEXT NOT NULL,
       last_name TEXT NOT NULL,
       nationality TEXT,
       created_at TIMESTAMP DEFAULT NOW()
   );
   ```

2. Create `app/database/migrations/002_create_books.sql`:
   ```sql
   CREATE TABLE IF NOT EXISTS books (
       id SERIAL PRIMARY KEY,
       title TEXT NOT NULL,
       isbn VARCHAR(13) UNIQUE NOT NULL,
       genre TEXT NOT NULL,
       publication_year INTEGER,
       available BOOLEAN DEFAULT true NOT NULL,
       created_at TIMESTAMP DEFAULT NOW(),
       updated_at TIMESTAMP DEFAULT NOW()
   );
   ```

3. Create `app/database/migrations/003_create_book_authors.sql`:
   ```sql
   CREATE TABLE IF NOT EXISTS book_authors (
       book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,
       author_id INTEGER REFERENCES authors(id) ON DELETE CASCADE,
       PRIMARY KEY (book_id, author_id)
   );
   ```

4. Create `run_migrations.py` at the project root:
   - Read all `.sql` files from `app/database/migrations/` in sorted order.
   - Execute each file against the database.
   - Use `CREATE TABLE IF NOT EXISTS` to prevent errors on re-run.
   - Print which migration files were executed.

**Verification:** Run `python run_migrations.py` — tables are created. Run it again — no errors (idempotent).

**Commit:** `"feat: add database migration files and runner"`

---

### Task 3 — Build the Author Repository

**Branch:** `feature/author-repository`

**What to do:**

1. Create `app/models/author.py`:
   - Define Pydantic models: `AuthorCreate`, `AuthorUpdate`, `AuthorResponse`.

2. Create `app/repositories/author_repository.py` with these methods:
   - `create(data)` → `INSERT INTO authors ... RETURNING *` — returns the created author.
   - `get_by_id(id)` → `SELECT * FROM authors WHERE id = %s` — returns an author or `None`.
   - `get_all()` → `SELECT * FROM authors` — returns all authors.
   - `update(id, data)` → `UPDATE authors SET ... WHERE id = %s RETURNING *` — returns updated author or `None`.
   - `delete(id)` → `DELETE FROM authors WHERE id = %s` — returns `True` if deleted, `False` if not found.

3. **All queries must be parameterized** — no string concatenation.

4. Write unit tests in `app/tests/test_authors.py`:
   - Test create, read, update, delete operations.
   - Use the test database (`TEST_DATABASE_URL`).
   - Roll back or truncate tables between tests.

**Verification:** `pytest app/tests/test_authors.py` — all tests pass.

**Commit:** `"feat: implement author repository"`

---

### Task 4 — Build the Book Repository

**Branch:** `feature/book-repository`

**What to do:**

1. Create `app/models/book.py`:
   - Define Pydantic models: `BookCreate` (includes `author_ids: list[int]`), `BookUpdate`, `BookResponse` (includes list of authors).

2. Create `app/repositories/book_repository.py` with these methods:
   - `create(data, author_ids)`:
     - Use a **transaction**: `INSERT INTO books ... RETURNING *`, then `INSERT INTO book_authors` for each author_id.
     - If any author_id is invalid, the transaction rolls back.
   - `get_by_id(id)`:
     - `SELECT` book joined with its authors via `book_authors`.
     - Returns book with authors list, or `None`.
   - `get_all(filters)`:
     - Supports optional filters: `author_id`, `genre`, `available`.
     - Build the query dynamically with parameterized conditions.
   - `update(id, data)`:
     - `UPDATE books SET ... WHERE id = %s RETURNING *`.
     - Update `updated_at` timestamp.
   - `checkout(id)`:
     - **Transaction with row lock:**
       ```sql
       BEGIN
         SELECT available FROM books WHERE id = %s FOR UPDATE
         -- If not available: raise error
         UPDATE books SET available = false, updated_at = NOW() WHERE id = %s
       COMMIT
       ```
     - Fails with error if book is already checked out.
   - `return_book(id)`:
     - `UPDATE books SET available = true, updated_at = NOW() WHERE id = %s`.
   - `delete(id)`:
     - `DELETE FROM books WHERE id = %s` — `book_authors` rows cascade.

3. **All queries must be parameterized.**

4. Write unit tests in `app/tests/test_books.py`:
   - Test create with valid authors, create with invalid authors.
   - Test checkout of available book, checkout of already-checked-out book.
   - Test return, delete, filtering.

**Verification:** `pytest app/tests/test_books.py` — all tests pass.

**Commit:** `"feat: implement book repository with transaction for checkout"`

---

### Task 5 — Build Service and Route Layers

**Branch:** `feature/service-routes`

**What to do:**

1. Create `app/services/author_service.py`:
   - Methods: `create_author`, `get_author`, `get_all_authors`, `update_author`, `delete_author`.
   - Call the author repository methods.
   - Raise domain exceptions (e.g., `AuthorNotFoundError`) when appropriate.

2. Create `app/services/book_service.py`:
   - Methods: `create_book`, `get_book`, `get_all_books`, `update_book`, `delete_book`, `checkout_book`, `return_book`.
   - Call the book repository methods.
   - Raise domain exceptions (e.g., `BookNotFoundError`, `BookAlreadyCheckedOutError`).

3. Create `app/routes/authors.py` — FastAPI router:
   - `POST /authors` → create author → `201 Created`
   - `GET /authors` → list all authors → `200 OK`
   - `GET /authors/{id}` → get author by ID → `200 OK` / `404 Not Found`
   - `PUT /authors/{id}` → update author → `200 OK` / `404 Not Found`
   - `DELETE /authors/{id}` → delete author → `204 No Content` / `404 Not Found`

4. Create `app/routes/books.py` — FastAPI router:
   - `POST /books` → create book → `201 Created`
   - `GET /books` → list books (query params: `author_id`, `genre`, `available`) → `200 OK`
   - `GET /books/{id}` → get book by ID → `200 OK` / `404 Not Found`
   - `PUT /books/{id}` → update book → `200 OK` / `404 Not Found`
   - `DELETE /books/{id}` → delete book → `204 No Content` / `404 Not Found`
   - `POST /books/{id}/checkout` → checkout book → `200 OK` / `409 Conflict`
   - `POST /books/{id}/return` → return book → `200 OK`

5. Create `app/main.py`:
   - Initialize FastAPI app.
   - Include both routers.

**Verification:** Start the server with `uvicorn app.main:app --reload` and test endpoints manually or via Swagger UI at `/docs`.

**Commit:** `"feat: implement service and route layers"`

---

### Task 6 — Handle Database Errors

**Branch:** `feature/error-handling`

**What to do:**

1. Create structured error handling that catches database exceptions and returns proper HTTP responses:

   | Database Error | HTTP Response |
   |---|---|
   | Unique constraint violation (duplicate ISBN) | `409 Conflict` |
   | Foreign key violation (invalid author_id) | `400 Bad Request` |
   | Record not found | `404 Not Found` |
   | Book already checked out | `409 Conflict` |
   | Database unavailable / connection error | `503 Service Unavailable` |

2. Implement FastAPI exception handlers in `app/main.py` or use middleware.

3. **Never expose raw database error messages to the client.** All responses return a clean JSON body:
   ```json
   { "detail": "A book with this ISBN already exists" }
   ```

**Verification:** Trigger each error case via API calls and verify the correct HTTP status and message.

**Commit:** `"feat: add database error handling"`

---

### Task 7 — Add Indexes

**Branch:** `feature/indexes`

**What to do:**

1. Create `app/database/migrations/004_add_indexes.sql`:
   ```sql
   CREATE INDEX IF NOT EXISTS idx_books_genre ON books(genre);
   CREATE INDEX IF NOT EXISTS idx_books_available ON books(available);
   CREATE INDEX IF NOT EXISTS idx_book_authors_author_id ON book_authors(author_id);
   ```

2. Run `python run_migrations.py` to apply.

3. **Why these indexes:**
   - `books.genre` — frequently used in `WHERE` filters for book searches.
   - `books.available` — frequently used in `WHERE` filters for availability checks.
   - `book_authors.author_id` — frequently used in `JOIN` operations to find books by author.

4. **Trade-off of indexes:** Indexes speed up reads (`SELECT`) but slow down writes (`INSERT`, `UPDATE`, `DELETE`) because the index must be updated on every write. They also consume additional disk space.

**Verification:** Run migrations — indexes are created. Query plan (`EXPLAIN`) shows index usage.

**Commit:** `"feat: add database indexes"`

---

### Task 8 — Write API Integration Tests

**Branch:** `feature/integration-tests`

**What to do:**

1. Create the `library_catalog_test` database in PostgreSQL.

2. Set up `app/tests/conftest.py`:
   - Connect to the test database using `TEST_DATABASE_URL`.
   - Run migrations against the test database.
   - Truncate all tables (`book_authors`, `books`, `authors`) before each test.
   - Provide an `httpx.AsyncClient` fixture pointing to the FastAPI test app.

3. Write the following required test cases in `app/tests/test_books.py` and `app/tests/test_authors.py`:

   | Test Case | Expected Result |
   |---|---|
   | Create a book with valid author(s) | `201 Created` |
   | Create a book with non-existent author | `400 Bad Request` |
   | Create a book with duplicate ISBN | `409 Conflict` |
   | Check out an available book | `200 OK` |
   | Check out an already checked-out book | `409 Conflict` |
   | Delete an author who has books | Verify the defined deletion policy is enforced |
   | Filter books by genre | Returns only matching books |
   | Get a non-existent book | `404 Not Found` |
   | Get a non-existent author | `404 Not Found` |
   | Full CRUD lifecycle for books | Create → Read → Update → Delete |
   | Full CRUD lifecycle for authors | Create → Read → Update → Delete |
   | Checkout and return lifecycle | Checkout → verify unavailable → Return → verify available |

**Verification:** `pytest` — all tests pass.

**Commit:** `"test: add integration tests with test database"`

---

### Task 9 — Environment Variables & Final Configuration

**Branch:** `feature/env-config`

**What to do:**

1. Verify all configuration is loaded from environment variables:
   ```
   DATABASE_URL=postgresql://user:postgresahmed@localhost:5432/library_catalog
   TEST_DATABASE_URL=postgresql://user:postgresahmed@localhost:5432/library_catalog_test
   ```

2. Verify `python-dotenv` is used to load `.env` in every entry point (`main.py`, `run_migrations.py`, `conftest.py`).

3. Verify `.env` is in `.gitignore` and has **never** been committed.

4. Verify `.env.example` is committed with placeholder values:
   ```
   DATABASE_URL=postgresql://user:password@localhost:5432/library_catalog
   TEST_DATABASE_URL=postgresql://user:password@localhost:5432/library_catalog_test
   ```

**Commit:** `"feat: externalize all configuration to environment variables"`

---

## Git Repository

**Remote:** `https://github.com/AhmedMelliti9/Library-Catalog.git`

### Branch Strategy

| Task | Branch Name | Commit Message |
|---|---|---|
| Task 1 | `feature/postgresql-setup` | `"chore: set up PostgreSQL connection"` |
| Task 2 | `feature/migrations` | `"feat: add database migration files and runner"` |
| Task 3 | `feature/author-repository` | `"feat: implement author repository"` |
| Task 4 | `feature/book-repository` | `"feat: implement book repository with transaction for checkout"` |
| Task 5 | `feature/service-routes` | `"feat: implement service and route layers"` |
| Task 6 | `feature/error-handling` | `"feat: add database error handling"` |
| Task 7 | `feature/indexes` | `"feat: add database indexes"` |
| Task 8 | `feature/integration-tests` | `"test: add integration tests with test database"` |
| Task 9 | `feature/env-config` | `"feat: externalize all configuration to environment variables"` |

### Git Rules

- Each task gets its own feature branch.
- Merge into `main` after task is verified.
- **Migration files are never modified after commit.** New schema changes → new migration file.

---

## Testing Requirements Summary

- **Framework:** `pytest` + `httpx`
- **Database:** Separate `library_catalog_test` database
- **Isolation:** Truncate all tables before each test
- **Coverage:**
  - All CRUD operations for books and authors
  - All filter scenarios (by genre, author, availability)
  - Checkout and return lifecycle
  - All error cases (not found, duplicate, conflict)

---

## Definition of Done

- [ ] All functional requirements (FR-01 through FR-10) are met
- [ ] Database tables created via migration files
- [ ] All SQL uses parameterized queries (no string concatenation with user input)
- [ ] Checkout operation uses a transaction
- [ ] Author deletion policy is defined and enforced
- [ ] All database error types return appropriate HTTP status codes
- [ ] Database configuration is stored in environment variables
- [ ] `.env` is in `.gitignore` and never committed
- [ ] Integration tests pass against a test database
- [ ] `README.md` explains setup, migration steps, and available endpoints
- [ ] Debugging exercise completed and answers written

---

## Stretch Goals

> [!CAUTION]
> Do **NOT** implement:
> - Authentication
> - Docker
> - ORMs

---

