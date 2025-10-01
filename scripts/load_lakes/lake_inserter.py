"""Lake database insertion utilities."""

from typing import Any, Dict, Optional

from core.database import db
from scripts.common import setup_logging

logger = setup_logging()


def insert_lake(yaml_key: str, lake_data: Dict[str, Any], dry_run: bool = False) -> Optional[int]:
    """Insert a lake into the database.

    Args:
        yaml_key: The YAML key for the lake
        lake_data: Dictionary containing lake information
        dry_run: If True, only log what would be inserted

    Returns:
        The lake ID if successful, None otherwise
    """
    display_name = lake_data.get("display_name")
    if not display_name:
        if yaml_key == "walter e. long (decker)":
            display_name = "Lake Walter E. Long (Decker)"
        else:
            display_name = f"Lake {yaml_key.replace('_', ' ').title()}"

    google_maps_iframe = lake_data.get("google_maps", "")

    try:
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
            result = db(
                "INSERT INTO lakes (yaml_key, display_name, google_maps) VALUES (:yaml_key, :display_name, :google_maps) RETURNING id",
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
