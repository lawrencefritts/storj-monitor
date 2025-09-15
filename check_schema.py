#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('db/storj_monitor.db')
cursor = conn.cursor()

cursor.execute('PRAGMA table_info(node_satellites)')
print('node_satellites schema:')
for row in cursor.fetchall():
    print(f'  {row[1]} ({row[2]})')

cursor.execute('SELECT * FROM node_satellites LIMIT 3')
print('\nFirst 3 records:')
for row in cursor.fetchall():
    print(f'  {row}')

conn.close()