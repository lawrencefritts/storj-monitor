"""
Satellite data extraction utilities for Storj Monitor.
Extracts per-satellite vetting status and metrics.
"""

from datetime import datetime, date
from typing import Dict, List, Any, Tuple
import logging

from storj_monitor.models import StorjNodeInfo, StorjSatelliteInfo
from storj_monitor.utils import safe_int, safe_float, utc_now, timestamp_to_datetime


logger = logging.getLogger(__name__)

# Known Storj satellites with their IDs
KNOWN_SATELLITES = {
    "12EayRS2V1kEsWESU9QMRseFhdxYxKicsiFmxrsLZHeLUtdps3S": {"name": "us1", "region": "North America"},
    "12L9ZFwhzVpuEKMUNUqkaTLGzwY9G24tbiigLiXpmZWKwmcNDDs": {"name": "eu1", "region": "Europe"}, 
    "121RTSDpyNZVcEU84Ticf2L1ntiuUimbWgfATz21tuvgk3vzoA6": {"name": "ap1", "region": "Asia Pacific"},
    "1wFTAgs9DP5RSnCqKV1eLf6N9wtk4EAtmN5DpSxcs8EjT69tGE": {"name": "saltlake", "region": "North America"},
    # Legacy IDs (in case they change)
    "12EayRS2V1kEsWESU9QMRseFhdxYxKicsiFHpkmn1LT3StBp1R": {"name": "us1_legacy", "region": "North America"}
}


