# Project 05 — Library Catalog


---

## Problem Statement

A public library manages its catalog with an aging system that cannot handle concurrent updates and has no search capability. The librarians need a modern API-backed catalog that stores books and authors, supports filtering by author or genre, tracks whether a book is available or checked out, and persists data reliably.

You are building the backend API and the database layer. A simple frontend is optional (stretch goal) — focus on the data model and the API.

---

## Functional Requirements

```
FR-01: The catalog stores books. Each book has: title, ISBN, genre, publication year, available status.
FR-02: Each book belongs to one or more authors.
FR-03: Authors have: first name, last name, nationality.
FR-04: Clients can create, read, update, and delete books.
FR-05: Clients can create, read, update, and delete authors.
FR-06: Clients can list books filtered by author, genre, or availability.
FR-07: Clients can check out a book (mark unavailable) and return it (mark available).
FR-08: The API rejects a checkout if the book is already checked out.
FR-09: Deleting an author who has books must either fail with an error or be handled according to a defined policy.
FR-10: All data persists between server restarts.
```

---

## Non-Functional Requirements

```
NFR-01: The database layer is fully isolated behind a repository interface.
NFR-02: SQL queries are written directly — do not use an ORM.
NFR-03: All write operations that span multiple steps use a transaction.
NFR-04: The API returns consistent, structured error responses for database failures.
NFR-05: Sensitive database configuration is stored in environment variables.
```

---

## Technical Requirements

### You must use:

- Python 3.11+
- FastAPI
- PostgreSQL (run locally)
- `psycopg2` or `psycopg` (Python PostgreSQL driver) — no ORM
- `python-dotenv` for environment variable management
- pytest + httpx for API tests
- Git with feature branches

### You must NOT use:

- SQLAlchemy, Tortoise ORM, or any ORM
- Alembic or migration framework — write raw SQL migration files
- Docker (comes in Project 08)
- Authentication

### Why no ORM?

ORMs are valuable tools — but they hide SQL. You must understand what SQL actually executes when you write a query. Once you understand SQL, using an ORM becomes a deliberate choice rather than a crutch.

### Running PostgreSQL locally:

Install PostgreSQL on your system or use a local PostgreSQL service. Create a database named `library_catalog`.( i created them )


---

## SQL Fundamentals — Read Before You Build

Before writing any code, you must understand these concepts:

### Data Types

| Type | Use for |
|---|---|
| `INTEGER` or `BIGINT` | Numeric IDs, counts |
| `SERIAL` or `BIGSERIAL` | Auto-incrementing IDs |
| `TEXT` | Strings of arbitrary length |
| `VARCHAR(n)` | Strings with a maximum length |
| `BOOLEAN` | True/false |
| `DATE` | Date only |
| `TIMESTAMP` | Date and time |
| `NUMERIC(p, s)` | Exact decimal numbers |

### Constraints

| Constraint | Purpose |
|---|---|
| `PRIMARY KEY` | Uniquely identifies each row |
| `NOT NULL` | The column must have a value |
| `UNIQUE` | No two rows can have the same value |
| `FOREIGN KEY` | Enforces a relationship to another table |
| `CHECK` | Enforces a condition on a column value |

### Key SQL Statements

```sql
-- Create a table
CREATE TABLE books (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    ...
);

-- Insert a row
INSERT INTO books (title, ...) VALUES ('...', ...) RETURNING *;

-- Query rows
SELECT * FROM books WHERE genre = 'Fiction';

-- Update a row
UPDATE books SET available = false WHERE id = $1;

-- Delete a row
DELETE FROM books WHERE id = $1;

-- Join two tables
SELECT b.title, a.first_name, a.last_name
FROM books b
JOIN book_authors ba ON b.id = ba.book_id
JOIN authors a ON ba.author_id = a.id;
```

---

## Data Model

Design the following tables before you write any code. You may adjust column names, but the relationships must be correct.

