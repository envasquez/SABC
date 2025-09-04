#!/usr/bin/env python3
"""
Migration script to remove the is_cancelled column from the events table.
This column was not working properly and the feature has been removed.
"""

import sqlite3
from pathlib import Path


def remove_is_cancelled_column():
    """Remove the is_cancelled column from the events table."""

    db_path = Path("sabc.db")
    if not db_path.exists():
        print("❌ Database file 'sabc.db' not found!")
        return False

    conn = sqlite3.connect("sabc.db")
    cursor = conn.cursor()

    try:
        # Check if the column exists
        cursor.execute("PRAGMA table_info(events)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "is_cancelled" not in columns:
            print("ℹ️  Column 'is_cancelled' does not exist, no migration needed")
            return True

        print("🔄 Removing 'is_cancelled' column from events table...")

        # Drop views that depend on the events table
        views_to_drop = ['tournament_standings', 'angler_of_year', 'big_bass_of_year', 'tournament_payouts', 'active_polls']
        for view in views_to_drop:
            try:
                cursor.execute(f"DROP VIEW IF EXISTS {view}")
                print(f"  📊 Dropped view: {view}")
            except sqlite3.Error:
                pass  # View might not exist

        # SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
        # First, create the new table without the is_cancelled column
        cursor.execute("""
            CREATE TABLE events_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                year INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                event_type TEXT DEFAULT 'sabc_tournament',
                start_time TIME,
                weigh_in_time TIME,
                lake_name TEXT,
                ramp_name TEXT,
                entry_fee DECIMAL DEFAULT 25.00,
                holiday_name TEXT
            )
        """)

        # Copy data from old table to new table (excluding is_cancelled)
        cursor.execute("""
            INSERT INTO events_new (id, date, year, name, description, event_type, 
                                  start_time, weigh_in_time, lake_name, ramp_name, 
                                  entry_fee, holiday_name)
            SELECT id, date, year, name, description, event_type, 
                   start_time, weigh_in_time, lake_name, ramp_name, 
                   entry_fee, holiday_name
            FROM events
        """)

        # Drop the old table
        cursor.execute("DROP TABLE events")

        # Rename the new table
        cursor.execute("ALTER TABLE events_new RENAME TO events")

        conn.commit()
        print("✅ Successfully removed 'is_cancelled' column from events table")

        # Show the current schema
        print("\n📊 Updated events table schema:")
        cursor.execute("PRAGMA table_info(events)")
        for row in cursor.fetchall():
            print(
                f"  {row[1]:15} {row[2]:15} {'NOT NULL' if row[3] else 'NULL':8} default={row[4] if row[4] else 'None'}"
            )

        print("\n⚠️  Note: Views have been dropped and will need to be recreated.")
        print("Run: python database.py to recreate views")

        return True

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    print("🚀 Starting is_cancelled column removal migration...\n")

    if remove_is_cancelled_column():
        print("\n✅ Migration completed successfully!")
    else:
        print("\n❌ Migration failed!")