class SatelliteDataExtractor:
    """Extracts per-satellite data from Storj API responses."""
    
    def extract_satellite_status(self, node_name: str, node_info: StorjNodeInfo, 
                                satellite_info: StorjSatelliteInfo) -> List[Dict[str, Any]]:
        """Extract per-satellite status including vetting information."""
        timestamp = utc_now()
        satellite_statuses = []
        
        # Process satellites from node_info (this contains the satellite list)
        if node_info.satellites:
            for satellite_data in node_info.satellites:
                satellite_id = satellite_data.get('id', '')
                if satellite_id not in KNOWN_SATELLITES:
                    logger.debug(f"Unknown satellite ID: {satellite_id}")
                    continue
                
                satellite_name = KNOWN_SATELLITES[satellite_id]['name']
                satellite_region = KNOWN_SATELLITES[satellite_id]['region']
                
                # Extract vetting status - check vettedAt field (more reliable)
                vetted_timestamp = satellite_data.get('vettedAt')
                is_vetted = vetted_timestamp is not None
                vetted_at = None
                
                if is_vetted:
                    try:
                        vetted_at = timestamp_to_datetime(vetted_timestamp)
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid vettedAt timestamp: {vetted_timestamp}")
                        pass
                
                # Calculate vetting progress
                vetting_progress = 1.0 if is_vetted else self._calculate_vetting_progress(satellite_data, is_vetted)
                
                # Extract join date (when node joined this satellite)
                joined_at = None
                join_timestamp = satellite_data.get('joinedAt')
                if join_timestamp:
                    try:
                        joined_at = timestamp_to_datetime(join_timestamp)
                    except (ValueError, TypeError):
                        pass
                
                # Extract current month bandwidth (if available)
                current_month_egress = safe_int(satellite_data.get('currentMonthEgress', 0))
                current_month_ingress = safe_int(satellite_data.get('currentMonthIngress', 0))
                
                # Scores are typically aggregated, not per-satellite in the basic API
                # We'll use overall scores for now
                audit_score = 1.0
                suspension_score = 1.0
                online_score = 1.0
                
                satellite_statuses.append({
                    'node_name': node_name,
                    'satellite_id': satellite_id,
                    'satellite_name': satellite_name,
                    'satellite_region': satellite_region,
                    'timestamp': timestamp,
                    'is_vetted': is_vetted,
                    'vetting_progress': vetting_progress,
                    'vetted_at': vetted_at,
                    'audit_score': audit_score,
                    'suspension_score': suspension_score,
                    'online_score': online_score,
                    'joined_at': joined_at,
                    'current_month_egress': current_month_egress,
                    'current_month_ingress': current_month_ingress
                })
                
                logger.debug(f"Extracted satellite status for {node_name} -> {satellite_name}: vetted={is_vetted}, progress={vetting_progress:.2f}")
        
        # If we have satellite_info.audits, use those for per-satellite scores
        if satellite_info.audits:
            self._update_satellite_scores(satellite_statuses, satellite_info.audits)
        
        return satellite_statuses
    
    def _calculate_vetting_progress(self, satellite_data: Dict[str, Any], is_vetted: bool) -> float:
        """Calculate vetting progress (0.0 to 1.0)."""
        # If already vetted, return 1.0
        if is_vetted:
            return 1.0
        
        # For Storj vetting, nodes need to pass certain thresholds
        # This is an approximation based on available data
        
        # Check if we have vetting-related data
        vetting_progress = safe_float(satellite_data.get('vettingProgress', 0.0))
        if vetting_progress > 0:
            return min(vetting_progress, 1.0)
        
        # Try to estimate based on current month bandwidth
        current_ingress = safe_int(satellite_data.get('currentMonthIngress', 0))
        current_egress = safe_int(satellite_data.get('currentMonthEgress', 0))
        
        # Rough heuristic: vetting requires consistent activity
        total_bandwidth = current_ingress + current_egress
        if total_bandwidth > 0:
            # Assume 1GB total bandwidth shows some progress (very rough estimate)
            gb_threshold = 1024 * 1024 * 1024  # 1GB
            progress = min(total_bandwidth / (gb_threshold * 100), 1.0)  # Scale to reasonable progress
            return progress
        
        # If no data available, return 0
        return 0.0
    
    def _update_satellite_scores(self, satellite_statuses: List[Dict[str, Any]], 
                               audits: List[Dict[str, Any]]) -> None:
        """Update satellite statuses with per-satellite audit scores."""
        # Create a mapping of satellite ID to audit data
        audit_map = {}
        for audit in audits:
            satellite_id = audit.get('satelliteID')
            if satellite_id:
                audit_map[satellite_id] = audit
        
        # Update satellite statuses with audit scores
        for satellite_status in satellite_statuses:
            satellite_id = satellite_status['satellite_id']
            if satellite_id in audit_map:
                audit_data = audit_map[satellite_id]
                satellite_status['audit_score'] = safe_float(audit_data.get('auditScore', 1.0))
                satellite_status['suspension_score'] = safe_float(audit_data.get('suspensionScore', 1.0))
                satellite_status['online_score'] = safe_float(audit_data.get('onlineScore', 1.0))
    
    def extract_daily_satellite_metrics(self, node_name: str, 
                                       satellite_info: StorjSatelliteInfo) -> List[Dict[str, Any]]:
        """Extract daily metrics per satellite."""
        daily_metrics = []
        
        # Process daily bandwidth data
        bandwidth_daily = satellite_info.bandwidth_daily or []
        for daily_bw in bandwidth_daily:
            interval_start = daily_bw.get('intervalStart', '')
            if not interval_start:
                continue
                
            try:
                metric_date = timestamp_to_datetime(interval_start).date()
            except (ValueError, TypeError):
                continue
            
            # Extract satellite ID if available
            satellite_id = daily_bw.get('satelliteId')
            if not satellite_id or satellite_id not in KNOWN_SATELLITES:
                # If no satellite ID, this might be aggregated data
                continue
            
            # Extract bandwidth metrics
            egress = daily_bw.get('egress', {})
            ingress = daily_bw.get('ingress', {})
            
            daily_metrics.append({
                'node_name': node_name,
                'satellite_id': satellite_id,
                'date': metric_date,
                'storage_used_bytes': 0,  # Not available in bandwidth data
                'storage_at_rest_bytes': 0,
                'ingress_usage_bytes': safe_int(ingress.get('usage', 0)),
                'ingress_repair_bytes': safe_int(ingress.get('repair', 0)),
                'egress_usage_bytes': safe_int(egress.get('usage', 0)),
                'egress_repair_bytes': safe_int(egress.get('repair', 0)),
                'egress_audit_bytes': safe_int(egress.get('audit', 0)),
                'vetting_bandwidth_requirement': 1024 * 1024 * 1024 * 1024,  # 1TB
                'vetting_bandwidth_completed': safe_int(ingress.get('usage', 0)) + safe_int(egress.get('usage', 0))
            })
        
        # Process daily storage data
        storage_daily = satellite_info.storage_daily or []
        for daily_storage in storage_daily:
            interval_start = daily_storage.get('intervalStart', '')
            if not interval_start:
                continue
                
            try:
                metric_date = timestamp_to_datetime(interval_start).date()
            except (ValueError, TypeError):
                continue
            
            # Extract satellite ID if available
            satellite_id = daily_storage.get('satelliteId')
            if not satellite_id or satellite_id not in KNOWN_SATELLITES:
                continue
            
            # Find matching bandwidth metric or create new one
            existing_metric = None
            for metric in daily_metrics:
                if (metric['satellite_id'] == satellite_id and 
                    metric['date'] == metric_date):
                    existing_metric = metric
                    break
            
            storage_bytes = safe_int(daily_storage.get('atRestTotalBytes', 0))
            
            if existing_metric:
                existing_metric['storage_used_bytes'] = storage_bytes
                existing_metric['storage_at_rest_bytes'] = storage_bytes
            else:
                daily_metrics.append({
                    'node_name': node_name,
                    'satellite_id': satellite_id,
                    'date': metric_date,
                    'storage_used_bytes': storage_bytes,
                    'storage_at_rest_bytes': storage_bytes,
                    'ingress_usage_bytes': 0,
                    'ingress_repair_bytes': 0,
                    'egress_usage_bytes': 0,
                    'egress_repair_bytes': 0,
                    'egress_audit_bytes': 0,
                    'vetting_bandwidth_requirement': 1024 * 1024 * 1024 * 1024,
                    'vetting_bandwidth_completed': 0
                })
        
        return daily_metrics