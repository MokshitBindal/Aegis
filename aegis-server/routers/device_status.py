# aegis-server/routers/device_status.py

"""
Router for handling device status updates from agents.
"""

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel

from internal.auth.jwt import get_current_user
from internal.storage.postgres import get_db_pool
from models.models import TokenData

router = APIRouter()


# Helper function to get user ID from email
async def get_user_by_email(email: str, conn):
    """Helper to fetch a user's ID by email."""
    user_record = await conn.fetchrow("SELECT id FROM users WHERE email = $1", email)
    if user_record:
        return user_record['id']
    return None


class StatusUpdate(BaseModel):
    """Model for device status updates"""
    agent_id: str
    status: str  # "online" or "offline"


@router.post("/device/status")
async def update_device_status(
    status_update: StatusUpdate,
    x_aegis_agent_id: str | None = Header(None),
):
    """
    Updates the status of a device (agent).
    
    Args:
        status_update: Status update containing agent_id and status
        x_aegis_agent_id: Agent ID from request header
        
    Returns:
        Success message
    """
    # Validate agent_id from header matches payload
    if x_aegis_agent_id and x_aegis_agent_id != status_update.agent_id:
        raise HTTPException(
            status_code=403,
            detail="Agent ID mismatch between header and payload"
        )
    
    # Validate status value
    if status_update.status not in ["online", "offline"]:
        raise HTTPException(
            status_code=400,
            detail="Status must be either 'online' or 'offline'"
        )
    
    pool = get_db_pool()
    if not pool:
        raise HTTPException(
            status_code=500,
            detail="Database connection pool not available"
        )
    
    try:
        async with pool.acquire() as conn:
            # Update device status and last_seen timestamp
            sql = """
                UPDATE devices
                SET status = $1, last_seen = $2
                WHERE agent_id = $3
                RETURNING id
            """
            
            result = await conn.fetchrow(
                sql,
                status_update.status,
                datetime.now(),
                uuid.UUID(status_update.agent_id)
            )
            
            if not result:
                raise HTTPException(
                    status_code=404,
                    detail="Device not found. Agent may not be registered."
                )
            
            return {
                "status": "success",
                "agent_id": status_update.agent_id,
                "new_status": status_update.status,
                "updated_at": datetime.now().isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating device status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update device status: {e}"
        )


@router.post("/devices/refresh-status")
async def refresh_all_device_statuses(current_user: TokenData = Depends(get_current_user)):
    """
    Refreshes the status of all devices based on last_seen timestamp.
    Devices that haven't sent data in the last 2 minutes are marked offline.
    
    Args:
        current_user: Authenticated user from JWT token
        
    Returns:
        Summary of status updates
    """
    pool = get_db_pool()
    if not pool:
        raise HTTPException(
            status_code=500,
            detail="Database connection pool not available"
        )
    
    try:
        async with pool.acquire() as conn:
            # Get the user's ID from email
            user_id = await get_user_by_email(current_user.email, conn)
            if not user_id:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Define timeout threshold (90 seconds to account for 30s forwarding interval + buffer)
            # Agent sends data every 30 seconds, so 90 seconds = 3 missed intervals
            timeout_threshold = datetime.now() - timedelta(seconds=90)
            
            # Mark devices as offline if last_seen is older than threshold
            offline_sql = """
                UPDATE devices
                SET status = 'offline'
                WHERE user_id = $1
                  AND (last_seen < $2 OR last_seen IS NULL)
                  AND status != 'offline'
                RETURNING agent_id
            """
            
            offline_results = await conn.fetch(offline_sql, user_id, timeout_threshold)
            offline_count = len(offline_results)
            
            # Mark devices as online if last_seen is recent
            online_sql = """
                UPDATE devices
                SET status = 'online'
                WHERE user_id = $1
                  AND last_seen >= $2
                  AND status != 'online'
                RETURNING agent_id
            """
            
            online_results = await conn.fetch(online_sql, user_id, timeout_threshold)
            online_count = len(online_results)
            
            return {
                "status": "success",
                "updated": {
                    "online": online_count,
                    "offline": offline_count
                },
                "threshold_seconds": 90,
                "checked_at": datetime.now().isoformat()
            }
            
    except Exception as e:
        print(f"Error refreshing device statuses: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh device statuses: {e}"
        )
