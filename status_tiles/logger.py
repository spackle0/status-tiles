import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: str = "INFO",
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    log_file: Optional[Path] = None,
    max_bytes: int = 10_485_760,  # 10MB
    backup_count: int = 5,
) -> None:
    """
    Configure logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format: Log message format
        log_file: Optional path to log file. If provided, logs will be written to file
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")

    # Create formatter
    formatter = logging.Formatter(format)

    # Configure root logger first
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove any existing handlers
    root_logger.handlers = []

    # Add stdout handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add file handler if specified
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Configure third-party loggers
    third_party_loggers = {
        "uvicorn": logging.INFO,
        "fastapi": logging.INFO,
        "aiohttp": logging.INFO,
        "urllib3": logging.INFO,
        "asyncio": logging.INFO,
    }

    for logger_name, logger_level in third_party_loggers.items():
        logging.getLogger(logger_name).setLevel(logger_level)

    # Configure our application logger
    app_logger = logging.getLogger("status_tiles")
    app_logger.setLevel(numeric_level)  # Use the same level as specified in the args

    # Log startup information
    app_logger.info(f"Logging configured with level: {level}")
    if log_file:
        app_logger.info(f"Logging to file: {log_file}")

    # Log a test message at each level to verify configuration
    app_logger.debug("Debug test message")
    app_logger.info("Info test message")
    app_logger.warning("Warning test message")
    app_logger.error("Error test message")
