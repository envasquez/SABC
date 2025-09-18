#!/usr/bin/env python3
"""
Create admin user for SABC application.
"""

import os
import sys

import bcrypt

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import db


def create_admin_user():
    """Create the admin user if it doesn't exist."""

    # Check if admin user already exists
    existing = db("SELECT id FROM anglers WHERE email = 'admin@sabc.com'")
    if existing:
        print("Admin user already exists")
        return

    # Create admin user
    password_hash = bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    try:
        result = db(
            """INSERT INTO anglers (name, email, password_hash, member, is_admin, year_joined)
               VALUES (:name, :email, :password_hash, :member, :is_admin, :year_joined) RETURNING id""",
            {
                "name": "Admin User",
                "email": "admin@sabc.com",
                "password_hash": password_hash,
                "member": True,
                "is_admin": True,
                "year_joined": 2024,
            },
        )
        admin_id = result[0]["id"]
        print(f"Admin user created with ID: {admin_id}")
        print("Login: admin@sabc.com / admin123")

    except Exception as e:
        print(f"Error creating admin user: {e}")
        sys.exit(1)


if __name__ == "__main__":
    create_admin_user()
