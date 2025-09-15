"""Data collection service for Storj Monitor."""

import asyncio
import logging
import signal
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List

import aiosqlite

# Add parent directory to path to import storj_monitor
sys.path.insert(0, str(Path(__file__).parent.parent))

from storj_monitor.config import load_settings
from storj_monitor.models import (
    StorjNodeInfo, StorjSatelliteInfo, DiskMetrics, BandwidthMetrics,
    HealthMetrics, DailyBandwidthMetrics, DailyStorageMetrics
)
from storj_monitor.utils import (
    setup_logging, create_http_client, utc_now, timestamp_to_datetime,
    calculate_uptime_seconds, safe_int, safe_float, PerformanceTimer
)
from collector.satellite_extractor import SatelliteDataExtractor


class StorjCollector:
    """Main collector service for Storj node metrics."""

    def __init__(self):
        self.settings = load_settings()
        self.logger = setup_logging(
            self.settings.logging.level,
            "logs/collector.log"
        )
        self.is_running = False
        self.satellite_extractor = SatelliteDataExtractor()
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.is_running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def collect_node_data(self, node_name: str, dashboard_url: str) -> Dict[str, Any]:
        """Collect data from a single Storj node."""
        async with create_http_client() as client:
            sno_url = f"{dashboard_url}/api/sno"
            satellites_url = f"{dashboard_url}/api/sno/satellites"
            
            # Fetch both endpoints
            sno_data = await client.fetch_json(sno_url)
            satellites_data = await client.fetch_json(satellites_url)
            
            return {
                'node_info': StorjNodeInfo(**sno_data),
                'satellite_info': StorjSatelliteInfo(**satellites_data)
            }

    def extract_disk_metrics(self, node_name: str, node_info: StorjNodeInfo) -> DiskMetrics:
        """Extract disk metrics from node info."""
        disk_space = node_info.disk_space
        timestamp = utc_now()
        
        return DiskMetrics(
            node_name=node_name,
            timestamp=timestamp,
            used_bytes=safe_int(disk_space.get('used', 0)),
            available_bytes=safe_int(disk_space.get('available', 0)),
            trash_bytes=safe_int(disk_space.get('trash', 0)),
            overused_bytes=safe_int(disk_space.get('overused', 0))
        )

    def extract_bandwidth_metrics(self, node_name: str, node_info: StorjNodeInfo) -> BandwidthMetrics:
        """Extract bandwidth metrics from node info."""
        bandwidth = node_info.bandwidth
        timestamp = utc_now()
        
        return BandwidthMetrics(
            node_name=node_name,
            timestamp=timestamp,
            used_bytes=safe_int(bandwidth.get('used', 0)),
            available_bytes=safe_int(bandwidth.get('available', 0))
        )

    def extract_health_metrics(self, node_name: str, node_info: StorjNodeInfo, 
                             satellite_info: StorjSatelliteInfo) -> HealthMetrics:
        """Extract health metrics from node and satellite info."""
        timestamp = utc_now()
        
        # Calculate average audit scores
        audits = satellite_info.audits
        audit_score = 1.0
        suspension_score = 1.0
        online_score = 1.0
        
        if audits:
            audit_scores = [safe_float(audit.get('auditScore', 1.0)) for audit in audits]
            suspension_scores = [safe_float(audit.get('suspensionScore', 1.0)) for audit in audits]
            online_scores = [safe_float(audit.get('onlineScore', 1.0)) for audit in audits]
            
            if audit_scores:
                audit_score = sum(audit_scores) / len(audit_scores)
            if suspension_scores:
                suspension_score = sum(suspension_scores) / len(suspension_scores)
            if online_scores:
                online_score = sum(online_scores) / len(online_scores)

        return HealthMetrics(
            node_name=node_name,
            timestamp=timestamp,
            version=node_info.version,
            uptime_seconds=calculate_uptime_seconds(node_info.started_at),
            last_pinged=timestamp_to_datetime(node_info.last_pinged),
            quic_status=node_info.quic_status,
            audit_score=audit_score,
            suspension_score=suspension_score,
            online_score=online_score,
            satellites_count=len(node_info.satellites) if node_info.satellites else 0
        )

    def extract_daily_bandwidth_metrics(self, node_name: str, 
                                      satellite_info: StorjSatelliteInfo) -> List[DailyBandwidthMetrics]:
        """Extract daily bandwidth metrics from satellite info."""
        metrics = []
        
        bandwidth_daily = satellite_info.bandwidth_daily or []
        for daily_bw in bandwidth_daily:
            interval_start = daily_bw.get('intervalStart', '')
            if not interval_start:
                continue
                
            try:
                metric_date = timestamp_to_datetime(interval_start).date()
            except ValueError:
                continue
            
            # Extract ingress/egress data
            egress = daily_bw.get('egress', {})
            ingress = daily_bw.get('ingress', {})
            
            metrics.append(DailyBandwidthMetrics(
                node_name=node_name,
                date=metric_date,
                ingress_usage_bytes=safe_int(ingress.get('usage', 0)),
                ingress_repair_bytes=safe_int(ingress.get('repair', 0)),
                egress_usage_bytes=safe_int(egress.get('usage', 0)),
                egress_repair_bytes=safe_int(egress.get('repair', 0)),
                egress_audit_bytes=safe_int(egress.get('audit', 0)),
                delete_bytes=safe_int(daily_bw.get('delete', 0))
            ))
        
        return metrics

    def extract_daily_storage_metrics(self, node_name: str, 
                                    satellite_info: StorjSatelliteInfo) -> List[DailyStorageMetrics]:
        """Extract daily storage metrics from satellite info."""
        metrics = []
        
        storage_daily = satellite_info.storage_daily or []
        for daily_storage in storage_daily:
            interval_start = daily_storage.get('intervalStart', '')
            if not interval_start:
                continue
                
            try:
                metric_date = timestamp_to_datetime(interval_start).date()
            except ValueError:
                continue
            
            metrics.append(DailyStorageMetrics(
                node_name=node_name,
                date=metric_date,
                at_rest_total_bytes=safe_int(daily_storage.get('atRestTotalBytes', 0)),
                average_usage_bytes=safe_int(daily_storage.get('atRestTotal', 0) / 24 if daily_storage.get('atRestTotal') else 0)
            ))
        
        return metrics

    async def store_metrics(self, all_metrics: Dict[str, List]) -> None:
        """Store all collected metrics in the database."""
        db_path = Path(self.settings.database.path)
        
        async with aiosqlite.connect(db_path) as db:
            # Update node information
            for node in self.settings.nodes:
                await db.execute(
                    """
                    UPDATE nodes 
                    SET node_id = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE name = ? AND node_id IS NULL
                    """,
                    (all_metrics.get(f'{node.name}_node_id'), node.name)
                )
            
            # Insert disk metrics
            for disk_metric in all_metrics.get('disk', []):
                await db.execute(
                    """
                    INSERT INTO metrics_disk 
                    (node_name, used_bytes, available_bytes, trash_bytes, overused_bytes)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (disk_metric.node_name, disk_metric.used_bytes, disk_metric.available_bytes,
                     disk_metric.trash_bytes, disk_metric.overused_bytes)
                )
            
            # Insert bandwidth metrics
            for bw_metric in all_metrics.get('bandwidth', []):
                await db.execute(
                    """
                    INSERT INTO metrics_bandwidth 
                    (node_name, used_bytes, available_bytes)
                    VALUES (?, ?, ?)
                    """,
                    (bw_metric.node_name, bw_metric.used_bytes, bw_metric.available_bytes)
                )
            
            # Insert health metrics
            for health_metric in all_metrics.get('health', []):
                await db.execute(
                    """
                    INSERT INTO metrics_health 
                    (node_name, version, uptime_seconds, last_pinged, quic_status,
                     audit_score, suspension_score, online_score, satellites_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (health_metric.node_name, health_metric.version, health_metric.uptime_seconds,
                     health_metric.last_pinged, health_metric.quic_status, health_metric.audit_score,
                     health_metric.suspension_score, health_metric.online_score, health_metric.satellites_count)
                )
            
            # Insert daily bandwidth metrics (with conflict resolution)
            for daily_bw in all_metrics.get('daily_bandwidth', []):
                await db.execute(
                    """
                    INSERT OR REPLACE INTO metrics_daily_bandwidth 
                    (node_name, date, ingress_usage_bytes, ingress_repair_bytes,
                     egress_usage_bytes, egress_repair_bytes, egress_audit_bytes, delete_bytes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (daily_bw.node_name, daily_bw.date, daily_bw.ingress_usage_bytes,
                     daily_bw.ingress_repair_bytes, daily_bw.egress_usage_bytes,
                     daily_bw.egress_repair_bytes, daily_bw.egress_audit_bytes, daily_bw.delete_bytes)
                )
            
            # Insert daily storage metrics (with conflict resolution)
            for daily_storage in all_metrics.get('daily_storage', []):
                await db.execute(
                    """
                    INSERT OR REPLACE INTO metrics_daily_storage 
                    (node_name, date, at_rest_total_bytes, average_usage_bytes)
                    VALUES (?, ?, ?, ?)
                    """,
                    (daily_storage.node_name, daily_storage.date, 
                     daily_storage.at_rest_total_bytes, daily_storage.average_usage_bytes)
                )
            
            # Insert satellite status data
            for satellite_status in all_metrics.get('satellite_status', []):
                await db.execute(
                    """
                    INSERT OR REPLACE INTO node_satellites 
                    (node_name, satellite_id, timestamp, is_vetted, vetting_progress, vetted_at,
                     audit_score, suspension_score, online_score, joined_at, 
                     current_month_egress, current_month_ingress)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (satellite_status['node_name'], satellite_status['satellite_id'], 
                     satellite_status['timestamp'], satellite_status['is_vetted'], 
                     satellite_status['vetting_progress'], satellite_status['vetted_at'],
                     satellite_status['audit_score'], satellite_status['suspension_score'], 
                     satellite_status['online_score'], satellite_status['joined_at'],
                     satellite_status['current_month_egress'], satellite_status['current_month_ingress'])
                )
            
            # Insert daily satellite metrics (with conflict resolution)
            for daily_satellite in all_metrics.get('daily_satellite', []):
                await db.execute(
                    """
                    INSERT OR REPLACE INTO metrics_daily_satellite
                    (node_name, satellite_id, date, storage_used_bytes, storage_at_rest_bytes,
                     ingress_usage_bytes, ingress_repair_bytes, egress_usage_bytes, 
                     egress_repair_bytes, egress_audit_bytes, vetting_bandwidth_requirement,
                     vetting_bandwidth_completed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (daily_satellite['node_name'], daily_satellite['satellite_id'], 
                     daily_satellite['date'], daily_satellite['storage_used_bytes'],
                     daily_satellite['storage_at_rest_bytes'], daily_satellite['ingress_usage_bytes'],
                     daily_satellite['ingress_repair_bytes'], daily_satellite['egress_usage_bytes'],
                     daily_satellite['egress_repair_bytes'], daily_satellite['egress_audit_bytes'],
                     daily_satellite['vetting_bandwidth_requirement'], daily_satellite['vetting_bandwidth_completed'])
                )
            
            await db.commit()

    async def collect_all_metrics(self) -> None:
        """Collect metrics from all configured nodes."""
        with PerformanceTimer("Full collection cycle", self.logger):
            all_metrics = {
                'disk': [],
                'bandwidth': [],
                'health': [],
                'daily_bandwidth': [],
                'daily_storage': [],
                'satellite_status': [],
                'daily_satellite': []
            }
            
            for node in self.settings.nodes:
                try:
                    self.logger.info(f"Collecting data from node: {node.name}")
                    
                    data = await self.collect_node_data(node.name, node.dashboard_url)
                    node_info = data['node_info']
                    satellite_info = data['satellite_info']
                    
                    # Store node ID for database update
                    all_metrics[f'{node.name}_node_id'] = node_info.node_id
                    
                    # Extract all metrics
                    all_metrics['disk'].append(
                        self.extract_disk_metrics(node.name, node_info)
                    )
                    all_metrics['bandwidth'].append(
                        self.extract_bandwidth_metrics(node.name, node_info)
                    )
                    all_metrics['health'].append(
                        self.extract_health_metrics(node.name, node_info, satellite_info)
                    )
                    all_metrics['daily_bandwidth'].extend(
                        self.extract_daily_bandwidth_metrics(node.name, satellite_info)
                    )
                    all_metrics['daily_storage'].extend(
                        self.extract_daily_storage_metrics(node.name, satellite_info)
                    )
                    
                    # Extract satellite-specific data
                    satellite_statuses = self.satellite_extractor.extract_satellite_status(
                        node.name, node_info, satellite_info
                    )
                    all_metrics['satellite_status'].extend(satellite_statuses)
                    
                    daily_satellite_metrics = self.satellite_extractor.extract_daily_satellite_metrics(
                        node.name, satellite_info
                    )
                    all_metrics['daily_satellite'].extend(daily_satellite_metrics)
                    
                    self.logger.info(
                        f"Successfully collected data from {node.name} "
                        f"(satellites: {len(satellite_statuses)}, daily metrics: {len(daily_satellite_metrics)})"
                    )
                    
                except Exception as e:
                    self.logger.error(f"Failed to collect data from {node.name}: {e}")
                    continue
            
            # Store all metrics
            try:
                await self.store_metrics(all_metrics)
                self.logger.info(f"Successfully stored metrics for {len(all_metrics['disk'])} nodes")
            except Exception as e:
                self.logger.error(f"Failed to store metrics: {e}")

    async def run(self) -> None:
        """Main collection loop."""
        self.is_running = True
        self.logger.info("Starting Storj Monitor collector...")
        
        # Initial collection
        await self.collect_all_metrics()
        
        # Main loop
        while self.is_running:
            try:
                # Wait for the configured interval
                poll_interval_seconds = self.settings.monitoring.poll_interval * 60
                self.logger.info(f"Waiting {poll_interval_seconds} seconds until next collection...")
                
                for _ in range(poll_interval_seconds):
                    if not self.is_running:
                        break
                    await asyncio.sleep(1)
                
                if self.is_running:
                    await self.collect_all_metrics()
                    
            except Exception as e:
                self.logger.error(f"Unexpected error in collection loop: {e}")
                if self.is_running:
                    await asyncio.sleep(60)  # Wait 1 minute before retrying
        
        self.logger.info("Collector stopped.")


async def main():
    """Entry point for the collector service."""
    collector = StorjCollector()
    await collector.run()


if __name__ == "__main__":
    asyncio.run(main())