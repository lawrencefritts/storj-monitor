#!/usr/bin/env python3
"""Main entry point for Storj Monitor web application."""

import sys
import asyncio
import logging
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from storj_monitor.config import load_settings
from storj_monitor.utils import setup_logging

def main():
    """Main entry point for the web server."""
    try:
        # Load configuration
        config_path = Path(__file__).parent / "config" / "settings.yaml"
        if not config_path.exists():
            print(f"Configuration file not found: {config_path}")
            print("Please create the configuration file before starting the server.")
            sys.exit(1)
        
        settings = load_settings(config_path)
        
        # Set up logging
        logger = setup_logging(settings.logging.level, settings.logging.file)
        
        # Ensure required directories exist
        Path(settings.database.path).parent.mkdir(parents=True, exist_ok=True)
        Path(settings.logging.file).parent.mkdir(parents=True, exist_ok=True)
        
        logger.info("Starting Storj Monitor web server...")
        logger.info(f"Server will be available at http://{settings.web_server.host}:{settings.web_server.port}")
        
        # Start the FastAPI server with uvicorn
        uvicorn.run(
            "webapp.server:app",
            host=settings.web_server.host,
            port=settings.web_server.port,
            reload=settings.web_server.reload,
            log_level=settings.logging.level.lower(),
            access_log=True
        )
        
    except FileNotFoundError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()