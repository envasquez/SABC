#!/usr/bin/env python3
"""
Setup admin user for SABC application.
Consolidates bootstrap_admin_postgres.py and create_admin.py functionality.
"""

import argparse
import getpass
import sys
from typing import Optional

import bcrypt
from common import ensure_database_url, setup_logging

from core.database import db


def create_admin_user(
    email: Optional[str] = None,
    name: Optional[str] = None,
    password: Optional[str] = None,
    interactive: bool = True,
) -> int:
    """
    Create admin user with optional interactive mode.

    Args:
        email: Admin email (prompts if None and interactive)
        name: Admin name (prompts if None and interactive)
        password: Admin password (prompts if None and interactive)
        interactive: Whether to prompt for missing values

    Returns:
        0 on success, 1 on failure
    """
    logger = setup_logging()
    ensure_database_url()

    # Use defaults for non-interactive mode
    if not interactive:
        email = email or "admin@sabc.com"
        name = name or "Admin User"
        password = password or "admin123"

    # Interactive prompts
    if interactive:
        if not email:
            email = input("Admin email: ")
        if not name:
            name = input("Admin name: ")
        if not password:
            while True:
                password = getpass.getpass("Admin password: ")
                confirm = getpass.getpass("Confirm password: ")
                if password == confirm:
                    break
                print("Passwords do not match. Try again.")

    # Hash password
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    try:
        # Check if user exists
        existing = db("SELECT id FROM anglers WHERE email = :email", {"email": email})

        if existing:
            db(
                """UPDATE anglers
                   SET password_hash = :password_hash, is_admin = true, member = true, name = :name
                   WHERE email = :email""",
                {"password_hash": password_hash, "email": email, "name": name},
            )
            logger.info(f"Updated existing user {email} as admin")
        else:
            result = db(
                """INSERT INTO anglers (name, email, password_hash, member, is_admin, year_joined)
                   VALUES (:name, :email, :password_hash, true, true, 2024) RETURNING id""",
                {"name": name, "email": email, "password_hash": password_hash},
            )
            admin_id = result[0][0]
            logger.info(f"Created new admin user {email} with ID: {admin_id}")

        if not interactive:
            print(f"Login: {email} / {password}")

        logger.info("Admin user setup complete!")
        return 0

    except Exception as e:
        logger.error(f"Failed to create admin user: {e}")
        return 1


def main() -> int:
    """Main function with CLI argument parsing."""
    parser = argparse.ArgumentParser(description="Create SABC admin user")
    parser.add_argument("--email", help="Admin email")
    parser.add_argument("--name", help="Admin name")
    parser.add_argument("--password", help="Admin password")
    parser.add_argument(
        "--non-interactive", action="store_true", help="Use defaults without prompts"
    )

    args = parser.parse_args()

    return create_admin_user(
        email=args.email,
        name=args.name,
        password=args.password,
        interactive=not args.non_interactive,
    )


if __name__ == "__main__":
    sys.exit(main())
