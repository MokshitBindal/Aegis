"""
API endpoints for device behavioral baselines.

Author: Mokshit Bindal
Date: November 8, 2025
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from internal.auth.jwt import get_current_user
from internal.storage.postgres import get_db_pool
from internal.analysis.baseline_engine import BaselineLearner
from models.models import TokenData, UserRole

router = APIRouter(prefix="/api/baselines", tags=["baselines"])
logger = logging.getLogger(__name__)


@router.post("/learn/{device_id}")
async def learn_baseline(
    device_id: UUID,
    duration_days: int = Query(28, ge=7, le=90, description="Days of data to analyze"),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Learn behavioral baseline for a specific device.
    
    **Required role:** owner or admin
    
    Args:
        device_id: UUID of the device
        duration_days: Number of days of historical data to analyze (7-90)
    
    Returns:
        Learned baseline profile
    """
    # Only owners and admins can trigger baseline learning
    if current_user.role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        pool = get_db_pool()
        async with pool.acquire() as conn:
            # Check if device exists and user has access
            device = await conn.fetchrow(
                """
                SELECT d.agent_id, d.hostname
                FROM devices d
                LEFT JOIN device_assignments da ON d.agent_id = da.device_id
                WHERE d.agent_id = $1
                AND (da.user_id = $2 OR $3 IN ('owner', 'admin'))
                """,
                device_id, current_user.id, current_user.role
            )
            
            if not device:
                raise HTTPException(status_code=404, detail="Device not found or access denied")
            
            # Learn baseline (this will take a while)
            logger.info(f"Starting baseline learning for device {device_id} ({device['hostname']})")
            
            # TODO: This should be done asynchronously in production
            # For now, we'll do it synchronously
            from internal.analysis.baseline_engine import train_baseline_for_device
            baseline = await train_baseline_for_device(device_id, duration_days)
            
            # Store each baseline type in database
            baseline_types = ['process_baseline', 'metrics_baseline', 'activity_baseline', 'command_baseline']
            
            for baseline_type in baseline_types:
                if baseline_type in baseline and baseline[baseline_type]:
                    # Check if baseline already exists
                    existing = await conn.fetchrow(
                        """
                        SELECT id, version FROM device_baselines
                        WHERE device_id = $1 AND baseline_type = $2
                        ORDER BY version DESC
                        LIMIT 1
                        """,
                        device_id, baseline_type.replace('_baseline', '')
                    )
                    
                    new_version = (existing['version'] + 1) if existing else 1
                    
                    # Insert new baseline
                    await conn.execute(
                        """
                        INSERT INTO device_baselines (
                            device_id, baseline_type, baseline_data, 
                            learned_at, duration_days, version
                        )
                        VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        device_id,
                        baseline_type.replace('_baseline', ''),
                        baseline[baseline_type],
                        datetime.fromisoformat(baseline['learned_at']),
                        duration_days,
                        new_version
                    )
            
            # Store full baseline
            await conn.execute(
                """
                INSERT INTO device_baselines (
                    device_id, baseline_type, baseline_data, 
                    learned_at, duration_days, version
                )
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (device_id, baseline_type, version)
                DO UPDATE SET baseline_data = $3, updated_at = CURRENT_TIMESTAMP
                """,
                device_id,
                'full',
                baseline,
                datetime.fromisoformat(baseline['learned_at']),
                duration_days,
                1
            )
            
            logger.info(f"Baseline learning complete for device {device_id}")
            
            return {
                "success": True,
                "device_id": str(device_id),
                "hostname": device['hostname'],
                "baseline": baseline,
                "message": f"Learned baseline from {duration_days} days of data"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to learn baseline for device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to learn baseline: {str(e)}")


@router.get("/{device_id}")
async def get_baseline(
    device_id: UUID,
    baseline_type: Optional[str] = Query(None, description="Type: process, metrics, activity, command, or full"),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get learned baseline for a device.
    
    Args:
        device_id: UUID of the device
        baseline_type: Optional filter by baseline type
    
    Returns:
        Baseline data
    """
    try:
        pool = get_db_pool()
        async with pool.acquire() as conn:
            # Check device access
            device = await conn.fetchrow(
                """
                SELECT d.agent_id, d.hostname
                FROM devices d
                LEFT JOIN device_assignments da ON d.agent_id = da.device_id
                WHERE d.agent_id = $1
                AND (da.user_id = $2 OR $3 IN ('owner', 'admin'))
                """,
                device_id, current_user.id, current_user.role
            )
            
            if not device:
                raise HTTPException(status_code=404, detail="Device not found or access denied")
            
            # Get baseline
            if baseline_type:
                baseline = await conn.fetchrow(
                    """
                    SELECT * FROM device_baselines
                    WHERE device_id = $1 AND baseline_type = $2
                    ORDER BY version DESC
                    LIMIT 1
                    """,
                    device_id, baseline_type
                )
                
                if not baseline:
                    raise HTTPException(status_code=404, detail=f"No {baseline_type} baseline found for device")
                
                return {
                    "device_id": str(device_id),
                    "hostname": device['hostname'],
                    "baseline_type": baseline['baseline_type'],
                    "baseline_data": baseline['baseline_data'],
                    "learned_at": baseline['learned_at'].isoformat(),
                    "duration_days": baseline['duration_days'],
                    "version": baseline['version']
                }
            else:
                # Get all baselines
                baselines = await conn.fetch(
                    """
                    SELECT DISTINCT ON (baseline_type)
                        baseline_type, baseline_data, learned_at, duration_days, version
                    FROM device_baselines
                    WHERE device_id = $1
                    ORDER BY baseline_type, version DESC
                    """,
                    device_id
                )
                
                if not baselines:
                    raise HTTPException(status_code=404, detail="No baselines found for device")
                
                return {
                    "device_id": str(device_id),
                    "hostname": device['hostname'],
                    "baselines": [
                        {
                            "baseline_type": b['baseline_type'],
                            "baseline_data": b['baseline_data'],
                            "learned_at": b['learned_at'].isoformat(),
                            "duration_days": b['duration_days'],
                            "version": b['version']
                        }
                        for b in baselines
                    ]
                }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get baseline for device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get baseline: {str(e)}")


@router.get("/")
async def list_all_baselines(
    current_user: TokenData = Depends(get_current_user)
):
    """
    List all learned baselines (for owners/admins).
    
    Returns:
        List of all baselines
    """
    # Only owners and admins can see all baselines
    if current_user.role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        pool = get_db_pool()
        async with pool.acquire() as conn:
            baselines = await conn.fetch(
                """
                SELECT DISTINCT ON (db.device_id, db.baseline_type)
                    db.device_id,
                    d.hostname,
                    db.baseline_type,
                    db.learned_at,
                    db.duration_days,
                    db.version
                FROM device_baselines db
                JOIN devices d ON db.device_id = d.agent_id
                ORDER BY db.device_id, db.baseline_type, db.version DESC
                """
            )
            
            # Group by device
            devices_baselines = {}
            for b in baselines:
                device_id = str(b['device_id'])
                if device_id not in devices_baselines:
                    devices_baselines[device_id] = {
                        "device_id": device_id,
                        "hostname": b['hostname'],
                        "baselines": []
                    }
                
                devices_baselines[device_id]['baselines'].append({
                    "baseline_type": b['baseline_type'],
                    "learned_at": b['learned_at'].isoformat(),
                    "duration_days": b['duration_days'],
                    "version": b['version']
                })
            
            return {
                "total_devices": len(devices_baselines),
                "devices": list(devices_baselines.values())
            }
    
    except Exception as e:
        logger.error(f"Failed to list baselines: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list baselines: {str(e)}")


@router.delete("/{device_id}")
async def delete_baseline(
    device_id: UUID,
    baseline_type: Optional[str] = Query(None, description="Type to delete, or all if not specified"),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Delete baseline(s) for a device.
    
    **Required role:** owner or admin
    
    Args:
        device_id: UUID of the device
        baseline_type: Optional specific type to delete
    
    Returns:
        Deletion confirmation
    """
    # Only owners and admins can delete baselines
    if current_user.role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        pool = get_db_pool()
        async with pool.acquire() as conn:
            if baseline_type:
                result = await conn.execute(
                    "DELETE FROM device_baselines WHERE device_id = $1 AND baseline_type = $2",
                    device_id, baseline_type
                )
            else:
                result = await conn.execute(
                    "DELETE FROM device_baselines WHERE device_id = $1",
                    device_id
                )
            
            deleted_count = int(result.split()[-1])
            
            return {
                "success": True,
                "device_id": str(device_id),
                "baseline_type": baseline_type or "all",
                "deleted_count": deleted_count
            }
    
    except Exception as e:
        logger.error(f"Failed to delete baseline for device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete baseline: {str(e)}")
