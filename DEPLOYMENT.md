# Storj Monitor - Same-Server Deployment Guide

## 🚀 Ready for Same-Server Deployment!

Your Storj Monitor has been configured for deployment on the same server as your Storj nodes.

### Key Changes Made:
✅ **Node URLs**: Updated to use localhost (127.0.0.1:14002, 14003, 14004)
✅ **Web Server**: Configured to bind to 0.0.0.0:8080 for network access  
✅ **Database**: Updated with correct localhost node configurations
✅ **Services**: Created systemd service files for automatic startup
✅ **Installation**: Created installation script

### Quick Deployment:
```bash
# 1. Install services
./install-services.sh

# 2. Start services  
sudo systemctl start storj-monitor-collector
sudo systemctl start storj-monitor-webapp

# 3. Check status
sudo systemctl status storj-monitor-collector
sudo systemctl status storj-monitor-webapp

# 4. Access dashboard at: http://YOUR_SERVER_IP:8080
```

### Manual Testing:
```bash
# Test data collection
source venv/bin/activate
PYTHONPATH=. python scripts/collect_now.py

# Start web server manually
PYTHONPATH=. python -m uvicorn webapp.server:app --host 0.0.0.0 --port 8080
```

Your Storj Monitor is ready to deploy! 🎉