```
books
  id (PK)
  title
  isbn (UNIQUE)
  genre
  publication_year
  available (BOOLEAN, default true)
  created_at
  updated_at

authors
  id (PK)
  first_name
  last_name
  nationality
  created_at

book_authors (join table — a book can have multiple authors)
  book_id (FK → books.id)
  author_id (FK → authors.id)
  PRIMARY KEY (book_id, author_id)
```

Think through:

- What should happen to `book_authors` rows when a book is deleted?
- What should happen to `book_authors` rows when an author is deleted?
- What constraints prevent a book from being inserted with an invalid ISBN?
- Why is `book_authors` a separate table instead of a column on `books`?

---

## Suggested Project Structure

```
05-postgresql/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
└── app/
    ├── main.py
    ├── database/
    │   ├── connection.py
    │   └── migrations/
    │       ├── 001_create_authors.sql
    │       ├── 002_create_books.sql
    │       └── 003_create_book_authors.sql
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

### Why the repository pattern?

The repository pattern puts all SQL in one place. The service layer calls repository methods — it never writes SQL. If you later swap PostgreSQL for another database, you only change the repository, not the service or routes.

---
git repository: 'https://github.com/AhmedMelliti9/Library-Catalog.git'
## Implementation Tasks

### Task 1 — Set Up PostgreSQL

- Install PostgreSQL and create the `library_catalog` database
- Write a `database/connection.py` module that:
  - Reads `DATABASE_URL` from environment variables
  - Provides a function to get a database connection
  - Raises a clear error if the database cannot be reached
- Create `.env` and `.env.example`
- Add `.env` to `.gitignore`

Verify: Your connection module can connect to the database.

Commit: `"chore: set up PostgreSQL connection"`

---

### Task 2 — Write Migration Files

Write SQL migration files as plain `.sql` files in `database/migrations/`.

Number them (001, 002, 003) so they run in order.

Write a simple Python script `run_migrations.py` that reads and executes all migration files in order.

The migration files should create the three tables with correct types, constraints, and foreign keys.

Think: What happens if you run the migrations twice? How do you prevent duplicate table creation?

Commit: `"feat: add database migration files and runner"`

---

### Task 3 — Build the Author Repository

In `repositories/author_repository.py`, implement:

- `create(data)` → inserts an author, returns the created author
- `get_by_id(id)` → returns an author or None
- `get_all()` → returns all authors
- `update(id, data)` → updates an author, returns updated author or None
- `delete(id)` → deletes an author, returns True or False

Every method should use parameterized queries. Never concatenate user input into SQL strings.

Write unit tests for the repository using a test database (a separate database or a transaction that rolls back).

Commit: `"feat: implement author repository"`

---

### Task 4 — Build the Book Repository

In `repositories/book_repository.py`, implement:

- `create(data, author_ids)` → inserts a book and its author relationships in a transaction
- `get_by_id(id)` → returns a book with its authors
- `get_all(filters)` → returns books, supports filtering by author_id, genre, available
- `update(id, data)` → updates a book
- `checkout(id)` → marks available=false, fails if already unavailable
- `return_book(id)` → marks available=true
- `delete(id)` → deletes a book

The `checkout` operation must use a transaction: check availability, then update. These two steps must be atomic.

Commit: `"feat: implement book repository with transaction for checkout"`

---

### Task 5 — Build Service and Route Layers

Following the same pattern as Project 03, build:

- `services/book_service.py` and `services/author_service.py` — call repositories, raise domain exceptions
- `routes/books.py` and `routes/authors.py` — FastAPI routes that call services

Commit: `"feat: implement service and route layers"`

---

### Task 6 — Handle Database Errors

Identify what database errors can occur and handle them:

| Database Error | API Response |
|---|---|
| Unique constraint violation (duplicate ISBN) | 409 Conflict |
| Foreign key violation (invalid author_id) | 400 Bad Request |
| Record not found | 404 Not Found |
| Book already checked out | 409 Conflict |
| Database unavailable | 503 Service Unavailable |

Never expose database error messages directly to the client.

Commit: `"feat: add database error handling"`

---

### Task 7 — Add Indexes

Add indexes to improve query performance:

- Index on `books.genre`
- Index on `books.available`
- Index on `book_authors.author_id`

Write these as a new migration file.

Then answer: Why do these specific columns benefit from an index? What is the trade-off of adding indexes?

Commit: `"feat: add database indexes"`

---

### Task 8 — Write API Tests

Write integration tests that:
- Use a test database (separate from development)
- Reset the database state before each test (truncate tables or use transactions)
- Test every endpoint including error cases

Required:
- Create a book with valid author → 201
- Create a book with non-existent author → 400
- Create a book with duplicate ISBN → 409
- Check out an available book → 200
- Check out an already checked-out book → 409
- Delete an author with books → verify your defined policy is enforced
- Filter books by genre → returns only matching books

Commit: `"test: add integration tests with test database"`

---

### Task 9 — Environment Variables

Store all configuration in environment variables:

```
DATABASE_URL=postgresql://user:postgresahmed@localhost:5432/library_catalog
TEST_DATABASE_URL=postgresql://user:postgresahmed@localhost:5432/library_catalog_test
```

Use `python-dotenv` to load them from `.env`.

The `.env` file must NEVER be committed to Git.

Commit: `"feat: externalize all configuration to environment variables"`

---

## Error Handling Requirements

| Scenario | HTTP Status | Explanation |
|---|---|---|
| Book not found | 404 | Expected business error |
| Author not found | 404 | Expected business error |
| Duplicate ISBN | 409 | Unique constraint violation |
| Book already checked out | 409 | Business rule violation |
| Invalid author_id in request | 400 | Bad client input |
| Database unavailable | 503 | Infrastructure failure |
| Unhandled exception | 500 | Programming or infrastructure error |

### Key concept this week: Transaction atomicity

The checkout operation must be atomic:

```
BEGIN
  SELECT available FROM books WHERE id = ? FOR UPDATE
  IF NOT available: RAISE error
  UPDATE books SET available = false WHERE id = ?
