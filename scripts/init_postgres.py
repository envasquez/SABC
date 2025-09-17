#!/usr/bin/env python3

import logging
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db_schema import create_views, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    # Set PostgreSQL connection for Docker setup
    database_url = os.environ.get(
        "DATABASE_URL", "postgresql://postgres:dev123@localhost:5432/sabc"
    )

    logger.info(f"Initializing PostgreSQL database at: {database_url}")

    # Override the DATABASE_URL for this script
    os.environ["DATABASE_URL"] = database_url

    try:
        # Initialize database schema
        init_db()
        logger.info("Database schema created successfully")

        # Create views
        create_views()
        logger.info("Database views created successfully")

        logger.info("PostgreSQL database initialization complete!")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
