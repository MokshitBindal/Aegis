# aegis-server/routers/websocket.py

from fastapi import APIRouter, WebSocket, Depends, WebSocketDisconnect
from internal.auth.jwt import get_current_user
from models.models import TokenData

router = APIRouter()

# This is a very simple in-memory store for active connections
# In a production multi-worker setup, we'd use Redis Pub/Sub
active_connections: dict[int, WebSocket] = {} # user_id: WebSocket

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    # We can't use the standard Depends(get_current_user) because
    # WebSockets don't use standard headers. We'll authenticate
    # via a token sent as the first message.
):
    """
    Main WebSocket endpoint for real-time dashboard updates.
    """
    await websocket.accept()
    user_id = None
    try:
        # --- WebSocket Authentication ---
        # 1. Wait for the client to send its JWT
        auth_data = await websocket.receive_json()
        token = auth_data.get("token")

        if not token:
            await websocket.close(code=1008, reason="Token not provided")
            return

        # 2. Validate the token
        try:
            # We have to manually implement auth dependency logic here
            # (This is a simplified version for brevity)
            from internal.auth.jwt import jwt, settings, JWTError
            from internal.storage.postgres import get_db_pool
            from .device import get_user_by_email

            payload = jwt.decode(
                token,
                settings.jwt.secret_key,
                algorithms=[settings.jwt.algorithm]
            )
            email: str = payload.get("sub")
            if email is None:
                raise JWTError()

            # 3. Find the user
            pool = get_db_pool()
            async with pool.acquire() as conn:
                user = await get_user_by_email(email, conn)
                if not user:
                    raise JWTError()
                user_id = user.id

        except Exception:
            await websocket.close(code=1008, reason="Invalid token")
            return

        # --- If Auth is Successful ---
        await websocket.send_json({"message": "WebSocket connection successful."})
        active_connections[user_id] = websocket

        # 4. Keep the connection alive
        while True:
            # We just wait for messages (or for the client to disconnect)
            await websocket.receive_text()

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for user {user_id}")
        if user_id in active_connections:
            del active_connections[user_id]
    except Exception as e:
        print(f"WebSocket error: {e}")
        if user_id in active_connections:
            del active_connections[user_id]
        await websocket.close()

# We will call this function from other parts of our app
# (e.g., from /api/ingest in a future module)
async def push_update_to_user(user_id: int, message: dict):
    """
    Pushes a JSON message to a specific user's WebSocket.
    """
    if user_id in active_connections:
        try:
            await active_connections[user_id].send_json(message)
        except Exception as e:
            print(f"Failed to push WS message: {e}")
            # Connection might be dead, remove it
            del active_connections[user_id]