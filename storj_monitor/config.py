"""Configuration management for Storj Monitor."""

from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import yaml


class NodeConfig(BaseModel):
    """Configuration for a single Storj node."""
    name: str
    dashboard_url: str
    description: Optional[str] = None

    @property
    def api_base_url(self) -> str:
        """Get the base API URL for this node."""
        return f"{self.dashboard_url}/api"

    @property
    def sno_endpoint(self) -> str:
        """Get the SNO endpoint URL."""
        return f"{self.api_base_url}/sno"

    @property
    def satellites_endpoint(self) -> str:
        """Get the satellites endpoint URL."""
        return f"{self.api_base_url}/sno/satellites"


class MonitoringConfig(BaseModel):
    """Monitoring configuration."""
    poll_interval: int = Field(default=30, description="Polling interval in minutes")
    http_timeout: int = Field(default=30, description="HTTP timeout in seconds")
    max_retries: int = Field(default=3, description="Number of retries for failed requests")
    retry_delay: int = Field(default=5, description="Delay between retries in seconds")


class DatabaseConfig(BaseModel):
    """Database configuration."""
    path: str = Field(default="db/storj_monitor.db", description="SQLite database file path")
    wal_mode: bool = Field(default=True, description="Enable WAL mode for better performance")
    pool_size: int = Field(default=5, description="Connection pool size")

    @property
    def absolute_path(self) -> Path:
        """Get the absolute path to the database file."""
        return Path(self.path).resolve()


class WebServerConfig(BaseModel):
    """Web server configuration."""
    host: str = Field(default="127.0.0.1", description="Host to bind to")
    port: int = Field(default=8080, description="Port to listen on")
    debug: bool = Field(default=False, description="Enable debug mode")
    reload: bool = Field(default=False, description="Auto-reload on code changes")


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO", description="Log level")
    file: str = Field(default="logs/storj_monitor.log", description="Log file path")
    max_size_mb: int = Field(default=10, description="Maximum log file size in MB")
    backup_count: int = Field(default=5, description="Number of backup files to keep")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )

    @property
    def absolute_file_path(self) -> Path:
        """Get the absolute path to the log file."""
        return Path(self.file).resolve()


class Settings(BaseSettings):
    """Main application settings."""
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    nodes: List[NodeConfig] = Field(default_factory=list)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    web_server: WebServerConfig = Field(default_factory=WebServerConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def load_from_yaml(cls, yaml_path: str | Path) -> "Settings":
        """Load settings from a YAML file."""
        yaml_path = Path(yaml_path)
        if not yaml_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {yaml_path}")

        with open(yaml_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)

        return cls(**data)

    def validate_nodes(self) -> None:
        """Validate node configuration."""
        if not self.nodes:
            raise ValueError("At least one node must be configured")

        node_names = [node.name for node in self.nodes]
        if len(node_names) != len(set(node_names)):
            raise ValueError("Node names must be unique")

        for node in self.nodes:
            if not node.dashboard_url.startswith(('http://', 'https://')):
                raise ValueError(f"Invalid dashboard URL for node {node.name}: {node.dashboard_url}")


# Global settings instance
settings: Optional[Settings] = None


def load_settings(config_path: str | Path = "config/settings.yaml") -> Settings:
    """Load and validate settings from configuration file."""
    global settings
    settings = Settings.load_from_yaml(config_path)
    settings.validate_nodes()
    return settings


def get_settings() -> Settings:
    """Get the current settings instance."""
    if settings is None:
        raise RuntimeError("Settings not loaded. Call load_settings() first.")
    return settings