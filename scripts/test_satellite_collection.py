#!/usr/bin/env python3
"""
Test script to run a single collection cycle and verify satellite data collection.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from collector.service import StorjCollector

async def test_collection():
    """Run a single collection cycle to test satellite data extraction."""
    
    collector = StorjCollector()
    
    print("🚀 Starting test collection with satellite data extraction...")
    
    try:
        # Run a single collection cycle
        await collector.collect_all_metrics()
        print("✅ Collection completed successfully!")
        
        # Check what was collected
        import sqlite3
        db_path = Path(__file__).parent.parent / "db" / "storj_monitor.db"
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check satellite status records
        cursor.execute("SELECT COUNT(*) FROM node_satellites")
        satellite_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM metrics_daily_satellite") 
        daily_satellite_count = cursor.fetchone()[0]
        
        print(f"📊 Collection Results:")
        print(f"   • Satellite status records: {satellite_count}")
        print(f"   • Daily satellite metrics: {daily_satellite_count}")
        
        if satellite_count > 0:
            print("\\n🛰️ Satellite Status Summary:")
            cursor.execute("""
                SELECT node_name, satellite_name, is_vetted, 
                       ROUND(vetting_progress * 100, 1) as progress_pct
                FROM latest_satellite_status 
                ORDER BY node_name, satellite_name
            """)
            
            for row in cursor.fetchall():
                node_name, sat_name, is_vetted, progress = row
                status = "VETTED" if is_vetted else f"{progress}%"
                print(f"   • {node_name} -> {sat_name}: {status}")
        
        if daily_satellite_count > 0:
            print("\\n📈 Recent Daily Metrics:")
            cursor.execute("""
                SELECT node_name, satellite_id, date, 
                       ingress_usage_bytes, egress_usage_bytes
                FROM metrics_daily_satellite 
                WHERE date >= date('now', '-7 days')
                ORDER BY date DESC, node_name 
                LIMIT 10
            """)
            
            for row in cursor.fetchall():
                node_name, sat_id, date, ingress, egress = row
                sat_name = next((v['name'] for k, v in collector.satellite_extractor.KNOWN_SATELLITES.items() if k == sat_id), sat_id[:8])
                print(f"   • {node_name} -> {sat_name} ({date}): {ingress/1024/1024:.1f}MB in, {egress/1024/1024:.1f}MB out")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Collection failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    if asyncio.run(test_collection()):
        print("\\n🎉 Satellite data collection test completed successfully!")
        print("   • Check your dashboard at /db to explore the satellite data")
        print("   • Try the new satellite API endpoints")
        sys.exit(0)
    else:
        print("\\n❌ Test failed!")
        sys.exit(1)