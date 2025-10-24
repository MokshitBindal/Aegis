# aegis-server/internal/auth/security.py

from passlib.context import CryptContext

# 1. Create a CryptContext instance
# --- MODIFICATION ---
# We now specify 'argon2' as the default scheme.
# This is a modern, secure standard without the 72-byte limit.
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a hashed password.
    
    Args:
        plain_password (str): The password from the user login.
        hashed_password (str): The hash stored in the database.
        
    Returns:
        bool: True if the passwords match, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Hashes a plain-text password for storage.
    
    Args:
        password (str): The plain-text password from signup.
        
    Returns:
        str: The securely hashed and salted password.
    """
    return pwd_context.hash(password)