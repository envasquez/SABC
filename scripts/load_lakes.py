#!/usr/bin/env python3
"""
Load lakes and ramps data from YAML file into the database.
This script populates the lakes and ramps tables from scripts/lakes.yaml.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml  # type: ignore
from common import setup_logging

from core.database import db

logger = setup_logging()


def load_yaml_data(filepath: str) -> Dict[str, Any]:
    """Load and parse the YAML file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file: {e}")
        raise


def insert_lake(yaml_key: str, lake_data: Dict[str, Any], dry_run: bool = False) -> Optional[int]:
    """
    Insert a lake into the database.

    Args:
        yaml_key: The key from the YAML file (e.g., 'belton', 'travis')
        lake_data: The lake data dictionary
        dry_run: If True, only show what would be inserted

    Returns:
        The lake ID if inserted, None if skipped or dry run
    """
    # Get display name - use display_name if provided, otherwise title-case the key
    display_name = lake_data.get("display_name")
    if not display_name:
        # Handle special cases
        if yaml_key == "walter e. long (decker)":
            display_name = "Lake Walter E. Long (Decker)"
        else:
            display_name = f"Lake {yaml_key.replace('_', ' ').title()}"

    google_maps_iframe = lake_data.get("google_maps", "")

    try:
        # Check if lake already exists
        existing = db(
            "SELECT id, display_name FROM lakes WHERE yaml_key = :yaml_key", {"yaml_key": yaml_key}
        )

        if existing:
            logger.info(f"  Lake '{display_name}' already exists (ID: {existing[0][0]})")
            return existing[0][0]

        if dry_run:
            logger.info(f"  Would insert lake: {display_name} (key: {yaml_key})")
            return None
        else:
            # Insert the lake
            result = db(
                """INSERT INTO lakes (yaml_key, display_name, google_maps_iframe)
                   VALUES (:yaml_key, :display_name, :google_maps)
                   RETURNING id""",
                {
                    "yaml_key": yaml_key,
                    "display_name": display_name,
                    "google_maps": google_maps_iframe,
                },
            )
            lake_id = result[0][0]
            logger.info(f"  Inserted lake: {display_name} (ID: {lake_id})")
            return lake_id

    except Exception as e:
        logger.error(f"  Error inserting lake '{display_name}': {e}")
        return None


def insert_ramps(
    lake_id: int, lake_name: str, ramps: List[Dict[str, str]], dry_run: bool = False
) -> int:
    """
    Insert ramps for a lake.

    Args:
        lake_id: The database ID of the lake
        lake_name: The name of the lake (for logging)
        ramps: List of ramp dictionaries
        dry_run: If True, only show what would be inserted

    Returns:
        Number of ramps inserted
    """
    if not ramps or not lake_id:
        return 0

    inserted = 0

    for ramp in ramps:
        ramp_name = ramp.get("name", "").strip()
        if not ramp_name:
            continue

        google_maps_iframe = ramp.get("google_maps", "")

        try:
            # Check if ramp already exists
            existing = db(
                "SELECT id FROM ramps WHERE lake_id = :lake_id AND name = :name",
                {"lake_id": lake_id, "name": ramp_name},
            )

            if existing:
                logger.info(f"    Ramp '{ramp_name}' already exists")
                continue

            if dry_run:
                logger.info(f"    Would insert ramp: {ramp_name}")
                inserted += 1
            else:
                # Insert the ramp
                db(
                    """INSERT INTO ramps (lake_id, name, google_maps_iframe)
                       VALUES (:lake_id, :name, :google_maps)""",
                    {"lake_id": lake_id, "name": ramp_name, "google_maps": google_maps_iframe},
                )
                logger.info(f"    Inserted ramp: {ramp_name}")
                inserted += 1

        except Exception as e:
            logger.error(f"    Error inserting ramp '{ramp_name}': {e}")

    return inserted


def load_lakes_and_ramps(
    filepath: str = "scripts/lakes.yaml", dry_run: bool = False
) -> Tuple[int, int]:
    """
    Load all lakes and ramps from the YAML file.

    Args:
        filepath: Path to the YAML file
        dry_run: If True, only show what would be inserted

    Returns:
        Tuple of (number of lakes inserted, number of ramps inserted)
    """
    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Loading lakes and ramps from {filepath}")

    # Load YAML data
    data = load_yaml_data(filepath)

    total_lakes = 0
    total_ramps = 0

    # Process each lake
    for yaml_key, lake_data in data.items():
        if not isinstance(lake_data, dict):
            logger.warning(f"Skipping '{yaml_key}' - not a dictionary")
            continue

        logger.info(f"\nProcessing lake: {yaml_key}")

        # Insert lake
        lake_id = insert_lake(yaml_key, lake_data, dry_run)
        if lake_id and not dry_run:
            total_lakes += 1
        elif dry_run and not lake_id:
            total_lakes += 1

        # Insert ramps if we have a lake ID (not in dry run for new lakes)
        if lake_id or dry_run:
            ramps = lake_data.get("ramps", [])
            if ramps:
                display_name = lake_data.get("display_name", yaml_key)
                ramps_inserted = insert_ramps(
                    lake_id if lake_id else 0,  # Use 0 for dry run
                    display_name,
                    ramps,
                    dry_run,
                )
                total_ramps += ramps_inserted

    return total_lakes, total_ramps


def main():
    """Main entry point for the script."""
    import argparse

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

    # Check if YAML file exists
    if not Path(args.yaml_file).exists():
        logger.error(f"YAML file not found: {args.yaml_file}")
        return 1

    # Override database URL if provided
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