COMMIT
```

If the SELECT and UPDATE are not in a transaction, two simultaneous checkouts could both see `available = true` and both succeed, leaving the book double-checked-out. This is a **race condition**.

You will not test this race condition this week, but you must understand why the transaction is necessary.

---

## Testing Requirements

### Integration tests (pytest + test database)

- All CRUD operations for books and authors
- All filter scenarios
- Checkout and return lifecycle
- All error cases (not found, duplicate, conflict)

### How to set up a test database

Create a separate database: `library_catalog_test`

In `conftest.py`, connect to the test database and truncate all tables before each test.

Run: `pytest`

---

## Git Requirements

Continue feature branches.

New rule this week:

**Migration files are never modified after they are committed.** If you need to change the schema, write a new migration. This is how database migrations work in production — you cannot rewrite history.

---

## Security Requirements

**SQL Injection**

Never concatenate user input into SQL strings:

```python
# WRONG — SQL injection vulnerability
query = f"SELECT * FROM books WHERE genre = '{genre}'"

# CORRECT — parameterized query
query = "SELECT * FROM books WHERE genre = %s"
cursor.execute(query, (genre,))
```

This is one of the most critical security concepts in backend engineering. Understand it deeply.

**Environment Variables**

The database password must never appear in code or in Git.

---

---

## Stretch Goals

```


Do NOT implement:
- Authentication
- Docker
- ORMs
```

---

## Definition of Done

```
[ ] All functional requirements (FR-01 through FR-10) are met
[ ] Database tables created via migration files
[ ] All SQL uses parameterized queries (no string concatenation with user input)
[ ] Checkout operation uses a transaction
[ ] Author deletion policy is defined and enforced
[ ] All database error types return appropriate HTTP status codes
[ ] Database configuration is stored in environment variables
[ ] .env is in .gitignore and never committed
[ ] Integration tests pass against a test database
[ ] README.md explains setup, migration steps, and available endpoints
[ ] Debugging exercise completed and answers written
```

---

