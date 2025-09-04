#!/usr/bin/env python3
"""
Migration script to fix federal holiday event types.
Changes 'holiday' to 'federal_holiday' to match the frontend expectations.
"""

import sqlite3
from pathlib import Path


def fix_holiday_event_types():
    """Update event_type from 'holiday' to 'federal_holiday'."""

    db_path = Path("sabc.db")
    if not db_path.exists():
        print("❌ Database file 'sabc.db' not found!")
        return False

    conn = sqlite3.connect("sabc.db")
    cursor = conn.cursor()

    try:
        # Check how many holiday events exist
        cursor.execute("SELECT COUNT(*) FROM events WHERE event_type = 'holiday'")
        holiday_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM events WHERE event_type = 'federal_holiday'")
        federal_holiday_count = cursor.fetchone()[0]

        print(f"📊 Found {holiday_count} events with event_type = 'holiday'")
        print(f"📊 Found {federal_holiday_count} events with event_type = 'federal_holiday'")

        if holiday_count == 0:
            print("ℹ️  No events with 'holiday' event_type found, no migration needed")
            return True

        print(f"🔄 Converting {holiday_count} holiday events to federal_holiday...")

        # Update event_type from 'holiday' to 'federal_holiday'
        cursor.execute("""
            UPDATE events 
            SET event_type = 'federal_holiday' 
            WHERE event_type = 'holiday'
        """)

        updated_count = cursor.rowcount
        conn.commit()
        
        print(f"✅ Successfully updated {updated_count} events from 'holiday' to 'federal_holiday'")

        # Verify the update
        cursor.execute("SELECT COUNT(*) FROM events WHERE event_type = 'federal_holiday'")
        final_count = cursor.fetchone()[0]
        print(f"📊 Total federal_holiday events after update: {final_count}")

        return True

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    print("🚀 Starting federal holiday event type migration...\n")

    if fix_holiday_event_types():
        print("\n✅ Migration completed successfully!")
        print("📝 Events management page should now show federal holidays correctly.")
    else:
        print("\n❌ Migration failed!")