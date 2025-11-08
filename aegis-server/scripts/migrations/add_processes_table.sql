-- Migration: Add processes table for AI/ML behavioral anomaly detection
-- Date: 2025-11-08
-- Description: Creates table to store process monitoring data from agents

CREATE TABLE IF NOT EXISTS processes (
    id BIGSERIAL,
    agent_id UUID NOT NULL REFERENCES devices(agent_id) ON DELETE CASCADE,
    
    -- Process identification
    pid INTEGER NOT NULL,
    name TEXT NOT NULL,
    exe TEXT,
    cmdline TEXT,
    username TEXT,
    status TEXT,
    create_time TIMESTAMPTZ,
    ppid INTEGER,
    
    -- Resource usage
    cpu_percent REAL,
    memory_percent REAL,
    memory_rss BIGINT,
    memory_vms BIGINT,
    num_threads INTEGER,
    num_fds INTEGER,
    
    -- Network activity
    num_connections INTEGER,
    connection_details JSONB,
    
    -- Collection metadata
    collected_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Composite primary key including partitioning column
    PRIMARY KEY (id, collected_at)
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_processes_agent_id ON processes(agent_id);
CREATE INDEX IF NOT EXISTS idx_processes_collected_at ON processes(collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_processes_agent_collected ON processes(agent_id, collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_processes_name ON processes(name);
CREATE INDEX IF NOT EXISTS idx_processes_username ON processes(username);
CREATE INDEX IF NOT EXISTS idx_processes_cpu ON processes(cpu_percent DESC) WHERE cpu_percent > 50;
CREATE INDEX IF NOT EXISTS idx_processes_memory ON processes(memory_percent DESC) WHERE memory_percent > 50;

-- Create hypertable for time-series optimization (if TimescaleDB is available)
-- This will allow efficient queries and automatic data retention policies
SELECT create_hypertable('processes', 'collected_at', if_not_exists => TRUE);

-- Add retention policy (optional - auto-delete data older than 30 days)
-- SELECT add_retention_policy('processes', INTERVAL '30 days', if_not_exists => TRUE);

-- Create comments
COMMENT ON TABLE processes IS 'Process monitoring data for AI/ML behavioral anomaly detection';
COMMENT ON COLUMN processes.agent_id IS 'Reference to device/agent that collected this data';
COMMENT ON COLUMN processes.pid IS 'Process ID on the monitored system';
COMMENT ON COLUMN processes.name IS 'Process name (e.g., python, nginx)';
COMMENT ON COLUMN processes.exe IS 'Full path to executable';
COMMENT ON COLUMN processes.cmdline IS 'Complete command line with arguments';
COMMENT ON COLUMN processes.username IS 'User that owns the process';
COMMENT ON COLUMN processes.status IS 'Process status (running, sleeping, zombie, etc.)';
COMMENT ON COLUMN processes.create_time IS 'When the process was started';
COMMENT ON COLUMN processes.ppid IS 'Parent process ID';
COMMENT ON COLUMN processes.cpu_percent IS 'CPU usage percentage';
COMMENT ON COLUMN processes.memory_percent IS 'Memory usage percentage';
COMMENT ON COLUMN processes.memory_rss IS 'Resident Set Size (physical memory) in bytes';
COMMENT ON COLUMN processes.memory_vms IS 'Virtual Memory Size in bytes';
COMMENT ON COLUMN processes.num_threads IS 'Number of threads';
COMMENT ON COLUMN processes.num_fds IS 'Number of file descriptors (Unix/Linux)';
COMMENT ON COLUMN processes.num_connections IS 'Number of network connections';
COMMENT ON COLUMN processes.connection_details IS 'JSON array of network connection details';
COMMENT ON COLUMN processes.collected_at IS 'When this data was collected by the agent';
