"""
Process Data Ingestion Router

This router handles incoming process data from agents.
Process data is used for AI/ML behavioral anomaly detection.
"""

import logging
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException

from internal.auth.jwt import get_current_user
from internal.storage.postgres import get_db_pool
from models.models import ProcessData, TokenData, UserRole
from routers.device import get_user_by_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/processes", tags=["processes"])


@router.post("")
async def ingest_processes(
    processes: List[ProcessData],
    x_aegis_agent_id: str = Header(..., description="Agent UUID"),
):
    """
    Ingest process data from an agent.
    
    This endpoint receives process information collected by the agent,
    including process details, resource usage, and network connections.
    
    **Args:**
        processes: List of process data dictionaries
        x_aegis_agent_id: Agent UUID from header
    
    **Returns:**
        Success message with count of stored processes
    """
    if not processes:
        return {"message": "No processes to ingest"}
    
    logger.info(f"Received {len(processes)} processes from agent {x_aegis_agent_id}")
    
    # Validate agent_id format
    try:
        agent_uuid = UUID(x_aegis_agent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent_id format")
    
    pool = get_db_pool()
    
    try:
        async with pool.acquire() as conn:
            # Prepare bulk insert
            import json
            records = []
            for proc in processes:
                # Convert connection details to JSON string for JSONB
                connection_details = json.dumps([
                    {
                        "family": conn.family,
                        "type": conn.type,
                        "laddr": conn.laddr,
                        "raddr": conn.raddr,
                        "status": conn.status,
                    }
                    for conn in proc.connection_details
                ])
                
                # Parse datetime strings to datetime objects
                create_time = None
                if proc.create_time:
                    try:
                        create_time = datetime.fromisoformat(proc.create_time.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        create_time = None
                
                collected_at = None
                if proc.collected_at:
                    try:
                        collected_at = datetime.fromisoformat(proc.collected_at.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        collected_at = datetime.now()
                
                records.append((
                    str(proc.agent_id),
                    proc.pid,
                    proc.name,
                    proc.exe,
                    proc.cmdline,
                    proc.username,
                    proc.status,
                    create_time,
                    proc.ppid,
                    proc.cpu_percent,
                    proc.memory_percent,
                    proc.memory_rss,
                    proc.memory_vms,
                    proc.num_threads,
                    proc.num_fds,
                    proc.num_connections,
                    connection_details,  # Will be converted to JSONB
                    collected_at,
                ))
            
            # DUAL STORAGE STRATEGY:
            # 1. processes_history: Keep ALL snapshots for ML training
            # 2. processes: Keep only latest snapshot for live dashboard
            
            # First, store in history table for ML (create if not exists)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS processes_history (
                    id BIGSERIAL PRIMARY KEY,
                    agent_id UUID NOT NULL,
                    pid INTEGER NOT NULL,
                    name TEXT,
                    exe TEXT,
                    cmdline TEXT,
                    username TEXT,
                    status TEXT,
                    create_time TIMESTAMP WITH TIME ZONE,
                    ppid INTEGER,
                    cpu_percent REAL,
                    memory_percent REAL,
                    memory_rss BIGINT,
                    memory_vms BIGINT,
                    num_threads INTEGER,
                    num_fds INTEGER,
                    num_connections INTEGER,
                    connection_details JSONB,
                    collected_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                )
            """)
            
            # Create index for efficient querying
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_processes_history_agent_time 
                ON processes_history(agent_id, collected_at DESC)
            """)
            
            # Insert into history table (keeps all snapshots)
            await conn.copy_records_to_table(
                "processes_history",
                records=records,
                columns=[
                    "agent_id",
                    "pid",
                    "name",
                    "exe",
                    "cmdline",
                    "username",
                    "status",
                    "create_time",
                    "ppid",
                    "cpu_percent",
                    "memory_percent",
                    "memory_rss",
                    "memory_vms",
                    "num_threads",
                    "num_fds",
                    "num_connections",
                    "connection_details",
                    "collected_at",
                ],
            )
            
            # Delete old snapshot from live table
            await conn.execute(
                "DELETE FROM processes WHERE agent_id = $1",
                str(agent_uuid)
            )
            
            # Insert into live table (only latest snapshot)
            await conn.copy_records_to_table(
                "processes",
                records=records,
                columns=[
                    "agent_id",
                    "pid",
                    "name",
                    "exe",
                    "cmdline",
                    "username",
                    "status",
                    "create_time",
                    "ppid",
                    "cpu_percent",
                    "memory_percent",
                    "memory_rss",
                    "memory_vms",
                    "num_threads",
                    "num_fds",
                    "num_connections",
                    "connection_details",
                    "collected_at",
                ],
            )
            
            logger.info(f"Successfully stored {len(records)} processes for agent {x_aegis_agent_id}")
    
    except Exception as e:
        logger.error(f"Error storing processes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to store processes: {str(e)}")
    
    return {"message": f"Successfully stored {len(processes)} processes"}


@router.get("/{agent_id}")
async def get_processes(
    agent_id: UUID,
    limit: int = 100,
    offset: int = 0,
    current_user: TokenData = Depends(get_current_user),
):
    """
    Get process data for a specific agent.
    
    **Args:**
        agent_id: Agent UUID
        limit: Maximum number of processes to return
        offset: Pagination offset
    
    **Returns:**
        List of process data
    """
    pool = get_db_pool()
    
    try:
        async with pool.acquire() as conn:
            # Verify user has access to this device
            user = await get_user_by_email(current_user.email, conn)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            if user.role == UserRole.OWNER:
                # Owner can access all devices
                device_check = await conn.fetchrow(
                    "SELECT 1 FROM devices WHERE agent_id = $1", str(agent_id)
                )
            elif user.role == UserRole.ADMIN:
                # Admin can access devices they own OR are assigned to
                device_check = await conn.fetchrow(
                    """
                    SELECT 1 FROM devices d
                    LEFT JOIN device_assignments da ON d.id = da.device_id
                    WHERE d.agent_id = $1 AND (d.user_id = $2 OR da.user_id = $2)
                    """,
                    str(agent_id), user.id
                )
            else:
                # Device User can only access their own devices
                device_check = await conn.fetchrow(
                    "SELECT 1 FROM devices WHERE agent_id = $1 AND user_id = $2",
                    str(agent_id), user.id
                )
            
            if not device_check:
                raise HTTPException(
                    status_code=403,
                    detail="Access forbidden: You do not have access to this device"
                )
            
            # Get processes (only latest snapshot kept in DB - like htop)
            # Old snapshots are deleted on each new ingestion
            rows = await conn.fetch(
                """
                SELECT * FROM processes
                WHERE agent_id = $1
                ORDER BY cpu_percent DESC, memory_percent DESC
                LIMIT $2 OFFSET $3
                """,
                str(agent_id),
                limit,
                offset,
            )
            
            # Convert rows to dictionaries
            processes = [dict(row) for row in rows]
            
            return {
                "agent_id": str(agent_id),
                "count": len(processes),
                "processes": processes,
            }
    
    except Exception as e:
        logger.error(f"Error retrieving processes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve processes: {str(e)}")


@router.get("/{agent_id}/latest")
async def get_latest_processes(
    agent_id: UUID,
    current_user: TokenData = Depends(get_current_user),
):
    """
    Get the most recent process snapshot for an agent.
    
    Returns all processes from the latest collection cycle.
    
    **Args:**
        agent_id: Agent UUID
    
    **Returns:**
        Latest process snapshot
    """
    pool = get_db_pool()
    
    try:
        async with pool.acquire() as conn:
            # Verify user has access to this device
            user = await get_user_by_email(current_user.email, conn)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            if user.role == UserRole.OWNER:
                device_check = await conn.fetchrow(
                    "SELECT 1 FROM devices WHERE agent_id = $1", str(agent_id)
                )
            elif user.role == UserRole.ADMIN:
                device_check = await conn.fetchrow(
                    """
                    SELECT 1 FROM devices d
                    LEFT JOIN device_assignments da ON d.id = da.device_id
                    WHERE d.agent_id = $1 AND (d.user_id = $2 OR da.user_id = $2)
                    """,
                    str(agent_id), user.id
                )
            else:
                device_check = await conn.fetchrow(
                    "SELECT 1 FROM devices WHERE agent_id = $1 AND user_id = $2",
                    str(agent_id), user.id
                )
            
            if not device_check:
                raise HTTPException(
                    status_code=403,
                    detail="Access forbidden: You do not have access to this device"
                )
            
            # Get the latest collection timestamp
            latest_time = await conn.fetchval(
                """
                SELECT MAX(collected_at) FROM processes
                WHERE agent_id = $1
                """,
                str(agent_id),
            )
            
            if not latest_time:
                return {
                    "agent_id": str(agent_id),
                    "collected_at": None,
                    "count": 0,
                    "processes": [],
                }
            
            # Get all processes from that timestamp
            rows = await conn.fetch(
                """
                SELECT * FROM processes
                WHERE agent_id = $1 AND collected_at = $2
                ORDER BY pid
                """,
                str(agent_id),
                latest_time,
            )
            
            processes = [dict(row) for row in rows]
            
            return {
                "agent_id": str(agent_id),
                "collected_at": latest_time,
                "count": len(processes),
                "processes": processes,
            }
    
    except Exception as e:
        logger.error(f"Error retrieving latest processes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve latest processes: {str(e)}")


@router.get("/{agent_id}/summary")
async def get_process_summary(
    agent_id: UUID,
    current_user: TokenData = Depends(get_current_user),
):
    """
    Get aggregated process statistics for an agent.
    
    **Args:**
        agent_id: Agent UUID
    
    **Returns:**
        Process statistics summary
    """
    pool = get_db_pool()
    
    try:
        async with pool.acquire() as conn:
            # Verify user has access to this device
            user = await get_user_by_email(current_user.email, conn)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            if user.role == UserRole.OWNER:
                device_check = await conn.fetchrow(
                    "SELECT 1 FROM devices WHERE agent_id = $1", str(agent_id)
                )
            elif user.role == UserRole.ADMIN:
                device_check = await conn.fetchrow(
                    """
                    SELECT 1 FROM devices d
                    LEFT JOIN device_assignments da ON d.id = da.device_id
                    WHERE d.agent_id = $1 AND (d.user_id = $2 OR da.user_id = $2)
                    """,
                    str(agent_id), user.id
                )
            else:
                device_check = await conn.fetchrow(
                    "SELECT 1 FROM devices WHERE agent_id = $1 AND user_id = $2",
                    str(agent_id), user.id
                )
            
            if not device_check:
                raise HTTPException(
                    status_code=403,
                    detail="Access forbidden: You do not have access to this device"
                )
            
            # Get latest processes
            latest_time = await conn.fetchval(
                """
                SELECT MAX(collected_at) FROM processes
                WHERE agent_id = $1
                """,
                str(agent_id),
            )
            
            if not latest_time:
                return {
                    "agent_id": str(agent_id),
                    "error": "No process data available",
                }
            
            # Get CPU info and system metrics from latest metrics
            system_metrics = await conn.fetchrow(
                """
                SELECT 
                    cpu_data->>'cpu_count' as cpu_count,
                    cpu_data->>'cpu_percent' as system_cpu_percent
                FROM system_metrics 
                WHERE agent_id = $1 
                ORDER BY timestamp DESC 
                LIMIT 1
                """,
                str(agent_id),
            )
            # Default to 1 if not available to avoid division by zero
            cpu_count = int(system_metrics["cpu_count"]) if system_metrics and system_metrics["cpu_count"] else 1
            system_cpu_percent = float(system_metrics["system_cpu_percent"]) if system_metrics and system_metrics["system_cpu_percent"] else None
            
            # Aggregate statistics
            stats = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as total_processes,
                    SUM(num_threads) as total_threads,
                    SUM(num_connections) as total_connections,
                    AVG(cpu_percent) as avg_cpu,
                    SUM(cpu_percent) as total_cpu,
                    AVG(memory_percent) as avg_memory,
                    SUM(memory_percent) as total_memory,
                    SUM(memory_rss) as total_memory_rss
                FROM processes
                WHERE agent_id = $1 AND collected_at = $2
                """,
                str(agent_id),
                latest_time,
            )
            
            # Get process count by user
            by_user = await conn.fetch(
                """
                SELECT username, COUNT(*) as count
                FROM processes
                WHERE agent_id = $1 AND collected_at = $2
                GROUP BY username
                ORDER BY count DESC
                LIMIT 10
                """,
                str(agent_id),
                latest_time,
            )
            
            total_cpu_raw = float(stats["total_cpu"] or 0)
            # Calculate actual CPU utilization (total_cpu / num_cores)
            cpu_utilization = round(total_cpu_raw / cpu_count, 2) if cpu_count > 0 else 0
            
            return {
                "agent_id": str(agent_id),
                "collected_at": latest_time,
                "total_processes": stats["total_processes"],
                "total_threads": stats["total_threads"],
                "total_connections": stats["total_connections"],
                "cpu_count": cpu_count,
                "system_cpu_percent": system_cpu_percent,
                "avg_cpu_percent": round(float(stats["avg_cpu"] or 0), 2),
                "total_cpu_percent": round(total_cpu_raw, 2),
                "cpu_utilization_percent": cpu_utilization,
                "avg_memory_percent": round(float(stats["avg_memory"] or 0), 2),
                "total_memory_percent": round(float(stats["total_memory"] or 0), 2),
                "total_memory_rss_mb": round((stats["total_memory_rss"] or 0) / 1024 / 1024, 2),
                "processes_by_user": [
                    {"username": row["username"], "count": row["count"]}
                    for row in by_user
                ],
            }
    
    except Exception as e:
        logger.error(f"Error retrieving process summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve process summary: {str(e)}")
