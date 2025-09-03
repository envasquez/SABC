#!/usr/bin/env python3
"""
Migration script to add new fields to the events table for enhanced event management.
Adds: start_time, weigh_in_time, lake_name, ramp_name, entry_fee, is_cancelled
"""

import sqlite3
from pathlib import Path


def migrate_events_table():
    """Add new columns to the events table."""

    db_path = Path("sabc.db")
    if not db_path.exists():
        print("❌ Database file 'sabc.db' not found!")
        return False

    conn = sqlite3.connect("sabc.db")
    cursor = conn.cursor()

    try:
        # Check which columns already exist
        cursor.execute("PRAGMA table_info(events)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        migrations = []

        # Add new columns if they don't exist
        if "start_time" not in existing_columns:
            migrations.append(("start_time", "ALTER TABLE events ADD COLUMN start_time TIME"))

        if "weigh_in_time" not in existing_columns:
            migrations.append(("weigh_in_time", "ALTER TABLE events ADD COLUMN weigh_in_time TIME"))

        if "lake_name" not in existing_columns:
            migrations.append(("lake_name", "ALTER TABLE events ADD COLUMN lake_name TEXT"))

        if "ramp_name" not in existing_columns:
            migrations.append(("ramp_name", "ALTER TABLE events ADD COLUMN ramp_name TEXT"))

        if "entry_fee" not in existing_columns:
            migrations.append(
                ("entry_fee", "ALTER TABLE events ADD COLUMN entry_fee DECIMAL DEFAULT 25.00")
            )

        if "is_cancelled" not in existing_columns:
            migrations.append(
                ("is_cancelled", "ALTER TABLE events ADD COLUMN is_cancelled BOOLEAN DEFAULT 0")
            )

        if "holiday_name" not in existing_columns:
            migrations.append(("holiday_name", "ALTER TABLE events ADD COLUMN holiday_name TEXT"))

        # Update event_type CHECK constraint to include new types
        # First, we need to check current event types
        cursor.execute("SELECT DISTINCT event_type FROM events")
        [row[0] for row in cursor.fetchall()]

        # Apply migrations
        if migrations:
            print("🔄 Applying migrations to events table...")
            for column_name, sql in migrations:
                print(f"  ✅ Adding column: {column_name}")
                cursor.execute(sql)

            conn.commit()
            print(f"\n✅ Successfully added {len(migrations)} new columns to events table")
        else:
            print("ℹ️  All columns already exist, no migration needed")

        # Update the event_type constraint to include new types
        # Note: SQLite doesn't support ALTER COLUMN, so we need to recreate the table
        # For now, let's just document the new types we want to support
        print("\n📝 New event types to support:")
        print("  - sabc_tournament (SABC club tournaments)")
        print("  - federal_holiday (Federal holidays)")
        print("  - other_tournament (External tournaments)")
        print("  - club_event (Meetings, socials, etc.)")

        # Show the current schema
        print("\n📊 Current events table schema:")
        cursor.execute("PRAGMA table_info(events)")
        for row in cursor.fetchall():
            print(
                f"  {row[1]:15} {row[2]:15} {'NOT NULL' if row[3] else 'NULL':8} default={row[4] if row[4] else 'None'}"
            )

        return True

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def update_existing_tournaments():
    """Update existing SABC tournaments with default values."""

    conn = sqlite3.connect("sabc.db")
    cursor = conn.cursor()

    try:
        # Set default times for existing SABC tournaments
        cursor.execute("""
            UPDATE events
            SET start_time = '06:00',
                weigh_in_time = '15:00',
                entry_fee = 25.00
            WHERE event_type = 'sabc_tournament'
            AND start_time IS NULL
        """)

        updated = cursor.rowcount
        if updated > 0:
            conn.commit()
            print(f"\n✅ Updated {updated} existing SABC tournaments with default times and fees")
        else:
            print("\nℹ️  No tournaments needed default values")

    except sqlite3.Error as e:
        print(f"❌ Error updating existing tournaments: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    print("🚀 Starting events table migration...\n")

    if migrate_events_table():
        update_existing_tournaments()
        print("\n✅ Migration completed successfully!")
    else:
        print("\n❌ Migration failed!")
