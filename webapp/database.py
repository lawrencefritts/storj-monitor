"""Database access layer for the web API."""

import aiosqlite
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from storj_monitor.config import get_settings
from storj_monitor.models import NodeStatus, NodeSatelliteStatus, VettingSummary, SatelliteInfo
from storj_monitor.utils import bytes_to_human_readable


logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and queries for the web API."""

    def __init__(self):
        self.settings = get_settings()
        self.db_path = Path(self.settings.database.path)

    def get_connection(self):
        """Get a database connection."""
        return aiosqlite.connect(self.db_path)

    async def get_latest_node_status(self) -> List[NodeStatus]:
        """Get the latest status for all nodes."""
        async with self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM node_overview_with_satellites
                ORDER BY name
            """)
            rows = await cursor.fetchall()
            
            return [NodeStatus(**dict(row)) for row in rows]

    async def get_node_status(self, node_name: str) -> Optional[NodeStatus]:
        """Get status for a specific node."""
        async with self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM latest_node_status WHERE name = ?
            """, (node_name,))
            row = await cursor.fetchone()
            
            return NodeStatus(**dict(row)) if row else None

    async def get_disk_usage_history(self, node_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get disk usage history for a node."""
        since_time = datetime.utcnow() - timedelta(hours=hours)
        
        async with self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT timestamp, used_bytes, available_bytes, trash_bytes
                FROM metrics_disk 
                WHERE node_name = ? AND timestamp >= ?
                ORDER BY timestamp
            """, (node_name, since_time))
            rows = await cursor.fetchall()
            
            return [
                {
                    'timestamp': row['timestamp'],
                    'used_gb': round(row['used_bytes'] / (1024**3), 2),
                    'available_gb': round(row['available_bytes'] / (1024**3), 2),
                    'trash_gb': round(row['trash_bytes'] / (1024**3), 2),
                    'usage_percentage': round((row['used_bytes'] / (row['used_bytes'] + row['available_bytes']) * 100), 2) if (row['used_bytes'] + row['available_bytes']) > 0 else 0
                }
                for row in rows
            ]

    async def get_bandwidth_usage_history(self, node_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get bandwidth usage history for a node."""
        since_time = datetime.utcnow() - timedelta(hours=hours)
        
        async with self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT timestamp, used_bytes
                FROM metrics_bandwidth 
                WHERE node_name = ? AND timestamp >= ?
                ORDER BY timestamp
            """, (node_name, since_time))
            rows = await cursor.fetchall()
            
            return [
                {
                    'timestamp': row['timestamp'],
                    'used_gb': round(row['used_bytes'] / (1024**3), 2)
                }
                for row in rows
            ]

    async def get_daily_bandwidth_summary(self, node_name: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily bandwidth summary for a node."""
        since_date = date.today() - timedelta(days=days)
        
        async with self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT date, total_ingress, total_egress
                FROM daily_summary 
                WHERE node_name = ? AND date >= ?
                ORDER BY date
            """, (node_name, since_date))
            rows = await cursor.fetchall()
            
            return [
                {
                    'date': row['date'],
                    'ingress_gb': round((row['total_ingress'] or 0) / (1024**3), 2),
                    'egress_gb': round((row['total_egress'] or 0) / (1024**3), 2),
                    'total_gb': round(((row['total_ingress'] or 0) + (row['total_egress'] or 0)) / (1024**3), 2)
                }
                for row in rows
            ]

    async def get_health_metrics_history(self, node_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get health metrics history for a node."""
        since_time = datetime.utcnow() - timedelta(hours=hours)
        
        async with self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT timestamp, audit_score, suspension_score, online_score, 
                       uptime_seconds, satellites_count
                FROM metrics_health 
                WHERE node_name = ? AND timestamp >= ?
                ORDER BY timestamp
            """, (node_name, since_time))
            rows = await cursor.fetchall()
            
            return [
                {
                    'timestamp': row['timestamp'],
                    'audit_score': round(row['audit_score'], 4),
                    'suspension_score': round(row['suspension_score'], 4),
                    'online_score': round(row['online_score'], 4),
                    'uptime_hours': round(row['uptime_seconds'] / 3600, 1),
                    'satellites_count': row['satellites_count']
                }
                for row in rows
            ]

    async def get_system_summary(self) -> Dict[str, Any]:
        """Get overall system summary."""
        async with self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            
            # Get total counts
            cursor = await db.execute("SELECT COUNT(*) as node_count FROM nodes")
            node_count = (await cursor.fetchone())['node_count']
            
            cursor = await db.execute("SELECT COUNT(*) as total_records FROM metrics_disk")
            total_records = (await cursor.fetchone())['total_records']
            
            # Get latest metrics summary
            cursor = await db.execute("""
                SELECT 
                    SUM(disk_used) as total_disk_used,
                    SUM(disk_available) as total_disk_available,
                    SUM(bandwidth_used) as total_bandwidth_used,
                    AVG(audit_score) as avg_audit_score,
                    MIN(audit_score) as min_audit_score,
                    COUNT(*) as active_nodes
                FROM latest_node_status 
                WHERE disk_used IS NOT NULL
            """)
            summary_row = await cursor.fetchone()
            
            # Get database size
            cursor = await db.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            db_size = (await cursor.fetchone())['size']
            
            # Get oldest and newest records
            cursor = await db.execute("SELECT MIN(timestamp) as oldest, MAX(timestamp) as newest FROM metrics_disk")
            time_range = await cursor.fetchone()
            
            return {
                'node_count': node_count,
                'active_nodes': summary_row['active_nodes'] if summary_row else 0,
                'total_records': total_records,
                'database_size_mb': round(db_size / (1024**2), 2) if db_size else 0,
                'data_range': {
                    'oldest': time_range['oldest'],
                    'newest': time_range['newest']
                },
                'storage_summary': {
                    'total_used_gb': round((summary_row['total_disk_used'] or 0) / (1024**3), 2),
                    'total_available_gb': round((summary_row['total_disk_available'] or 0) / (1024**3), 2),
                    'usage_percentage': round((summary_row['total_disk_used'] or 0) / ((summary_row['total_disk_used'] or 0) + (summary_row['total_disk_available'] or 1)) * 100, 2)
                },
                'health_summary': {
                    'avg_audit_score': round(summary_row['avg_audit_score'] or 0, 4),
                    'min_audit_score': round(summary_row['min_audit_score'] or 0, 4),
                    'total_bandwidth_used_gb': round((summary_row['total_bandwidth_used'] or 0) / (1024**3), 2)
                }
            }

    async def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent important events (score drops, downtimes, etc.)."""
        async with self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            
            # Get recent health metrics with potential issues
            cursor = await db.execute("""
                SELECT node_name, timestamp, audit_score, suspension_score, online_score
                FROM metrics_health 
                WHERE audit_score < 0.99 OR suspension_score < 0.99 OR online_score < 0.95
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            rows = await cursor.fetchall()
            
            events = []
            for row in rows:
                event_type = "warning"
                message = f"Node {row['node_name']}"
                details = []
                
                if row['audit_score'] < 0.95:
                    event_type = "critical"
                    details.append(f"audit score: {row['audit_score']:.3f}")
                elif row['audit_score'] < 0.99:
                    details.append(f"audit score: {row['audit_score']:.3f}")
                
                if row['suspension_score'] < 0.95:
                    event_type = "critical"
                    details.append(f"suspension score: {row['suspension_score']:.3f}")
                elif row['suspension_score'] < 0.99:
                    details.append(f"suspension score: {row['suspension_score']:.3f}")
                
                if row['online_score'] < 0.95:
                    details.append(f"online score: {row['online_score']:.3f}")
                
                if details:
                    message += f" - {', '.join(details)}"
                    events.append({
                        'timestamp': row['timestamp'],
                        'node_name': row['node_name'],
                        'type': event_type,
                        'message': message
                    })
            
            return events

    async def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema information."""
        async with self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            
            # Get all tables
            cursor = await db.execute("""
                SELECT name, type FROM sqlite_master 
                WHERE type IN ('table', 'view')
                ORDER BY type DESC, name
            """)
            tables = await cursor.fetchall()
            
            schema_info = {"tables": [], "views": []}
            
            for table in tables:
                table_name = table['name']
                table_type = table['type']
                
                # Get column information
                cursor = await db.execute(f"PRAGMA table_info({table_name})")
                columns = await cursor.fetchall()
                
                # Get row count
                cursor = await db.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                row_count = (await cursor.fetchone())['count']
                
                table_info = {
                    "name": table_name,
                    "columns": [dict(col) for col in columns],
                    "row_count": row_count
                }
                
                if table_type == 'table':
                    schema_info["tables"].append(table_info)
                else:
                    schema_info["views"].append(table_info)
            
            return schema_info

    async def get_table_data(self, table_name: str, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Get data from a specific table or view."""
        async with self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            
            # Validate table name to prevent SQL injection
            cursor = await db.execute("""
                SELECT name FROM sqlite_master 
                WHERE type IN ('table', 'view') AND name = ?
            """, (table_name,))
            if not await cursor.fetchone():
                raise ValueError(f"Table or view '{table_name}' not found")
            
            # Get total count
            cursor = await db.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            total_count = (await cursor.fetchone())['count']
            
            # Get data with limit and offset
            cursor = await db.execute(
                f"SELECT * FROM {table_name} ORDER BY rowid DESC LIMIT ? OFFSET ?", 
                (limit, offset)
            )
            rows = await cursor.fetchall()
            
            # Convert rows to dictionaries
            data = [dict(row) for row in rows]
            
            return {
                "table_name": table_name,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "data": data
            }

    async def execute_query(self, query: str) -> Dict[str, Any]:
        """Execute a read-only SQL query (for debugging/admin purposes)."""
        # Basic safety check - only allow SELECT statements
        query = query.strip()
        if not query.upper().startswith('SELECT'):
            raise ValueError("Only SELECT queries are allowed")
            
        async with self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            
            try:
                cursor = await db.execute(query)
                rows = await cursor.fetchall()
                
                return {
                    "query": query,
                    "row_count": len(rows),
                    "data": [dict(row) for row in rows]
                }
            except Exception as e:
                return {
                    "query": query,
                    "error": str(e),
                    "data": []
                }

    async def get_satellites(self) -> List[SatelliteInfo]:
        """Get all satellites information."""
        async with self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT satellite_id, name, region, description
                FROM satellites
                ORDER BY name
            """)
            rows = await cursor.fetchall()
            
            return [SatelliteInfo(**dict(row)) for row in rows]

    async def get_node_satellite_status(self, node_name: str) -> List[NodeSatelliteStatus]:
        """Get satellite status for a specific node."""
        async with self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM latest_satellite_status 
                WHERE node_name = ?
                ORDER BY satellite_name
            """, (node_name,))
            rows = await cursor.fetchall()
            
            return [NodeSatelliteStatus(**dict(row)) for row in rows]

    async def get_all_satellite_status(self) -> Dict[str, List[NodeSatelliteStatus]]:
        """Get satellite status for all nodes."""
        async with self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM latest_satellite_status 
                ORDER BY node_name, satellite_name
            """)
            rows = await cursor.fetchall()
            
            # Group by node name
            node_satellites = {}
            for row in rows:
                node_name = row['node_name']
                if node_name not in node_satellites:
                    node_satellites[node_name] = []
                node_satellites[node_name].append(NodeSatelliteStatus(**dict(row)))
            
            return node_satellites

    async def get_vetting_summary(self, node_name: Optional[str] = None) -> List[VettingSummary]:
        """Get vetting summary for nodes."""
        async with self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            
            if node_name:
                cursor = await db.execute("""
                    SELECT * FROM vetting_summary WHERE node_name = ?
                """, (node_name,))
            else:
                cursor = await db.execute("SELECT * FROM vetting_summary ORDER BY node_name")
            
            rows = await cursor.fetchall()
            return [VettingSummary(**dict(row)) for row in rows]

    async def get_satellite_comparison(self) -> Dict[str, Any]:
        """Get comparison data across all satellites."""
        async with self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            
            # Get per-satellite stats
            cursor = await db.execute("""
                SELECT 
                    s.name as satellite_name,
                    s.region,
                    COUNT(lss.node_name) as total_nodes,
                    SUM(CASE WHEN lss.is_vetted = 1 THEN 1 ELSE 0 END) as vetted_nodes,
                    AVG(lss.vetting_progress) as avg_vetting_progress,
                    AVG(lss.audit_score) as avg_audit_score,
                    AVG(lss.suspension_score) as avg_suspension_score,
                    AVG(lss.online_score) as avg_online_score,
                    SUM(lss.current_month_egress) as total_egress,
                    SUM(lss.current_month_ingress) as total_ingress
                FROM satellites s
                LEFT JOIN latest_satellite_status lss ON s.satellite_id = lss.satellite_id
                GROUP BY s.satellite_id, s.name, s.region
                ORDER BY s.name
            """)
            satellite_stats = await cursor.fetchall()
            
            return {
                "satellites": [dict(row) for row in satellite_stats],
                "summary": {
                    "total_satellites": len(satellite_stats),
                    "total_node_satellite_pairs": sum(row['total_nodes'] for row in satellite_stats),
                    "total_vetted_pairs": sum(row['vetted_nodes'] for row in satellite_stats)
                }
            }
