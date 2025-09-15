#!/usr/bin/env python3
"""
Database migration script for Storj Monitor Schema v2
Adds per-satellite tracking and vetting status support
"""

import sqlite3
import sys
from pathlib import Path

def run_migration():
    """Run the database migration to schema v2."""
    
    # Get paths
    project_root = Path(__file__).parent.parent
    db_path = project_root / "db" / "storj_monitor.db"
    schema_path = project_root / "db" / "schema_v2.sql"
    
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return False
        
    if not schema_path.exists():
        print(f"Error: Schema file not found at {schema_path}")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current schema version
        cursor.execute("SELECT MAX(version) FROM schema_versions")
        current_version = cursor.fetchone()[0] or 0
        
        print(f"Current schema version: {current_version}")
        
        if current_version >= 2:
            print("Schema v2 already applied!")
            conn.close()
            return True
        
        # Read and execute schema v2
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        print("Applying schema v2 migration...")
        cursor.executescript(schema_sql)
        conn.commit()
        
        # Verify migration
        cursor.execute("SELECT MAX(version) FROM schema_versions")
        new_version = cursor.fetchone()[0]
        
        print(f"Migration complete! New schema version: {new_version}")
        
        # Show new tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%satellite%'")
        satellite_tables = cursor.fetchall()
        print(f"Added satellite-related tables: {[table[0] for table in satellite_tables]}")
        
        # Show new views
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view' AND name LIKE '%satellite%'")
        satellite_views = cursor.fetchall()
        print(f"Added satellite-related views: {[view[0] for view in satellite_views]}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    if run_migration():
        print("\n✅ Database migration completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Database migration failed!")
        sys.exit(1)