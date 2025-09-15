#!/usr/bin/env python3
"""Check database contents."""

import sqlite3
from datetime import datetime

def check_database():
    conn = sqlite3.connect('db/storj_monitor.db')
    cursor = conn.cursor()
    
    print("=== NODES ===")
    cursor.execute('SELECT name, node_id, description, created_at FROM nodes')
    for row in cursor.fetchall():
        print(f'Name: {row[0]}, ID: {row[1]}, Desc: {row[2]}, Created: {row[3]}')
    
    print("\n=== RECENT HEALTH METRICS ===")
    cursor.execute('SELECT node_name, timestamp, audit_score, suspension_score, satellites_count FROM metrics_health ORDER BY timestamp DESC LIMIT 5')
    for row in cursor.fetchall():
        print(f'Node: {row[0]}, Time: {row[1]}, Audit: {row[2]}, Suspension: {row[3]}, Satellites: {row[4]}')
    
    print("\n=== RECENT DISK METRICS ===")
    cursor.execute('SELECT node_name, timestamp, used_bytes, available_bytes FROM metrics_disk ORDER BY timestamp DESC LIMIT 5')
    for row in cursor.fetchall():
        used_gb = row[2] / (1024**3) if row[2] else 0
        available_gb = row[3] / (1024**3) if row[3] else 0
        print(f'Node: {row[0]}, Time: {row[1]}, Used: {used_gb:.2f}GB, Available: {available_gb:.2f}GB')
    
    print("\n=== DATABASE TABLE COUNTS ===")
    tables = ['nodes', 'metrics_disk', 'metrics_bandwidth', 'metrics_health', 'metrics_daily_bandwidth', 'metrics_daily_storage']
    for table in tables:
        cursor.execute(f'SELECT COUNT(*) FROM {table}')
        count = cursor.fetchone()[0]
        print(f'{table}: {count} records')
    
    conn.close()

if __name__ == "__main__":
    check_database()