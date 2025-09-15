# Storj Monitor

A comprehensive monitoring solution for Storj storage nodes with real-time data collection, historical tracking, and a beautiful web dashboard.

## Features

- **Real-time Monitoring**: Tracks disk usage, bandwidth, and health metrics from your Storj nodes
- **Historical Data**: Stores time-series data for trend analysis and performance tracking
- **Beautiful Dashboard**: Responsive web interface with charts and visualizations
- **Automated Collection**: Runs as a Linux daemon collecting data every 30 minutes
- **Health Alerts**: Traffic-light status indicators and event notifications
- **REST API**: Full API access to all collected metrics

## Prerequisites

- **Ubuntu 20.04+** (bash shell)
- **Python 3.13.x** (required for optimal compatibility)
- **Storj nodes** accessible via their dashboard APIs (ports 14002, 14003, etc.)
- **sudo privileges** (for systemd integration)

## Quick Start

### 1. Installation

```powershell
# Clone or download the project
cd storj-monitor

# Run the setup script (this will create a virtual environment and install dependencies)
.\scripts\setup.ps1
```

### 2. Configuration

Edit `config/settings.yaml` to match your Storj node setup:

```yaml
nodes:
  - name: "node1"
    dashboard_url: "http://192.168.177.133:14002"
    description: "Primary Storj Node"
  - name: "node2"
    dashboard_url: "http://192.168.177.133:14003"
    description: "Secondary Storj Node"
  - name: "node3"
    dashboard_url: "http://192.168.177.133:14004"
    description: "Tertiary Storj Node"
```

### 3. Initialize Database

```powershell
# Create and set up the SQLite database
python scripts\init_db.py
```

### 4. Start Services

```powershell
# Install and start the data collector as a Linux daemon
.\scripts\install_collector.ps1
.\scripts\start_collector.ps1

# Start the web dashboard
.\scripts\run_web.ps1
```

### 5. Access Dashboard

Open your browser to: **http://127.0.0.1:8080**

## Detailed Setup Guide

### Environment Setup

1. **Install Python 3.13.x**:
   - Download from https://python.org
   - Ensure "Add to PATH" is checked during installation
   - Verify: `python --version` should show Python 3.13.x

2. **Run Setup Script**:
   ```powershell
   .\scripts\setup.ps1
   ```
   This script:
   - Creates a Python virtual environment
   - Installs all required dependencies
   - Verifies Python version compatibility

### Configuration Options

The `config/settings.yaml` file contains all configuration options:

#### Monitoring Settings
```yaml
monitoring:
  poll_interval: 30        # Minutes between data collection
  http_timeout: 30         # HTTP request timeout in seconds
  max_retries: 3          # Number of retry attempts
  retry_delay: 5          # Seconds between retries
```

#### Node Configuration
```yaml
nodes:
  - name: "unique_name"
    dashboard_url: "http://ip:port"
    description: "Optional description"
```

#### Database Settings
```yaml
database:
  path: "db/storj_monitor.db"
  wal_mode: true           # Enable WAL mode for better performance
  pool_size: 5
```

#### Web Server Settings
```yaml
web_server:
  host: "127.0.0.1"       # Use "0.0.0.0" to allow external access
  port: 8080
  debug: false
```

#### Logging Configuration
```yaml
logging:
  level: "INFO"           # DEBUG, INFO, WARNING, ERROR, CRITICAL
  file: "logs/storj_monitor.log"
  max_size_mb: 10
  backup_count: 5
```

### Service Management

#### Data Collector Service

The collector runs as a Windows scheduled task:

```powershell
# Install service (run as Administrator)
.\scripts\install_collector.ps1

# Start/stop service
.\scripts\start_collector.ps1
.\scripts\stop_collector.ps1

# Check status
. .\scripts\collector_scripts.ps1
Get-CollectorStatus

# View logs
Show-CollectorLogs -Lines 100
```

#### Web Server

The web server runs on-demand:

```powershell
# Start with default settings
.\scripts\run_web.ps1

# Start with custom settings
.\scripts\run_web.ps1 -Host "0.0.0.0" -Port 8080 -Debug

# Start with auto-reload for development
.\scripts\run_web.ps1 -Reload
```

## Dashboard Guide

### Main Dashboard
- **System Summary Cards**: Overview of nodes, storage, audit scores
- **Node Status Cards**: Individual node health with traffic-light indicators
- **Charts**: Disk usage trends and storage distribution
- **Recent Events**: Latest alerts and status changes

### Navigation
- **Dashboard**: Main overview page
- **Nodes**: Detailed view of each node
- **History**: Historical charts with filtering options
- **Events**: Complete event log and alerts

