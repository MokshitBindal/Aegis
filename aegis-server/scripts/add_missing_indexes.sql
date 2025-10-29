-- Migration: Add Missing Indexes for Sprint 2
-- Date: January 2025
-- Purpose: Add performance indexes that were defined in init_db.py but never created

-- ============================================================
-- ALERTS TABLE INDEXES
-- ============================================================

-- Composite index for device-specific alert queries (most common query pattern)
-- Used by: routers/alerts.py, dashboard alert filtering
CREATE INDEX IF NOT EXISTS idx_alerts_agent_time 
ON alerts(agent_id, created_at DESC);

-- Foreign key index for incident lookups
-- Used by: incident_aggregator.py, routers/incidents.py
CREATE INDEX IF NOT EXISTS idx_alerts_incident 
ON alerts(incident_id);

-- Severity filtering index
-- Used by: dashboard severity filters, alert prioritization
CREATE INDEX IF NOT EXISTS idx_alerts_severity 
ON alerts(severity);

-- ============================================================
-- INCIDENTS TABLE INDEXES
-- ============================================================

-- Status filtering index (open/closed/resolved)
-- Used by: routers/incidents.py, dashboard incident views
CREATE INDEX IF NOT EXISTS idx_incidents_status 
ON incidents(status);

-- Severity filtering index
-- Used by: dashboard severity filters, critical incident queries
CREATE INDEX IF NOT EXISTS idx_incidents_severity 
ON incidents(severity);

-- Time-based ordering index
-- Used by: recent incidents queries, incident timeline
CREATE INDEX IF NOT EXISTS idx_incidents_created 
ON incidents(created_at DESC);

-- ============================================================
-- VERIFICATION
-- ============================================================

-- Display all indexes for alerts and incidents tables
SELECT 
    tablename, 
    indexname,
    indexdef
FROM pg_indexes 
WHERE schemaname = 'public' 
AND tablename IN ('alerts', 'incidents')
ORDER BY tablename, indexname;
