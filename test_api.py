#!/usr/bin/env python3
"""Test API endpoints to see what data is returned."""

import sys
import asyncio
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from webapp.database import DatabaseManager
from storj_monitor.config import load_settings

async def test_api():
    # Load settings first
    load_settings()
    db = DatabaseManager()
    
    print("=== TESTING API ENDPOINTS ===")
    
    # Test node status
    print("\n1. Node Status:")
    nodes = await db.get_latest_node_status()
    for node in nodes:
        print(f"  {node.name}: Health={node.health_status}, Disk Used={node.disk_used/(1024**3):.2f}GB, Satellites={node.satellites_count}")
        print(f"    Audit Score: {node.audit_score}, Suspension Score: {node.suspension_score}")
    
    # Test system summary
    print("\n2. System Summary:")
    summary = await db.get_system_summary()
    print(f"  {json.dumps(summary, indent=2)}")
    
    # Test individual node
    if nodes:
        node_name = nodes[0].name
        print(f"\n3. Individual Node ({node_name}):")
        node = await db.get_node_status(node_name)
        if node:
            print(f"  Name: {node.name}")
            print(f"  Node ID: {node.node_id}")
            print(f"  Health Status: {node.health_status}")
            print(f"  Disk Usage: {node.disk_usage_percentage:.1f}% ({node.disk_used/(1024**3):.2f}GB used)")
            print(f"  Satellites: {node.satellites_count}")
            print(f"  Scores: Audit={node.audit_score}, Suspension={node.suspension_score}, Online={node.online_score}")
    
    # Test disk usage history
    print(f"\n4. Disk Usage History (last 24h):")
    if nodes:
        disk_data = await db.get_disk_usage_history(nodes[0].name, 24)
        print(f"  Found {len(disk_data)} disk usage records")
        if disk_data:
            latest = disk_data[-1]
            print(f"  Latest: {latest['timestamp']}, Used: {latest['used_bytes']/(1024**3):.2f}GB")

if __name__ == "__main__":
    asyncio.run(test_api())