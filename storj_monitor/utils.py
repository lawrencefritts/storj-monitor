"""Shared utilities for Storj Monitor."""

import asyncio
import logging
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from .config import get_settings


class AsyncHTTPClient:
    """Async HTTP client with retry logic and timeout handling."""

    def __init__(self, timeout: int = 30, max_retries: int = 3, retry_delay: int = 5):
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=self.timeout, follow_redirects=True)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    async def fetch_json(self, url: str) -> Dict[str, Any]:
        """Fetch JSON data from URL with retry logic."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.get(url)
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, httpx.RequestError) as e:
                last_exception = e
                logger = logging.getLogger(__name__)
                
                if attempt < self.max_retries:
                    logger.warning(
                        f"Request to {url} failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}. "
                        f"Retrying in {self.retry_delay} seconds..."
                    )
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(f"All {self.max_retries + 1} attempts failed for {url}: {e}")

        # If we get here, all attempts failed
        raise last_exception


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """Set up structured logging with rotating file handler."""
    settings = get_settings()
    
    # Create logs directory if it doesn't exist
    if log_file:
        log_path = Path(log_file)
    else:
        log_path = settings.logging.absolute_file_path
    
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create formatters
    formatter = logging.Formatter(settings.logging.format)

    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=settings.logging.max_size_mb * 1024 * 1024,
        backupCount=settings.logging.backup_count,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def bytes_to_human_readable(bytes_value: int, decimal_places: int = 2) -> str:
    """Convert bytes to human-readable format (KB, MB, GB, TB)."""
    if bytes_value == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    unit_index = 0

    size = float(bytes_value)
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.{decimal_places}f} {units[unit_index]}"


def human_readable_to_bytes(size_str: str) -> int:
    """Convert human-readable size string to bytes."""
    size_str = size_str.strip().upper()
    
    # Handle just numbers (assume bytes)
    try:
        return int(float(size_str))
    except ValueError:
        pass

    # Unit mapping
    units = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4,
        'PB': 1024 ** 5
    }

    # Extract number and unit
    for unit, multiplier in units.items():
        if size_str.endswith(unit):
            number_str = size_str[:-len(unit)].strip()
            try:
                return int(float(number_str) * multiplier)
            except ValueError:
                break

    raise ValueError(f"Invalid size format: {size_str}")


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def timestamp_to_datetime(timestamp_str: str) -> datetime:
    """Convert ISO timestamp string to datetime object."""
    # Handle different timestamp formats
    timestamp_str = timestamp_str.replace('Z', '+00:00')
    
    try:
        return datetime.fromisoformat(timestamp_str)
    except ValueError:
        # Try parsing without timezone info
        try:
            dt = datetime.fromisoformat(timestamp_str.replace('+00:00', ''))
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            raise ValueError(f"Cannot parse timestamp: {timestamp_str}")


def calculate_uptime_seconds(started_at: str) -> int:
    """Calculate uptime in seconds from started_at timestamp."""
    try:
        start_time = timestamp_to_datetime(started_at)
        now = utc_now()
        return int((now - start_time).total_seconds())
    except (ValueError, TypeError):
        return 0


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to integer with default fallback."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float with default fallback."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


class PerformanceTimer:
    """Context manager for measuring execution time."""

    def __init__(self, name: str, logger: Optional[logging.Logger] = None):
        self.name = name
        self.logger = logger or logging.getLogger(__name__)
        self.start_time = 0.0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        self.logger.debug(f"{self.name} took {elapsed:.2f} seconds")


def create_http_client() -> AsyncHTTPClient:
    """Create HTTP client with settings from configuration."""
    settings = get_settings()
    return AsyncHTTPClient(
        timeout=settings.monitoring.http_timeout,
        max_retries=settings.monitoring.max_retries,
        retry_delay=settings.monitoring.retry_delay
    )
