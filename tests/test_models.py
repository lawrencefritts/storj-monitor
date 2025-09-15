"""Unit tests for Storj Monitor data models."""

import pytest
from datetime import datetime, date
from storj_monitor.models import (
    StorjNodeInfo, StorjSatelliteInfo, DiskMetrics, BandwidthMetrics,
    HealthMetrics, NodeStatus, DailyBandwidthMetrics
)


class TestStorjNodeInfo:
    """Test StorjNodeInfo model."""
    
    def test_basic_creation(self):
        """Test basic model creation."""
        data = {
            "nodeID": "test_node_123",
            "wallet": "0x123456789",
            "diskSpace": {"used": 1000000, "available": 5000000, "trash": 0},
            "bandwidth": {"used": 500000, "available": 0},
            "lastPinged": "2025-09-14T23:00:00Z",
            "version": "1.136.4",
            "startedAt": "2025-09-13T12:00:00Z",
            "quicStatus": "OK"
        }
        
        node = StorjNodeInfo(**data)
        
        assert node.node_id == "test_node_123"
        assert node.wallet == "0x123456789"
        assert node.disk_space["used"] == 1000000
        assert node.bandwidth["used"] == 500000
        assert node.version == "1.136.4"
        assert node.quic_status == "OK"

    def test_alias_fields(self):
        """Test that field aliases work properly."""
        data = {
            "nodeID": "test_node_456",  # Should map to node_id
            "wallet": "0x987654321",
            "diskSpace": {"used": 2000000, "available": 8000000},  # Should map to disk_space
            "bandwidth": {"used": 1000000},
            "lastPinged": "2025-09-14T23:00:00Z",  # Should map to last_pinged
            "version": "1.136.4",
            "startedAt": "2025-09-13T12:00:00Z",  # Should map to started_at
            "quicStatus": "OK"  # Should map to quic_status
        }
        
        node = StorjNodeInfo(**data)
        
        assert node.node_id == "test_node_456"
        assert node.disk_space["used"] == 2000000
        assert node.last_pinged == "2025-09-14T23:00:00Z"
        assert node.started_at == "2025-09-13T12:00:00Z"
        assert node.quic_status == "OK"


class TestNodeStatus:
    """Test NodeStatus model and computed properties."""
    
    def test_disk_usage_percentage(self):
        """Test disk usage percentage calculation."""
        node = NodeStatus(
            name="test_node",
            disk_used=2500000000,  # 2.5 GB
            disk_available=7500000000  # 7.5 GB
        )
        
        assert node.disk_usage_percentage == 25.0  # 2.5 / (2.5 + 7.5) * 100

    def test_disk_usage_percentage_zero_total(self):
        """Test disk usage percentage with zero total."""
        node = NodeStatus(
            name="test_node",
            disk_used=0,
            disk_available=0
        )
        
        assert node.disk_usage_percentage is None

    def test_disk_usage_percentage_none_values(self):
        """Test disk usage percentage with None values."""
        node = NodeStatus(name="test_node")
        
        assert node.disk_usage_percentage is None

    def test_health_status_healthy(self):
        """Test healthy status determination."""
        node = NodeStatus(
            name="test_node",
            audit_score=0.999,
            suspension_score=0.999,
            online_score=0.98
        )
        
        assert node.health_status == "healthy"

    def test_health_status_warning(self):
        """Test warning status determination."""
        node = NodeStatus(
            name="test_node",
            audit_score=0.97,  # Less than 0.98
            suspension_score=0.999,
            online_score=0.98
        )
        
        assert node.health_status == "warning"

    def test_health_status_critical_audit(self):
        """Test critical status from low audit score."""
        node = NodeStatus(
            name="test_node",
            audit_score=0.94,  # Less than 0.95
            suspension_score=0.999,
            online_score=0.98
        )
        
        assert node.health_status == "critical"

    def test_health_status_critical_suspension(self):
        """Test critical status from low suspension score."""
        node = NodeStatus(
            name="test_node",
            audit_score=0.999,
            suspension_score=0.94,  # Less than 0.95
            online_score=0.98
        )
        
        assert node.health_status == "critical"


class TestMetricsModels:
    """Test various metrics models."""
    
    def test_disk_metrics(self):
        """Test DiskMetrics model."""
        timestamp = datetime.now()
        
        metrics = DiskMetrics(
            node_name="test_node",
            timestamp=timestamp,
            used_bytes=1000000000,
            available_bytes=9000000000,
            trash_bytes=50000000,
            overused_bytes=0
        )
        
        assert metrics.node_name == "test_node"
        assert metrics.timestamp == timestamp
        assert metrics.used_bytes == 1000000000
        assert metrics.available_bytes == 9000000000
        assert metrics.trash_bytes == 50000000

    def test_bandwidth_metrics(self):
        """Test BandwidthMetrics model."""
        timestamp = datetime.now()
        
        metrics = BandwidthMetrics(
            node_name="test_node",
            timestamp=timestamp,
            used_bytes=500000000,
            available_bytes=0
        )
        
        assert metrics.node_name == "test_node"
        assert metrics.used_bytes == 500000000

    def test_health_metrics(self):
        """Test HealthMetrics model."""
        timestamp = datetime.now()
        last_pinged = datetime.now()
        
        metrics = HealthMetrics(
            node_name="test_node",
            timestamp=timestamp,
            version="1.136.4",
            uptime_seconds=86400,  # 1 day
            last_pinged=last_pinged,
            quic_status="OK",
            audit_score=0.999,
            suspension_score=1.0,
            online_score=0.98,
            satellites_count=4
        )
        
        assert metrics.node_name == "test_node"
        assert metrics.version == "1.136.4"
        assert metrics.uptime_seconds == 86400
        assert metrics.audit_score == 0.999
        assert metrics.satellites_count == 4

    def test_daily_bandwidth_metrics(self):
        """Test DailyBandwidthMetrics model."""
        test_date = date.today()
        
        metrics = DailyBandwidthMetrics(
            node_name="test_node",
            date=test_date,
            ingress_usage_bytes=1000000000,
            ingress_repair_bytes=50000000,
            egress_usage_bytes=800000000,
            egress_repair_bytes=20000000,
            egress_audit_bytes=5000000,
            delete_bytes=1000000
        )
        
        assert metrics.node_name == "test_node"
        assert metrics.date == test_date
        assert metrics.ingress_usage_bytes == 1000000000
        assert metrics.egress_usage_bytes == 800000000


if __name__ == "__main__":
    pytest.main([__file__])