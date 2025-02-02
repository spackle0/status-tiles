import logging
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, field_validator


class LogConfig(BaseModel):
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @field_validator("level")
    def validate_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()


class RSSServiceConfig(BaseModel):
    name: str
    feed_url: str
    timeout: int

class ServiceConfig(BaseModel):
    name: str
    type: str
    config: RSSServiceConfig  # Now using a specific type instead of Dict[str, Any]
    polling_interval: int = 300

    @field_validator("type")
    def validate_service_type(cls, v: str) -> str:
        if v not in ["rss"]:  # Add more types as needed
            raise ValueError(f"Unsupported service type: {v}")
        return v


class AppConfig(BaseModel):
    log: LogConfig = LogConfig()
    services: List[ServiceConfig]

    model_config = {
        "validate_default": True,
        "extra": "allow"
    }

    def __init__(self, **data):
        if 'services' not in data:
            data['services'] = []
        super().__init__(**data)

@lru_cache()
def get_config(config_path: Optional[Path | str] = None) -> AppConfig:
    """
    Get application configuration, using cached values if available.

    Args:
        config_path: Optional path to config file. If not provided,
                    looks for config.yml in current directory.
    """
    if config_path is None:
        config_path = Path("config.yml")

    try:
        return AppConfig.from_yaml(config_path)
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        # Return default configuration
        return AppConfig()


def load_config(config_path: Path | str = "config.yml") -> AppConfig:
    """
    Load configuration from YAML file. This is a non-cached version
    that's useful for testing and reloading config.
    """
    return AppConfig.from_yaml(config_path)
