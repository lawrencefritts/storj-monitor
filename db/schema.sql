-- Storj Monitor Database Schema
-- This schema stores metrics from Storj storage nodes

-- Schema versioning table
CREATE TABLE IF NOT EXISTS schema_versions (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Insert initial schema version
INSERT OR IGNORE INTO schema_versions (version, description) 
VALUES (1, 'Initial schema with basic node metrics tables');

-- Node configuration table
CREATE TABLE IF NOT EXISTS nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    node_id TEXT,  -- Storj node ID from API
    dashboard_url TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Disk space metrics
CREATE TABLE IF NOT EXISTS metrics_disk (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_name TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_bytes INTEGER NOT NULL,
    available_bytes INTEGER NOT NULL,
    trash_bytes INTEGER DEFAULT 0,
    overused_bytes INTEGER DEFAULT 0,
    FOREIGN KEY (node_name) REFERENCES nodes(name)
);

-- Bandwidth metrics
CREATE TABLE IF NOT EXISTS metrics_bandwidth (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_name TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_bytes INTEGER NOT NULL,
    available_bytes INTEGER DEFAULT 0,
    FOREIGN KEY (node_name) REFERENCES nodes(name)
);

-- Node health and status metrics
CREATE TABLE IF NOT EXISTS metrics_health (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_name TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version TEXT,
    uptime_seconds INTEGER,
    last_pinged TIMESTAMP,
    quic_status TEXT,
    audit_score REAL,
    suspension_score REAL,
    online_score REAL,
    satellites_count INTEGER DEFAULT 0,
    FOREIGN KEY (node_name) REFERENCES nodes(name)
);

-- Daily bandwidth aggregated metrics (from satellites API)
CREATE TABLE IF NOT EXISTS metrics_daily_bandwidth (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_name TEXT NOT NULL,
    date DATE NOT NULL,
    ingress_usage_bytes INTEGER DEFAULT 0,
    ingress_repair_bytes INTEGER DEFAULT 0,
    egress_usage_bytes INTEGER DEFAULT 0,
    egress_repair_bytes INTEGER DEFAULT 0,
    egress_audit_bytes INTEGER DEFAULT 0,
    delete_bytes INTEGER DEFAULT 0,
    FOREIGN KEY (node_name) REFERENCES nodes(name),
    UNIQUE(node_name, date)
);

-- Daily storage metrics (from satellites API)
CREATE TABLE IF NOT EXISTS metrics_daily_storage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_name TEXT NOT NULL,
    date DATE NOT NULL,
    at_rest_total_bytes INTEGER DEFAULT 0,
    average_usage_bytes INTEGER DEFAULT 0,
    FOREIGN KEY (node_name) REFERENCES nodes(name),
    UNIQUE(node_name, date)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_disk_node_timestamp ON metrics_disk(node_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_bandwidth_node_timestamp ON metrics_bandwidth(node_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_health_node_timestamp ON metrics_health(node_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_daily_bw_node_date ON metrics_daily_bandwidth(node_name, date);
CREATE INDEX IF NOT EXISTS idx_daily_storage_node_date ON metrics_daily_storage(node_name, date);

-- Create composite indexes for time-series queries
CREATE INDEX IF NOT EXISTS idx_disk_timestamp_node ON metrics_disk(timestamp, node_name);
CREATE INDEX IF NOT EXISTS idx_bandwidth_timestamp_node ON metrics_bandwidth(timestamp, node_name);
CREATE INDEX IF NOT EXISTS idx_health_timestamp_node ON metrics_health(timestamp, node_name);

-- Views for easier querying
CREATE VIEW IF NOT EXISTS latest_node_status AS
SELECT 
    n.name,
    n.node_id,
    n.description,
    d.used_bytes as disk_used,
    d.available_bytes as disk_available,
    d.trash_bytes as disk_trash,
    b.used_bytes as bandwidth_used,
    h.version,
    h.audit_score,
    h.suspension_score,
    h.online_score,
    h.quic_status,
    h.last_pinged,
    h.satellites_count,
    d.timestamp as last_updated
FROM nodes n
LEFT JOIN metrics_disk d ON n.name = d.node_name AND d.id = (
    SELECT MAX(id) FROM metrics_disk WHERE node_name = n.name
)
LEFT JOIN metrics_bandwidth b ON n.name = b.node_name AND b.id = (
    SELECT MAX(id) FROM metrics_bandwidth WHERE node_name = n.name
)
LEFT JOIN metrics_health h ON n.name = h.node_name AND h.id = (
    SELECT MAX(id) FROM metrics_health WHERE node_name = n.name
);

-- View for daily aggregated metrics
CREATE VIEW IF NOT EXISTS daily_summary AS
SELECT 
    node_name,
    date,
    COALESCE(ingress_usage_bytes + ingress_repair_bytes, 0) as total_ingress,
    COALESCE(egress_usage_bytes + egress_repair_bytes + egress_audit_bytes, 0) as total_egress,
    at_rest_total_bytes,
    average_usage_bytes
FROM metrics_daily_bandwidth db
LEFT JOIN metrics_daily_storage ds USING (node_name, date)
ORDER BY date DESC, node_name;