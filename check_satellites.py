#!/usr/bin/env python3
"""Check satellite data in database."""

import sqlite3
import sys
from pathlib import Path

def check_satellites():
    conn = sqlite3.connect('db/storj_monitor.db')
    cursor = conn.cursor()
    
    print("=== DATABASE TABLES ===")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"{table[0]}: {count} records")
    
    print("\n=== LOOKING FOR SATELLITE DATA ===")
    
    # Check if we have per-satellite data tables
    satellite_tables = ['node_satellite_status', 'satellite_info', 'metrics_satellite']
    for table in satellite_tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"✅ {table}: {count} records")
        except sqlite3.OperationalError:
            print(f"❌ {table}: Table does not exist")
    
    print("\n=== RECENT HEALTH METRICS (with satellite count) ===")
    cursor.execute("""
        SELECT node_name, timestamp, satellites_count, audit_score, suspension_score 
        FROM metrics_health 
        ORDER BY timestamp DESC 
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"Node: {row[0]}, Time: {row[1]}, Satellites: {row[2]}, Audit: {row[3]}, Suspension: {row[4]}")
    
    print("\n=== DAILY BANDWIDTH DATA ===")
    cursor.execute("SELECT COUNT(*) FROM metrics_daily_bandwidth")
    daily_bw_count = cursor.fetchone()[0]
    print(f"Daily bandwidth records: {daily_bw_count}")
    
    if daily_bw_count > 0:
        cursor.execute("SELECT node_name, date, ingress_usage_bytes, egress_usage_bytes FROM metrics_daily_bandwidth ORDER BY date DESC LIMIT 3")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]} - Ingress: {row[2]/(1024**3):.2f}GB, Egress: {row[3]/(1024**3):.2f}GB")
    
    print("\n=== SATELLITES ===\n")
    cursor.execute("SELECT * FROM satellites")
    for row in cursor.fetchall():
        print(f"ID: {row[0]}, Name: {row[1]}, Region: {row[2]}")
    
    print("\n=== NODE SATELLITES (first 10) ===\n")
    cursor.execute("SELECT node_name, satellite_name, is_vetted, vetting_progress, audit_score FROM node_satellites LIMIT 10")
    for row in cursor.fetchall():
        vetted_status = "✅ VETTED" if row[2] else f"🟡 {row[3]*100:.1f}% progress"
        print(f"{row[0]} -> {row[1]}: {vetted_status}, Audit: {row[4]:.3f}")
    
    conn.close()

if __name__ == "__main__":
    check_satellites()