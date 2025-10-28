# aegis-server/routers/query.py

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from internal.auth.jwt import get_current_user
from internal.storage.postgres import get_db_pool
from models.models import TokenData

# We need the user helper from the device router
from routers.device import get_user_by_email

router = APIRouter()

# Define the allowed timeframes
Timeframe = Literal["1h", "6h", "24h", "7d"]

@router.get("/logs")
async def get_logs_for_agent(
    request: Request,
    agent_id: uuid.UUID = Query(...), # Require an agent_id
    timeframe: Timeframe = Query("24h"), # Default to 24h
    limit: int = Query(1000, le=5000), # Default 1000, max 5000
    current_user: TokenData = Depends(get_current_user)
):
    """
    Fetches logs for a specific agent, owned by the current user.
    """
    pool = get_db_pool()
    
    # Map our timeframe strings to timedelta objects
    time_deltas = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
    }
    
    # Calculate the start time
    start_time = datetime.now(UTC) - time_deltas[timeframe]
    
    try:
        async with pool.acquire() as conn:
            # --- CRITICAL SECURITY CHECK ---
            # 1. Get the current user
            user = await get_user_by_email(current_user.email, conn)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # 2. Verify this user *owns* the agent they are asking about
            sql_check = "SELECT id FROM devices WHERE user_id = $1 AND agent_id = $2"
            device = await conn.fetchrow(sql_check, user.id, agent_id)
            if not device:
                # If no record, this user does not own this agent
                raise HTTPException(
                    status_code=403,
                    detail="Access forbidden: You do not own this agent",
                )
            
            # --- If check passes, fetch the logs ---
            # This query is fast because 'logs' is a hypertable!
            sql_logs = """
            SELECT timestamp, hostname, raw_data->>'MESSAGE' as message, raw_data
            FROM logs
            WHERE agent_id = $1 AND timestamp >= $2
            ORDER BY timestamp DESC
            LIMIT $3
            """
            log_records = await conn.fetch(sql_logs, agent_id, start_time, limit)
            
            # Convert records to a list of dicts for JSON response
            logs = [dict(record) for record in log_records]
            return logs
            
    except Exception as e:
        print(f"Error fetching logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch logs")