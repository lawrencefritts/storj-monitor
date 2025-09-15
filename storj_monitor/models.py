"""Data models for Storj node metrics."""

from datetime import datetime, date
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class StorjNodeInfo(BaseModel):
    """Basic node information from the /api/sno endpoint."""
    node_id: str = Field(alias="nodeID")
    wallet: str
    satellites: Optional[List[Dict[str, Any]]] = None
    disk_space: Dict[str, int] = Field(alias="diskSpace")
    bandwidth: Dict[str, int]
    last_pinged: str = Field(alias="lastPinged")
    version: str
    started_at: str = Field(alias="startedAt")
    quic_status: str = Field(alias="quicStatus")
    
    class Config:
        allow_population_by_field_name = True


class StorjSatelliteInfo(BaseModel):
    """Satellite information and daily metrics from /api/sno/satellites endpoint."""
    storage_daily: Optional[List[Dict[str, Any]]] = Field(alias="storageDaily", default_factory=list)
    bandwidth_daily: Optional[List[Dict[str, Any]]] = Field(alias="bandwidthDaily", default_factory=list)
    storage_summary: float = Field(alias="storageSummary", default=0.0)
    bandwidth_summary: int = Field(alias="bandwidthSummary", default=0)
    egress_summary: int = Field(alias="egressSummary", default=0)
    ingress_summary: int = Field(alias="ingressSummary", default=0)
    audits: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        allow_population_by_field_name = True


class DiskMetrics(BaseModel):
    """Disk usage metrics."""
    node_name: str
    timestamp: datetime
    used_bytes: int
    available_bytes: int
    trash_bytes: int = 0
    overused_bytes: int = 0


class BandwidthMetrics(BaseModel):
    """Bandwidth usage metrics."""
    node_name: str
    timestamp: datetime
    used_bytes: int
    available_bytes: int = 0


class HealthMetrics(BaseModel):
    """Node health and status metrics."""
    node_name: str
    timestamp: datetime
    version: str
    uptime_seconds: int
    last_pinged: datetime
    quic_status: str
    audit_score: float = 1.0
    suspension_score: float = 1.0
    online_score: float = 1.0
    satellites_count: int = 0


class DailyBandwidthMetrics(BaseModel):
    """Daily aggregated bandwidth metrics."""
    node_name: str
    date: date
    ingress_usage_bytes: int = 0
    ingress_repair_bytes: int = 0
    egress_usage_bytes: int = 0
    egress_repair_bytes: int = 0
    egress_audit_bytes: int = 0
    delete_bytes: int = 0


class DailyStorageMetrics(BaseModel):
    """Daily storage metrics."""
    node_name: str
    date: date
    at_rest_total_bytes: int = 0
    average_usage_bytes: int = 0


class SatelliteInfo(BaseModel):
    """Information about a Storj satellite."""
    satellite_id: str
    name: str  # us1, eu1, ap1, saltlake
    region: str
    description: Optional[str] = None


class NodeSatelliteStatus(BaseModel):
    """Per-satellite status for a node."""
    node_name: str
    satellite_id: str
    satellite_name: str
    satellite_region: str
    is_vetted: bool = False
    vetting_progress: float = 0.0  # 0.0 to 1.0
    vetted_at: Optional[datetime] = None
    audit_score: float = 1.0
    suspension_score: float = 1.0
    online_score: float = 1.0
    joined_at: Optional[datetime] = None
    current_month_egress: int = 0
    current_month_ingress: int = 0
    last_updated: Optional[datetime] = None


class VettingSummary(BaseModel):
    """Vetting summary for a node across all satellites."""
    node_name: str
    total_satellites: int
    vetted_count: int
    avg_progress: float
    min_progress: float
    max_progress: float
    status_summary: str  # e.g., "us1:VETTED,eu1:45.2%,ap1:VETTED,saltlake:12.8%"
    
    @property
    def vetting_percentage(self) -> float:
        """Calculate overall vetting percentage."""
        return (self.vetted_count / self.total_satellites * 100) if self.total_satellites > 0 else 0.0


class NodeStatus(BaseModel):
    """Combined node status for API responses."""
    name: str
    node_id: Optional[str] = None
    description: Optional[str] = None
    disk_used: Optional[int] = None
    disk_available: Optional[int] = None
    disk_trash: Optional[int] = None
    bandwidth_used: Optional[int] = None
    version: Optional[str] = None
    audit_score: Optional[float] = None
    suspension_score: Optional[float] = None
    online_score: Optional[float] = None
    quic_status: Optional[str] = None
    last_pinged: Optional[datetime] = None
    satellites_count: Optional[int] = None
    last_updated: Optional[datetime] = None
    
    # Enhanced satellite information
    active_satellites: Optional[int] = None
    vetted_satellites: Optional[int] = None
    avg_vetting_progress: Optional[float] = None
    vetted_satellite_names: Optional[str] = None
    
    # Computed properties
    @property
    def disk_usage_percentage(self) -> Optional[float]:
        """Calculate disk usage percentage."""
        if self.disk_used is not None and self.disk_available is not None:
            total = self.disk_used + self.disk_available
            if total > 0:
                return (self.disk_used / total) * 100
        return None

    @property
    def health_status(self) -> str:
        """Determine overall health status."""
        if (self.audit_score is not None and self.audit_score < 0.95) or \
           (self.suspension_score is not None and self.suspension_score < 0.95):
            return "critical"
        elif (self.audit_score is not None and self.audit_score < 0.98) or \
             (self.online_score is not None and self.online_score < 0.95):
            return "warning"
        else:
            return "healthy"