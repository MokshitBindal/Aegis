"""
API endpoints for ML data export and management.

Allows owners/admins to:
- View export status and thresholds
- Manually trigger exports
- Create labeled datasets for training
- Download exported data
- Configure auto-export schedules

Author: Mokshit Bindal
Date: November 13, 2025
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID
import asyncpg

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from internal.auth.jwt import get_current_user
from internal.ml.data_exporter import get_data_exporter
from models.models import TokenData, UserRole

router = APIRouter(prefix="/api/ml-data", tags=["ml-data"])


class ExportStatusResponse(BaseModel):
    """Response for export status"""
    logs_threshold: int
    metrics_threshold: int
    processes_threshold: int
    commands_threshold: int
    export_directory: str
    last_export_counts: dict
    total_exports: int
    last_export_time: Optional[str] = None
    # Unexported counts (current in database)
    unexported_logs: int = 0
    unexported_metrics: int = 0
    unexported_processes: int = 0
    unexported_commands: int = 0


class LabeledDatasetRequest(BaseModel):
    """Request to export a labeled dataset"""
    device_id: UUID
    label: str
    description: str
    start_time: datetime
    end_time: datetime


class ThresholdUpdateRequest(BaseModel):
    """Request to update export thresholds"""
    logs: Optional[int] = None
    metrics: Optional[int] = None
    processes: Optional[int] = None
    commands: Optional[int] = None


@router.get("/status", response_model=ExportStatusResponse)
async def get_export_status(
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get current export status and thresholds.
    
    **Required role:** owner or admin
    """
    # Only owners and admins can view export status
    if current_user.role not in [UserRole.OWNER.value, UserRole.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can view export status"
        )
    
    exporter = get_data_exporter()
    if not exporter:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data exporter not initialized"
        )
    
    # Count total exported rows across all files
    total_exports = 0
    for file_type in ['logs', 'metrics', 'processes', 'commands']:
        csv_file = exporter.export_dir / f"{file_type}.csv"
        if csv_file.exists():
            try:
                import subprocess
                row_count = int(subprocess.check_output(['wc', '-l', str(csv_file)]).split()[0]) - 1
                total_exports += row_count
            except:
                pass
    
    # Count unexported data (new data since last export)
    from internal.storage.postgres import get_db_pool
    pool = get_db_pool()
    unexported_logs = 0
    unexported_metrics = 0
    unexported_processes = 0
    unexported_commands = 0
    
    try:
        async with pool.acquire() as conn:
            # Count logs (total in DB)
            total_logs = await conn.fetchval("SELECT COUNT(*) FROM logs")
            # Calculate new logs since last export
            unexported_logs = max(0, total_logs - exporter.last_export_counts['logs'])
            
            # Count metrics (total in DB)
            total_metrics = await conn.fetchval("SELECT COUNT(*) FROM system_metrics")
            unexported_metrics = max(0, total_metrics - exporter.last_export_counts['metrics'])
            
            # Count processes from history table (all snapshots for ML)
            try:
                total_processes = await conn.fetchval("SELECT COUNT(*) FROM processes_history")
                unexported_processes = max(0, total_processes - exporter.last_export_counts['processes'])
            except asyncpg.exceptions.UndefinedTableError:
                unexported_processes = 0
            
            # Count commands (total in DB)
            try:
                total_commands = await conn.fetchval("SELECT COUNT(*) FROM commands")
                unexported_commands = max(0, total_commands - exporter.last_export_counts['commands'])
            except asyncpg.exceptions.UndefinedTableError:
                unexported_commands = 0
    except Exception as e:
        print(f"Error counting unexported data: {e}")
    
    return ExportStatusResponse(
        logs_threshold=exporter.thresholds["logs"],
        metrics_threshold=exporter.thresholds["metrics"],
        processes_threshold=exporter.thresholds["processes"],
        commands_threshold=exporter.thresholds["commands"],
        export_directory=str(exporter.export_dir),
        last_export_counts=exporter.last_export_counts,
        total_exports=total_exports,
        last_export_time=exporter.last_export_time.isoformat() if exporter.last_export_time else None,
        unexported_logs=unexported_logs,
        unexported_metrics=unexported_metrics,
        unexported_processes=unexported_processes,
        unexported_commands=unexported_commands
    )


