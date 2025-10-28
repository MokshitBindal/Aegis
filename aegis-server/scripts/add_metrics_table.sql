-- Add system_metrics table
CREATE TABLE IF NOT EXISTS system_metrics (
    id BIGSERIAL PRIMARY KEY,
    agent_id UUID NOT NULL REFERENCES devices(agent_id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    cpu_data JSONB NOT NULL,
    memory_data JSONB NOT NULL,
    disk_data JSONB NOT NULL,
    network_data JSONB NOT NULL,
    process_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for efficient querying
CREATE INDEX IF NOT EXISTS idx_metrics_agent_time 
ON system_metrics(agent_id, timestamp DESC);

-- Create cleanup function for old metrics
CREATE OR REPLACE FUNCTION cleanup_old_metrics() RETURNS void AS $$
BEGIN
    DELETE FROM system_metrics 
    WHERE timestamp < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- Grant permissions to aegis_user
GRANT ALL PRIVILEGES ON TABLE system_metrics TO aegis_user;
GRANT ALL PRIVILEGES ON SEQUENCE system_metrics_id_seq TO aegis_user;