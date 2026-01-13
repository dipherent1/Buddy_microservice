import logging
import logging.config
from pathlib import Path
from typing import Any, Dict

# Define a log directory
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "app.log"

# Logging configuration dictionary
LOGGING_CONFIG: Dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "standard": {
            "format": "[%(asctime)s] [%(levelname)s] "
                      "%(name)s:%(funcName)s:%(lineno)d | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "access": {
            "format": '%(asctime)s - %(levelname)s - %(client_addr)s - "%(request_line)s" - %(status_code)s',
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "DEBUG",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "standard",
            "filename": str(LOG_FILE),
            "maxBytes": 10 * 1024 * 1024,  # 10 MB per file
            "backupCount": 5,
            "encoding": "utf-8",
            "level": "INFO",
        },
    },

    "loggers": {
        "uvicorn": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
        "uvicorn.access": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "fastapi": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
        "langchain": {"handlers": ["file"], "level": "WARNING", "propagate": False},
        "app": {"handlers": ["console", "file"], "level": "DEBUG", "propagate": False},
    },

    "root": {"handlers": ["console", "file"], "level": "INFO"},
}


def setup_logging() -> None:
    """
    Configure the logging system for the application.
    Should be called once, typically in app.main.py
    """
    logging.config.dictConfig(LOGGING_CONFIG)
    logging.getLogger("app").info("✅ Logging configured successfully.")


def get_logger(name: str = "app") -> logging.Logger:
    """
    Get a logger instance for a specific module.
    Example: logger = get_logger(__name__)
    """
    return logging.getLogger(name)
