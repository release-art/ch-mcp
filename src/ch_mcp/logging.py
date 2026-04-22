from __future__ import annotations

import logging
import logging.config
import os

logger = logging.getLogger(__name__)

_HUMAN_LOGS = os.environ.get("HUMAN_LOGS", "").lower() in ("1", "true", "yes", "on")


def get_config() -> dict:
    """Generate the current log configuration as a dictionary."""
    sqelched_loggers = {
        name: {
            "level": "ERROR",
            "handlers": ["console"],
            "propagate": False,
        }
        for name in [
            "azure.core.pipeline.policies.http_logging_policy",
            "docket.worker",
            "sse_starlette.sse",
        ]
    }
    if _HUMAN_LOGS:
        formatter = {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        }
    else:
        formatter = {
            "()": "pythonjsonlogger.json.JsonFormatter",
            "fmt": "%(asctime)s %(name)s %(levelname)s %(message)s",
        }
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": formatter,
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "level": "DEBUG",
            },
        },
        "loggers": {**sqelched_loggers},
        "root": {
            "level": "DEBUG",
            "handlers": ["console"],
        },
    }


def configure():
    """Apply the logging configuration to the root logger."""
    logging.config.dictConfig(get_config())
