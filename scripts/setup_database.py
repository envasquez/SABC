#!/usr/bin/env python3
"""
Setup database schema for SABC application.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import db
from core.db_schema import create_all_tables

def setup_database():
    """Initialize database with tables and views."""
    try:
        print("Creating database tables and views...")
        create_all_tables()
        print("Database setup complete!")

    except Exception as e:
        print(f"Error setting up database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup_database()