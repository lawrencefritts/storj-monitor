"""Unit tests for utility functions."""

import pytest
from datetime import datetime, timezone
from storj_monitor.utils import (
    bytes_to_human_readable, human_readable_to_bytes, 
    timestamp_to_datetime, calculate_uptime_seconds,
    safe_int, safe_float
)


class TestBytesFormatting:
    """Test byte formatting functions."""
    
    def test_bytes_to_human_readable(self):
        """Test bytes to human readable conversion."""
        assert bytes_to_human_readable(0) == "0 B"
        assert bytes_to_human_readable(512) == "512.00 B"
        assert bytes_to_human_readable(1024) == "1.00 KB"
        assert bytes_to_human_readable(1024 * 1024) == "1.00 MB"
        assert bytes_to_human_readable(1024 * 1024 * 1024) == "1.00 GB"
        assert bytes_to_human_readable(1024 * 1024 * 1024 * 1024) == "1.00 TB"
        
        # Test with different decimal places
        assert bytes_to_human_readable(1536, 1) == "1.5 KB"
        assert bytes_to_human_readable(2048000, 0) == "2 MB"

    def test_human_readable_to_bytes(self):
        """Test human readable to bytes conversion."""
        assert human_readable_to_bytes("1024") == 1024
        assert human_readable_to_bytes("1 KB") == 1024
        assert human_readable_to_bytes("1.5 KB") == 1536
        assert human_readable_to_bytes("2 MB") == 2097152
        assert human_readable_to_bytes("1 GB") == 1073741824
        assert human_readable_to_bytes("1 TB") == 1099511627776
        
        # Test case insensitive
        assert human_readable_to_bytes("1 gb") == 1073741824
        assert human_readable_to_bytes("1 Gb") == 1073741824

    def test_human_readable_to_bytes_invalid(self):
        """Test invalid input handling."""
        with pytest.raises(ValueError):
            human_readable_to_bytes("invalid")
        
        with pytest.raises(ValueError):
            human_readable_to_bytes("1 XB")  # Invalid unit


class TestTimestampHandling:
    """Test timestamp and datetime functions."""
    
    def test_timestamp_to_datetime_with_z(self):
        """Test timestamp parsing with Z suffix."""
        timestamp = "2025-09-14T23:00:00Z"
        dt = timestamp_to_datetime(timestamp)
        
        assert isinstance(dt, datetime)
        assert dt.year == 2025
        assert dt.month == 9
        assert dt.day == 14
        assert dt.hour == 23
        assert dt.tzinfo is not None

    def test_timestamp_to_datetime_with_offset(self):
        """Test timestamp parsing with timezone offset."""
        timestamp = "2025-09-14T23:00:00+00:00"
        dt = timestamp_to_datetime(timestamp)
        
        assert isinstance(dt, datetime)
        assert dt.year == 2025
        assert dt.month == 9
        assert dt.day == 14
        assert dt.hour == 23

    def test_timestamp_to_datetime_without_tz(self):
        """Test timestamp parsing without timezone."""
        timestamp = "2025-09-14T23:00:00"
        dt = timestamp_to_datetime(timestamp)
        
        assert isinstance(dt, datetime)
        assert dt.year == 2025
        assert dt.month == 9
        assert dt.day == 14
        assert dt.hour == 23
        assert dt.tzinfo == timezone.utc

    def test_timestamp_to_datetime_invalid(self):
        """Test invalid timestamp handling."""
        with pytest.raises(ValueError):
            timestamp_to_datetime("invalid-timestamp")

    def test_calculate_uptime_seconds(self):
        """Test uptime calculation."""
        # Mock current time for consistent testing
        import time
        from unittest.mock import patch
        
        started_at = "2025-09-14T22:00:00Z"  # 1 hour ago
        current_time = datetime(2025, 9, 14, 23, 0, 0, tzinfo=timezone.utc)
        
        with patch('storj_monitor.utils.utc_now', return_value=current_time):
            uptime = calculate_uptime_seconds(started_at)
            assert uptime == 3600  # 1 hour = 3600 seconds

    def test_calculate_uptime_seconds_invalid(self):
        """Test uptime calculation with invalid input."""
        assert calculate_uptime_seconds("invalid") == 0
        assert calculate_uptime_seconds(None) == 0


class TestSafeConversions:
    """Test safe conversion functions."""
    
    def test_safe_int(self):
        """Test safe integer conversion."""
        assert safe_int("123") == 123
        assert safe_int(123.45) == 123
        assert safe_int("123.45") == 123
        assert safe_int("invalid") == 0
        assert safe_int(None) == 0
        assert safe_int("invalid", 999) == 999

    def test_safe_float(self):
        """Test safe float conversion."""
        assert safe_float("123.45") == 123.45
        assert safe_float(123) == 123.0
        assert safe_float("invalid") == 0.0
        assert safe_float(None) == 0.0
        assert safe_float("invalid", 999.9) == 999.9


if __name__ == "__main__":
    pytest.main([__file__])