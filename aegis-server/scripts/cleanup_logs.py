#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from internal.storage.postgres import init_db_pool, get_db_pool, close_db_pool

async def cleanup_server_logs():
    """Cleans up all logs from the PostgreSQL database"""
    try:
        await init_db_pool()
        pool = get_db_pool()
        
        async with pool.acquire() as conn:
            # Delete all logs
            await conn.execute("DELETE FROM logs")
            print("Successfully cleared server logs database.")
            
        await close_db_pool()
    except Exception as e:
        print(f"Error clearing server logs: {e}")
        raise e

if __name__ == "__main__":
    print("Starting server cleanup process...")
    asyncio.run(cleanup_server_logs())
    print("Server cleanup complete!")