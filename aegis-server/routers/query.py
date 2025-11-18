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
Timeframe = Literal["1h", "6h", "24h", "7d", "30d", "6months"]

@router.get("/query/logs")
async def get_logs_for_agent(
    request: Request,
    agent_id: uuid.UUID = Query(None), # Optional agent_id - None means all devices
    timeframe: Timeframe = Query(None), # Optional timeframe
    since: str = Query(None), # Optional: ISO timestamp to fetch logs since
    limit: int = Query(1000, le=50000), # Default 1000, max 50000 for historical data
    current_user: TokenData = Depends(get_current_user)
):
    """
    Fetches logs for a specific agent or all accessible agents.
    - If agent_id is provided: Returns logs for that specific device (if user has access)
    - If agent_id is None: Returns logs from all devices the user can access
    
    Access control:
    - Device User: Only their own devices
    - Admin: Devices they're assigned to + devices they own
    - Owner: All devices
    """
    pool = get_db_pool()
    
    # Determine start time based on 'since' or 'timeframe'
    if since:
        # Use explicit timestamp if provided
        try:
            start_time = datetime.fromisoformat(since.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid 'since' timestamp format")
    elif timeframe:
        # Map our timeframe strings to timedelta objects
        time_deltas = {
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "6months": timedelta(days=180),
        }
        start_time = datetime.now(UTC) - time_deltas[timeframe]
    else:
        # Default to 24h if neither provided
        start_time = datetime.now(UTC) - timedelta(hours=24)
    
    try:
        async with pool.acquire() as conn:
            # --- CRITICAL SECURITY CHECK ---
            # 1. Get the current user
            user = await get_user_by_email(current_user.email, conn)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # 2. Determine which devices the user can access
            from models.models import UserRole
            
            if agent_id:
                # Specific device requested - verify access
                if user.role == UserRole.OWNER:
                    # Owner can access all devices
                    device_check = await conn.fetchrow(
                        "SELECT id FROM devices WHERE agent_id = $1", agent_id
                    )
                elif user.role == UserRole.ADMIN:
                    # Admin can access devices they own OR are assigned to
                    device_check = await conn.fetchrow(
                        """
                        SELECT d.id FROM devices d
                        LEFT JOIN device_assignments da ON d.id = da.device_id
                        WHERE d.agent_id = $1 AND (d.user_id = $2 OR da.user_id = $2)
                        """,
                        agent_id, user.id
                    )
                else:
                    # Device User can only access their own devices
                    device_check = await conn.fetchrow(
                        "SELECT id FROM devices WHERE agent_id = $1 AND user_id = $2",
                        agent_id, user.id
                    )
                
                if not device_check:
                    raise HTTPException(
                        status_code=403,
                        detail="Access forbidden: You do not have access to this device",
                    )
                
                # Fetch logs for specific device
                sql_logs = """
                SELECT 
                    timestamp, 
                    agent_id,
                    hostname, 
                    raw_data->>'MESSAGE' as message,
                    COALESCE(raw_data->>'PRIORITY', '6') as severity,
                    COALESCE(raw_data->>'SYSLOG_FACILITY', '1') as facility,
                    COALESCE(raw_data->>'SYSLOG_IDENTIFIER', raw_data->>'_COMM', '') as process_name
                FROM logs
                WHERE agent_id = $1 AND timestamp >= $2
                ORDER BY timestamp DESC
                LIMIT $3
                """
                log_records = await conn.fetch(sql_logs, agent_id, start_time, limit)
            else:
                # No specific device - get logs from all accessible devices
                if user.role == UserRole.OWNER:
                    # Owner sees all logs
                    sql_logs = """
                    SELECT 
                        timestamp, 
                        agent_id,
                        hostname, 
                        raw_data->>'MESSAGE' as message,
                        COALESCE(raw_data->>'PRIORITY', '6') as severity,
                        COALESCE(raw_data->>'SYSLOG_FACILITY', '1') as facility,
                        COALESCE(raw_data->>'SYSLOG_IDENTIFIER', raw_data->>'_COMM', '') as process_name
                    FROM logs
                    WHERE timestamp >= $1
                    ORDER BY timestamp DESC
                    LIMIT $2
                    """
                    log_records = await conn.fetch(sql_logs, start_time, limit)
                elif user.role == UserRole.ADMIN:
                    # Admin sees logs from owned devices + assigned devices
                    sql_logs = """
                    SELECT 
                        l.timestamp, 
                        l.agent_id,
                        l.hostname, 
                        l.raw_data->>'MESSAGE' as message,
                        COALESCE(l.raw_data->>'PRIORITY', '6') as severity,
                        COALESCE(l.raw_data->>'SYSLOG_FACILITY', '1') as facility,
                        COALESCE(l.raw_data->>'SYSLOG_IDENTIFIER', l.raw_data->>'_COMM', '') as process_name
                    FROM logs l
                    INNER JOIN devices d ON l.agent_id = d.agent_id
                    LEFT JOIN device_assignments da ON d.id = da.device_id
                    WHERE l.timestamp >= $1 AND (d.user_id = $2 OR da.user_id = $2)
                    ORDER BY l.timestamp DESC
                    LIMIT $3
                    """
                    log_records = await conn.fetch(sql_logs, start_time, user.id, limit)
                else:
                    # Device User sees only their own device logs
                    sql_logs = """
                    SELECT 
                        l.timestamp, 
                        l.agent_id,
                        l.hostname, 
                        l.raw_data->>'MESSAGE' as message,
                        COALESCE(l.raw_data->>'PRIORITY', '6') as severity,
                        COALESCE(l.raw_data->>'SYSLOG_FACILITY', '1') as facility,
                        COALESCE(l.raw_data->>'SYSLOG_IDENTIFIER', l.raw_data->>'_COMM', '') as process_name
                    FROM logs l
                    INNER JOIN devices d ON l.agent_id = d.agent_id
                    WHERE l.timestamp >= $1 AND d.user_id = $2
                    ORDER BY l.timestamp DESC
                    LIMIT $3
                    """
                    log_records = await conn.fetch(sql_logs, start_time, user.id, limit)
            
            # Convert records to a list of dicts for JSON response
            logs = []
            for idx, record in enumerate(log_records):
                # Generate a pseudo-ID using hash of timestamp + hostname + message
                pseudo_id = hash(f"{record['timestamp']}{record['hostname']}{record['message']}")
                logs.append({
                    "id": pseudo_id,
                    "agent_id": str(record['agent_id']),
                    "timestamp": record['timestamp'].isoformat(),
                    "hostname": record['hostname'],
                    "message": record['message'] or "",
                    "severity": record['severity'],
                    "facility": record['facility'],
                    "process_name": record['process_name'],
                })
            return logs
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching logs: {e}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Failed to fetch logs")