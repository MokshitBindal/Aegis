# aegis-server/internal/auth/jwt.py

from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError

from internal.config.config import settings
from models.models import TokenData

# This tells FastAPI what URL to check for the token
# (This is our login endpoint)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def create_access_token(data: dict) -> str:
    """
    Creates a new JWT access token.
    """
    to_encode = data.copy()
    
    # Set the token expiration time
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt.access_token_expire_minutes
    )
    to_encode.update({"exp": expire})
    
    # Encode the token with our secret key and algorithm
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.jwt.secret_key, 
        algorithm=settings.jwt.algorithm
    )
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    """
    FastAPI Dependency to validate a token and get the user data.
    
    This function will be used on all protected endpoints.
    It automatically validates the 'Authorization: Bearer <token>' header.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode the token
        payload = jwt.decode(
            token,
            settings.jwt.secret_key,
            algorithms=[settings.jwt.algorithm]
        )
        
        # The 'sub' (subject) field should contain our user's email
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
            
        # Validate the payload against our TokenData model
        token_data = TokenData(email=email)
        
    except (JWTError, ValidationError):
        raise credentials_exception
        
    return token_data