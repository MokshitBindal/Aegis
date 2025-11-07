# aegis-server/routers/auth.py

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from internal.auth.jwt import create_access_token  # <--- IMPORT
from internal.auth.security import get_password_hash, verify_password
from internal.storage.postgres import get_db_pool
from models.models import Token, UserCreate, UserInDB

router = APIRouter()

@router.post("/signup", response_model=UserInDB, status_code=status.HTTP_201_CREATED)
async def signup(
    user: UserCreate,
    request: Request
):
    # ... (This function remains unchanged) ...
    pool = get_db_pool()
    hashed_pass = get_password_hash(user.password)
    # Include default role as device_user
    sql = "INSERT INTO users (email, hashed_pass, role) VALUES ($1, $2, $3) RETURNING id, email, role, is_active"
    try:
        async with pool.acquire() as conn:
            new_user = await conn.fetchrow(sql, user.email, hashed_pass, "device_user")
            if new_user:
                return UserInDB.model_validate(dict(new_user))
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create user.",
                )
    except asyncpg.exceptions.UniqueViolationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during signup: {e}",
        )


@router.post("/login", response_model=Token) # <--- MODIFICATION: Set response model
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Handles user login.
    Verifies email and password, then returns a JWT with role and user_id.
    """
    pool = get_db_pool()
    email = form_data.username
    password = form_data.password

    # 1. Find the user
    sql = "SELECT id, email, hashed_pass, role, is_active FROM users WHERE email = $1"
    try:
        async with pool.acquire() as conn:
            db_user = await conn.fetchrow(sql, email)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {e}"
        )

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Incorrect email or password"
        )
    
    # Check if user is active
    if not db_user['is_active']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )

    # 2. Verify the password
    if not verify_password(password, db_user['hashed_pass']):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Incorrect email or password"
        )

    # 3. Update last_login timestamp
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET last_login = NOW() WHERE id = $1",
                db_user['id']
            )
    except Exception:
        pass  # Non-critical failure
    
    # 4. Generate and return a JWT with role and user_id
    access_token = create_access_token(data={
        "sub": db_user['email'],
        "role": db_user['role'],
        "user_id": db_user['id']
    })
    
    return Token(access_token=access_token, token_type="bearer")