#!/usr/bin/env python3
"""
Bootstrap script to create the first admin user for SABC
Run this script after setting up the database to create initial admin access.
"""

import argparse
import getpass
import re

import bcrypt
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

DATABASE_URL = "sqlite:///sabc.db"


def validate_email(email):
    """Basic email validation"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def hash_password(password):
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_admin_user(email=None, password=None, name=None, force=False):
    """Create the first admin user"""
    print("🎣 SABC Admin User Setup")
    print("=" * 40)

    # Connect to database
    try:
        engine = create_engine(DATABASE_URL, echo=False)
        with engine.connect() as conn:
            # Check if any admin users already exist
            result = conn.execute(
                text("SELECT COUNT(*) FROM anglers WHERE is_admin = true")
            ).fetchone()

            if result[0] > 0:
                print(f"⚠️  {result[0]} admin user(s) already exist.")
                if force:
                    print("Force flag set, creating admin anyway...")
                else:
                    confirm = input("Do you want to create another admin? (y/N): ").lower()
                    if confirm != "y":
                        print("Exiting...")
                        return False

    except SQLAlchemyError as e:
        print(f"❌ Database connection failed: {e}")
        print("Make sure the database has been initialized with: python database.py")
        return False

    # Get user information
    if not all([name, email, password]):
        print("\nEnter admin user details:")

    # Name
    if not name:
        while True:
            name = input("Full Name: ").strip()
            if name:
                break
            print("Name cannot be empty.")

    # Email
    if not email:
        while True:
            email = input("Email Address: ").strip().lower()
            if validate_email(email):
                # Check if email already exists
                try:
                    with engine.connect() as conn:
                        result = conn.execute(
                            text("SELECT COUNT(*) FROM anglers WHERE email = :email"),
                            {"email": email},
                        ).fetchone()

                        if result[0] > 0:
                            print("❌ Email already exists. Please use a different email.")
                            continue
                        break
                except SQLAlchemyError as e:
                    print(f"❌ Database error: {e}")
                    continue
            else:
                print("❌ Invalid email format.")
    else:
        # Validate provided email
        if not validate_email(email):
            print(f"❌ Invalid email format: {email}")
            return False

        # Check if email already exists
        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT COUNT(*) FROM anglers WHERE email = :email"), {"email": email}
                ).fetchone()

                if result[0] > 0 and not force:
                    print(f"❌ Email already exists: {email}")
                    return False
        except SQLAlchemyError as e:
            print(f"❌ Database error: {e}")
            return False

    # Password
    if not password:
        while True:
            password = getpass.getpass("Password (min 8 characters): ")
            if len(password) < 8:
                print("❌ Password must be at least 8 characters.")
                continue

            password_confirm = getpass.getpass("Confirm Password: ")
            if password != password_confirm:
                print("❌ Passwords do not match.")
                continue

            break
    else:
        # Validate provided password
        if len(password) < 8:
            print("❌ Password must be at least 8 characters.")
            return False

    # Confirm creation
    print("\nCreating admin user:")
    print(f"Name: {name}")
    print(f"Email: {email}")
    print("Admin: Yes")
    print("Member: Yes")

    if not force:
        confirm = input("\nCreate this admin user? (y/N): ").lower()
        if confirm != "y":
            print("❌ User creation cancelled.")
            return False

    # Create user
    try:
        password_hash = hash_password(password)

        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO anglers (name, email, member, is_admin, password_hash)
                    VALUES (:name, :email, true, true, :password_hash)
                """),
                {"name": name, "email": email, "password_hash": password_hash},
            )
            conn.commit()

        print("✅ Admin user created successfully!")
        print("\nYou can now login at: http://localhost:8000/login")
        print(f"Email: {email}")
        print("Password: [hidden]")
        return True

    except SQLAlchemyError as e:
        print(f"❌ Failed to create user: {e}")
        return False


def list_admin_users():
    """List existing admin users"""
    try:
        engine = create_engine(DATABASE_URL, echo=False)
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT name, email, created_at
                    FROM anglers
                    WHERE is_admin = true
                    ORDER BY created_at ASC
                """)
            ).fetchall()

            if not result:
                print("No admin users found.")
                return

            print(f"\nCurrent Admin Users ({len(result)}):")
            print("-" * 50)
            for row in result:
                print(f"• {row[0]} ({row[1]}) - Created: {row[2]}")

    except SQLAlchemyError as e:
        print(f"❌ Database error: {e}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="SABC Admin Bootstrap Script")
    parser.add_argument(
        "action",
        nargs="?",
        default="create",
        choices=["create", "list"],
        help="Action to perform (default: create)",
    )
    parser.add_argument("--email", help="Admin email address")
    parser.add_argument("--password", help="Admin password (min 8 characters)")
    parser.add_argument("--name", help="Admin full name")
    parser.add_argument(
        "--force", action="store_true", help="Force creation without prompts (for CI)"
    )

    args = parser.parse_args()

    if args.action == "list":
        list_admin_users()
        return

    success = create_admin_user(
        email=args.email, password=args.password, name=args.name, force=args.force
    )

    if success:
        print("\n🚀 Next steps:")
        print("1. Start the development server: nix develop -> start-app")
        print("2. Open http://localhost:8000 in your browser")
        print("3. Login with the admin credentials you just created")
        print("4. Begin setting up events, polls, and tournaments")


if __name__ == "__main__":
    main()
