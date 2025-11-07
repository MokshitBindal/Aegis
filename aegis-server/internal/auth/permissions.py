# aegis-server/internal/auth/permissions.py

from functools import wraps
from typing import Callable

from fastapi import HTTPException, status
from models.models import UserRole, TokenData


def require_role(*allowed_roles: UserRole):
    """
    Decorator to enforce role-based access control on endpoints.
    
    Usage:
        @require_role(UserRole.OWNER)
        async def owner_only_endpoint(current_user: TokenData = Depends(get_current_user)):
            ...
        
        @require_role(UserRole.OWNER, UserRole.ADMIN)
        async def admin_or_owner_endpoint(current_user: TokenData = Depends(get_current_user)):
            ...
    
    Args:
        *allowed_roles: One or more UserRole values that are allowed to access the endpoint
    
    Raises:
        HTTPException: 403 Forbidden if user's role is not in allowed_roles
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs (injected by get_current_user dependency)
            current_user: TokenData = kwargs.get("current_user")
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated"
                )
            
            if current_user.role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required role: {', '.join([r.value for r in allowed_roles])}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def check_device_ownership(user: TokenData, device_user_id: int | None) -> bool:
    """
    Check if a user has permission to access a device.
    
    Rules:
    - Owner and Admin can access all devices
    - Device User can only access their own devices
    
    Args:
        user: Current user's token data
        device_user_id: The user_id associated with the device
    
    Returns:
        True if user can access the device, False otherwise
    """
    if user.role in [UserRole.OWNER, UserRole.ADMIN]:
        return True
    
    return user.user_id == device_user_id


def check_alert_access(user: TokenData, alert_assigned_to: int | None) -> bool:
    """
    Check if a user has permission to access an alert.
    
    Rules:
    - Owner can access all alerts
    - Admin can access alerts assigned to them or unassigned alerts
    - Device User cannot access alerts directly (only through their devices)
    
    Args:
        user: Current user's token data
        alert_assigned_to: The user_id the alert is assigned to (None if unassigned)
    
    Returns:
        True if user can access the alert, False otherwise
    """
    if user.role == UserRole.OWNER:
        return True
    
    if user.role == UserRole.ADMIN:
        # Admins can access unassigned alerts or alerts assigned to them
        return alert_assigned_to is None or alert_assigned_to == user.user_id
    
    return False


def can_create_user(creator_role: UserRole, target_role: UserRole) -> bool:
    """
    Check if a user with creator_role can create a user with target_role.
    
    Rules:
    - Owner can create Admin and Device User accounts
    - Admin cannot create any accounts (user self-registration only)
    - Device User cannot create any accounts
    
    Args:
        creator_role: Role of the user creating the account
        target_role: Role of the account being created
    
    Returns:
        True if creation is allowed, False otherwise
    """
    if creator_role == UserRole.OWNER:
        return target_role in [UserRole.ADMIN, UserRole.DEVICE_USER]
    
    return False


def can_modify_user(modifier_role: UserRole, target_role: UserRole) -> bool:
    """
    Check if a user can modify another user's account.
    
    Rules:
    - Owner can modify any account except other Owners
    - Admin cannot modify any accounts
    - Device User cannot modify any accounts
    
    Args:
        modifier_role: Role of the user performing the modification
        target_role: Role of the account being modified
    
    Returns:
        True if modification is allowed, False otherwise
    """
    if modifier_role == UserRole.OWNER:
        return target_role != UserRole.OWNER
    
    return False


def can_escalate_alert(user_role: UserRole) -> bool:
    """
    Check if a user can escalate an alert to the Owner.
    
    Rules:
    - Only Admins can escalate alerts
    
    Args:
        user_role: Role of the user attempting escalation
    
    Returns:
        True if escalation is allowed, False otherwise
    """
    return user_role == UserRole.ADMIN
