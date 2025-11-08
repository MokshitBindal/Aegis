# aegis-server/main.py

import asyncio  # <--- IMPORT ASYNCIO
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- IMPORT THE ANALYSIS LOOP ---
from internal.analysis.correlation import run_analysis_loop
from internal.analysis.incident_aggregator import run_incident_aggregation_loop
from internal.storage.postgres import close_db_pool, init_db_pool
from internal.utils.cleanup_task import run_daily_cleanup
from routers import (
    agent_alerts,
    alerts,
    alert_triage,
    auth,
    commands,
    device,
    device_status,
    incidents,
    ingest,
    metrics,
    processes,
    query,
    user_management,
    websocket,
)

# Store the background tasks so we can cancel them on shutdown
background_task = None
aggregation_task = None
cleanup_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global background_task, aggregation_task, cleanup_task
    print("Server starting up...")
    await init_db_pool()
    
    # Clean up old invitation tokens with invalid hash format
    from internal.storage.postgres import get_db_pool
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

@app.get("/")
async def root():
    return {"message": "Aegis SIEM Server is running."}