@router.post("/export/manual")
async def trigger_manual_export(
    current_user: TokenData = Depends(get_current_user)
):
    """
    Manually trigger data export (even if thresholds not reached).
    
    Exports data to files and optionally clears old data from live view.
    
    **Required role:** owner or admin
    """
    # Only owners and admins can trigger exports
    if current_user.role not in [UserRole.OWNER.value, UserRole.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can trigger data export"
        )
    
    exporter = get_data_exporter()
    if not exporter:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data exporter not initialized"
        )
    
    try:
        result = await exporter.check_and_export(force=True)
        return {
            "message": "Manual export triggered successfully",
            "export_directory": str(exporter.export_dir),
            "exported_counts": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger export: {str(e)}"
        )


@router.post("/export/labeled")
async def export_labeled_dataset(
    request: LabeledDatasetRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Export a labeled dataset for a specific time range.
    
    Use this to create training datasets for specific scenarios:
    - Normal behavior: label="normal"
    - Attack scenarios: label="brute_force", "privilege_escalation", etc.
    
    **Required role:** owner or admin
    """
    # Only owners and admins can export labeled datasets
    if current_user.role not in [UserRole.OWNER.value, UserRole.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can export labeled datasets"
        )
    
    exporter = get_data_exporter()
    if not exporter:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data exporter not initialized"
        )
    
    try:
        metadata_file = await exporter.export_labeled_dataset(
            device_id=request.device_id,
            label=request.label,
            description=request.description,
            start_time=request.start_time,
            end_time=request.end_time
        )
        
        return {
            "message": f"Labeled dataset '{request.label}' exported successfully",
            "metadata_file": str(metadata_file),
            "export_directory": str(exporter.export_dir / "labeled" / request.label)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export labeled dataset: {str(e)}"
        )


@router.put("/thresholds")
async def update_export_thresholds(
    request: ThresholdUpdateRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Update export thresholds.
    
    **Required role:** owner only
    """
    # Only owners can update thresholds
    if current_user.role != UserRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can update export thresholds"
        )
    
    exporter = get_data_exporter()
    if not exporter:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data exporter not initialized"
        )
    
    # Update thresholds
    if request.logs is not None:
        exporter.thresholds["logs"] = request.logs
    if request.metrics is not None:
        exporter.thresholds["metrics"] = request.metrics
    if request.processes is not None:
        exporter.thresholds["processes"] = request.processes
    if request.commands is not None:
        exporter.thresholds["commands"] = request.commands
    
    return {
        "message": "Export thresholds updated successfully",
        "thresholds": exporter.thresholds
    }


@router.get("/exports")
async def list_exports(
    current_user: TokenData = Depends(get_current_user)
):
    """
    List all available data export files with statistics.
    
    **Required role:** owner or admin
    """
    if current_user.role not in [UserRole.OWNER.value, UserRole.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can view exports"
        )
    
    exporter = get_data_exporter()
    if not exporter:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data exporter not initialized"
        )
    
    exports = []
    
    # List the four main export files
    for file_type in ['logs', 'metrics', 'processes', 'commands']:
        csv_file = exporter.export_dir / f"{file_type}.csv"
        if csv_file.exists():
            # Get file stats
            file_size = csv_file.stat().st_size
            modified_time = datetime.fromtimestamp(csv_file.stat().st_mtime)
            
            # Count rows (excluding header)
            try:
                import subprocess
                row_count = int(subprocess.check_output(['wc', '-l', str(csv_file)]).split()[0]) - 1
            except:
                row_count = "unknown"
            
            exports.append({
                "type": file_type,
                "filename": f"{file_type}.csv",
                "size_bytes": file_size,
                "size_mb": round(file_size / 1024 / 1024, 2),
                "row_count": row_count,
                "last_modified": modified_time.isoformat(),
            })
    
    # List labeled datasets
    labeled_dir = exporter.export_dir / "labeled"
    if labeled_dir.exists():
        for label_dir in sorted(labeled_dir.glob("*"), reverse=True):
            if label_dir.is_dir():
                for csv_file in label_dir.glob("*.csv"):
                    file_size = csv_file.stat().st_size
                    modified_time = datetime.fromtimestamp(csv_file.stat().st_mtime)
                    
                    exports.append({
                        "type": "labeled",
                        "label": label_dir.name,
                        "filename": csv_file.name,
                        "size_bytes": file_size,
                        "size_mb": round(file_size / 1024 / 1024, 2),
                        "last_modified": modified_time.isoformat(),
                    })
    
    return {
        "exports": exports,
        "total": len(exports)
    }


