-- SkillOS PostgreSQL initialization
-- This runs once when the container is first created.
-- All actual schema is managed by Python migrations (db/migrations.py).

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For full-text search
GRANT ALL PRIVILEGES ON DATABASE skillos TO skillos;
