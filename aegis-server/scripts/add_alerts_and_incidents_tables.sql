-- Add alerts and incidents tables for Sprint 2

-- Create alerts table
CREATE TABLE IF NOT EXISTS alerts (
    id BIGSERIAL PRIMARY KEY,
    rule_name VARCHAR(255) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    details JSONB,
    agent_id UUID REFERENCES devices(agent_id) ON DELETE CASCADE,
    incident_id BIGINT REFERENCES incidents(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create incidents table
CREATE TABLE IF NOT EXISTS incidents (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    description TEXT,
    severity VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'open',
    alert_count INTEGER DEFAULT 0,
    affected_devices TEXT[], -- Array of device identifiers
    attack_vector VARCHAR(255),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_alerts_agent_time 
ON alerts(agent_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_alerts_incident 
ON alerts(incident_id);

CREATE INDEX IF NOT EXISTS idx_alerts_severity 
ON alerts(severity);

CREATE INDEX IF NOT EXISTS idx_incidents_status 
ON incidents(status);

CREATE INDEX IF NOT EXISTS idx_incidents_severity 
ON incidents(severity);

CREATE INDEX IF NOT EXISTS idx_incidents_created 
ON incidents(created_at DESC);

-- Grant permissions to aegis_user
GRANT ALL PRIVILEGES ON TABLE alerts TO aegis_user;
GRANT ALL PRIVILEGES ON SEQUENCE alerts_id_seq TO aegis_user;
GRANT ALL PRIVILEGES ON TABLE incidents TO aegis_user;
GRANT ALL PRIVILEGES ON SEQUENCE incidents_id_seq TO aegis_user;
