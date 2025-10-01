import argparse
import sys

from common import ensure_database_url, setup_logging

from core.db_schema import create_all_tables, create_views, init_db


def setup_database(method: str = "full") -> int:
    logger = setup_logging()
    database_url = ensure_database_url()

    logger.info(f"Setting up database at: {database_url}")

    try:
        if method == "full":
            logger.info("Creating database schema...")
            init_db()
            logger.info("Database schema created successfully")

            logger.info("Creating database views...")
            create_views()
            logger.info("Database views created successfully")

        elif method == "tables":
            logger.info("Creating database tables and views...")
            create_all_tables()

        else:
            logger.error(f"Unknown method: {method}")
            return 1

        logger.info("Database setup complete!")
        return 0

    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Setup SABC database")
    parser.add_argument(
        "--method",
        choices=["full", "tables"],
        default="full",
        help="Setup method: 'full' (default) or 'tables'",
    )

    args = parser.parse_args()
    return setup_database(args.method)


if __name__ == "__main__":
    sys.exit(main())
