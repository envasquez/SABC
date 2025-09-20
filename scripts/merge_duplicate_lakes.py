#!/usr/bin/env python3
"""
Script to merge duplicate lake entries.
This script identifies uppercase lake names that are duplicates of existing lakes
and merges them by updating references and removing the duplicates.
"""

import os
import sys

from sqlalchemy import create_engine, text

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:dev123@localhost:5432/sabc")


def main():
    engine = create_engine(DATABASE_URL)

    # Define the lake mapping from uppercase duplicates to their original counterparts

    # Actually, let's approach this differently - keep the ones with proper yaml_keys
    # and merge the uppercase duplicates into them
    merges = [
        {"keep": "austin", "remove": "lake_austin"},
        {"keep": "buchanan", "remove": "lake_buchanan"},
        {"keep": "lbj", "remove": "lake_lbj"},
        {"keep": "travis", "remove": "lake_travis"},
        {"keep": "inks", "remove": "inks_lake"},  # Actually keep inks, remove inks_lake
    ]

    with engine.begin() as conn:
        for merge in merges:
            keep_key = merge["keep"]
            remove_key = merge["remove"]

            # Get the lake IDs
            keep_lake = conn.execute(
                text("SELECT id, display_name FROM lakes WHERE yaml_key = :key"), {"key": keep_key}
            ).fetchone()

            remove_lake = conn.execute(
                text("SELECT id, display_name FROM lakes WHERE yaml_key = :key"),
                {"key": remove_key},
            ).fetchone()

            if not keep_lake or not remove_lake:
                print(f"Skipping {keep_key} -> {remove_key}: one or both lakes not found")
                continue

            print(
                f"Merging '{remove_lake.display_name}' (ID: {remove_lake.id}) into '{keep_lake.display_name}' (ID: {keep_lake.id})"
            )

            # Update any tournaments that reference the duplicate lake
            result = conn.execute(
                text("UPDATE tournaments SET lake_id = :keep_id WHERE lake_id = :remove_id"),
                {"keep_id": keep_lake.id, "remove_id": remove_lake.id},
            )
            print(f"  Updated {result.rowcount} tournament records")

            # Update any events that reference the duplicate lake by name
            result = conn.execute(
                text("UPDATE events SET lake_name = :keep_name WHERE lake_name = :remove_name"),
                {"keep_name": keep_lake.display_name, "remove_name": remove_lake.display_name},
            )
            print(f"  Updated {result.rowcount} event records")

            # Update any ramps that might be associated with the duplicate lake
            result = conn.execute(
                text("UPDATE ramps SET lake_id = :keep_id WHERE lake_id = :remove_id"),
                {"keep_id": keep_lake.id, "remove_id": remove_lake.id},
            )
            print(f"  Updated {result.rowcount} ramp records")

            # Remove the duplicate lake
            conn.execute(
                text("DELETE FROM lakes WHERE id = :remove_id"), {"remove_id": remove_lake.id}
            )
            print(f"  Removed duplicate lake '{remove_lake.display_name}'")
            print()

    print("Lake merge completed successfully!")


if __name__ == "__main__":
    main()
