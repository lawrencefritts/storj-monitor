"""FastAPI web server for Storj Monitor."""

import sys
from pathlib import Path
from typing import List, Optional
import logging

# Add parent directory to path to import storj_monitor
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Query, Depends, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from storj_monitor.config import load_settings, get_settings
from storj_monitor.models import NodeStatus
from storj_monitor.utils import setup_logging
from .database import DatabaseManager


# Initialize settings and logging
settings = load_settings()
logger = setup_logging(settings.logging.level, "logs/webapp.log")

# Create FastAPI app
app = FastAPI(
    title="Storj Monitor API",
    description="REST API for monitoring Storj storage nodes",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database dependency
def get_db_manager() -> DatabaseManager:
    return DatabaseManager()

# Mount static files
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Root endpoint serves the main dashboard
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the main dashboard."""
    dashboard_file = Path(__file__).parent / "static" / "index.html"
    if dashboard_file.exists():
        return FileResponse(dashboard_file)
    return HTMLResponse("""
        <html>
            <head><title>Storj Monitor</title></head>
            <body>
                <h1>Storj Monitor Dashboard</h1>
                <p>Dashboard not available. Static files not found.</p>
                <p><a href="/api/docs">View API Documentation</a></p>
            </body>
        </html>
    """)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "storj-monitor-api"}

# API Routes
@app.get("/api/nodes", response_model=List[NodeStatus])
async def get_nodes(db: DatabaseManager = Depends(get_db_manager)):
    """Get status of all nodes."""
    try:
        return await db.get_latest_node_status()
    except Exception as e:
        logger.error(f"Error fetching node status: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch node status")

@app.get("/api/nodes/{node_name}", response_model=NodeStatus)
async def get_node(node_name: str, db: DatabaseManager = Depends(get_db_manager)):
    """Get status of a specific node."""
    try:
        node = await db.get_node_status(node_name)
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")
        return node
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching node {node_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch node data")

@app.get("/api/nodes/{node_name}/disk-usage")
async def get_disk_usage_history(
    node_name: str,
    hours: int = Query(default=24, ge=1, le=168, description="Hours of history to fetch"),
    db: DatabaseManager = Depends(get_db_manager)
):
    """Get disk usage history for a node."""
    try:
        return await db.get_disk_usage_history(node_name, hours)
    except Exception as e:
        logger.error(f"Error fetching disk usage for {node_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch disk usage data")

@app.get("/api/nodes/{node_name}/bandwidth-usage")
async def get_bandwidth_usage_history(
    node_name: str,
    hours: int = Query(default=24, ge=1, le=168, description="Hours of history to fetch"),
    db: DatabaseManager = Depends(get_db_manager)
):
    """Get bandwidth usage history for a node."""
    try:
        return await db.get_bandwidth_usage_history(node_name, hours)
    except Exception as e:
        logger.error(f"Error fetching bandwidth usage for {node_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch bandwidth usage data")

@app.get("/api/nodes/{node_name}/daily-bandwidth")
async def get_daily_bandwidth_summary(
    node_name: str,
    days: int = Query(default=30, ge=1, le=365, description="Days of history to fetch"),
    db: DatabaseManager = Depends(get_db_manager)
):
    """Get daily bandwidth summary for a node."""
    try:
        return await db.get_daily_bandwidth_summary(node_name, days)
    except Exception as e:
        logger.error(f"Error fetching daily bandwidth for {node_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch daily bandwidth data")

@app.get("/api/nodes/{node_name}/health-metrics")
async def get_health_metrics_history(
    node_name: str,
    hours: int = Query(default=24, ge=1, le=168, description="Hours of history to fetch"),
    db: DatabaseManager = Depends(get_db_manager)
):
    """Get health metrics history for a node."""
    try:
        return await db.get_health_metrics_history(node_name, hours)
    except Exception as e:
        logger.error(f"Error fetching health metrics for {node_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch health metrics data")

@app.get("/api/system/summary")
async def get_system_summary(db: DatabaseManager = Depends(get_db_manager)):
    """Get overall system summary."""
    try:
        return await db.get_system_summary()
    except Exception as e:
        logger.error(f"Error fetching system summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch system summary")

@app.get("/api/system/events")
async def get_recent_events(
    limit: int = Query(default=50, ge=1, le=500, description="Maximum number of events to return"),
    db: DatabaseManager = Depends(get_db_manager)
):
    """Get recent system events and alerts."""
    try:
        return await db.get_recent_events(limit)
    except Exception as e:
        logger.error(f"Error fetching recent events: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch recent events")

# Configuration endpoint (read-only)
@app.get("/api/config")
async def get_config():
    """Get current configuration (read-only, sensitive data excluded)."""
    try:
        config = get_settings()
        return {
            "monitoring": {
                "poll_interval": config.monitoring.poll_interval,
                "node_count": len(config.nodes)
            },
            "nodes": [
                {
                    "name": node.name,
                    "description": node.description,
                    "url": node.dashboard_url  # This is already public info
                }
                for node in config.nodes
            ],
            "web_server": {
                "host": config.web_server.host,
                "port": config.web_server.port
            }
        }
    except Exception as e:
        logger.error(f"Error fetching config: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch configuration")

# Database Browser Routes
@app.get("/db", response_class=HTMLResponse)
async def database_browser():
    """Serve the database browser page."""
    db_browser_file = Path(__file__).parent / "static" / "db.html"
    if db_browser_file.exists():
        return FileResponse(db_browser_file)
    return HTMLResponse("""
        <html>
            <head><title>Database Browser - Storj Monitor</title></head>
            <body>
                <h1>Database Browser</h1>
                <p>Database browser not available. db.html file not found.</p>
                <p><a href="/">Back to Dashboard</a></p>
            </body>
        </html>
    """)

@app.get("/api/db/schema")
async def get_database_schema(db: DatabaseManager = Depends(get_db_manager)):
    """Get database schema information."""
    try:
        return await db.get_database_schema()
    except Exception as e:
        logger.error(f"Error fetching database schema: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch database schema")

@app.get("/api/db/table/{table_name}")
async def get_table_data(
    table_name: str,
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum rows to return"),
    offset: int = Query(default=0, ge=0, description="Row offset for pagination"),
    db: DatabaseManager = Depends(get_db_manager)
):
    """Get data from a specific table or view."""
    try:
        return await db.get_table_data(table_name, limit, offset)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching table data for {table_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch table data")

@app.post("/api/db/query")
async def execute_query(
    query_data: dict = Body(...),
    db: DatabaseManager = Depends(get_db_manager)
):
    """Execute a read-only SQL query."""
    try:
        query = query_data.get('query', '').strip()
        if not query:
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        return await db.execute_query(query)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        raise HTTPException(status_code=500, detail="Failed to execute query")

# Satellite API Routes
@app.get("/api/satellites")
async def get_satellites(db: DatabaseManager = Depends(get_db_manager)):
    """Get all satellites information."""
    try:
        return await db.get_satellites()
    except Exception as e:
        logger.error(f"Error fetching satellites: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch satellites")

@app.get("/api/nodes/{node_name}/satellites")
async def get_node_satellites(
    node_name: str,
    db: DatabaseManager = Depends(get_db_manager)
):
    """Get satellite status for a specific node."""
    try:
        return await db.get_node_satellite_status(node_name)
    except Exception as e:
        logger.error(f"Error fetching node satellites for {node_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch node satellite data")

@app.get("/api/satellites/status")
async def get_all_satellites_status(db: DatabaseManager = Depends(get_db_manager)):
    """Get satellite status for all nodes."""
    try:
        return await db.get_all_satellite_status()
    except Exception as e:
        logger.error(f"Error fetching all satellite status: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch satellite status")

@app.get("/api/vetting/summary")
async def get_vetting_summary(
    node_name: Optional[str] = Query(default=None, description="Specific node name (optional)"),
    db: DatabaseManager = Depends(get_db_manager)
):
    """Get vetting summary for nodes."""
    try:
        return await db.get_vetting_summary(node_name)
    except Exception as e:
        logger.error(f"Error fetching vetting summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch vetting summary")

@app.get("/api/satellites/comparison")
async def get_satellite_comparison(db: DatabaseManager = Depends(get_db_manager)):
    """Get comparison data across all satellites."""
    try:
        return await db.get_satellite_comparison()
    except Exception as e:
        logger.error(f"Error fetching satellite comparison: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch satellite comparison")


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Storj Monitor web server...")
    uvicorn.run(
        "webapp.server:app",
        host=settings.web_server.host,
        port=settings.web_server.port,
        reload=settings.web_server.reload,
        log_level=settings.logging.level.lower()
    )