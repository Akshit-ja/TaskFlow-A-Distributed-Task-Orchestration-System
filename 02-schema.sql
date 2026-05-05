-- Initial database schema for distributed task queue
-- This file will be automatically executed when PostgreSQL container starts

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create enum types
CREATE TYPE task_status AS ENUM ('pending', 'running', 'completed', 'failed', 'retrying', 'cancelled');
CREATE TYPE task_priority AS ENUM ('low', 'normal', 'high', 'critical');

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    queue_name VARCHAR(100) NOT NULL DEFAULT 'default',
    priority task_priority NOT NULL DEFAULT 'normal',
    status task_status NOT NULL DEFAULT 'pending',
    
    -- Task data and configuration
    payload JSONB NOT NULL DEFAULT '{}',
    result JSONB,
    error_message TEXT,
    
    -- Retry configuration
    max_retries INTEGER NOT NULL DEFAULT 3,
    current_retries INTEGER NOT NULL DEFAULT 0,
    retry_delay INTEGER NOT NULL DEFAULT 60, -- seconds
    
    -- Timing information
    timeout INTEGER, -- seconds
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Worker information
    worker_id VARCHAR(255),
    worker_hostname VARCHAR(255),
    
    -- Metadata
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}'
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_queue_name ON tasks(queue_name);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
CREATE INDEX IF NOT EXISTS idx_tasks_scheduled_at ON tasks(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_tasks_worker_id ON tasks(worker_id);
CREATE INDEX IF NOT EXISTS idx_tasks_queue_status ON tasks(queue_name, status);
CREATE INDEX IF NOT EXISTS idx_tasks_tags ON tasks USING GIN(tags);

-- Queue statistics table (for monitoring)
CREATE TABLE IF NOT EXISTS queue_stats (
    id SERIAL PRIMARY KEY,
    queue_name VARCHAR(100) NOT NULL,
    pending_count INTEGER NOT NULL DEFAULT 0,
    running_count INTEGER NOT NULL DEFAULT 0,
    completed_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    total_processing_time BIGINT NOT NULL DEFAULT 0, -- milliseconds
    last_updated TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    UNIQUE(queue_name)
);

-- Worker registration table (for monitoring active workers)
CREATE TABLE IF NOT EXISTS workers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id VARCHAR(255) NOT NULL UNIQUE,
    hostname VARCHAR(255) NOT NULL,
    pid INTEGER,
    queues JSONB NOT NULL DEFAULT '[]', -- array of queue names this worker handles
    concurrency INTEGER NOT NULL DEFAULT 1,
    current_tasks INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'active', -- active, idle, stopped
    last_heartbeat TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Create index for worker queries
CREATE INDEX IF NOT EXISTS idx_workers_worker_id ON workers(worker_id);
CREATE INDEX IF NOT EXISTS idx_workers_status ON workers(status);
CREATE INDEX IF NOT EXISTS idx_workers_last_heartbeat ON workers(last_heartbeat);

-- Task execution log table (for debugging and monitoring)
CREATE TABLE IF NOT EXISTS task_logs (
    id SERIAL PRIMARY KEY,
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    level VARCHAR(20) NOT NULL, -- DEBUG, INFO, WARNING, ERROR, CRITICAL
    message TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    worker_id VARCHAR(255),
    metadata JSONB DEFAULT '{}'
);

-- Create index for task logs
CREATE INDEX IF NOT EXISTS idx_task_logs_task_id ON task_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_task_logs_level ON task_logs(level);
CREATE INDEX IF NOT EXISTS idx_task_logs_timestamp ON task_logs(timestamp);

-- Function to automatically update queue statistics
CREATE OR REPLACE FUNCTION update_queue_stats() RETURNS TRIGGER AS $$
BEGIN
    -- Update or insert queue statistics
    INSERT INTO queue_stats (queue_name, pending_count, running_count, completed_count, failed_count, last_updated)
    SELECT 
        queue_name,
        COUNT(*) FILTER (WHERE status = 'pending'),
        COUNT(*) FILTER (WHERE status = 'running'),
        COUNT(*) FILTER (WHERE status = 'completed'),
        COUNT(*) FILTER (WHERE status = 'failed'),
        NOW()
    FROM tasks 
    WHERE queue_name = COALESCE(NEW.queue_name, OLD.queue_name)
    GROUP BY queue_name
    ON CONFLICT (queue_name) 
    DO UPDATE SET
        pending_count = EXCLUDED.pending_count,
        running_count = EXCLUDED.running_count,
        completed_count = EXCLUDED.completed_count,
        failed_count = EXCLUDED.failed_count,
        last_updated = EXCLUDED.last_updated;
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update queue statistics
CREATE TRIGGER trigger_update_queue_stats
    AFTER INSERT OR UPDATE OR DELETE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_queue_stats();

-- Function to clean up old completed tasks (can be called periodically)
CREATE OR REPLACE FUNCTION cleanup_old_tasks(days_old INTEGER DEFAULT 30) RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM tasks 
    WHERE status IN ('completed', 'failed') 
    AND completed_at < NOW() - INTERVAL '1 day' * days_old;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Insert initial queue stats for default queue
INSERT INTO queue_stats (queue_name) VALUES ('default') ON CONFLICT DO NOTHING;