# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

Storj Monitor is a comprehensive monitoring solution for Storj storage nodes with real-time data collection, historical tracking, and a web dashboard. It consists of a data collector service, REST API, and web interface built with Python 3.13, FastAPI, and SQLite.

## Prerequisites

- **Windows 10/11** with PowerShell 5.1 or later
- **Python 3.13.x** (required for optimal compatibility)
- **Administrator privileges** (for Windows Task Scheduler integration)
- **Active Storj nodes** accessible via dashboard APIs (ports 14002, 14003, etc.)

## Quick Start Commands

### Initial Setup
```powershell
# Setup virtual environment and install dependencies
.\scripts\setup.ps1

# Initialize database schema
python scripts\init_db.py

# Configure nodes in config/settings.yaml (required before first run)
```

### Development Commands
```powershell
# Run all tests
.\scripts\run_tests.ps1

# Run tests with coverage
.\scripts\run_tests.ps1 -Coverage

# Run specific tests
.\scripts\run_tests.ps1 -TestPattern "test_models"

# Run integration tests only
.\scripts\run_tests.ps1 -Integration

# Start web server for development
.\scripts\run_web.ps1 -Reload

# Start web server with custom settings
.\scripts\run_web.ps1 -Host "0.0.0.0" -Port 8080 -Debug
```

### Service Management
```powershell
# Install collector service (requires admin)
.\scripts\install_collector.ps1

# Start/stop collector service
.\scripts\start_collector.ps1
.\scripts\stop_collector.ps1

# Check collector status and logs
. .\scripts\collector_scripts.ps1
Get-CollectorStatus
Show-CollectorLogs -Lines 100
```

### Manual Collection & Testing
```powershell
# Trigger immediate data collection
.\scripts\collect_now.ps1

# Test specific satellite collection
python scripts\test_satellite_collection.py

# Debug API response from nodes
python scripts\debug_api_response.py
```

## Architecture Overview

### Core Components
- **Collector Service** (`collector/`): Automated data collection from Storj node APIs
- **Web Application** (`webapp/`): FastAPI-based REST API and dashboard
- **Core Models** (`storj_monitor/`): Shared data models, configuration, and utilities
- **Database Layer** (`db/`): SQLite database with time-series metrics storage

### Data Flow
1. **Collection**: Collector fetches data from node dashboard APIs every 30 minutes
2. **Processing**: Raw API data is parsed into structured metrics (disk, bandwidth, health)
3. **Storage**: Metrics stored in SQLite with time-series indexing
4. **API**: FastAPI serves processed data via REST endpoints
5. **Dashboard**: Web interface displays real-time and historical data

### Key Models
- **StorjNodeInfo**: Raw node data from `/api/sno` endpoint
- **StorjSatelliteInfo**: Satellite and daily metrics from `/api/sno/satellites`
- **DiskMetrics/BandwidthMetrics/HealthMetrics**: Time-series storage structures
- **NodeStatus**: Aggregated node status for API responses

## Development Notes

### Database Schema
The SQLite database uses:
- **metrics_disk**: Disk usage over time
- **metrics_bandwidth**: Bandwidth usage over time  
- **metrics_health**: Health scores and node status
- **metrics_daily_bandwidth**: Daily aggregated bandwidth per satellite
- **metrics_daily_storage**: Daily storage summaries
- **nodes**: Node configuration and metadata

WAL mode is enabled by default for better concurrent access.

### Configuration System
All settings are managed through `config/settings.yaml` using Pydantic models:
- Node URLs and descriptions
- Collection intervals and timeouts
- Database and web server settings
- Logging configuration

The config system validates node URLs and ensures unique node names.

### HTTP Client & Retry Logic
The `AsyncHTTPClient` class in `utils.py` handles:
- Configurable timeouts and retry attempts
- Exponential backoff for failed requests
- Proper connection pooling and cleanup
- JSON response parsing with error handling

### Satellite Data Extraction
The `SatelliteDataExtractor` processes per-satellite metrics:
- Vetting status and progress tracking
- Per-satellite audit scores and bandwidth
- Known satellite mapping (us1, eu1, ap1, saltlake)
- Daily bandwidth and storage aggregation

### Testing Strategy
- **Unit tests**: Model validation and utility functions
- **Integration tests**: End-to-end API and database operations
- **Mocking**: HTTP responses for reliable testing
- **Coverage reporting**: Track test coverage across modules

## Working with the Codebase

### Adding New Metrics
1. Define Pydantic model in `storj_monitor/models.py`
2. Add extraction logic in `collector/service.py`
3. Create database table in `db/schema.sql`
4. Add API endpoint in `webapp/server.py`
5. Update database manager in `webapp/database.py`

### Modifying Collection Logic
The collector service runs these steps:
1. Fetch data from node `/api/sno` and `/api/sno/satellites` endpoints
2. Parse into structured models
3. Extract metrics (disk, bandwidth, health, daily aggregates)
4. Store in database with timestamp indexing
5. Log collection status and errors

### API Development
FastAPI endpoints follow this pattern:
- Dependency injection for database access
- Pydantic response models for type safety
- Query parameters for filtering (hours, days, limits)
- Proper error handling with HTTP status codes
- OpenAPI documentation at `/api/docs`

### Database Operations
All database operations use `aiosqlite` for async access:
- Connection pooling through context managers
- Parameterized queries to prevent SQL injection
- Time-based indexing for efficient historical queries
- Upsert operations for daily metrics (INSERT OR REPLACE)

### Logging Best Practices
- Use structured logging with configurable levels
- Rotating file handlers to manage disk space  
- Separate log files for collector, webapp, and general operations
- Performance timing for collection operations
- HTTP request/response logging for debugging

## Testing Utilities

### Mock Data Generation
Use `scripts/populate_satellite_sample_data.py` to create test data:
- Generates realistic node metrics
- Creates historical time-series data
- Useful for UI development and API testing

### Database Management
```powershell
# Clear sample data
python scripts\clear_sample_data.py

# Migrate to newer schema version
python scripts\migrate_db_v2.py

# Update satellite IDs for existing data
python scripts\update_satellite_ids.py
```

### Development Environment
The web server supports development mode:
- Auto-reload on code changes (`-Reload` flag)
- Debug logging for detailed diagnostics
- CORS enabled for frontend development
- Static file serving from `webapp/static/`

## Common Patterns

### Error Handling
- Use `safe_int()` and `safe_float()` for API data parsing
- HTTP client includes comprehensive retry logic
- Database operations wrapped in try/catch with proper logging
- FastAPI exception handlers return structured error responses

### Time Management
- All timestamps stored as UTC
- Helper functions for ISO string parsing
- Uptime calculation from node `startedAt` timestamps
- Date-based partitioning for daily metrics

### Configuration Management
- Environment-based configuration through Pydantic Settings
- YAML configuration file with validation
- Global settings instance with lazy loading
- Type-safe configuration access throughout codebase

## Performance Considerations

### Collection Optimization
- Default 30-minute collection interval balances freshness and load
- HTTP timeout of 30 seconds with 3 retries
- Concurrent collection from multiple nodes
- Efficient SQLite indexes for time-series queries

### Database Performance
- WAL mode enabled for better concurrent read/write
- Indexes on node_name + timestamp for fast filtering
- Composite indexes for time-range queries
- Daily metrics use UNIQUE constraints for upsert operations

### Memory Management
- Async context managers for HTTP clients
- Proper connection cleanup in database operations
- Limited result sets for API endpoints (with pagination)
- Log file rotation to prevent disk space issues