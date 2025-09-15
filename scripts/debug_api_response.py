#!/usr/bin/env python3
"""
Debug script to examine the actual Storj API response structure.
"""

import asyncio
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from storj_monitor.config import load_settings
from storj_monitor.utils import create_http_client

async def debug_api_responses():
    """Debug the actual API responses from Storj nodes."""
    
    settings = load_settings()
    
    print("🔍 Examining actual API responses from your Storj nodes...")
    
    for node in settings.nodes[:1]:  # Just check first node
        print(f"\\n📡 Node: {node.name} ({node.dashboard_url})")
        
        async with create_http_client() as client:
            try:
                # Get /api/sno response
                sno_url = f"{node.dashboard_url}/api/sno"
                sno_data = await client.fetch_json(sno_url)
                
                print("\\n🛰️ Satellites from /api/sno:")
                if 'satellites' in sno_data and sno_data['satellites']:
                    for i, satellite in enumerate(sno_data['satellites']):
                        print(f"   Satellite {i+1}:")
                        for key, value in satellite.items():
                            if isinstance(value, (int, float)) and value > 1000000:
                                # Format large numbers
                                print(f"     {key}: {value:,}")
                            else:
                                print(f"     {key}: {value}")
                        print()
                else:
                    print("   No satellites found or empty list")
                
                # Get /api/sno/satellites response  
                satellites_url = f"{node.dashboard_url}/api/sno/satellites"
                satellites_data = await client.fetch_json(satellites_url)
                
                print("\\n📊 Audits from /api/sno/satellites:")
                if 'audits' in satellites_data and satellites_data['audits']:
                    for i, audit in enumerate(satellites_data['audits']):
                        print(f"   Audit {i+1}:")
                        for key, value in audit.items():
                            if isinstance(value, float) and key.endswith('Score'):
                                print(f"     {key}: {value:.6f}")
                            else:
                                print(f"     {key}: {value}")
                        print()
                else:
                    print("   No audits found")
                
                print("\\n📈 Bandwidth Daily:")
                if 'bandwidthDaily' in satellites_data and satellites_data['bandwidthDaily']:
                    recent_bw = satellites_data['bandwidthDaily'][-5:]  # Last 5 entries
                    for entry in recent_bw:
                        interval = entry.get('intervalStart', 'unknown')
                        ingress = entry.get('ingress', {})
                        egress = entry.get('egress', {})
                        print(f"     {interval}: Ingress {ingress.get('usage', 0):,}, Egress {egress.get('usage', 0):,}")
                else:
                    print("   No bandwidth daily data")
                
            except Exception as e:
                print(f"   ❌ Error fetching data from {node.name}: {e}")

if __name__ == "__main__":
    asyncio.run(debug_api_responses())