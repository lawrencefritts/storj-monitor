"""Integration tests for Storj Monitor components."""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock, patch
import aiosqlite
import respx
import httpx

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from storj_monitor.config import Settings
from collector.service import StorjCollector


class TestCollectorIntegration:
    """Integration tests for the collector service."""
    
    @pytest.fixture
    async def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            db_path = tmp.name
        
        # Initialize database with schema
        async with aiosqlite.connect(db_path) as db:
            schema_path = Path(__file__).parent.parent / "db" / "schema.sql"
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            await db.executescript(schema_sql)
            
            # Add test nodes
            await db.execute(
                "INSERT INTO nodes (name, dashboard_url, description) VALUES (?, ?, ?)",
                ("test_node1", "http://192.168.177.133:14002", "Test Node 1")
            )
            await db.execute(
                "INSERT INTO nodes (name, dashboard_url, description) VALUES (?, ?, ?)",
                ("test_node2", "http://192.168.177.133:14003", "Test Node 2")
            )
            await db.commit()
        
        yield db_path
        
        # Cleanup
        Path(db_path).unlink(missing_ok=True)

    @pytest.fixture
    def mock_settings(self, temp_db):
        """Create mock settings for testing."""
        settings = Settings(
            monitoring={
                "poll_interval": 1,  # 1 minute for faster testing
                "http_timeout": 10,
                "max_retries": 2,
                "retry_delay": 1
            },
            nodes=[
                {
                    "name": "test_node1",
                    "dashboard_url": "http://192.168.177.133:14002",
                    "description": "Test Node 1"
                },
                {
                    "name": "test_node2", 
                    "dashboard_url": "http://192.168.177.133:14003",
                    "description": "Test Node 2"
                }
            ],
            database={"path": temp_db, "wal_mode": False},
            web_server={"host": "127.0.0.1", "port": 8080},
            logging={"level": "DEBUG", "file": "test.log"}
        )
        return settings

    def create_mock_node_response(self, node_id="test_node_123"):
        """Create mock response for /api/sno endpoint."""
        return {
            "nodeID": node_id,
            "wallet": "0x123456789abcdef",
            "walletFeatures": None,
            "satellites": [
                {
                    "id": "1wFTAgs9DP5RSnCqKV1eLf6N9wtk4EAtmN5DpSxcs8EjT69tGE",
                    "url": "saltlake.tardigrade.io:7777",
                    "disqualified": None,
                    "suspended": None,
                    "vettedAt": None
                }
            ],
            "diskSpace": {
                "used": 1500000000,  # 1.5 GB
                "available": 8500000000,  # 8.5 GB
                "trash": 50000000,  # 50 MB
                "overused": 0
            },
            "bandwidth": {
                "used": 750000000,  # 750 MB
                "available": 0
            },
            "lastPinged": "2025-09-14T23:30:00Z",
            "version": "1.136.4",
            "allowedVersion": "1.135.5",
            "upToDate": True,
            "startedAt": "2025-09-14T20:00:00Z",
            "configuredPort": "28967",
            "quicStatus": "OK",
            "lastQuicPingedAt": "2025-09-14T23:25:00Z"
        }

    def create_mock_satellites_response(self):
        """Create mock response for /api/sno/satellites endpoint."""
        return {
            "storageDaily": [
                {
                    "atRestTotal": 1200000000000,  # 1.2 TB-hours
                    "atRestTotalBytes": 50000000000,  # 50 GB
                    "intervalStart": "2025-09-14T00:00:00Z"
                }
            ],
            "bandwidthDaily": [
                {
                    "egress": {
                        "repair": 10000000,
                        "audit": 1000000,
                        "usage": 500000000
                    },
                    "ingress": {
                        "repair": 50000000,
                        "usage": 1000000000
                    },
                    "delete": 100000,
                    "intervalStart": "2025-09-14T00:00:00Z"
                }
            ],
            "storageSummary": 1200000000000,
            "averageUsageBytes": 50000000000,
            "bandwidthSummary": 1561100000,
            "egressSummary": 511000000,
            "ingressSummary": 1050000000,
            "earliestJoinedAt": "2025-09-13T12:00:00Z",
            "audits": [
                {
                    "auditScore": 0.999,
                    "suspensionScore": 1.0,
                    "onlineScore": 0.98,
                    "satelliteName": "saltlake.tardigrade.io:7777"
                }
            ]
        }

    @respx.mock
    async def test_collector_data_collection(self, mock_settings, temp_db):
        """Test that the collector can fetch and store data."""
        # Mock HTTP responses
        respx.get("http://192.168.177.133:14002/api/sno").mock(
            return_value=httpx.Response(200, json=self.create_mock_node_response("node1_id"))
        )
        respx.get("http://192.168.177.133:14002/api/sno/satellites").mock(
            return_value=httpx.Response(200, json=self.create_mock_satellites_response())
        )
        respx.get("http://192.168.177.133:14003/api/sno").mock(
            return_value=httpx.Response(200, json=self.create_mock_node_response("node2_id"))
        )
        respx.get("http://192.168.177.133:14003/api/sno/satellites").mock(
            return_value=httpx.Response(200, json=self.create_mock_satellites_response())
        )

        # Create collector with mocked settings
        with patch('collector.service.load_settings', return_value=mock_settings):
            with patch('collector.service.setup_logging'):
                collector = StorjCollector()
                
                # Run single collection cycle
                await collector.collect_all_metrics()
        
        # Verify data was stored in database
        async with aiosqlite.connect(temp_db) as db:
            # Check disk metrics
            cursor = await db.execute("SELECT COUNT(*) FROM metrics_disk")
            disk_count = (await cursor.fetchone())[0]
            assert disk_count == 2  # Two nodes
            
            # Check bandwidth metrics
            cursor = await db.execute("SELECT COUNT(*) FROM metrics_bandwidth")
            bandwidth_count = (await cursor.fetchone())[0]
            assert bandwidth_count == 2
            
            # Check health metrics
            cursor = await db.execute("SELECT COUNT(*) FROM metrics_health")
            health_count = (await cursor.fetchone())[0]
            assert health_count == 2
            
            # Check specific values for one node
            cursor = await db.execute("""
                SELECT used_bytes, available_bytes FROM metrics_disk 
                WHERE node_name = 'test_node1'
            """)
            row = await cursor.fetchone()
            assert row[0] == 1500000000  # 1.5 GB
            assert row[1] == 8500000000  # 8.5 GB
            
            # Check health metrics
            cursor = await db.execute("""
                SELECT audit_score, version, satellites_count FROM metrics_health
                WHERE node_name = 'test_node1'
            """)
            row = await cursor.fetchone()
            assert row[0] == 0.999
            assert row[1] == "1.136.4"
            assert row[2] == 1  # One satellite in mock data

    @respx.mock
    async def test_collector_error_handling(self, mock_settings, temp_db):
        """Test that collector handles errors gracefully."""
        # Mock one successful response and one failed response
        respx.get("http://192.168.177.133:14002/api/sno").mock(
            return_value=httpx.Response(200, json=self.create_mock_node_response("node1_id"))
        )
        respx.get("http://192.168.177.133:14002/api/sno/satellites").mock(
            return_value=httpx.Response(200, json=self.create_mock_satellites_response())
        )
        respx.get("http://192.168.177.133:14003/api/sno").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        with patch('collector.service.load_settings', return_value=mock_settings):
            with patch('collector.service.setup_logging'):
                collector = StorjCollector()
                
                # Should not raise exception even with one failing node
                await collector.collect_all_metrics()
        
        # Verify only successful node data was stored
        async with aiosqlite.connect(temp_db) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM metrics_disk")
            disk_count = (await cursor.fetchone())[0]
            assert disk_count == 1  # Only one successful node

    async def test_database_schema_integrity(self, temp_db):
        """Test that database schema is correctly applied."""
        async with aiosqlite.connect(temp_db) as db:
            # Check that all required tables exist
            cursor = await db.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            tables = [row[0] for row in await cursor.fetchall()]
            
            required_tables = [
                'schema_versions', 'nodes', 'metrics_disk', 'metrics_bandwidth',
                'metrics_health', 'metrics_daily_bandwidth', 'metrics_daily_storage'
            ]
            
            for table in required_tables:
                assert table in tables, f"Table {table} not found"
            
            # Check that indexes exist
            cursor = await db.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
            """)
            indexes = [row[0] for row in await cursor.fetchall()]
            
            # Should have several indexes for performance
            assert len(indexes) > 0, "No indexes found"
            
            # Check that views exist
            cursor = await db.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='view'
            """)
            views = [row[0] for row in await cursor.fetchall()]
            
            assert 'latest_node_status' in views
            assert 'daily_summary' in views

    async def test_data_extraction_accuracy(self, mock_settings):
        """Test that data extraction methods work correctly."""
        with patch('collector.service.load_settings', return_value=mock_settings):
            with patch('collector.service.setup_logging'):
                collector = StorjCollector()
                
                # Create mock data
                from storj_monitor.models import StorjNodeInfo, StorjSatelliteInfo
                
                node_data = self.create_mock_node_response()
                satellite_data = self.create_mock_satellites_response()
                
                node_info = StorjNodeInfo(**node_data)
                satellite_info = StorjSatelliteInfo(**satellite_data)
                
                # Test disk metrics extraction
                disk_metrics = collector.extract_disk_metrics("test_node", node_info)
                assert disk_metrics.used_bytes == 1500000000
                assert disk_metrics.available_bytes == 8500000000
                assert disk_metrics.trash_bytes == 50000000
                
                # Test bandwidth metrics extraction
                bw_metrics = collector.extract_bandwidth_metrics("test_node", node_info)
                assert bw_metrics.used_bytes == 750000000
                
                # Test health metrics extraction
                health_metrics = collector.extract_health_metrics("test_node", node_info, satellite_info)
                assert health_metrics.audit_score == 0.999
                assert health_metrics.version == "1.136.4"
                assert health_metrics.satellites_count == 1
                
                # Test daily metrics extraction
                daily_bw = collector.extract_daily_bandwidth_metrics("test_node", satellite_info)
                assert len(daily_bw) == 1
                assert daily_bw[0].ingress_usage_bytes == 1000000000
                assert daily_bw[0].egress_usage_bytes == 500000000


