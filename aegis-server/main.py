# aegis-server/main.py

import asyncio # <--- IMPORT ASYNCIO
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from internal.storage.postgres import init_db_pool, close_db_pool
# --- IMPORT THE ANALYSIS LOOP ---
from internal.analysis.correlation import run_analysis_loop
from routers import ingest, auth, device, websocket, query, alerts

# Store the background task so we can cancel it on shutdown
background_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global background_task
    print("Server starting up...")
    await init_db_pool()
    
    # --- START BACKGROUND TASK ---
    print("Starting background analysis task...")
    background_task = asyncio.create_task(run_analysis_loop())
    
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
app.include_router(websocket.router)
app.include_router(query.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Aegis SIEM Server is running."}