import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict

import yaml
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from stevedore import driver

from .config import get_config
from .logger import setup_logging
from .models import ServiceConfig, ServiceState
from .service_modules.base import ServiceModule

# Service registry
services: Dict[str, ServiceModule] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events"""
    # Startup
    config = get_config()
    setup_logging(level=config.log.level, format=config.log.format)
    # setup_logging(level="DEBUG", format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger = logging.getLogger("status_tiles")

    config_path = Path("config.yml")
    if not config_path.exists():
        logger.warning("No config.yml found. Using default configuration.")
        yield
        return

    with open(config_path) as f:
        config = yaml.safe_load(f)

    for service_config in config.get("services", []):
        try:
            service_cfg = ServiceConfig(**service_config)
            mgr = driver.DriverManager(
                namespace="status_tiles.modules",
                name=service_cfg.type,
                invoke_on_load=True,
                invoke_args=(service_cfg.config,),
            )
            services[service_cfg.name] = mgr.driver
            logger.info(f"Loaded service module: {service_cfg.name}")
        except Exception as e:
            logger.error(f"Failed to load service {service_config.get('name')}: {e}")
            print(sys.path)
            print(os.path.abspath("."))

    yield

    # Shutdown
    services.clear()


app = FastAPI(title="Status Tiles", lifespan=lifespan)
logger = logging.getLogger(__name__)

# Get the current file's directory
current_dir = Path(__file__).parent

# Mount static files
static_path = current_dir / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Setup templates
templates = Jinja2Templates(directory=current_dir / "templates")


@app.get("/")
async def home(request: Request):
    """Render the main dashboard page"""
    return templates.TemplateResponse("base.html", {"request": request})


@app.get("/status")
async def get_status(request: Request):
    """Endpoint for HTMX to poll for service status updates"""
    try:
        results = await asyncio.gather(*[service.get_status() for service in services.values()], return_exceptions=True)

        statuses = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error getting status: {result}")
                continue
            if isinstance(result, ServiceState):
                statuses.append(result)

        return templates.TemplateResponse("components/status_tile.html", {"request": request, "services": statuses})
    except Exception as e:
        logger.error(f"Error in status endpoint: {e}")
        return templates.TemplateResponse(
            "components/status_tile.html", {"request": request, "services": [], "error": str(e)}
        )
