"""
Secure storage for agent credentials.

This module handles secure storage and retrieval of the agent's
registration data using the system keyring when available,
falling back to an encrypted file if keyring is not accessible.
"""

import os
import json
import base64
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

# Constants for credential storage
KEYRING_SERVICE = "aegis-agent"
KEYRING_USERNAME = "agent-credentials"
CREDS_FILE = "agent.credentials"

def _get_encryption_key(salt: bytes) -> bytes:
    """
    Derives an encryption key from the agent ID and salt using PBKDF2.
    """
    from internal.agent.id import get_agent_id
    agent_id = str(get_agent_id()).encode()
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(agent_id))

def store_credentials(server_url: str, agent_id: str):
    """
    Securely stores the agent's credentials.
    """
    creds = {
        "server_url": server_url,
        "agent_id": agent_id,
        "registered": True
    }
    
    if KEYRING_AVAILABLE:
        try:
            keyring.set_password(
                KEYRING_SERVICE,
                KEYRING_USERNAME,
                json.dumps(creds)
            )
            return
        except Exception:
            # Fall back to file storage
            pass
    
    # File-based storage with encryption
    salt = os.urandom(16)
    key = _get_encryption_key(salt)
    f = Fernet(key)
    encrypted = f.encrypt(json.dumps(creds).encode())
    
    creds_path = Path(CREDS_FILE)
    creds_path.write_bytes(salt + encrypted)

def load_credentials():
    """
    Loads the agent's credentials from secure storage.
    Returns None if not registered.
    """
    if KEYRING_AVAILABLE:
        try:
            data = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
            if data:
                return json.loads(data)
        except Exception:
            # Fall back to file storage
            pass
    
    # Try file-based storage
    try:
        creds_path = Path(CREDS_FILE)
        if not creds_path.exists():
            return None
            
        data = creds_path.read_bytes()
        salt = data[:16]
        encrypted = data[16:]
        
        key = _get_encryption_key(salt)
        f = Fernet(key)
        decrypted = f.decrypt(encrypted)
        return json.loads(decrypted)
    except Exception:
        return None

def is_registered():
    """
    Checks if the agent has valid credentials stored.
    """
    creds = load_credentials()
    return bool(creds and creds.get("registered"))