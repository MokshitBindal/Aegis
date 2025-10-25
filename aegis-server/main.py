# aegis-server/main.py

from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware # <--- 1. IMPORT THIS

from internal.storage.postgres import init_db_pool, close_db_pool
from routers import ingest, auth, device, websocket

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server starting up...")
    await init_db_pool()
    yield
    print("Server shutting down...")
    await close_db_pool()

app = FastAPI(
    title="Aegis SIEM Server",
    description="The central API and ingestion server for Aegis SIEM.",
    version="0.1.0",
    lifespan=lifespan
)

# --- 2. ADD THIS MIDDLEWARE BLOCK ---
# This is the "permission slip" for our browser
app.add_middleware(
    CORSMiddleware,
    # This is the URL of our React app
    allow_origins=["http://localhost:5173"], 
    # Allow credentials (like cookies, though we use tokens)
    allow_credentials=True, 
    # Allow all HTTP methods
    allow_methods=["*"],
    # Allow all headers (including our 'Authorization' header)
    allow_headers=["*"],
)

# --- Include Routers ---
app.include_router(ingest.router, prefix="/api")
app.include_router(auth.router, prefix="/auth")
app.include_router(device.router, prefix="/api")
app.include_router(websocket.router) 

@app.get("/")
async def root():
    return {"message": "Aegis SIEM Server is running."}