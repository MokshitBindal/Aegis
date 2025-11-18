-- Migration: Add device_assignments table for many-to-many device access control
-- This allows multiple admins to be assigned to multiple devices

CREATE TABLE IF NOT EXISTS device_assignments (
    id SERIAL PRIMARY KEY,
    device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    assigned_by INTEGER REFERENCES users(id), -- Owner who made the assignment
    
    -- Ensure a user can only be assigned to a device once
    UNIQUE(device_id, user_id)
);

-- Indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_device_assignments_device_id ON device_assignments(device_id);
CREATE INDEX IF NOT EXISTS idx_device_assignments_user_id ON device_assignments(user_id);

-- Comments for documentation
COMMENT ON TABLE device_assignments IS 'Many-to-many relationship: which admins/users can access which devices';
COMMENT ON COLUMN device_assignments.assigned_by IS 'User ID of the Owner who assigned this device';
