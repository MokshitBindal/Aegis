# aegis-server/models/models.py

from pydantic import BaseModel, ConfigDict, EmailStr
from datetime import datetime
import uuid

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