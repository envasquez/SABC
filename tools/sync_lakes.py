#!/usr/bin/env python3
"""
Script to sync lake and ramp data from data/lakes.yaml to the database.
This script performs incremental updates - adds new lakes/ramps and updates existing ones.
Safe to run multiple times.

Usage:
    python sync_lakes.py           # Sync all data
    python sync_lakes.py --check   # Check what would be updated without making changes
"""

import argparse
import sqlite3
import sys
from pathlib import Path

import yaml


def load_yaml_data():
    """Load lakes data from YAML file."""
    yaml_path = Path(__file__).parent / "data" / "lakes.yaml"

    if not yaml_path.exists():
        raise FileNotFoundError(f"Lakes YAML file not found: {yaml_path}")

    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_database_connection():
    """Get database connection."""
    db_path = Path(__file__).parent / "sabc.db"

    if not db_path.exists():
        raise FileNotFoundError(f"Database file not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def check_lake_changes(cursor, yaml_key, lake_data):
    """Check if lake needs to be updated."""
    display_name = lake_data.get("display_name", yaml_key.title())
    google_maps_iframe = lake_data.get("google_maps", "")

    cursor.execute(
        "SELECT id, display_name, google_maps_iframe FROM lakes WHERE yaml_key = ?", (yaml_key,)
    )
    existing = cursor.fetchone()

    if not existing:
        return "new", None, (display_name, google_maps_iframe)

    changes = []
    if existing["display_name"] != display_name:
        changes.append(f"display_name: '{existing['display_name']}' -> '{display_name}'")
    if existing["google_maps_iframe"] != google_maps_iframe:
        changes.append("google_maps_iframe: updated")

    if changes:
        return "update", existing["id"], changes
    else:
        return "unchanged", existing["id"], None


def check_ramp_changes(cursor, lake_id, ramp_data):
    """Check if ramp needs to be updated."""
    ramp_name = ramp_data["name"]
    google_maps_iframe = ramp_data.get("google_maps", "")

    cursor.execute(
        "SELECT id, google_maps_iframe FROM ramps WHERE lake_id = ? AND name = ?",
        (lake_id, ramp_name),
    )
    existing = cursor.fetchone()

    if not existing:
        return "new", None, google_maps_iframe

    if existing["google_maps_iframe"] != google_maps_iframe:
        return "update", existing["id"], "google_maps_iframe: updated"
    else:
        return "unchanged", existing["id"], None


def apply_lake_changes(cursor, yaml_key, lake_data, dry_run=False):
    """Apply lake changes to database."""
    display_name = lake_data.get("display_name", yaml_key.title())
    google_maps_iframe = lake_data.get("google_maps", "")

    cursor.execute("SELECT id FROM lakes WHERE yaml_key = ?", (yaml_key,))
    existing = cursor.fetchone()

    if existing:
        if not dry_run:
            cursor.execute(
                """
                UPDATE lakes
                SET display_name = ?, google_maps_iframe = ?, updated_at = CURRENT_TIMESTAMP
                WHERE yaml_key = ?
            """,
                (display_name, google_maps_iframe, yaml_key),
            )
        lake_id = existing["id"]
        action = "Updated"
    else:
        if not dry_run:
            cursor.execute(
                """
                INSERT INTO lakes (yaml_key, display_name, google_maps_iframe)
                VALUES (?, ?, ?)
            """,
                (yaml_key, display_name, google_maps_iframe),
            )
            lake_id = cursor.lastrowid
        else:
            lake_id = None
        action = "Added"

    return lake_id, action


def apply_ramp_changes(cursor, lake_id, ramp_data, dry_run=False):
    """Apply ramp changes to database."""
    ramp_name = ramp_data["name"]
    google_maps_iframe = ramp_data.get("google_maps", "")

    cursor.execute("SELECT id FROM ramps WHERE lake_id = ? AND name = ?", (lake_id, ramp_name))
    existing = cursor.fetchone()

    if existing:
        if not dry_run:
            cursor.execute(
                """
                UPDATE ramps
                SET google_maps_iframe = ?, updated_at = CURRENT_TIMESTAMP
                WHERE lake_id = ? AND name = ?
            """,
                (google_maps_iframe, lake_id, ramp_name),
            )
        action = "Updated"
    else:
        if not dry_run:
            cursor.execute(
                """
                INSERT INTO ramps (lake_id, name, google_maps_iframe)
                VALUES (?, ?, ?)
            """,
                (lake_id, ramp_name, google_maps_iframe),
            )
        action = "Added"

    return action


def sync_lakes_data(dry_run=False):
    """Sync lakes data from YAML to database."""
    action_verb = "Checking" if dry_run else "Syncing"
    print(f"{action_verb} lakes data from YAML...")

    try:
        lakes_data = load_yaml_data()
        print(f"Found {len(lakes_data)} lakes in YAML file")

        conn = get_database_connection()
        cursor = conn.cursor()

        total_lake_changes = 0
        total_ramp_changes = 0

        for yaml_key, lake_data in lakes_data.items():
            print(f"\nProcessing lake: {yaml_key}")

            # Check what changes are needed
            lake_status, lake_id, lake_info = check_lake_changes(cursor, yaml_key, lake_data)

            if lake_status == "new":
                print(f"  🆕 NEW LAKE: Will add '{lake_info[0]}'")
                total_lake_changes += 1
            elif lake_status == "update":
                print(f"  🔄 UPDATE LAKE: {', '.join(lake_info)}")
                total_lake_changes += 1
            else:
                print(f"  ✅ Lake unchanged: {lake_data.get('display_name', yaml_key.title())}")

            # Apply lake changes if not dry run
            if not dry_run:
                lake_id, action = apply_lake_changes(cursor, yaml_key, lake_data, dry_run)

            # Process ramps for this lake
            ramps = lake_data.get("ramps", [])
            if ramps:
                print(f"  Processing {len(ramps)} ramps...")
                for ramp_data in ramps:
                    ramp_status, ramp_id, ramp_info = check_ramp_changes(cursor, lake_id, ramp_data)
                    ramp_name = ramp_data["name"]

                    if ramp_status == "new":
                        print(f"    🆕 NEW RAMP: Will add '{ramp_name}'")
                        total_ramp_changes += 1
                    elif ramp_status == "update":
                        print(f"    🔄 UPDATE RAMP: {ramp_name} - {ramp_info}")
                        total_ramp_changes += 1
                    else:
                        print(f"    ✅ Ramp unchanged: {ramp_name}")

                    # Apply ramp changes if not dry run
                    if not dry_run:
                        apply_ramp_changes(cursor, lake_id, ramp_data, dry_run)
            else:
                print("  No ramps defined for this lake")

        if not dry_run:
            conn.commit()
            print("\n✅ Successfully synced lakes data to database")
        else:
            print("\n📋 Summary of changes that would be made:")
            print(f"   Lakes: {total_lake_changes} changes")
            print(f"   Ramps: {total_ramp_changes} changes")

        # Show final summary
        cursor.execute("SELECT COUNT(*) as count FROM lakes")
        lake_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM ramps")
        ramp_count = cursor.fetchone()["count"]

        status_verb = "would contain" if dry_run else "now contains"
        print(f"\nDatabase {status_verb} {lake_count} lakes and {ramp_count} ramps")

        conn.close()

    except Exception as e:
        print(f"❌ Error syncing lakes data: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Sync lakes data from YAML to database")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check what changes would be made without applying them",
    )
    args = parser.parse_args()

    sync_lakes_data(dry_run=args.check)


if __name__ == "__main__":
    main()
