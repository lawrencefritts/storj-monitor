-- Storj Monitor Database Schema v2
-- Enhanced schema with per-satellite tracking and vetting status

-- First run the original schema
-- Then apply these enhancements

-- Satellites reference table
CREATE TABLE IF NOT EXISTS satellites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    satellite_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    region TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert the four main Storj satellites
INSERT OR IGNORE INTO satellites (satellite_id, name, region, description) VALUES 
('12EayRS2V1kEsWESU9QMRseFhdxYxKicsiFHpkmn1LT3StBp1R', 'us1', 'North America', 'US Central 1'),
('12L9ZFwhzVpuEKMUNUqkaTLGzwY9G24tbiigLiXpmZWKwmcNDDs', 'eu1', 'Europe', 'Europe North 1'), 
('121RTSDpyNZVcEU84Ticf2L1ntiuUimbWgfATz21tuvgk3vzoA6', 'ap1', 'Asia Pacific', 'Asia East 1'),
('1wFTAgs9DP5RSnCqKV1eLf6N9wtk4EAtmN5DpSxcs8EjT69tGE', 'saltlake', 'North America', 'US West (Salt Lake)');

-- Per-satellite node status and vetting information
CREATE TABLE IF NOT EXISTS node_satellites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_name TEXT NOT NULL,
    satellite_id TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Vetting status
    is_vetted BOOLEAN DEFAULT FALSE,
    vetting_progress REAL DEFAULT 0.0, -- 0.0 to 1.0
    vetted_at TIMESTAMP NULL,
    
    -- Satellite-specific scores
    audit_score REAL DEFAULT 1.0,
    suspension_score REAL DEFAULT 1.0,
    online_score REAL DEFAULT 1.0,
    
    -- Satellite-specific stats
    joined_at TIMESTAMP,
    current_month_egress INTEGER DEFAULT 0,
    current_month_ingress INTEGER DEFAULT 0,
    
    FOREIGN KEY (node_name) REFERENCES nodes(name),
    FOREIGN KEY (satellite_id) REFERENCES satellites(satellite_id),
    UNIQUE(node_name, satellite_id, timestamp)
);

-- Enhanced daily metrics per satellite
CREATE TABLE IF NOT EXISTS metrics_daily_satellite (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_name TEXT NOT NULL,
    satellite_id TEXT NOT NULL,
    date DATE NOT NULL,
    
    -- Storage metrics per satellite
    storage_used_bytes INTEGER DEFAULT 0,
    storage_at_rest_bytes INTEGER DEFAULT 0,
    
    -- Bandwidth metrics per satellite
    ingress_usage_bytes INTEGER DEFAULT 0,
    ingress_repair_bytes INTEGER DEFAULT 0,
    egress_usage_bytes INTEGER DEFAULT 0,
    egress_repair_bytes INTEGER DEFAULT 0,
    egress_audit_bytes INTEGER DEFAULT 0,
    
    -- Vetting progress tracking
    vetting_bandwidth_requirement INTEGER DEFAULT 0,
    vetting_bandwidth_completed INTEGER DEFAULT 0,
    
    FOREIGN KEY (node_name) REFERENCES nodes(name),
    FOREIGN KEY (satellite_id) REFERENCES satellites(satellite_id),
    UNIQUE(node_name, satellite_id, date)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_node_satellites_node_time ON node_satellites(node_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_node_satellites_satellite_time ON node_satellites(satellite_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_daily_satellite_node_date ON metrics_daily_satellite(node_name, date);
CREATE INDEX IF NOT EXISTS idx_daily_satellite_satellite_date ON metrics_daily_satellite(satellite_id, date);

-- Enhanced views
CREATE VIEW IF NOT EXISTS latest_satellite_status AS
SELECT 
    ns.node_name,
    s.name as satellite_name,
    s.region as satellite_region,
    ns.satellite_id,
    ns.is_vetted,
    ns.vetting_progress,
    ns.vetted_at,
    ns.audit_score,
    ns.suspension_score,
    ns.online_score,
    ns.joined_at,
    ns.current_month_egress,
    ns.current_month_ingress,
    ns.timestamp as last_updated
FROM node_satellites ns
JOIN satellites s ON ns.satellite_id = s.satellite_id
WHERE ns.id IN (
    SELECT MAX(id) 
    FROM node_satellites 
    GROUP BY node_name, satellite_id
);

-- Enhanced node overview with satellite summary
CREATE VIEW IF NOT EXISTS node_overview_with_satellites AS
SELECT 
    n.name,
    n.node_id,
    n.description,
    d.used_bytes as disk_used,
    d.available_bytes as disk_available,
    h.version,
    h.audit_score as overall_audit_score,
    h.suspension_score as overall_suspension_score,
    h.online_score as overall_online_score,
    h.satellites_count,
    
    -- Satellite summary
    COUNT(lss.satellite_id) as active_satellites,
    SUM(CASE WHEN lss.is_vetted = 1 THEN 1 ELSE 0 END) as vetted_satellites,
    AVG(lss.vetting_progress) as avg_vetting_progress,
    GROUP_CONCAT(
        CASE WHEN lss.is_vetted = 1 
        THEN lss.satellite_name 
        ELSE NULL END
    ) as vetted_satellite_names,
    
    d.timestamp as last_updated
FROM nodes n
LEFT JOIN metrics_disk d ON n.name = d.node_name AND d.id = (
    SELECT MAX(id) FROM metrics_disk WHERE node_name = n.name
)
LEFT JOIN metrics_health h ON n.name = h.node_name AND h.id = (
    SELECT MAX(id) FROM metrics_health WHERE node_name = n.name
)
LEFT JOIN latest_satellite_status lss ON n.name = lss.node_name
GROUP BY n.name, n.node_id, n.description, d.used_bytes, d.available_bytes, 
         h.version, h.audit_score, h.suspension_score, h.online_score, h.satellites_count, d.timestamp;

-- Vetting progress summary view
CREATE VIEW IF NOT EXISTS vetting_summary AS
SELECT 
    node_name,
    COUNT(*) as total_satellites,
    SUM(CASE WHEN is_vetted = 1 THEN 1 ELSE 0 END) as vetted_count,
    AVG(vetting_progress) as avg_progress,
    MIN(CASE WHEN is_vetted = 0 THEN vetting_progress ELSE 1.0 END) as min_progress,
    MAX(vetting_progress) as max_progress,
    GROUP_CONCAT(
        satellite_name || ':' || 
        CASE WHEN is_vetted = 1 THEN 'VETTED' 
        ELSE ROUND(vetting_progress * 100, 1) || '%' END
    ) as status_summary
FROM latest_satellite_status
GROUP BY node_name;

-- Update schema version
INSERT OR REPLACE INTO schema_versions (version, description) 
VALUES (2, 'Added per-satellite tracking and vetting status');