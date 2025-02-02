import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict, Literal, Optional

import yaml
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
    feed_url: str  # Could use HttpUrl type if you want URL validation
    timeout: int


class HTTPServiceConfig(BaseModel):
    name: str
    url: str  # Could use HttpUrl type if you want URL validation
    method: Literal["GET", "POST", "PUT", "DELETE"] = "GET"
    timeout: int
    expected_status: int = 200
    headers: Optional[Dict[str, str]] = None


class ServiceConfig(BaseModel):
    name: str
    type: Literal["rss", "http"]
    config: RSSServiceConfig | HTTPServiceConfig  # Union type for different configs
    polling_interval: int = 300

    @field_validator("config")
    def validate_config_type(cls, v: Dict | RSSServiceConfig | HTTPServiceConfig, values: Dict) -> Dict:
        # This validates that the config matches the service type
        service_type = values.get("type")

        if service_type == "rss" and not isinstance(v, RSSServiceConfig):
            # If dict is passed, try to convert it
            if isinstance(v, dict):
                return RSSServiceConfig(**v)
            raise ValueError("RSS service must use RSSServiceConfig")

        if service_type == "http" and not isinstance(v, HTTPServiceConfig):
            # If dict is passed, try to convert it
            if isinstance(v, dict):
                return HTTPServiceConfig(**v)
            raise ValueError("HTTP service must use HTTPServiceConfig")

        return v


# Add this class method to AppConfig
class AppConfig(BaseModel):
    # ... existing AppConfig code ...

    @classmethod
    def from_yaml(cls, path: Path | str) -> "AppConfig":
        """Load configuration from YAML file.

        Args:
            path: Path to YAML configuration file

        Returns:
            AppConfig: Loaded configuration

        Raises:
            FileNotFoundError: If configuration file doesn't exist
            ValidationError: If configuration is invalid
            YAMLError: If YAML parsing fails
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with path.open() as f:
            config_data = yaml.safe_load(f)

        return cls.model_validate(config_data)


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
