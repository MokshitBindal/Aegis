#!/usr/bin/env python3
"""
Complete device registration helper.
1. Clears all old invitation tokens
2. Generates a new Argon2-hashed token
3. Displays registration command
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg
import secrets
from datetime import datetime, timedelta, timezone
from internal.config.config import settings
from internal.auth.security import get_password_hash


async def complete_registration_setup():
    """Clear old tokens and generate new one."""
    conn = await asyncpg.connect(
        host=settings.database.host,
        port=5432,
        user=settings.database.user,
        password=settings.database.password,
        database=settings.database.database,
    )
    
    try:
        # Step 1: Clear ALL old invitations
        print("=" * 70)
        print("STEP 1: Clearing old invitation tokens...")
        print("=" * 70)
        result = await conn.execute('DELETE FROM invitations')
        print(f"✅ Cleared all old tokens: {result}")
        
        # Step 2: Get owner
        print("\nSTEP 2: Finding owner account...")
        owner = await conn.fetchrow(
            "SELECT id, email FROM users WHERE role = $1",
            'owner'
        )
        
        if not owner:
            print("❌ No owner user found. Please run reset_users.py first.")
            return
        
        print(f"✅ Found owner: {owner['email']} (ID: {owner['id']})")
        
        # Step 3: Generate new token with Argon2
        print("\nSTEP 3: Generating new invitation token with Argon2...")
        token = secrets.token_urlsafe(32)
        token_hash = get_password_hash(token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        await conn.execute(
            """
            INSERT INTO invitations (user_id, token_hash, expires_at)
            VALUES ($1, $2, $3)
            """,
            owner['id'],
            token_hash,
            expires_at
        )
        
        print(f"✅ Token generated successfully")
        print(f"   Expires: {expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        # Step 4: Display registration info
        print("\n" + "=" * 70)
        print("✅ REGISTRATION READY!")
        print("=" * 70)
        print(f"\nOwner: {owner['email']}")
        print(f"Token: {token}")
        print("\n" + "=" * 70)
        print("REGISTER YOUR AGENT:")
        print("=" * 70)
        print("\nRun this command on your agent machine:\n")
        print(f"cd /path/to/aegis-agent")
        print(f"sudo python main.py register --token {token}")
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(complete_registration_setup())
