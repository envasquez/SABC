#!/usr/bin/env python3

import getpass
import logging
import os
import sys

import bcrypt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_admin_user():
    database_url = os.environ.get(
        "DATABASE_URL", "postgresql://postgres:dev123@localhost:5432/sabc"
    )
    logger.info(f"Creating admin user in PostgreSQL database: {database_url}")
    os.environ["DATABASE_URL"] = database_url
    email = input("Admin email: ")
    name = input("Admin name: ")
    while True:
        password = getpass.getpass("Admin password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password == confirm:
            break
        print("Passwords do not match. Try again.")
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    try:
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
            db(
                """INSERT INTO anglers (name, email, password_hash, is_admin, member)
                  VALUES (:name, :email, :password_hash, true, true)""",
                {"name": name, "email": email, "password_hash": password_hash},
            )
            logger.info(f"Created new admin user {email}")
        logger.info("Admin user setup complete!")
    except Exception as e:
        logger.error(f"Failed to create admin user: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(create_admin_user())
