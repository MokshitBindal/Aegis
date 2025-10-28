# aegis-server/models/models.py

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

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