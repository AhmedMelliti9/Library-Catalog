-- Migration 002: Create books table
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
