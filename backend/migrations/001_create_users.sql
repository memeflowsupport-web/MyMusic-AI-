-- Migration 001: create the user table required by app.auth.
-- Apply this migration to the configured database before enabling AUTH_ENABLED.
-- PostgreSQL syntax; do not run automatically on application startup.
BEGIN;
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(320) NOT NULL UNIQUE,
    password_hash VARCHAR(512) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);
COMMIT;
