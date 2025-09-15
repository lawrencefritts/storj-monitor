#!/usr/bin/env python
"""Trigger immediate data collection from Storj nodes."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import storj_monitor
sys.path.insert(0, str(Path(__file__).parent.parent))

from collector.service import StorjCollector

async def collect_now():
    """Run a single collection cycle immediately."""
    print("🚀 Starting immediate data collection...")
    
    try:
        collector = StorjCollector()
        await collector.collect_all_metrics()
        print("✅ Data collection completed successfully!")
        print("🌐 You can now refresh your dashboard at http://127.0.0.1:8080")
    except Exception as e:
        print(f"❌ Data collection failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(collect_now())
    sys.exit(exit_code)