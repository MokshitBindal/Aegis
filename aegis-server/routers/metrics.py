"""
Router for system metrics endpoints.
Handles metrics ingestion and querying.
"""

import json
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException

from internal.auth.jwt import get_current_user
from internal.storage.postgres import get_db_pool
from models.metrics import SystemMetrics
from models.models import TokenData
from routers.websocket import push_update_to_user

router = APIRouter()

@router.post("/metrics")
async def ingest_metrics(
    metrics: SystemMetrics,
    x_aegis_agent_id: uuid.UUID = Header(None)
):
    """
    Ingest system metrics from an agent.
    """
    if not x_aegis_agent_id:
        raise HTTPException(status_code=401, detail="X-Aegis-Agent-ID header missing")

    pool = get_db_pool()
    
    # Verify agent and get user_id
    try:
        async with pool.acquire() as conn:
            record = await conn.fetchrow(
                "SELECT user_id FROM devices WHERE agent_id = $1",
                x_aegis_agent_id
            )
            if not record:
                raise HTTPException(status_code=403, detail="Agent not registered")
            
            user_id = record['user_id']
            
            # Update last_seen timestamp to indicate agent is active
            await conn.execute(
                "UPDATE devices SET last_seen = NOW(), status = 'online' WHERE agent_id = $1",
                x_aegis_agent_id
            )
            
            # Convert model fields to JSON strings for JSONB columns
            cpu_json = json.dumps(dict(metrics.cpu))
            memory_json = json.dumps(dict(metrics.memory))
            disk_json = json.dumps(dict(metrics.disk))
            network_json = json.dumps(dict(metrics.network))
            process_json = json.dumps(dict(metrics.process))

            # Store metrics
            await conn.execute(
                """
                INSERT INTO system_metrics 
                (agent_id, timestamp, cpu_data, memory_data, disk_data,
                 network_data, process_data)
                VALUES ($1, $2, $3::jsonb, $4::jsonb, $5::jsonb, $6::jsonb, $7::jsonb)
                """,
                str(x_aegis_agent_id),
                metrics.timestamp,
                cpu_json,
                memory_json,
                disk_json,
                network_json,
                process_json
            )

            # Push real-time update
            metrics_dict = metrics.dict()
            metrics_dict["timestamp"] = metrics.timestamp.isoformat()
            await push_update_to_user(user_id, {
                "type": "device_metrics",
                "payload": {
                    "agent_id": str(x_aegis_agent_id),
                    "metrics": metrics_dict
                }
            })

            return {"message": "Metrics stored successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store metrics: {e}")

@router.get("/metrics/{agent_id}")
async def get_metrics(
    agent_id: uuid.UUID,
    current_user: TokenData = Depends(get_current_user),
    timespan: str | None = "1h"  # Options: 1h, 24h, 7d, 30d
) -> list[SystemMetrics]:
    """
    Get metrics for a specific agent within a timespan.
    """
    pool = get_db_pool()
    
    # Convert timespan to timedelta
    span_map = {
        "1h": timedelta(hours=1),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30)
    }
    time_delta = span_map.get(timespan, timedelta(hours=1))
    
    try:
        async with pool.acquire() as conn:
            # Get current user and verify access
            from models.models import UserRole
            from routers.device import get_user_by_email
            
            user = await get_user_by_email(current_user.email, conn)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Verify user has access to this device
            if user.role == UserRole.OWNER:
                # Owner can access all devices
                device = await conn.fetchrow(
                    "SELECT 1 FROM devices WHERE agent_id = $1",
                    str(agent_id)
                )
            elif user.role == UserRole.ADMIN:
                # Admin can access devices they own OR are assigned to
                device = await conn.fetchrow(
                    """
                    SELECT 1 FROM devices d
                    LEFT JOIN device_assignments da ON d.id = da.device_id
                    WHERE d.agent_id = $1 AND (d.user_id = $2 OR da.user_id = $2)
                    """,
                    str(agent_id), user.id
                )
            else:
                # Device User can only access their own devices
                device = await conn.fetchrow(
                    "SELECT 1 FROM devices WHERE agent_id = $1 AND user_id = $2",
                    str(agent_id), user.id
                )
            
            if not device:
                raise HTTPException(
                    status_code=403,
                    detail="Access forbidden: You do not have access to this device"
                )
            
            # Get metrics within timespan
            rows = await conn.fetch("""
                SELECT 
                    agent_id,
                    timestamp,
                    cpu_data::text as cpu_data,
                    memory_data::text as memory_data,
                    disk_data::text as disk_data,
                    network_data::text as network_data,
                    process_data::text as process_data
                FROM system_metrics 
                WHERE agent_id = $1 
                AND timestamp > $2
                ORDER BY timestamp DESC
            """,
            str(agent_id),
            datetime.now() - time_delta
            )
            
            # Convert JSONB text to Python dicts
            metrics = []
            for row in rows:
                try:
                    metric = SystemMetrics(
                        agent_id=str(row['agent_id']),
                        timestamp=row['timestamp'],
                        cpu=json.loads(row['cpu_data']),
                        memory=json.loads(row['memory_data']),
                        disk=json.loads(row['disk_data']),
                        network=json.loads(row['network_data']),
                        process=json.loads(row['process_data'])
                    )
                    metrics.append(metric)
                except Exception as e:
                    print(f"Error processing metric row: {e}")
                    continue
            
            return metrics
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve metrics: {e}"
        )