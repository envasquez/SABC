"""Main data loading orchestration."""

from typing import Tuple

from scripts.common import setup_logging
from scripts.load_lakes.lake_inserter import insert_lake
from scripts.load_lakes.ramp_inserter import insert_ramps
from scripts.load_lakes.yaml_loader import load_yaml_data

logger = setup_logging()


def load_lakes_and_ramps(
    filepath: str = "scripts/lakes.yaml", dry_run: bool = False
) -> Tuple[int, int]:
    """Load lakes and ramps from YAML file into the database.

    Args:
        filepath: Path to the YAML file
        dry_run: If True, only log what would be inserted

    Returns:
        Tuple of (lakes_inserted, ramps_inserted)
    """
    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Loading lakes and ramps from {filepath}")

    data = load_yaml_data(filepath)

    total_lakes = 0
    total_ramps = 0

    for yaml_key, lake_data in data.items():
        if not isinstance(lake_data, dict):
            logger.warning(f"Skipping '{yaml_key}' - not a dictionary")
            continue

        logger.info(f"\nProcessing lake: {yaml_key}")

        lake_id = insert_lake(yaml_key, lake_data, dry_run)
        if lake_id and not dry_run:
            total_lakes += 1
        elif dry_run and not lake_id:
            total_lakes += 1

        if lake_id or dry_run:
            ramps = lake_data.get("ramps", [])
            if ramps:
                display_name = lake_data.get("display_name", yaml_key)
                ramps_inserted = insert_ramps(
                    lake_id if lake_id else 0,
                    display_name,
                    ramps,
                    dry_run,
                )
                total_ramps += ramps_inserted

    return total_lakes, total_ramps
