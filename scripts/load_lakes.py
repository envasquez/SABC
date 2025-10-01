"""Main CLI script for loading lakes and ramps from YAML."""

import argparse
import os
import sys
from pathlib import Path

from scripts.common import setup_logging
from scripts.load_lakes import load_lakes_and_ramps

logger = setup_logging()


def main() -> int:
    """Main entry point for the script.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(description="Load lakes and ramps from YAML into database")
    parser.add_argument(
        "--yaml-file",
        default="scripts/lakes.yaml",
        help="Path to the YAML file containing lakes data",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be inserted without actually inserting",
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", "postgresql://postgres:dev123@localhost:5432/sabc"),
        help="Database connection URL",
    )

    args = parser.parse_args()

    if not Path(args.yaml_file).exists():
        logger.error(f"YAML file not found: {args.yaml_file}")
        return 1

    os.environ["DATABASE_URL"] = args.database_url

    logger.info(
        f"Connecting to database: {args.database_url.split('@')[1] if '@' in args.database_url else args.database_url}"
    )

    try:
        lakes_inserted, ramps_inserted = load_lakes_and_ramps(
            filepath=args.yaml_file, dry_run=args.dry_run
        )

        logger.info(f"\n{'[DRY RUN] ' if args.dry_run else ''}Summary:")
        logger.info(f"  Lakes {'would be ' if args.dry_run else ''}inserted: {lakes_inserted}")
        logger.info(f"  Ramps {'would be ' if args.dry_run else ''}inserted: {ramps_inserted}")

        if args.dry_run:
            logger.info("\nThis was a dry run. Use without --dry-run to actually insert data.")

        return 0

    except Exception as e:
        logger.error(f"Failed to load lakes and ramps: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
