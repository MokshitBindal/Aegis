"""
Background task for data retention cleanup.
Runs daily at 3 AM to delete commands and logs older than 6 months.
"""

import asyncio
from datetime import datetime, timedelta, time

from internal.storage.postgres import get_db_pool


async def run_daily_cleanup():
    """
    Background task that runs cleanup daily at 3 AM.
    Deletes commands and logs older than 6 months (180 days).
    """
    print("Data retention cleanup task started")
    
    while True:
        try:
            # Calculate time until next 3 AM
            now = datetime.now()
            target_time = datetime.combine(now.date(), time(hour=3, minute=0))
            
            # If it's already past 3 AM today, target tomorrow's 3 AM
            if now >= target_time:
                target_time += timedelta(days=1)
            
            # Calculate sleep duration
            sleep_seconds = (target_time - now).total_seconds()
            
            print(f"Next cleanup scheduled for: {target_time}")
            print(f"Sleeping for {sleep_seconds / 3600:.1f} hours...")
            
            # Sleep until 3 AM
            await asyncio.sleep(sleep_seconds)
            
            # Run the cleanup
            print(f"\n=== Starting scheduled cleanup at {datetime.now()} ===")
            await perform_cleanup()
            print(f"=== Cleanup completed at {datetime.now()} ===\n")
            
        except asyncio.CancelledError:
            print("Cleanup task cancelled")
            break
        except Exception as e:
            print(f"Error in cleanup task: {e}")
            # Wait 1 hour before retrying on error
            await asyncio.sleep(3600)


async def perform_cleanup():
    """
    Perform the actual cleanup of old data.
    """
    try:
        pool = get_db_pool()
        if not pool:
            print("ERROR: Database pool not available")
            return
        
        # Calculate cutoff date (6 months ago)
        cutoff_date = datetime.now() - timedelta(days=180)
        
        async with pool.acquire() as conn:
            # Delete old commands
            result_commands = await conn.execute(
                "DELETE FROM commands WHERE timestamp < $1",
                cutoff_date
            )
            commands_deleted = int(result_commands.split()[-1])
            
            # Delete old logs
            result_logs = await conn.execute(
                "DELETE FROM logs WHERE timestamp < $1",
                cutoff_date
            )
            logs_deleted = int(result_logs.split()[-1])
            
            print(f"Retention cleanup results:")
            print(f"  - Deleted {commands_deleted} commands older than {cutoff_date.date()}")
            print(f"  - Deleted {logs_deleted} logs older than {cutoff_date.date()}")
            
    except Exception as e:
        print(f"ERROR during cleanup: {e}")
        raise
