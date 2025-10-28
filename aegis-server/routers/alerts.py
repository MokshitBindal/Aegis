# aegis-server/routers/alerts.py

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request

# We need a Pydantic model for alerts
from pydantic import BaseModel

from internal.auth.jwt import get_current_user
from internal.storage.postgres import get_db_pool
from models.models import TokenData
from routers.device import get_user_by_email


class Alert(BaseModel):
    id: int
    agent_id: str | None = None  # Add agent_id field
    rule_name: str
    details: dict | None = None # Allow details to be None or dict
    severity: str
    created_at: datetime

router = APIRouter()

@router.get("/alerts", response_model=list[Alert])
async def get_alerts(
    request: Request,
    agent_id: uuid.UUID | None = Query(None),  # Optional device filter
    limit: int = 100,
    current_user: TokenData = Depends(get_current_user) # Secure endpoint
):
    """
    Fetches the most recent alerts.
    Filters by device (agent_id) if provided, otherwise returns all alerts
    for devices owned by the current user.
    """
    pool = get_db_pool()
    
    try:
        async with pool.acquire() as conn:
            # Get the current user
            user = await get_user_by_email(current_user.email, conn)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Build query based on filters
            if agent_id:
                # Verify user owns this device
                device_check = await conn.fetchrow(
                    "SELECT id FROM devices WHERE user_id = $1 AND agent_id = $2",
                    user.id, agent_id
                )
                if not device_check:
                    raise HTTPException(
                        status_code=403,
                        detail="Access forbidden: You do not own this device"
                    )
                
                # Fetch alerts for specific device
                sql = """
                SELECT * FROM alerts
                WHERE agent_id = $1
                ORDER BY created_at DESC 
                LIMIT $2
                """
                alert_records = await conn.fetch(sql, agent_id, limit)
            else:
                # Fetch alerts for all devices owned by this user
                sql = """
                SELECT a.* 
                FROM alerts a
                LEFT JOIN devices d ON a.agent_id = d.agent_id
                WHERE d.user_id = $1 OR a.agent_id IS NULL
                ORDER BY a.created_at DESC 
                LIMIT $2
                """
                alert_records = await conn.fetch(sql, user.id, limit)
            
            # Convert agent_id to string and parse details JSON for serialization
            alerts = []
            for record in alert_records:
                alert_dict = dict(record)
                if alert_dict.get('agent_id'):
                    alert_dict['agent_id'] = str(alert_dict['agent_id'])
                # Parse details if it's a string
                if isinstance(alert_dict.get('details'), str):
                    try:
                        alert_dict['details'] = json.loads(alert_dict['details'])
                    except json.JSONDecodeError:
                        alert_dict['details'] = {}
                alerts.append(Alert.model_validate(alert_dict))
            
            return alerts
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch alerts")