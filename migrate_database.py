#!/usr/bin/env python3
"""
Database migration script to add missing columns
"""
import sqlite3
import os

def migrate_database():
    """Add missing columns to existing tables if they don't exist"""
    
    if not os.path.exists('sabc.db'):
        print("No database found, skipping migration")
        return
    
    conn = sqlite3.connect('sabc.db')
    cursor = conn.cursor()
    
    # Check and add missing columns to anglers table
    cursor.execute("PRAGMA table_info(anglers)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'year_joined' not in columns:
        print("Adding year_joined column to anglers table...")
        cursor.execute("ALTER TABLE anglers ADD COLUMN year_joined INTEGER")
    
    if 'phone' not in columns:
        print("Adding phone column to anglers table...")
        cursor.execute("ALTER TABLE anglers ADD COLUMN phone TEXT")
    
    # Check and add missing columns to tournaments table
    cursor.execute("PRAGMA table_info(tournaments)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'limit_type' not in columns:
        print("Adding limit_type column to tournaments table...")
        cursor.execute("ALTER TABLE tournaments ADD COLUMN limit_type TEXT DEFAULT 'angler'")
    
    conn.commit()
    conn.close()
    print("Database migration complete")

if __name__ == "__main__":
    migrate_database()