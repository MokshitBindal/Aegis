"""Database initialization and schema management"""
import asyncpg

from internal.config.config import DB_URL


async def init_db():
    """Initialize database schema"""
    try:
        # Connect directly for initialization
        conn = await asyncpg.connect(DB_URL)
        
        # Create system_metrics table
        await conn.execute('''
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
        ''')
        
        # Create indexes for efficient querying
        await conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_metrics_agent_time 
        ON system_metrics(agent_id, timestamp DESC);
        ''')
        
        # Create metrics retention policy (optional)
        await conn.execute('''
        CREATE OR REPLACE FUNCTION cleanup_old_metrics() RETURNS void AS $$
        BEGIN
            DELETE FROM system_metrics 
            WHERE timestamp < NOW() - INTERVAL '30 days';
        END;
        $$ LANGUAGE plpgsql;
        ''')
        
        # Create incidents table (must be created before alerts due to FK)
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS incidents (
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(500) NOT NULL,
            description TEXT,
            severity VARCHAR(50) NOT NULL,
            status VARCHAR(50) DEFAULT 'open',
            alert_count INTEGER DEFAULT 0,
            affected_devices TEXT[],
            attack_vector VARCHAR(255),
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP WITH TIME ZONE
        );
        ''')
        
        # Create alerts table
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id BIGSERIAL PRIMARY KEY,
            rule_name VARCHAR(255) NOT NULL,
            severity VARCHAR(50) NOT NULL,
            details JSONB,
            agent_id UUID REFERENCES devices(agent_id) ON DELETE CASCADE,
            incident_id BIGINT REFERENCES incidents(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        ''')
        
        # Create indexes for alerts and incidents
        await conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_alerts_agent_time ON alerts(agent_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_alerts_incident ON alerts(incident_id);
        CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
        CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
        CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents(severity);
        CREATE INDEX IF NOT EXISTS idx_incidents_created ON incidents(created_at DESC);
        ''')
        
        # Create commands table for terminal command logging
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS commands (
            id BIGSERIAL PRIMARY KEY,
            command TEXT NOT NULL,
            user_name VARCHAR(255) NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            shell VARCHAR(50),
            source VARCHAR(255),
            working_directory TEXT,
            exit_code INTEGER,
            agent_id UUID REFERENCES devices(agent_id) ON DELETE CASCADE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        ''')
        
        # Create indexes for commands
        await conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_commands_agent_time ON commands(agent_id, timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_commands_user ON commands(user_name);
        CREATE INDEX IF NOT EXISTS idx_commands_created ON commands(created_at DESC);
        ''')
        
        # Create device_baselines table for AI/ML behavioral learning
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS device_baselines (
            id BIGSERIAL PRIMARY KEY,
            device_id UUID NOT NULL REFERENCES devices(agent_id) ON DELETE CASCADE,
            baseline_type VARCHAR(50) NOT NULL,
            baseline_data JSONB NOT NULL,
            learned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            duration_days INTEGER NOT NULL,
            version INTEGER DEFAULT 1,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(device_id, baseline_type, version)
        );
        ''')
        
        # Create indexes for baselines
        await conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_baselines_device ON device_baselines(device_id);
        CREATE INDEX IF NOT EXISTS idx_baselines_type ON device_baselines(baseline_type);
        CREATE INDEX IF NOT EXISTS idx_baselines_learned ON device_baselines(learned_at DESC);
        ''')
        
        await conn.close()
        print("Database schema initialized successfully.")
        
    except Exception as e:
        print(f"Failed to initialize database schema: {e}")
        raise