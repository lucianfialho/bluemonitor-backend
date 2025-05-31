"""Logging configuration for the application."""
import logging
import logging.config
import os
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
from structlog.types import EventDict, Processor

from app.core.config import settings


class RemoveSensitiveInfoProcessor:
    """Remove sensitive information from logs."""

    def __init__(self, keys_to_remove: Optional[list] = None):
        self.keys_to_remove = keys_to_remove or [
            "password",
            "token",
            "secret",
            "api_key",
            "authorization",
            "set-cookie",
            "cookie",
        ]

    def __call__(self, logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
        """Process the event dictionary to remove sensitive information."""
        for key in list(event_dict.keys()):
            if any(sensitive in key.lower() for sensitive in self.keys_to_remove):
                event_dict[key] = "[REDACTED]"
        return event_dict


def configure_logging() -> None:
    """Configure logging for the application."""
    # Ensure logs directory exists
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Configure structlog
    timestamper = structlog.processors.TimeStamper(fmt="iso")
    pre_chain = [
        # Add the log level and a timestamp to the event_dict if the log entry
        # is not from structlog.
        structlog.stdlib.add_log_level,
        timestamper,
    ]

    logging_config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.processors.JSONRenderer(),
                "foreign_pre_chain": pre_chain,
            },
            "colored": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.dev.ConsoleRenderer(colors=True),
                "foreign_pre_chain": pre_chain,
            },
        },
        "handlers": {
            "console": {
                "level": settings.LOG_LEVEL,
                "class": "logging.StreamHandler",
                "formatter": "colored",
            },
            "file": {
                "level": settings.LOG_LEVEL,
                "class": "logging.handlers.RotatingFileHandler",
                "filename": logs_dir / "bluemonitor.log",
                "maxBytes": 10 * 1024 * 1024,  # 10MB
                "backupCount": 5,
                "formatter": "json",
                "encoding": "utf8",
            },
        },
        "loggers": {
            "": {
                "handlers": ["console", "file"],
                "level": settings.LOG_LEVEL,
                "propagate": True,
            },
            "uvicorn": {"handlers": ["console", "file"], "level": settings.LOG_LEVEL},
            "uvicorn.error": {
                "handlers": ["console", "file"],
                "level": settings.LOG_LEVEL,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["console", "file"],
                "level": settings.LOG_LEVEL,
                "propagate": False,
            },
            "fastapi": {"handlers": ["console", "file"], "level": settings.LOG_LEVEL},
            "httpx": {"handlers": ["console", "file"], "level": settings.LOG_LEVEL},
            "httpcore": {"handlers": ["console", "file"], "level": settings.LOG_LEVEL},
        },
    }

    logging.config.dictConfig(logging_config)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            RemoveSensitiveInfoProcessor(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Set log level for all loggers
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format=settings.LOG_FORMAT,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(logs_dir / "bluemonitor.log"),
        ],
    )

    # Set log level for uvicorn loggers
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.setLevel(settings.LOG_LEVEL)
    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    uvicorn_error_logger.setLevel(settings.LOG_LEVEL)
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.setLevel(settings.LOG_LEVEL)

    # Set log level for application loggers
    app_logger = logging.getLogger("app")
    app_logger.setLevel(settings.LOG_LEVEL)

    # Set log level for third-party loggers
    logging.getLogger("httpx").setLevel(settings.LOG_LEVEL)
    logging.getLogger("httpcore").setLevel(settings.LOG_LEVEL)
    logging.getLogger("asyncio").setLevel(settings.LOG_LEVEL)

    # Suppress noisy loggers
    logging.getLogger("fsevents").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)
