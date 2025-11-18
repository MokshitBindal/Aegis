# aegis-server/main.py

import asyncio  # <--- IMPORT ASYNCIO
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- IMPORT THE ANALYSIS LOOP ---
from internal.analysis.correlation import run_analysis_loop
from internal.analysis.incident_aggregator import run_incident_aggregation_loop
from internal.ml.data_exporter import init_data_exporter, get_data_exporter
from internal.ml.ml_detector import init_ml_service, run_ml_detection_loop
from internal.storage.postgres import close_db_pool, init_db_pool
from internal.utils.cleanup_task import run_daily_cleanup
from routers import (
    agent_alerts,
    alerts,
    alert_triage,
    auth,
    baselines,
    commands,
    device,
    device_status,
    incidents,
    ingest,
    metrics,
    ml_data,
    ml_detection,
    processes,
    query,
    user_management,
    websocket,
)

# Store the background tasks so we can cancel them on shutdown
background_task = None
aggregation_task = None
cleanup_task = None
data_export_task = None
ml_detection_task = None


async def run_data_export_loop():
    """Background task to export data for ML training"""
    print("Starting data export loop for ML training...")
    await asyncio.sleep(60)  # Wait 1 minute for server to be ready
    
    exporter = get_data_exporter()
    if not exporter:
        print("Data exporter not initialized, skipping data export loop")
        return
    
    while True:
        try:
            await exporter.check_and_export()
            await asyncio.sleep(300)  # Check every 5 minutes
        except asyncio.CancelledError:
            print("Data export loop cancelled")
            raise
        except Exception as e:
            print(f"Error in data export loop: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying

@asynccontextmanager
async def lifespan(app: FastAPI):
    global background_task, aggregation_task, cleanup_task, data_export_task, ml_detection_task
    print("Server starting up...")
    await init_db_pool()
    
    # Initialize data exporter for ML training
    from internal.storage.postgres import get_db_pool
    pool = get_db_pool()
    init_data_exporter(pool)
    
    # Initialize ML detection service
    init_ml_service(pool)
    
    # Clean up old invitation tokens with invalid hash format
    try:
        pool = get_db_pool()
        async with pool.acquire() as conn:
            # Delete invitations older than 7 days (likely have old hash format)
            from datetime import datetime, timedelta, UTC
            week_ago = datetime.now(UTC) - timedelta(days=7)
            result = await conn.execute(
                "DELETE FROM invitations WHERE expires_at < $1",
                week_ago
            )
            if result != "DELETE 0":
                print(f"Cleaned up old invitation tokens: {result}")
    except Exception as e:
        print(f"Warning: Could not clean old invitations: {e}")
    
    # --- START BACKGROUND TASKS ---
    print("Starting background analysis task...")
    background_task = asyncio.create_task(run_analysis_loop())
    
    print("Starting incident aggregation task...")
    aggregation_task = asyncio.create_task(run_incident_aggregation_loop())
    
    print("Starting daily data retention cleanup task...")
    cleanup_task = asyncio.create_task(run_daily_cleanup())
    
    print("Starting data export task for ML training...")
    data_export_task = asyncio.create_task(run_data_export_loop())
    
    print("Starting ML anomaly detection task...")
    ml_detection_task = asyncio.create_task(run_ml_detection_loop())
    
    yield  # Application runs here
    
    # --- SHUTDOWN ---
    print("Server shutting down...")
    if background_task:
        print("Stopping background analysis task...")
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            print("Background analysis task cancelled.")
    
    if aggregation_task:
        print("Stopping incident aggregation task...")
        aggregation_task.cancel()
        try:
            await aggregation_task
        except asyncio.CancelledError:
            print("Incident aggregation task cancelled.")
    
    if cleanup_task:
        print("Stopping cleanup task...")
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            print("Cleanup task cancelled.")
    
    if data_export_task:
        print("Stopping data export task...")
        data_export_task.cancel()
        try:
            await data_export_task
        except asyncio.CancelledError:
            print("Data export task cancelled")
    
    if ml_detection_task:
        print("Stopping ML detection task...")
        ml_detection_task.cancel()
        try:
            await ml_detection_task
        except asyncio.CancelledError:
            print("ML detection task cancelled")
            
    await close_db_pool()

app = FastAPI(
    title="Aegis SIEM Server",
    description="The central API and ingestion server for Aegis SIEM.",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include Routers ---
app.include_router(ingest.router, prefix="/api")
app.include_router(auth.router, prefix="/auth")
app.include_router(baselines.router, prefix="/api")
app.include_router(device.router, prefix="/api")
app.include_router(device_status.router, prefix="/api")
app.include_router(websocket.router)
app.include_router(query.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(alert_triage.router, prefix="/api")
app.include_router(user_management.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")
app.include_router(agent_alerts.router, prefix="/api")
app.include_router(incidents.router, prefix="/api")
app.include_router(commands.router, prefix="/api")
app.include_router(processes.router)
app.include_router(ml_data.router)
app.include_router(ml_detection.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Aegis SIEM Server is running."}

@app.get("/health")
async def health_check():
    """Health check endpoint for deployment services"""
    return {
        "status": "healthy",
        "service": "aegis-siem-server",
        "version": "1.0.0"
    }