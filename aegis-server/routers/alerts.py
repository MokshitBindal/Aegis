# aegis-server/routers/alerts.py

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request

# We need a Pydantic model for alerts
from pydantic import BaseModel

from internal.auth.jwt import get_current_user
from internal.storage.postgres import get_db_pool
from models.models import TokenData


class Alert(BaseModel):
    id: int
    rule_name: str
    details: dict | None = None # Allow details to be None or dict
    severity: str
    created_at: datetime

router = APIRouter()

@router.get("/alerts", response_model=list[Alert])
async def get_alerts(
    request: Request,
    limit: int = 100,
    current_user: TokenData = Depends(get_current_user) # Secure endpoint
):
    """
    Fetches the most recent alerts.
    (Currently fetches for all users, needs refinement for multi-tenancy)
    """
    pool = get_db_pool()
    # TODO: In a multi-user system, we'd need to filter alerts
    # based on the user_id (e.g., only show alerts related to their devices).
    # This requires linking alerts to users/devices.
    
    sql = "SELECT * FROM alerts ORDER BY created_at DESC LIMIT $1"
    
    try:
        async with pool.acquire() as conn:
            alert_records = await conn.fetch(sql, limit)
            # Use model_validate to handle potential None for details
            alerts = [Alert.model_validate(dict(record)) for record in alert_records]
            return alerts
            
    except Exception as e:
        print(f"Error fetching alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch alerts")