@router.get("/download/{file_type}")
async def download_export_file(
    file_type: str,
    start_date: Optional[str] = Query(None, description="Start date (ISO format: 2025-11-01T00:00:00)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format: 2025-11-13T23:59:59)"),
    agent_id: Optional[str] = Query(None, description="Filter by specific agent ID"),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Download export file with optional filtering by date range and agent.
    
    **file_type**: logs, metrics, processes, or commands
    
    **Examples:**
    - Download all logs: `/api/ml-data/download/logs`
    - Download logs for date range: `/api/ml-data/download/logs?start_date=2025-11-01T00:00:00&end_date=2025-11-13T23:59:59`
    - Download logs for specific agent: `/api/ml-data/download/logs?agent_id=abc-123`
    - Combined filters: `/api/ml-data/download/logs?start_date=2025-11-10T00:00:00&agent_id=abc-123`
    
    **Required role:** owner or admin
    """
    if current_user.role not in [UserRole.OWNER.value, UserRole.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can download exports"
        )
    
    exporter = get_data_exporter()
    if not exporter:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data exporter not initialized"
        )
    
    # Validate file type
    if file_type not in ['logs', 'metrics', 'processes', 'commands']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Must be one of: logs, metrics, processes, commands"
        )
    
    # Find the file
    csv_file = exporter.export_dir / f"{file_type}.csv"
    if not csv_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export file '{file_type}.csv' not found. No data exported yet."
        )
    
    # If no filters, return the whole file
    if not start_date and not end_date and not agent_id:
        return FileResponse(
            path=str(csv_file),
            media_type="text/csv",
            filename=f"{file_type}_export.csv"
        )
    
    # Apply filters using pandas
    try:
        import pandas as pd
        import io
        
        # Read the CSV file
        df = pd.read_csv(csv_file)
        
        # Apply agent filter
        if agent_id:
            df = df[df['agent_id'] == agent_id]
        
        # Apply date filters
        timestamp_col = 'timestamp' if 'timestamp' in df.columns else 'collected_at'
        if timestamp_col in df.columns:
            df[timestamp_col] = pd.to_datetime(df[timestamp_col])
            
            if start_date:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                df = df[df[timestamp_col] >= start_dt]
            
            if end_date:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                df = df[df[timestamp_col] <= end_dt]
        
        # Check if any data remains after filtering
        if df.empty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No data found matching the specified filters"
            )
        
        # Create temporary file with filtered data
        from tempfile import NamedTemporaryFile
        temp_file = NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        df.to_csv(temp_file.name, index=False)
        temp_file.close()
        
        # Generate filename with filter info
        filename_parts = [file_type]
        if agent_id:
            filename_parts.append(f"agent_{agent_id[:8]}")
        if start_date:
            filename_parts.append(f"from_{start_date[:10]}")
        if end_date:
            filename_parts.append(f"to_{end_date[:10]}")
        filename = "_".join(filename_parts) + ".csv"
        
        return FileResponse(
            path=temp_file.name,
            media_type="text/csv",
            filename=filename,
            background=None  # Keep file until download completes
        )
        
    except Exception as e:
        print(f"Error filtering export file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to filter export data: {str(e)}"
        )
