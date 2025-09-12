#!/usr/bin/env python3
"""
Bootstrap script to create an admin user for SABC.
Run this script to set up your admin account.
"""

import getpass
import sys

from core.database import db
from routes.dependencies import bcrypt


def main():
    print("SABC Admin Bootstrap Script")
    print("=" * 30)

    # Get email
    email = input("Enter your admin email: ").strip().lower()
    if not email:
        print("Error: Email is required")
        return

    # Check if email already exists
    existing = db("SELECT id, name FROM anglers WHERE email = :email", {"email": email})
    if existing:
        user_id, name = existing[0]
        print(f"User '{name}' with email '{email}' already exists (ID: {user_id})")
        update = input("Update this user to admin? (y/N): ").lower()
        if update != "y":
            return

        # Get password
        password = getpass.getpass("Enter password: ")
        if not password:
            print("Error: Password is required")
            return

        # Update existing user
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        db(
            """UPDATE anglers
              SET password_hash = :password_hash, is_admin = 1, member = 1
              WHERE email = :email""",
            {"password_hash": password_hash, "email": email},
        )

        print(f"✓ Updated user '{name}' to admin with new password")

    else:
        # Create new user
        name = input("Enter your full name: ").strip()
        if not name:
            print("Error: Name is required")
            return

        password = getpass.getpass("Enter password: ")
        if not password:
            print("Error: Password is required")
            return

        # Create new admin user
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        db(
            """INSERT INTO anglers (name, email, password_hash, member, is_admin)
              VALUES (:name, :email, :password_hash, 1, 1)""",
            {"name": name, "email": email, "password_hash": password_hash},
        )

        print(f"✓ Created new admin user '{name}' with email '{email}'")

    print("\nYou can now log in at /login with your email and password.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
