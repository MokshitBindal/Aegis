# aegis-server/main.py

from fastapi import FastAPI
from contextlib import asynccontextmanager

from internal.storage.postgres import init_db_pool, close_db_pool
from routers import ingest, auth  # <--- IMPORT AUTH

# Use the new 'lifespan' context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    """
    print("Server starting up...")
    await init_db_pool()
    
    yield  # This is where the application runs
    
    print("Server shutting down...")
    await close_db_pool()


# Create the main FastAPI application instance
app = FastAPI(
    title="Aegis SIEM Server",
    description="The central API and ingestion server for Aegis SIEM.",
    version="0.1.0",
    lifespan=lifespan
)

# --- Include Routers ---
app.include_router(ingest.router, prefix="/api")
app.include_router(auth.router, prefix="/auth") # <--- ADD AUTH ROUTER

@app.get("/")
async def root():
    """
    Root endpoint.
    Provides a simple status check.
    """
    return {"message": "Aegis SIEM Server is running."}