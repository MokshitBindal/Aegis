#!/usr/bin/env python3
"""
Generate an invitation token for device registration.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg
import secrets
from datetime import datetime, timedelta, timezone
from internal.config.config import settings
from internal.auth.security import get_password_hash


async def generate_invitation():
    """Generate a new invitation token for the owner."""
    conn = await asyncpg.connect(
        host=settings.database.host,
        port=5432,
        user=settings.database.user,
        password=settings.database.password,
        database=settings.database.database,
    )
    
    try:
        # Get the owner user ID
        owner = await conn.fetchrow(
            "SELECT id, email FROM users WHERE role = $1",
            'owner'
        )
        
        if not owner:
            print("❌ No owner user found. Please create an owner user first.")
            return
        
        # Generate a URL-safe token (no dashes at start)
        token = secrets.token_urlsafe(32)
        
        # Hash the token using the same function as password hashing (Argon2)
        token_hash = get_password_hash(token)
        
        # Set expiration to 7 days from now
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        # Store in database
        await conn.execute(
            """
            INSERT INTO invitations (user_id, token_hash, expires_at)
            VALUES ($1, $2, $3)
            """,
            owner['id'],
            token_hash,
            expires_at
        )
        
        print("=" * 70)
        print("✅ NEW INVITATION TOKEN GENERATED")
        print("=" * 70)
        print(f"\nOwner: {owner['email']} (ID: {owner['id']})")
        print(f"Expires: {expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("\n" + "=" * 70)
        print("REGISTRATION TOKEN:")
        print("=" * 70)
        print(f"\n{token}\n")
        print("=" * 70)
        print("\nUse this token to register your agent:")
        print(f"sudo python main.py register --token {token}")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(generate_invitation())