class TestAPIIntegration:
    """Integration tests for the web API."""
    
    @pytest.fixture
    async def test_app(self, temp_db):
        """Create test FastAPI application."""
        from webapp.server import app
        from webapp.database import DatabaseManager
        
        # Mock the database path
        with patch.object(DatabaseManager, '__init__', lambda self: setattr(self, 'db_path', Path(temp_db))):
            yield app

    async def test_api_endpoints_basic(self, test_app, temp_db):
        """Test basic API endpoint functionality."""
        from httpx import AsyncClient
        
        # Add some test data to database
        async with aiosqlite.connect(temp_db) as db:
            await db.execute("""
                INSERT INTO metrics_disk (node_name, used_bytes, available_bytes, trash_bytes)
                VALUES ('test_node1', 1000000000, 9000000000, 50000000)
            """)
            await db.execute("""
                INSERT INTO metrics_health (node_name, version, audit_score, suspension_score, online_score, satellites_count, uptime_seconds, last_pinged)
                VALUES ('test_node1', '1.136.4', 0.999, 1.0, 0.98, 4, 86400, '2025-09-14T23:00:00Z')
            """)
            await db.commit()
        
        async with AsyncClient(app=test_app, base_url="http://test") as client:
            # Test health endpoint
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            
            # Test system summary endpoint
            response = await client.get("/api/system/summary")
            assert response.status_code == 200
            data = response.json()
            assert "node_count" in data
            assert "storage_summary" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])