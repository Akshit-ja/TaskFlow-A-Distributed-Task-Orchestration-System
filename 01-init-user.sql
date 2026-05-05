-- PostgreSQL Initialization Script
-- This ensures proper permissions are set for the application user
-- The user 'user' should already be created by POSTGRES_USER environment variable

-- Grant all privileges on the current database to the user
GRANT ALL PRIVILEGES ON DATABASE task_queue TO "user";

-- Grant schema permissions
GRANT ALL ON SCHEMA public TO "user";

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "user";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "user";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO "user";
