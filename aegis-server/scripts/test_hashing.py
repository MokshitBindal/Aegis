#!/usr/bin/env python3
"""Test token hashing and verification"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from internal.auth.security import get_password_hash, verify_password

# Test token
token = "test_token_12345"

# Hash it
token_hash = get_password_hash(token)

print(f"Token: {token}")
print(f"Hash: {token_hash}")
print(f"Hash length: {len(token_hash)}")
print(f"Hash starts with: ${token_hash[:20]}")

# Verify it
result = verify_password(token, token_hash)
print(f"\nVerification result: {result}")

if result:
    print("✅ Token hashing and verification working correctly!")
else:
    print("❌ Token verification failed!")
