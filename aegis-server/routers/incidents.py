# aegis-server/routers/incidents.py

"""
Router for incident management endpoints.
"""

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from internal.auth.jwt import get_current_user
from internal.storage.postgres import get_db_pool
from models.models import TokenData
from routers.device import get_user_by_email

router = APIRouter()


class Incident(BaseModel):
    """Model for security incidents"""

    id: int
    name: str
    description: str | None = None
    severity: str
    status: str
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    alert_count: int
    affected_devices: list[str]
    attack_vector: str | None = None
    metadata: dict | None = None
    alerts: list[dict] | None = None  # Optional expanded alerts


class IncidentUpdate(BaseModel):
    """Model for updating incident status"""

    status: str  # open, investigating, resolved
    notes: str | None = None


@router.get("/incidents", response_model=list[Incident])
async def get_incidents(
    status: str | None = Query(None),
    severity: str | None = Query(None),
    limit: int = 50,
    current_user: TokenData = Depends(get_current_user),
):
    """
    Get incidents for the current user's devices.
    """
    pool = get_db_pool()

    try:
        async with pool.acquire() as conn:
            # Get the current user
            user = await get_user_by_email(current_user.email, conn)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # Build query with filters
            conditions = []
            params = [user.id]
            param_num = 2

            if status:
                conditions.append(f"i.status = ${param_num}")
                params.append(status)
                param_num += 1

            if severity:
                conditions.append(f"i.severity = ${param_num}")
                params.append(severity)
                param_num += 1

            where_clause = (
                "AND " + " AND ".join(conditions) if conditions else ""
            )

            sql = f"""
            SELECT DISTINCT i.*
            FROM incidents i
            INNER JOIN alerts a ON a.incident_id = i.id
            LEFT JOIN devices d ON a.agent_id = d.agent_id
            WHERE (d.user_id = $1 OR a.agent_id IS NULL)
            {where_clause}
            ORDER BY i.created_at DESC
            LIMIT ${param_num}
            """
            params.append(limit)

            incident_records = await conn.fetch(sql, *params)

            incidents = []
            for record in incident_records:
                incident_dict = dict(record)
                # Parse metadata JSON
                if isinstance(incident_dict.get('metadata'), str):
                    try:
                        incident_dict['metadata'] = json.loads(
                            incident_dict['metadata']
                        )
                    except json.JSONDecodeError:
                        incident_dict['metadata'] = {}

                incidents.append(Incident.model_validate(incident_dict))

            return incidents

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching incidents: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch incidents")


@router.get("/incidents/{incident_id}", response_model=Incident)
async def get_incident(
    incident_id: int, current_user: TokenData = Depends(get_current_user)
):
    """
    Get detailed information about a specific incident including all related alerts.
    """
    pool = get_db_pool()

    try:
        async with pool.acquire() as conn:
            # Get the current user
            user = await get_user_by_email(current_user.email, conn)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # Get incident
            incident_sql = """
            SELECT i.*
            FROM incidents i
            INNER JOIN alerts a ON a.incident_id = i.id
            LEFT JOIN devices d ON a.agent_id = d.agent_id
            WHERE i.id = $1 AND (d.user_id = $2 OR a.agent_id IS NULL)
            LIMIT 1
            """

            incident_record = await conn.fetchrow(
                incident_sql, incident_id, user.id
            )

            if not incident_record:
                raise HTTPException(status_code=404, detail="Incident not found")

            incident_dict = dict(incident_record)

            # Parse metadata
            if isinstance(incident_dict.get('metadata'), str):
                try:
                    incident_dict['metadata'] = json.loads(
                        incident_dict['metadata']
                    )
                except json.JSONDecodeError:
                    incident_dict['metadata'] = {}

            # Get related alerts
            alerts_sql = """
            SELECT id, rule_name, severity, details, agent_id, created_at
            FROM alerts
            WHERE incident_id = $1
            ORDER BY created_at ASC
            """

            alert_records = await conn.fetch(alerts_sql, incident_id)

            alerts = []
            for alert_record in alert_records:
                alert_dict = dict(alert_record)
                if alert_dict.get('agent_id'):
                    alert_dict['agent_id'] = str(alert_dict['agent_id'])
                # Parse details
                if isinstance(alert_dict.get('details'), str):
                    try:
                        alert_dict['details'] = json.loads(alert_dict['details'])
                    except json.JSONDecodeError:
                        alert_dict['details'] = {}
                alerts.append(alert_dict)

            incident_dict['alerts'] = alerts

            return Incident.model_validate(incident_dict)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching incident: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch incident")


@router.patch("/incidents/{incident_id}", response_model=Incident)
async def update_incident(
    incident_id: int,
    update: IncidentUpdate,
    current_user: TokenData = Depends(get_current_user),
):
    """
    Update incident status (e.g., mark as resolved).
    """
    pool = get_db_pool()

    try:
        async with pool.acquire() as conn:
            # Verify ownership
            user = await get_user_by_email(current_user.email, conn)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # Update incident
            update_sql = """
            UPDATE incidents
            SET status = $1,
                updated_at = NOW(),
                resolved_at = CASE WHEN $1 = 'resolved' THEN NOW() ELSE resolved_at END
            WHERE id = $2
            RETURNING *
            """

            incident_record = await conn.fetchrow(
                update_sql, update.status, incident_id
            )

            if not incident_record:
                raise HTTPException(status_code=404, detail="Incident not found")

            incident_dict = dict(incident_record)
            if isinstance(incident_dict.get('metadata'), str):
                try:
                    incident_dict['metadata'] = json.loads(
                        incident_dict['metadata']
                    )
                except json.JSONDecodeError:
                    incident_dict['metadata'] = {}

            return Incident.model_validate(incident_dict)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating incident: {e}")
        raise HTTPException(status_code=500, detail="Failed to update incident")
