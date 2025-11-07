#!/usr/bin/env python3
"""
Data retention cleanup script for Aegis SIEM.
Deletes commands and logs older than 6 months.
Should be run daily via cron job.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from internal.storage.postgres import close_db_pool, get_db_pool, init_db_pool


async def cleanup_old_data():
    """
    Cleans up commands and logs older than 6 months from the database.
    """
    try:
        await init_db_pool()
        pool = get_db_pool()
        
        # Calculate the cutoff date (6 months ago)
        cutoff_date = datetime.now() - timedelta(days=180)  # 6 months = ~180 days
        
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
            
            print(f"Cleanup completed successfully:")
            print(f"  - Deleted {commands_deleted} commands older than {cutoff_date.date()}")
            print(f"  - Deleted {logs_deleted} logs older than {cutoff_date.date()}")
            
        await close_db_pool()
        return commands_deleted, logs_deleted
        
    except Exception as e:
        print(f"Error during cleanup: {e}")
        raise e


async def show_data_stats():
    """
    Show statistics about stored data.
    """
    try:
        await init_db_pool()
        pool = get_db_pool()
        
        cutoff_date = datetime.now() - timedelta(days=180)
        
        async with pool.acquire() as conn:
            # Count total commands
            total_commands = await conn.fetchval("SELECT COUNT(*) FROM commands")
            
            # Count old commands
            old_commands = await conn.fetchval(
                "SELECT COUNT(*) FROM commands WHERE timestamp < $1",
                cutoff_date
            )
            
            # Get oldest command timestamp
            oldest_command = await conn.fetchval(
                "SELECT MIN(timestamp) FROM commands"
            )
            
            # Get newest command timestamp
            newest_command = await conn.fetchval(
                "SELECT MAX(timestamp) FROM commands"
            )
            
            # Count total logs
            total_logs = await conn.fetchval("SELECT COUNT(*) FROM logs")
            
            # Count old logs
            old_logs = await conn.fetchval(
                "SELECT COUNT(*) FROM logs WHERE timestamp < $1",
                cutoff_date
            )
            
            print("\n=== Data Retention Statistics ===")
            print(f"Cutoff date (6 months ago): {cutoff_date.date()}")
            print(f"\nCommands:")
            print(f"  Total: {total_commands}")
            print(f"  Older than 6 months: {old_commands}")
            print(f"  Within retention: {total_commands - old_commands}")
            print(f"  Oldest: {oldest_command}")
            print(f"  Newest: {newest_command}")
            print(f"\nLogs:")
            print(f"  Total: {total_logs}")
            print(f"  Older than 6 months: {old_logs}")
            print(f"  Within retention: {total_logs - old_logs}")
            
        await close_db_pool()
        
    except Exception as e:
        print(f"Error getting stats: {e}")
        raise e


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Clean up Aegis SIEM data older than 6 months"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show statistics without deleting"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    
    args = parser.parse_args()
    
    if args.stats or args.dry_run:
        print("Fetching data statistics...")
        asyncio.run(show_data_stats())
        if not args.dry_run:
            sys.exit(0)
        else:
            print("\nDRY RUN: No data will be deleted.")
            sys.exit(0)
    
    print("Starting 6-month data retention cleanup...")
    try:
        asyncio.run(cleanup_old_data())
        print("\nCleanup completed successfully!")
    except Exception as e:
        print(f"\nCleanup failed: {e}")
        sys.exit(1)
