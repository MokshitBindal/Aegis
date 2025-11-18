-- RBAC Schema Migration for Aegis SIEM
-- Adds role-based access control with Owner/Admin/Device User hierarchy
-- Date: November 8, 2025

BEGIN;

-- Add role column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'device_user';
ALTER TABLE users ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES users(id);
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMPTZ;

-- Create index on role for faster filtering
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_created_by ON users(created_by);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

-- Add user_id to devices table for ownership tracking
ALTER TABLE devices ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id);
CREATE INDEX IF NOT EXISTS idx_devices_user_id ON devices(user_id);

-- Create alert_assignments table for alert triage workflow
CREATE TABLE IF NOT EXISTS alert_assignments (
    id SERIAL PRIMARY KEY,
    alert_id INTEGER NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    assigned_to INTEGER NOT NULL REFERENCES users(id),
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'investigating',
    notes TEXT,
    resolution VARCHAR(20),
    resolved_at TIMESTAMPTZ,
    escalated_at TIMESTAMPTZ,
    escalated_to INTEGER REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for alert_assignments
CREATE INDEX IF NOT EXISTS idx_alert_assignments_alert_id ON alert_assignments(alert_id);
CREATE INDEX IF NOT EXISTS idx_alert_assignments_assigned_to ON alert_assignments(assigned_to);
CREATE INDEX IF NOT EXISTS idx_alert_assignments_status ON alert_assignments(status);
CREATE INDEX IF NOT EXISTS idx_alert_assignments_escalated_to ON alert_assignments(escalated_to);

-- Add assignment_status to alerts table
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS assignment_status VARCHAR(20) DEFAULT 'unassigned';
CREATE INDEX IF NOT EXISTS idx_alerts_assignment_status ON alerts(assignment_status);

-- Update existing devices to have user_id (assign to first user or keep NULL)
-- This needs to be done manually based on your existing data
-- Example: UPDATE devices SET user_id = (SELECT id FROM users LIMIT 1) WHERE user_id IS NULL;

-- Set the first user as owner (modify email as needed)
-- UPDATE users SET role = 'owner' WHERE email = 'your-email@example.com';

COMMIT;

-- Verify changes
SELECT 'RBAC schema migration completed successfully!' as status;
SELECT 'Users table columns:' as info;
SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'users' ORDER BY ordinal_position;
SELECT 'Alert assignments table created:' as info;
SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'alert_assignments' ORDER BY ordinal_position;
