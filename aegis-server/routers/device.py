# aegis-server/routers/device.py

import secrets
from datetime import UTC, datetime, timedelta

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request, status

from internal.auth.jwt import get_current_user

# --- MODIFICATION: Import verify_password and permissions ---
from internal.auth.permissions import check_device_ownership
from internal.auth.security import get_password_hash, verify_password
from internal.storage.postgres import get_db_pool
from models.models import Device, DeviceRegister, Invitation, TokenData, UserInDB, UserRole

router = APIRouter()

# --- Helper function to get user from DB ---
async def get_user_by_email(email: str, conn) -> UserInDB | None:
    """Helper to fetch a user by email."""
    user_record = await conn.fetchrow("SELECT * FROM users WHERE email = $1", email)
    if user_record:
        return UserInDB.model_validate(dict(user_record))
    return None


@router.post("/device/create-invitation", response_model=Invitation)
async def create_invitation(
    request: Request,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Generates a new, single-use device invitation token for the
    currently authenticated user.
    """
    pool = get_db_pool()
    
    # 1. Generate a cryptographically secure token
    token = secrets.token_urlsafe(32)
    
    # 2. Hash the token for secure storage (just like a password)
    token_hash = get_password_hash(token)
    
    # 3. Set expiration (e.g., 1 hour from now)
    expires_at = datetime.now(UTC) + timedelta(hours=1)
    
    try:
        async with pool.acquire() as conn:
            # 4. Get the user's database ID from their email (in the JWT)
            user = await get_user_by_email(current_user.email, conn)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # 5. Store the *hashed* token in the invitations table
            sql = """
            INSERT INTO invitations (user_id, token_hash, expires_at)
            VALUES ($1, $2, $3)
            """
            await conn.execute(sql, user.id, token_hash, expires_at)
            
            # 6. Return the *raw, unhashed* token to the user ONCE.
            return Invitation(token=token, expires_at=expires_at)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create token: {e}")


@router.post(
    "/device/register",
    response_model=Device,
    status_code=status.HTTP_201_CREATED,
)
async def register_device(
    device_data: DeviceRegister,
    request: Request
):
    """
    Registers a new agent. This endpoint is called by the agent,
    so it is *not* authenticated with a JWT. It is authenticated
    by the invitation token.
    """
    pool = get_db_pool()
    token = device_data.token
    
    try:
        async with pool.acquire() as conn, conn.transaction():
            
            # 1. Find all non-expired invitations
            sql_find = "SELECT * FROM invitations WHERE expires_at > $1"
            invites = await conn.fetch(sql_find, datetime.now(UTC))
            
            valid_invite = None
            for invite in invites:
                # 2. Verify the token - returns False if hash is invalid
                try:
                    if verify_password(token, invite['token_hash']):
                        valid_invite = invite
                        break
                except Exception as e:
                    # Skip this invitation if verification fails (e.g., wrong hash format)
                    print(f"Skipping invitation {invite['id']}: {e}")
                    continue
                    
            if not valid_invite:
                raise HTTPException(
                    status_code=400, detail="Invalid or expired token"
                )
            
            # 3. Delete the invitation (single-use)
            await conn.execute(
                "DELETE FROM invitations WHERE id = $1", valid_invite['id']
            )
                
            # 4. Create the device
            sql_create = """
            INSERT INTO devices (user_id, agent_id, hostname, name)
            VALUES ($1, $2, $3, $4)
            RETURNING id, agent_id, name, hostname, registered_at
            """
            new_device_record = await conn.fetchrow(
                sql_create,
                valid_invite['user_id'],
                device_data.agent_id,
                device_data.hostname,
                device_data.name
            )
                
            return Device.model_validate(dict(new_device_record))

    except asyncpg.exceptions.UniqueViolationError:
        raise HTTPException(
            status_code=400, detail="This agent UUID is already registered."
        )
    except Exception as e:
        import traceback
        print(f"Error during device registration: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {e}")
    

@router.get("/devices", response_model=list[Device])
async def list_devices(
    request: Request,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Lists devices based on user role:
    - Device User: Only their own devices
    - Admin: All devices
    - Owner: All devices
    """
    pool = get_db_pool()
    try:
        async with pool.acquire() as conn:
            # Owner and Admin can see all devices
            if current_user.role in [UserRole.OWNER, UserRole.ADMIN]:
                sql = "SELECT * FROM devices ORDER BY registered_at DESC"
                device_records = await conn.fetch(sql)
            else:
                # Device User can only see their own devices
                sql = "SELECT * FROM devices WHERE user_id = $1 ORDER BY registered_at DESC"
                device_records = await conn.fetch(sql, current_user.user_id)
            
            # Validate and return the list
            return [Device.model_validate(dict(record)) for record in device_records]
            
    except Exception as e:
        print(f"Error listing devices: {e}")
        raise HTTPException(status_code=500, detail="Failed to list devices")


@router.post("/device/assign")
async def assign_device(
    device_id: int,
    user_id: int,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Assign a device to a specific user (admin or device_user).
    Only Owner can assign devices.
    
    **Args:**
        device_id: ID of the device to assign
        user_id: ID of the user to assign the device to
    
    **Returns:**
        Success message with assignment details
    """
    # Only Owner can assign devices
    if current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=403,
            detail="Only Owner can assign devices to users"
        )
    
    pool = get_db_pool()
    try:
        async with pool.acquire() as conn:
            # Check if device exists
            device = await conn.fetchrow(
                "SELECT * FROM devices WHERE id = $1",
                device_id
            )
            if not device:
                raise HTTPException(status_code=404, detail="Device not found")
            
            # Check if user exists
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1",
                user_id
            )
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Update device ownership
            await conn.execute(
                "UPDATE devices SET user_id = $1 WHERE id = $2",
                user_id,
                device_id
            )
            
            return {
                "message": "Device assigned successfully",
                "device_id": device_id,
                "device_name": device["name"],
                "user_id": user_id,
                "user_email": user["email"]
            }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error assigning device: {e}")
        raise HTTPException(status_code=500, detail="Failed to assign device")


@router.get("/device/unassigned")
async def get_unassigned_devices(
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get all devices that are not assigned to any user.
    Only Owner can view unassigned devices.
    
    **Returns:**
        List of unassigned devices
    """
    # Only Owner can view unassigned devices
    if current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=403,
            detail="Only Owner can view unassigned devices"
        )
    
    pool = get_db_pool()
    try:
        async with pool.acquire() as conn:
            devices = await conn.fetch(
                "SELECT * FROM devices WHERE user_id IS NULL ORDER BY registered_at DESC"
            )
            return [Device.model_validate(dict(record)) for record in devices]
    
    except Exception as e:
        print(f"Error fetching unassigned devices: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch unassigned devices")


@router.delete("/device/{device_id}/unassign")
async def unassign_device(
    device_id: int,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Unassign a device from its current user.
    Only Owner can unassign devices.
    
    **Args:**
        device_id: ID of the device to unassign
    
    **Returns:**
        Success message
    """
    # Only Owner can unassign devices
    if current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=403,
            detail="Only Owner can unassign devices"
        )
    
    pool = get_db_pool()
    try:
        async with pool.acquire() as conn:
            # Check if device exists
            device = await conn.fetchrow(
                "SELECT * FROM devices WHERE id = $1",
                device_id
            )
            if not device:
                raise HTTPException(status_code=404, detail="Device not found")
            
            # Unassign device
            await conn.execute(
                "UPDATE devices SET user_id = NULL WHERE id = $1",
                device_id
            )
            
            return {
                "message": "Device unassigned successfully",
                "device_id": device_id,
                "device_name": device["name"]
            }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error unassigning device: {e}")
        raise HTTPException(status_code=500, detail="Failed to unassign device")