### Health Status Indicators
- 🟢 **Green (Healthy)**: Audit score > 98%, suspension score > 95%
- 🟡 **Yellow (Warning)**: Audit score 95-98% or online issues
- 🔴 **Red (Critical)**: Audit score < 95% or suspension score < 95%

## API Documentation

### Base URL
`http://127.0.0.1:8080/api`

### Key Endpoints

#### Node Information
```
GET /nodes              # List all nodes
GET /nodes/{name}       # Get specific node details
```

#### Metrics
```
GET /nodes/{name}/disk-usage?hours=24
GET /nodes/{name}/bandwidth-usage?hours=24
GET /nodes/{name}/health-metrics?hours=24
GET /nodes/{name}/daily-bandwidth?days=30
```

#### System
```
GET /system/summary     # System overview
GET /system/events      # Recent events and alerts
GET /health            # API health check
```

### API Documentation
Visit `http://127.0.0.1:8080/api/docs` for interactive API documentation.

## Data Storage

### Database Schema

The application uses SQLite with the following main tables:

- **nodes**: Node configuration and metadata
- **metrics_disk**: Disk usage over time
- **metrics_bandwidth**: Bandwidth usage over time  
- **metrics_health**: Health scores and status
- **metrics_daily_bandwidth**: Daily aggregated bandwidth
- **metrics_daily_storage**: Daily storage summaries

### Data Retention

By default, all data is retained indefinitely. To manage database size:

1. **Monitor database size**: Check `db/storj_monitor.db` file size
2. **Manual cleanup**: Delete old records if needed
3. **Automated cleanup**: Add scheduled cleanup scripts (future enhancement)

## Troubleshooting

### Common Issues

#### 1. "Python not found" Error
```powershell
# Verify Python installation
python --version

# If not found, reinstall Python or check PATH
```

#### 2. Collector Not Starting
```powershell
# Check collector status
. .\scripts\collector_scripts.ps1
Get-CollectorStatus

# View logs for errors
Show-CollectorLogs

# Common solutions:
# - Run as Administrator
# - Check node URLs are accessible
# - Verify database permissions
```

#### 3. Web Dashboard Not Loading
```powershell
# Test API directly
curl http://127.0.0.1:8080/health

# Check web server logs
Get-Content logs\webapp.log -Tail 50

# Verify port is not in use
netstat -an | findstr :8080
```

#### 4. No Data in Dashboard
- Verify collector is running and collecting data
- Check node URLs are accessible
- Review collector logs for errors
- Confirm database was initialized properly

#### 5. Permission Errors
```powershell
# Run PowerShell as Administrator
# Or adjust execution policy:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Log Locations

- **Collector logs**: `logs/collector.log`
- **Web server logs**: `logs/webapp.log`
- **General logs**: `logs/storj_monitor.log`

### Network Troubleshooting

Test node connectivity:
```powershell
# Test basic connectivity
Test-NetConnection -ComputerName 192.168.177.133 -Port 14002

# Test API response
Invoke-WebRequest -Uri "http://192.168.177.133:14002/api/sno" -UseBasicParsing
```

## Development

### Running Tests

```powershell
# Run all tests
.\scripts\run_tests.ps1

# Run with coverage
.\scripts\run_tests.ps1 -Coverage

# Run specific tests
.\scripts\run_tests.ps1 -TestPattern "test_models"

# Run integration tests only
.\scripts\run_tests.ps1 -Integration
```

### Project Structure

```
storj-monitor/
├── config/             # Configuration files
├── collector/          # Data collection service
├── webapp/            # Web application and API
│   └── static/        # Frontend dashboard files
├── storj_monitor/     # Core Python modules
├── db/                # Database schema and files
├── scripts/           # PowerShell management scripts
├── tests/             # Unit and integration tests
├── logs/              # Log files
└── docs/              # Documentation
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Performance Tuning

### Database Optimization
- WAL mode is enabled by default for better performance
- Indexes are created for common queries
- Consider periodic database maintenance (VACUUM, REINDEX)

### Collection Frequency
- Default: 30 minutes (recommended)
- Minimum: 5 minutes (for testing)
- Maximum: Several hours (for low-frequency monitoring)

### Web Server Performance
- Use production WSGI server for high traffic
- Enable caching for API responses
- Consider reverse proxy (nginx) for production

## Security Considerations

- Dashboard binds to localhost by default
- No authentication is built-in (add reverse proxy with auth if needed)
- Database contains node performance data (not sensitive credentials)
- Collector needs network access to node dashboards

## Support

For issues and questions:
1. Check this documentation
2. Review troubleshooting section
3. Check log files for error details
4. Verify network connectivity to nodes
5. Test with minimal configuration

## License

[Add your license information here]

---

**Storj Monitor v1.0** - Monitor your Storj storage nodes with confidence!