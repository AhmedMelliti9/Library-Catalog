-- Migration 003: Create book_authors join table (many-to-many)
-- book_authors rows are deleted automatically when a book or author is deleted (ON DELETE CASCADE)
CREATE TABLE IF NOT EXISTS book_authors (
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    author_id INTEGER NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    PRIMARY KEY (book_id, author_id)
);
