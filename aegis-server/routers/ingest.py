# aegis-server/routers/ingest.py

import uuid

import asyncpg
from fastapi import APIRouter, Header, HTTPException, Request

from internal.storage.postgres import get_db_pool
from models.models import LogEntry

# --- 1. IMPORT THE WEBSOCKET PUSHER ---
from routers.websocket import push_update_to_user

router = APIRouter()

@router.post("/ingest")
async def ingest_logs(
    logs: list[LogEntry],
    request: Request,
    x_aegis_agent_id: uuid.UUID = Header(None)
):
    """
    The main log ingestion endpoint.
    Accepts a batch of logs and performs a high-speed bulk insert.
    """
    
    if not x_aegis_agent_id:
        raise HTTPException(
            status_code=401, detail="X-Aegis-Agent-ID header is missing"
        )

    pool = get_db_pool()
    if not pool:
        raise HTTPException(
            status_code=500, detail="Database connection pool not available"
        )

    # --- 2. FIND OUT WHICH USER THIS AGENT BELONGS TO ---
    user_id = None
    try:
        async with pool.acquire() as conn:
            # We need to find the user_id associated with this agent_id
            sql = "SELECT user_id FROM devices WHERE agent_id = $1"
            record = await conn.fetchrow(sql, x_aegis_agent_id)
            if not record:
                # This agent isn't registered. Reject the logs.
                raise HTTPException(status_code=403, detail="Agent not registered")
            
            user_id = record['user_id']
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent auth error: {e}")


    # --- 3. DATA PREPARATION ---
    records_to_insert = []
    for log in logs:
        records_to_insert.append(
            (
                log.timestamp,
                x_aegis_agent_id, 
                log.hostname,
                log.raw_json
            )
        )

    # --- 4. HIGH-SPEED BULK INSERT ---
    try:
        async with pool.acquire() as conn:
            await conn.copy_records_to_table(
                'logs',
                records=records_to_insert,
                columns=('timestamp', 'agent_id', 'hostname', 'raw_data')
            )
            
    except asyncpg.exceptions.PostgresError as e:
        print(f"Database error during log ingestion: {e}")
        raise HTTPException(status_code=500, detail=f"Database insertion error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

    # --- 5. PUSH REAL-TIME UPDATE ---
    # If the insert was successful, tell the user's dashboard
    if user_id:
        await push_update_to_user(user_id, {
            "type": "agent_status",
            "payload": {
                "agent_id": str(x_aegis_agent_id),
                "status": "online"
            }
        })

    return {"message": f"Successfully ingested {len(logs)} logs"}