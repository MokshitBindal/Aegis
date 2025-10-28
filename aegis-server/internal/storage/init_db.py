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
        
        await conn.close()
        print("Database schema initialized successfully.")
        
    except Exception as e:
        print(f"Failed to initialize database schema: {e}")
        raise