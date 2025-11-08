#!/usr/bin/env python3
"""
Reset users table and create test users with standard password.
Creates 3 users: owner, admin, and device_user with password 'test1234'
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg
from argon2 import PasswordHasher
from internal.config.config import settings

pwd_hasher = PasswordHasher()


async def reset_users():
    """Delete all users and create 3 test users."""
    config = settings
    
    # Connect to database
    conn = await asyncpg.connect(
        host=config.database.host,
        port=5432,  # Default PostgreSQL port
        user=config.database.user,
        password=config.database.password,
        database=config.database.database,
    )
    
    try:
        # Hash the password once
        hashed_password = pwd_hasher.hash("test1234")
        
        print("=" * 60)
        print("RESETTING USERS TABLE")
        print("=" * 60)
        
        # Delete in order to respect foreign key constraints
        print("\nDeleting related data...")
        
        # Delete alert assignments first
        await conn.execute("DELETE FROM alert_assignments")
        print("✅ Deleted all alert assignments")
        
        # Delete alerts
        await conn.execute("DELETE FROM alerts")
        print("✅ Deleted all alerts")
        
        # Delete incidents
        await conn.execute("DELETE FROM incidents")
        print("✅ Deleted all incidents")
        
        # Delete commands
        await conn.execute("DELETE FROM commands")
        print("✅ Deleted all commands")
        
        # Delete logs
        await conn.execute("DELETE FROM logs")
        print("✅ Deleted all logs")
        
        # Delete metrics
        await conn.execute("DELETE FROM system_metrics")
        print("✅ Deleted all system metrics")
        
        # Delete devices
        await conn.execute("DELETE FROM devices")
        print("✅ Deleted all devices")
        
        # Delete invitations
        await conn.execute("DELETE FROM invitations")
        print("✅ Deleted all invitations")
        
        # Finally delete all users
        deleted = await conn.execute("DELETE FROM users")
        print(f"✅ Deleted all users: {deleted}")
        
        print("\nCreating new test users...")
        print("-" * 60)
        
        # Create Owner user
        owner = await conn.fetchrow(
            """
            INSERT INTO users (email, hashed_pass, role, is_active)
            VALUES ($1, $2, $3, $4)
            RETURNING id, email, role
            """,
            "owner@aegis.com",
            hashed_password,
            "owner",
            True
        )
        print(f"✅ Created Owner:")
        print(f"   ID: {owner['id']}")
        print(f"   Email: {owner['email']}")
        print(f"   Password: test1234")
        print(f"   Role: {owner['role']}")
        
        # Create Admin user
        admin = await conn.fetchrow(
            """
            INSERT INTO users (email, hashed_pass, role, is_active, created_by)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, email, role
            """,
            "admin@aegis.com",
            hashed_password,
            "admin",
            True,
            owner['id']  # Created by owner
        )
        print(f"\n✅ Created Admin:")
        print(f"   ID: {admin['id']}")
        print(f"   Email: {admin['email']}")
        print(f"   Password: test1234")
        print(f"   Role: {admin['role']}")
        print(f"   Created by: Owner (ID: {owner['id']})")
        
        # Create Device User
        device_user = await conn.fetchrow(
            """
            INSERT INTO users (email, hashed_pass, role, is_active, created_by)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, email, role
            """,
            "user@aegis.com",
            hashed_password,
            "device_user",
            True,
            owner['id']  # Created by owner
        )
        print(f"\n✅ Created Device User:")
        print(f"   ID: {device_user['id']}")
        print(f"   Email: {device_user['email']}")
        print(f"   Password: test1234")
        print(f"   Role: {device_user['role']}")
        print(f"   Created by: Owner (ID: {owner['id']})")
        
        print("\n" + "=" * 60)
        print("SUMMARY - Login Credentials")
        print("=" * 60)
        print("\n1. Owner Account:")
        print(f"   Email: owner@aegis.com")
        print(f"   Password: test1234")
        print(f"   Role: owner")
        
        print("\n2. Admin Account:")
        print(f"   Email: admin@aegis.com")
        print(f"   Password: test1234")
        print(f"   Role: admin")
        
        print("\n3. Device User Account:")
        print(f"   Email: user@aegis.com")
        print(f"   Password: test1234")
        print(f"   Role: device_user")
        
        print("\n" + "=" * 60)
        print("✅ User reset completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(reset_users())
