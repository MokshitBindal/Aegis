-- Add status and last_seen columns to devices table for real-time status tracking

-- Add status column (default to 'offline')
ALTER TABLE devices 
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'offline';

-- Add last_seen column to track last agent activity
ALTER TABLE devices 
ADD COLUMN IF NOT EXISTS last_seen TIMESTAMPTZ;

-- Create index on status for efficient filtering
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);

-- Create index on last_seen for efficient status checks
CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen DESC);

-- Update existing devices to have a last_seen timestamp
UPDATE devices 
SET last_seen = NOW() 
WHERE last_seen IS NULL;

COMMIT;
