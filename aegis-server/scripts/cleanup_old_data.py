#!/usr/bin/env python3
"""
Cleanup script for Aegis SIEM - Deletes data older than 6 months.
This script should be run daily via cron or systemd timer.
"""

import asyncio
import asyncpg
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))

from internal.config.config import settings


async def cleanup_old_data():
    """Delete logs, commands, and metrics older than 6 months."""
    
    # Calculate cutoff date (6 months ago)
    cutoff_date = datetime.now() - timedelta(days=180)
    
    print(f"Starting cleanup for data older than {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(
            host=settings.database.host,
            port=settings.database.port,
            user=settings.database.user,
            password=settings.database.password,
            database=settings.database.database
        )
        
        # Delete old logs
        logs_deleted = await conn.fetchval(
            "DELETE FROM logs WHERE timestamp < $1 RETURNING count(*)",
            cutoff_date
        )
        print(f"Deleted {logs_deleted or 0} log entries older than 6 months")
        
        # Delete old commands
        commands_deleted = await conn.fetchval(
            "DELETE FROM commands WHERE timestamp < $1 RETURNING count(*)",
            cutoff_date
        )
        print(f"Deleted {commands_deleted or 0} command entries older than 6 months")
        
        # Delete old metrics
        metrics_deleted = await conn.fetchval(
            "DELETE FROM metrics WHERE timestamp < $1 RETURNING count(*)",
            cutoff_date
        )
        print(f"Deleted {metrics_deleted or 0} metric entries older than 6 months")
        
        # Delete old resolved/escalated alert assignments (keep recent ones for audit)
        assignments_deleted = await conn.fetchval(
            """
            DELETE FROM alert_assignments 
            WHERE resolved_at < $1 OR (escalated_at < $1 AND status = 'escalated')
            RETURNING count(*)
            """,
            cutoff_date
        )
        print(f"Deleted {assignments_deleted or 0} old alert assignments")
        
        # Run VACUUM to reclaim disk space
        print("Running VACUUM to reclaim disk space...")
        await conn.execute("VACUUM ANALYZE logs")
        await conn.execute("VACUUM ANALYZE commands")
        await conn.execute("VACUUM ANALYZE metrics")
        await conn.execute("VACUUM ANALYZE alert_assignments")
        
        await conn.close()
        
        print(f"Cleanup completed successfully at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"Error during cleanup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(cleanup_old_data())
