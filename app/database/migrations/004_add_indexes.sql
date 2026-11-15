-- Migration 004: Add indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_books_genre ON books(genre);
CREATE INDEX IF NOT EXISTS idx_books_available ON books(available);
CREATE INDEX IF NOT EXISTS idx_book_authors_author_id ON book_authors(author_id);
