-- Migration 001: Create authors table
CREATE TABLE IF NOT EXISTS authors (
    id SERIAL PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    nationality TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
