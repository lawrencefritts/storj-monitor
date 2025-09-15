#!/usr/bin/env python3
"""
Populate sample satellite data for testing the new satellite features.
This will add mock data to demonstrate the satellite tracking functionality.
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
import random

def populate_sample_data():
    """Populate sample satellite data."""
    
    project_root = Path(__file__).parent.parent
    db_path = project_root / "db" / "storj_monitor.db"
    
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get existing nodes
        cursor.execute("SELECT name FROM nodes")
        nodes = [row[0] for row in cursor.fetchall()]
        
        if not nodes:
            print("No nodes found in database. Add some nodes first.")
            return False
        
        print(f"Found {len(nodes)} nodes: {nodes}")
        
        # Get satellites
        cursor.execute("SELECT satellite_id, name FROM satellites")
        satellites = cursor.fetchall()
        
        print(f"Found {len(satellites)} satellites: {[s[1] for s in satellites]}")
        
        # Add sample satellite status for each node
        timestamp = datetime.utcnow()
        
        for node_name in nodes:
            for satellite_id, satellite_name in satellites:
                # Generate random but realistic data
                is_vetted = random.choice([True, False, False, True])  # 50% chance
                vetting_progress = 1.0 if is_vetted else random.uniform(0.1, 0.9)
                vetted_at = timestamp - timedelta(days=random.randint(30, 200)) if is_vetted else None
                
                # Generate realistic scores
                audit_score = random.uniform(0.95, 1.0)
                suspension_score = random.uniform(0.98, 1.0)
                online_score = random.uniform(0.95, 1.0)
                
                # Generate join date (node joined this satellite weeks/months ago)
                joined_at = timestamp - timedelta(days=random.randint(60, 365))
                
                # Generate current month bandwidth (in bytes)
                current_month_egress = random.randint(100_000_000, 50_000_000_000)  # 100MB to 50GB
                current_month_ingress = random.randint(500_000_000, 20_000_000_000)  # 500MB to 20GB
                
                cursor.execute("""
                    INSERT OR REPLACE INTO node_satellites 
                    (node_name, satellite_id, timestamp, is_vetted, vetting_progress, vetted_at,
                     audit_score, suspension_score, online_score, joined_at, 
                     current_month_egress, current_month_ingress)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    node_name, satellite_id, timestamp, is_vetted, vetting_progress, vetted_at,
                    audit_score, suspension_score, online_score, joined_at,
                    current_month_egress, current_month_ingress
                ))
                
                print(f"Added sample data for {node_name} -> {satellite_name} (vetted: {is_vetted}, progress: {vetting_progress:.1%})")
        
        # Add some sample daily satellite metrics for the past 30 days
        for node_name in nodes:
            for satellite_id, satellite_name in satellites:
                for days_ago in range(30):
                    metric_date = date.today() - timedelta(days=days_ago)
                    
                    # Generate realistic daily metrics
                    storage_used = random.randint(1_000_000_000, 100_000_000_000)  # 1GB to 100GB
                    ingress_usage = random.randint(0, 2_000_000_000)  # 0 to 2GB
                    egress_usage = random.randint(0, 5_000_000_000)   # 0 to 5GB
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO metrics_daily_satellite
                        (node_name, satellite_id, date, storage_used_bytes, storage_at_rest_bytes,
                         ingress_usage_bytes, egress_usage_bytes, vetting_bandwidth_requirement,
                         vetting_bandwidth_completed)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        node_name, satellite_id, metric_date, storage_used, storage_used,
                        ingress_usage, egress_usage, 1024**4,  # 1TB requirement
                        ingress_usage + egress_usage
                    ))
        
        conn.commit()
        
        # Show summary
        cursor.execute("SELECT COUNT(*) FROM node_satellites")
        satellite_records = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM metrics_daily_satellite")
        daily_records = cursor.fetchone()[0]
        
        cursor.execute("SELECT * FROM vetting_summary")
        vetting_summary = cursor.fetchall()
        
        print(f"\n✅ Sample data populated successfully!")
        print(f"   • {satellite_records} satellite status records")
        print(f"   • {daily_records} daily satellite metrics")
        print(f"   • Vetting summary for {len(vetting_summary)} nodes")
        
        print("\\n📊 Vetting Summary:")
        for row in vetting_summary:
            node_name, total_sats, vetted_count, avg_progress = row[:4]
            print(f"   • {node_name}: {vetted_count}/{total_sats} satellites vetted ({avg_progress:.1%} avg progress)")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error populating sample data: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    if populate_sample_data():
        print("\n🎉 You can now test the satellite features!")
        print("   • Visit /db in your browser to explore the new tables and views")
        print("   • Try the satellite query examples")
        print("   • Check the API endpoints: /api/satellites, /api/vetting/summary")
        sys.exit(0)
    else:
        print("\n❌ Failed to populate sample data!")
        sys.exit(1)