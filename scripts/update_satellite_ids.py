#!/usr/bin/env python3
"""
Update satellite IDs in database to match actual node responses.
"""

import sqlite3
import sys
from pathlib import Path

def update_satellite_ids():
    """Update satellite IDs in the database."""
    
    project_root = Path(__file__).parent.parent
    db_path = project_root / "db" / "storj_monitor.db"
    
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Update the US1 satellite ID to the correct one
        cursor.execute("""
            UPDATE satellites 
            SET satellite_id = '12EayRS2V1kEsWESU9QMRseFhdxYxKicsiFmxrsLZHeLUtdps3S'
            WHERE name = 'us1' AND satellite_id = '12EayRS2V1kEsWESU9QMRseFhdxYxKicsiFHpkmn1LT3StBp1R'
        """)
        
        # Add the correct US1 satellite if it doesn't exist
        cursor.execute("""
            INSERT OR IGNORE INTO satellites (satellite_id, name, region, description) VALUES 
            ('12EayRS2V1kEsWESU9QMRseFhdxYxKicsiFmxrsLZHeLUtdps3S', 'us1', 'North America', 'US Central 1')
        """)
        
        conn.commit()
        
        # Show current satellites
        cursor.execute("SELECT satellite_id, name, region FROM satellites ORDER BY name")
        satellites = cursor.fetchall()
        
        print("✅ Satellite IDs updated!")
        print("\\n🛰️ Current satellites in database:")
        for sat_id, name, region in satellites:
            print(f"   • {name}: {sat_id[:20]}... ({region})")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error updating satellite IDs: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    if update_satellite_ids():
        sys.exit(0)
    else:
        sys.exit(1)