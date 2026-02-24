-- =============================================================================
-- PostgreSQL Initialization Script
-- Creates initial schema and extensions
-- =============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For full-text search

-- Indexes for performance (created after Alembic migrations)
-- These are applied after table creation

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE codemix_nlp TO postgres;
