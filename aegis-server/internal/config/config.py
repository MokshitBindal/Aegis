# aegis-server/internal/config/config.py

from pathlib import Path

import tomli  # We installed this in Module 7
from pydantic import BaseModel

CONFIG_FILE_PATH = Path("config.toml")

class DBSettings(BaseModel):
    user: str
    password: str
    database: str
    host: str

class JWTSettings(BaseModel):
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

class Settings(BaseModel):
    database: DBSettings
    jwt: JWTSettings

def load_config() -> Settings:
    """
    Loads configuration from config.toml file.
    """
    if not CONFIG_FILE_PATH.exists():
        print(f"CRITICAL: Configuration file not found at {CONFIG_FILE_PATH.resolve()}")
        print("Please copy 'config.example.toml' to 'config.toml' and fill it out.")
        raise FileNotFoundError("config.toml not found")

    try:
        with open(CONFIG_FILE_PATH, "rb") as f:
            data = tomli.load(f)
        settings = Settings.model_validate(data)
        
        # Check for placeholder secret key
        if "REPLACE_ME" in settings.jwt.secret_key:
            print("WARNING: Using default placeholder JWT secret key.")
            print("Please generate a new key and update config.toml.")
            
        return settings
    except Exception as e:
        print(f"Error loading configuration: {e}")
        raise

# Load config on import and make it available
try:
    settings = load_config()
    DB_URL = (
        f"postgres://{settings.database.user}:{settings.database.password}"
        f"@{settings.database.host}/{settings.database.database}"
    )
except FileNotFoundError:
    # Allow app to start but fail on DB access
    settings = None
    DB_URL = None