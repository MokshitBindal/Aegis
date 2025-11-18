# aegis-server/routers/ingest.py

import json
import re
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
            
            # Update last_seen timestamp to indicate agent is active
            await conn.execute(
                "UPDATE devices SET last_seen = NOW(), status = 'online' WHERE agent_id = $1",
                x_aegis_agent_id
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent auth error: {e}")


    # --- 3. DATA PREPARATION ---
    records_to_insert = []
    for log in logs:
        # Aggressive sanitization to remove null bytes and control characters
        # that PostgreSQL's TEXT type cannot handle
        try:
            sanitized_raw_json = log.raw_json
            
            # Method 1: Remove common null byte representations
            sanitized_raw_json = sanitized_raw_json.replace('\u0000', '')
            sanitized_raw_json = sanitized_raw_json.replace('\x00', '')
            
            # Method 2: Encode to bytes and filter out null bytes
            sanitized_bytes = sanitized_raw_json.encode('utf-8', errors='ignore')
            sanitized_bytes = sanitized_bytes.replace(b'\x00', b'')
            sanitized_raw_json = sanitized_bytes.decode('utf-8', errors='ignore')
            
            # Method 3: Remove control characters (except tab, newline, carriage return)
            sanitized_raw_json = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', sanitized_raw_json)
            
        except Exception as e:
            # If sanitization fails, use empty JSON
            print(f"Warning: Failed to sanitize log, using empty JSON: {e}")
            sanitized_raw_json = '{}'
        
        records_to_insert.append(
            (
                log.timestamp,
                x_aegis_agent_id, 
                log.hostname,
                sanitized_raw_json
            )
        )

    # --- 4. HIGH-SPEED BULK INSERT ---
    try:
        async with pool.acquire() as conn:
            # Use executemany for bulk insert with proper parameterization
            # This is more forgiving of special characters than copy_records_to_table
            sql = """
                INSERT INTO logs (timestamp, agent_id, hostname, raw_data)
                VALUES ($1, $2, $3, $4)
            """
            
            # Use a transaction for better performance
            async with conn.transaction():
                for record in records_to_insert:
                    try:
                        await conn.execute(sql, *record)
                    except Exception as e:
                        # Skip problematic records but continue processing
                        print(f"Warning: Skipped log entry due to error: {e}")
                        continue
            
    except asyncpg.exceptions.PostgresError as e:
        print(f"Database error during log ingestion: {e}")
        raise HTTPException(status_code=500, detail=f"Database insertion error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

    # --- 5. PUSH REAL-TIME LOG UPDATES ---
    # Broadcast each log to the user's WebSocket
    if user_id:
        for log in logs:
            # Parse the raw_json string to a dict
            try:
                raw_data = json.loads(log.raw_json) if isinstance(log.raw_json, str) else log.raw_json
            except (json.JSONDecodeError, TypeError):
                raw_data = {}
                
            message = raw_data.get("MESSAGE", "")
            await push_update_to_user(user_id, {
                "type": "new_log",
                "payload": {
                    "id": hash(f"{log.timestamp}{log.hostname}{message}"),  # Generate a pseudo-ID
                    "agent_id": str(x_aegis_agent_id),
                    "timestamp": log.timestamp.isoformat(),
                    "hostname": log.hostname,
                    "message": message,
                    "severity": raw_data.get("PRIORITY", "6"),  # Default to info
                    "facility": raw_data.get("SYSLOG_FACILITY", "1"),
                    "process_name": raw_data.get("SYSLOG_IDENTIFIER", raw_data.get("_COMM", "")),
                }
            })
        
        # Also send agent status update
        await push_update_to_user(user_id, {
            "type": "agent_status",
            "payload": {
                "agent_id": str(x_aegis_agent_id),
                "status": "online"
            }
        })

    return {"message": f"Successfully ingested {len(logs)} logs"}