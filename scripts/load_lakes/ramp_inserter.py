"""Ramp database insertion utilities."""

from typing import Dict, List

from core.database import db
from scripts.common import setup_logging

logger = setup_logging()


def insert_ramps(
    lake_id: int, lake_name: str, ramps: List[Dict[str, str]], dry_run: bool = False
) -> int:
    """Insert ramps for a lake into the database.

    Args:
        lake_id: The ID of the lake
        lake_name: The name of the lake (for logging)
        ramps: List of ramp dictionaries with 'name' and 'google_maps'
        dry_run: If True, only log what would be inserted

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
                db(
                    "INSERT INTO ramps (lake_id, name, google_maps) VALUES (:lake_id, :name, :google_maps)",
                    {"lake_id": lake_id, "name": ramp_name, "google_maps": google_maps_iframe},
                )
                logger.info(f"    Inserted ramp: {ramp_name}")
                inserted += 1

        except Exception as e:
            logger.error(f"    Error inserting ramp '{ramp_name}': {e}")

    return inserted
