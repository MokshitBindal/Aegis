# aegis-server/routers/ingest.py

import uuid
from typing import List
from fastapi import APIRouter, Header, Depends, HTTPException, Request
import asyncpg

from models.models import LogEntry
from internal.storage.postgres import get_db_pool

# Create an APIRouter. This is like a "mini-FastAPI" app
# that we can later include in our main app.
router = APIRouter()

@router.post("/ingest")
async def ingest_logs(
    logs: List[LogEntry],
    request: Request, # We need the raw request to get the pool
    x_aegis_agent_id: uuid.UUID = Header(None) # Require the agent ID header
):
    """
    The main log ingestion endpoint.
    
    Accepts a batch of logs and performs a high-speed bulk insert.
    """
    
    # --- 1. Authentication & Validation ---
    if not x_aegis_agent_id:
        raise HTTPException(status_code=401, detail="X-Aegis-Agent-ID header is missing")

    # (In Phase 3, we'll add a check here to ensure this UUID
    # is actually registered in our 'devices' table)
    # print(f"Received batch of {len(logs)} logs from agent {x_aegis_agent_id}")

    # --- 2. Data Preparation ---
    # We must transform our Pydantic models into a list of tuples
    # in the *exact order* the 'logs' table columns expect:
    # (timestamp, agent_id, hostname, raw_data)
    
    records_to_insert = []
    for log in logs:
        # Note: We're adding the agent_id from the header
        records_to_insert.append(
            (
                log.timestamp,
                x_aegis_agent_id, 
                log.hostname,
                log.raw_json # This is already a JSON string
            )
        )

    # --- 3. High-Speed Bulk Insert ---
    pool = get_db_pool()
    if not pool:
        raise HTTPException(status_code=500, detail="Database connection pool not available")
        
    try:
        # Acquire a connection from the pool
        async with pool.acquire() as conn:
            # This is the high-performance part.
            # copy_records_to_table() streams the data directly
            # to the database, which is much faster than
            # running thousands of individual INSERT statements.
            await conn.copy_records_to_table(
                'logs',
                records=records_to_insert,
                columns=('timestamp', 'agent_id', 'hostname', 'raw_data')
            )
            
    except asyncpg.exceptions.PostgresError as e:
        # Log the error
        print(f"Database error during log ingestion: {e}")
        raise HTTPException(status_code=500, detail=f"Database insertion error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

    return {"message": f"Successfully ingested {len(logs)} logs"}