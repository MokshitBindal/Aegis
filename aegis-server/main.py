# aegis-server/main.py

import asyncio  # <--- IMPORT ASYNCIO
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- IMPORT THE ANALYSIS LOOP ---
from internal.analysis.correlation import run_analysis_loop
from internal.analysis.incident_aggregator import run_incident_aggregation_loop
from internal.storage.postgres import close_db_pool, init_db_pool
from routers import (
    agent_alerts,
    alerts,
    auth,
    commands,
    device,
    device_status,
    incidents,
    ingest,
    metrics,
    query,
    websocket,
)

# Store the background tasks so we can cancel them on shutdown
background_task = None
aggregation_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global background_task, aggregation_task
    print("Server starting up...")
    await init_db_pool()
    
    # --- START BACKGROUND TASKS ---
    print("Starting background analysis task...")
    background_task = asyncio.create_task(run_analysis_loop())
    
    print("Starting incident aggregation task...")
    aggregation_task = asyncio.create_task(run_incident_aggregation_loop())
    
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
app.include_router(metrics.router, prefix="/api")
app.include_router(agent_alerts.router, prefix="/api")
app.include_router(incidents.router, prefix="/api")
app.include_router(commands.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Aegis SIEM Server is running."}