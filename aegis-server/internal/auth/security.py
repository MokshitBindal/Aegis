# aegis-server/internal/auth/security.py

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError, VerificationError

# Use Argon2 directly for password hashing
# Modern, secure standard without password length limits
pwd_hasher = PasswordHasher()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a hashed password.
    
    Args:
        plain_password (str): The password from the user login.
        hashed_password (str): The hash stored in the database.
        
    Returns:
        bool: True if the passwords match, False otherwise.
    """
    try:
        pwd_hasher.verify(hashed_password, plain_password)
        return True
    except (VerifyMismatchError, InvalidHashError, VerificationError, Exception):
        # Return False for any verification error including invalid hash format
        return False

def get_password_hash(password: str) -> str:
    """
    Hashes a plain-text password for storage.
    
    Args:
        password (str): The plain-text password from signup.
        
    Returns:
        str: The securely hashed and salted password.
    """
    return pwd_hasher.hash(password)