# aegis-server/models/models.py

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr

# --- Role-Based Access Control ---

class UserRole(str, Enum):
    """
    Enum for user roles in the RBAC system.
    owner: Super admin, can create admins and manage all resources
    admin: SOC analyst, can claim and triage alerts
    device_user: Standard user, can view only their own devices
    """
    OWNER = "owner"
    ADMIN = "admin"
    DEVICE_USER = "device_user"

class AssignmentStatus(str, Enum):
    """
    Enum for alert assignment status.
    """
    UNASSIGNED = "unassigned"
    ASSIGNED = "assigned"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    ESCALATED = "escalated"

class ResolutionType(str, Enum):
    """
    Enum for alert resolution types.
    """
    TRUE_POSITIVE = "true_positive"
    FALSE_POSITIVE = "false_positive"
    BENIGN_POSITIVE = "benign_positive"

# --- Log Ingestion Models ---

class LogEntry(BaseModel):
    """
    Pydantic model for a single log entry sent by an agent.
    This one *does* use from_attributes, as it's built from the request.
    """
    model_config = ConfigDict(from_attributes=True)
    
    timestamp: datetime
    hostname: str
    message: str
    raw_json: str


# --- User Authentication Models ---

class UserCreate(BaseModel):
    """
    Pydantic model for user signup.
    """
    email: EmailStr
    password: str

class UserInDB(BaseModel):
    """
    Pydantic model for a user object read from the database.
    
    --- MODIFICATION ---
    REMOVED 'model_config = ConfigDict(from_attributes=True)'
    This allows Pydantic to validate the dict-like asyncpg.Record.
    """
    id: int
    email: EmailStr
    role: UserRole = UserRole.DEVICE_USER
    is_active: bool = True
    created_by: int | None = None
    last_login: datetime | None = None
    
class Token(BaseModel):
    """
    Pydantic model for the JWT response.
    """
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """
    Pydantic model for the data encoded within a JWT.
    """
    email: EmailStr | None = None
    role: UserRole | None = None
    user_id: int | None = None

class Invitation(BaseModel):
    """
    Model for the response when a user requests an invitation token.
    We send the raw token to the user *once*.
    """
    token: str
    expires_at: datetime

class DeviceRegister(BaseModel):
    """
    Model for the agent's registration request.
    This is what the agent sends to the /device/register endpoint.
    """
    token: str # The raw token
    agent_id: uuid.UUID
    hostname: str
    name: str # A user-friendly name, e.g. "dev-laptop"

class Device(BaseModel):
    """
    Model for representing a device as sent to the UI.
    """
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    agent_id: uuid.UUID
    name: str
    hostname: str
    registered_at: datetime
    user_id: int | None = None


# --- Alert Assignment Models ---

class AlertAssignment(BaseModel):
    """
    Model for alert assignments (triage workflow).
    """
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    alert_id: int
    assigned_to: int
    assigned_at: datetime
    status: AssignmentStatus
    notes: str | None = None
    resolution: ResolutionType | None = None
    resolved_at: datetime | None = None
    escalated_at: datetime | None = None
    escalated_to: int | None = None
    created_at: datetime
    updated_at: datetime

class AlertAssignmentCreate(BaseModel):
    """
    Model for claiming an alert.
    """
    alert_id: int

class AlertAssignmentUpdate(BaseModel):
    """
    Model for updating alert assignment status and notes.
    """
    status: AssignmentStatus | None = None
    notes: str | None = None
    resolution: ResolutionType | None = None

class AlertEscalation(BaseModel):
    """
    Model for escalating an alert to owner.
    """
    notes: str

# --- User Management Models ---

class UserCreateByOwner(BaseModel):
    """
    Model for Owner creating Admin users.
    """
    email: EmailStr
    password: str
    role: UserRole

class UserResponse(BaseModel):
    """
    Model for user info returned to UI (without password hash).
    """
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    email: EmailStr
    role: UserRole
    is_active: bool
    created_by: int | None = None
    last_login: datetime | None = None

class UserUpdate(BaseModel):
    """
    Model for updating user by Owner.
    """
    role: UserRole | None = None
    is_active: bool | None = None