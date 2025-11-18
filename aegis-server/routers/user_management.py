# aegis-server/routers/user_management.py

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from internal.auth.jwt import get_current_user
from internal.auth.permissions import can_create_user, can_modify_user
from internal.auth.security import get_password_hash
from internal.storage.postgres import get_db_pool
from models.models import (
    TokenData,
    UserCreateByOwner,
    UserResponse,
    UserRole,
    UserUpdate,
)

router = APIRouter()


@router.post("/admin/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreateByOwner,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Create a new user (Owner only).
    Owner can create Admin and Device User accounts.
    """
    # Check if current user is Owner
    if current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Owner can create users"
        )
    
    # Check if Owner can create this role
    if not can_create_user(current_user.role, user_data.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot create user with role: {user_data.role.value}"
        )
    
    # Prevent creating another Owner
    if user_data.role == UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create additional Owner accounts"
        )
    
    pool = get_db_pool()
    hashed_pass = get_password_hash(user_data.password)
    
    try:
        async with pool.acquire() as conn:
            new_user = await conn.fetchrow(
                """
                INSERT INTO users (email, hashed_pass, role, created_by, is_active)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, email, role, is_active, created_by, last_login
                """,
                user_data.email,
                hashed_pass,
                user_data.role.value,
                current_user.user_id,
                True
            )
            
            if not new_user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create user"
                )
            
            return UserResponse.model_validate(dict(new_user))
            
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email already exists"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@router.get("/admin/users", response_model=List[UserResponse])
async def list_users(
    current_user: TokenData = Depends(get_current_user),
    role: str | None = None,
    is_active: bool | None = None
):
    """
    List all users (Owner only).
    Optional filters: role, is_active status.
    """
    # Check if current user is Owner
    if current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Owner can list all users"
        )
    
    pool = get_db_pool()
    
    # Build query dynamically based on filters
    conditions = []
    params = []
    param_count = 1
    
    if role:
        conditions.append(f"role = ${param_count}")
        params.append(role)
        param_count += 1
    
    if is_active is not None:
        conditions.append(f"is_active = ${param_count}")
        params.append(is_active)
        param_count += 1
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    query = f"""
        SELECT id, email, role, is_active, created_by, last_login
        FROM users
        {where_clause}
        ORDER BY created_at DESC
    """
    
    try:
        async with pool.acquire() as conn:
            users = await conn.fetch(query, *params)
            return [UserResponse.model_validate(dict(u)) for u in users]
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list users: {str(e)}"
        )


@router.get("/admin/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get details of a specific user (Owner only).
    """
    # Check if current user is Owner
    if current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Owner can view user details"
        )
    
    pool = get_db_pool()
    
    try:
        async with pool.acquire() as conn:
            user = await conn.fetchrow(
                """
                SELECT id, email, role, is_active, created_by, last_login
                FROM users
                WHERE id = $1
                """,
                user_id
            )
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            return UserResponse.model_validate(dict(user))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user: {str(e)}"
        )


@router.put("/admin/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    update_data: UserUpdate,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Update user role or active status (Owner only).
    Cannot modify Owner accounts.
    """
    # Check if current user is Owner
    if current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Owner can update users"
        )
    
    # Cannot update self
    if user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update your own account"
        )
    
    pool = get_db_pool()
    
    try:
        async with pool.acquire() as conn:
            # Get current user info
            target_user = await conn.fetchrow(
                "SELECT id, email, role FROM users WHERE id = $1",
                user_id
            )
            
            if not target_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Check if Owner can modify this user
            if not can_modify_user(current_user.role, target_user['role']):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot modify Owner accounts"
                )
            
            # Prevent changing to Owner role
            if update_data.role == UserRole.OWNER:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot promote user to Owner role"
                )
            
            # Build update query dynamically
            update_fields = []
            params = []
            param_count = 1
            
            if update_data.role is not None:
                update_fields.append(f"role = ${param_count}")
                params.append(update_data.role.value)
                param_count += 1
            
            if update_data.is_active is not None:
                update_fields.append(f"is_active = ${param_count}")
                params.append(update_data.is_active)
                param_count += 1
            
            if not update_fields:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No fields to update"
                )
            
            # Add user_id as last parameter
            params.append(user_id)
            
            query = f"""
                UPDATE users
                SET {', '.join(update_fields)}
                WHERE id = ${param_count}
                RETURNING id, email, role, is_active, created_by, last_login
            """
            
            updated_user = await conn.fetchrow(query, *params)
            
            if not updated_user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update user"
                )
            
            return UserResponse.model_validate(dict(updated_user))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )


@router.delete("/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Delete a user account (Owner only).
    This is a soft delete - sets is_active to false.
    Cannot delete Owner accounts.
    """
    # Check if current user is Owner
    if current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Owner can delete users"
        )
    
    # Cannot delete self
    if user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    pool = get_db_pool()
    
    try:
        async with pool.acquire() as conn:
            # Get target user
            target_user = await conn.fetchrow(
                "SELECT id, role FROM users WHERE id = $1",
                user_id
            )
            
            if not target_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Check if Owner can modify this user
            if not can_modify_user(current_user.role, target_user['role']):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot delete Owner accounts"
                )
            
            # Soft delete by setting is_active to false
            await conn.execute(
                "UPDATE users SET is_active = false WHERE id = $1",
                user_id
            )
            
            # Also unassign any alerts
            await conn.execute(
                """
                UPDATE alert_assignments 
                SET status = 'unassigned'
                WHERE assigned_to = $1 AND status NOT IN ('resolved', 'escalated')
                """,
                user_id
            )
            
            return None
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )


@router.get("/users/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get current user's own information.
    Available to all authenticated users.
    """
    pool = get_db_pool()
    
    try:
        async with pool.acquire() as conn:
            user = await conn.fetchrow(
                """
                SELECT id, email, role, is_active, created_by, last_login
                FROM users
                WHERE id = $1
                """,
                current_user.user_id
            )
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            return UserResponse.model_validate(dict(user))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user info: {str(e)}"
        )
