#!/usr/bin/env python3
"""Diagnostic script to check if a user's password hash exists and is valid.

Usage: python check_user_password.py <email>
"""

import sys

from core.db_schema import Angler, get_session

if len(sys.argv) < 2:
    print("Usage: python check_user_password.py <email>")
    sys.exit(1)

email = sys.argv[1].lower().strip()

with get_session() as session:
    user = session.query(Angler).filter(Angler.email == email).first()

    if not user:
        print(f"❌ User not found: {email}")
        sys.exit(1)

    print(f"✅ User found: {user.name} (ID: {user.id})")
    print(f"   Email: {user.email}")
    print(f"   Member: {user.member}")
    print(f"   Admin: {user.is_admin}")

    if user.password_hash:
        print(f"   Password hash: {user.password_hash[:20]}...")
        print(f"   Hash length: {len(user.password_hash)} chars")

        # Check if it's a valid bcrypt hash
        if user.password_hash.startswith("$2"):
            print("   ✅ Valid bcrypt hash format")
        else:
            print("   ❌ WARNING: Not a valid bcrypt hash!")
    else:
        print("   ❌ NO PASSWORD HASH SET!")

print("\nTo test password manually:")
print(
    f"  docker exec sabc-postgres psql -U postgres -d sabc -c \"SELECT password_hash FROM anglers WHERE email='{email}';\""
)
