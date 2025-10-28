# aegis-server/internal/storage/postgres.py


import asyncpg

from internal.config.config import DB_URL  # <--- IMPORT DB_URL

# We'll create a global pool variable
db_pool: asyncpg.Pool = None

async def init_db_pool():
    """
    Initializes the asyncpg connection pool.
    """
    global db_pool
    if not DB_URL:
        print("CRITICAL: Database URL not configured. Check config.toml.")
        raise ValueError("Database configuration is missing.")
        
    try:
        db_pool = await asyncpg.create_pool(
            DB_URL,
            min_size=5,
            max_size=20
        )
        print("Database connection pool established.")
    except Exception as e:
        print(f"Failed to create database pool: {e}")
        raise

async def close_db_pool():
    """
    Closes the asyncpg connection pool.
    """
    global db_pool
    if db_pool:
        await db_pool.close()
        print("Database connection pool closed.")

def get_db_pool() -> asyncpg.Pool:
    """
    Dependency function to get the pool.
    """
    return db_pool