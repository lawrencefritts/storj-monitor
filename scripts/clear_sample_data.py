#!/usr/bin/env python3
"""
Clear sample satellite data from the database.
"""

import sqlite3
import sys
from pathlib import Path

def clear_sample_data():
    """Clear sample satellite data."""
    
    project_root = Path(__file__).parent.parent
    db_path = project_root / "db" / "storj_monitor.db"
    
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Clear satellite data tables
        cursor.execute("DELETE FROM node_satellites")
        cursor.execute("DELETE FROM metrics_daily_satellite")
        
        conn.commit()
        
        print("✅ Sample satellite data cleared!")
        print("The collector will now populate real data from your nodes.")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error clearing sample data: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    if clear_sample_data():
        sys.exit(0)
    else:
        sys.exit(1)