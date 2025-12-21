-- RAGent PostgreSQL Initialization Script
-- This script runs when the database is first created

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE ragent TO ragent;