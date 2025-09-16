#!/bin/bash
# Install Storj Monitor as systemd services

echo "🔧 Installing Storj Monitor systemd services..."

# Copy service files to systemd directory
sudo cp storj-monitor-collector.service /etc/systemd/system/
sudo cp storj-monitor-webapp.service /etc/systemd/system/

# Set proper permissions
sudo chmod 644 /etc/systemd/system/storj-monitor-collector.service
sudo chmod 644 /etc/systemd/system/storj-monitor-webapp.service

# Reload systemd
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable storj-monitor-collector.service
sudo systemctl enable storj-monitor-webapp.service

echo "✅ Services installed and enabled for auto-start"
echo "📋 Next steps:"
echo "   sudo systemctl start storj-monitor-collector"
echo "   sudo systemctl start storj-monitor-webapp"
echo "   sudo systemctl status storj-monitor-collector"
echo "   sudo systemctl status storj-monitor-webapp"
