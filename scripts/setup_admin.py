import argparse
import getpass
import logging
import os
import sys
from typing import Optional

import bcrypt
from sqlalchemy.exc import SQLAlchemyError

from core.db_schema import Angler, get_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_admin_user(
    email: Optional[str] = None,
    name: Optional[str] = None,
    password: Optional[str] = None,
    interactive: bool = True,
) -> int:
    if not os.environ.get("DATABASE_URL"):
        logger.error("DATABASE_URL environment variable not set")
        return 1

    if not interactive:
        email = email or "admin@sabc.com"
        name = name or "Admin User"
        if not password:
            password = os.environ.get("ADMIN_PASSWORD")
            if not password:
                logger.error("Password must be provided via --password or ADMIN_PASSWORD env var")
                return 1

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

    password_bytes = password.encode("utf-8")
    password_hash = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")

    try:
        with get_session() as session:
            existing = session.query(Angler).filter(Angler.email == email).first()

            if existing:
                existing.password_hash = password_hash
                existing.name = name
                existing.is_admin = True
                logger.info(f"Updated existing user {email} as admin")
            else:
                new_admin = Angler(
                    name=name,
                    email=email,
                    password_hash=password_hash,
                    member=True,
                    is_admin=True,
                )
                session.add(new_admin)
                session.flush()
                admin_id = new_admin.id
                logger.info(f"Created new admin user {email} with ID: {admin_id}")

        if not interactive:
            print(f"Admin user created successfully for: {email}")

        logger.info("Admin user setup complete!")
        return 0

    except SQLAlchemyError as db_error:
        logger.error(f"Failed to create admin user: {db_error}")
        return 1


def main() -> int:
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
