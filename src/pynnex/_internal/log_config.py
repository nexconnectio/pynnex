# src/pynnex/_internal/log_config.py

"""
Log setup for debugging.
"""

import logging
import logging.config
from typing import Optional, Union, Dict

class LogConfig:
    """Logging configuration for debugging."""

    LOG_FORMAT: str = "%(asctime)s - %(name)s - [%(filename)s:%(funcName)s] - %(levelname)s - %(message)s"
    DATE_FORMAT: str = "%H:%M:%S"
    DEFAULT_LEVEL: str = "INFO"

    @classmethod
    def get_config(cls, level: Optional[Union[str, int]] = None) -> Dict:
        """Get default logging configuration as a dictionary."""

        log_level = level or cls.DEFAULT_LEVEL

        return {
            "version": 1,
            "disable_existing_loggers": True,
            "formatters": {
                "default": {
                    "format": cls.LOG_FORMAT,
                    "datefmt": cls.DATE_FORMAT,
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                },
            },
            "loggers": {
                "pynnex": {"level": log_level, "handlers": ["console"]},
                "pynnex.emitter": {"level": log_level, "handlers": ["console"]},
                "pynnex.listener": {"level": log_level, "handlers": ["console"]},
                "pynnex.worker": {"level": log_level, "handlers": ["console"]},
            },
            "root": {
                "level": log_level,
                "handlers": ["console"],
            },
        }

def setup_logging(
    level: Optional[Union[str, int]] = None,
    logger_levels: Optional[Dict[str, Union[str, int]]] = None
) -> None:
    """
    Configure logging for pynnex.

    Args:
        level: Single log level (DEBUG, INFO, WARNING, ERROR, CRITICAL, or numeric value)
               Only used when logger_levels is None.
        logger_levels: Dictionary of {logger_name: log_level} pairs.
                       Sets the log level for each logger defined here.

    Examples:
        >>> # Use the same log level for all pynnex loggers
        >>> setup_logging("DEBUG")

        >>> # Set different log levels for each logger
        >>> setup_logging(logger_levels={
        ...     "pynnex": "INFO",
        ...     "pynnex.emitter": "DEBUG",
        ...     "pynnex.listener": "WARNING",
        ... })
    """
    if logger_levels is None:
        config = LogConfig.get_config(level)
    else:
        config = LogConfig.get_config(None)

        if level:
            config["root"]["level"] = level

        for logger_name, custom_level in logger_levels.items():
            if logger_name not in config["loggers"]:
                config["loggers"][logger_name] = {
                    "level": custom_level,
                    "handlers": ["console"],
                }
            else:
                config["loggers"][logger_name]["level"] = custom_level

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - [%(filename)s:%(funcName)s] - %(levelname)s - %(message)s",
                "datefmt": "%H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "pynnex": {"level": "DEBUG", "handlers": ["console"]},
            "pynnex.emitter": {"level": "DEBUG", "handlers": ["console"]},
            "pynnex.emitter.trace": {"level": "DEBUG", "handlers": ["console"]},
            "pynnex.listener": {"level": "DEBUG", "handlers": ["console"]},
            "pynnex.listener.trace": {"level": "DEBUG", "handlers": ["console"]},
            "pynnex.worker": {"level": "DEBUG", "handlers": ["console"]},
        },
        "root": {
            "level": "DEBUG",
            "handlers": ["console"],
        },
    }

    logging.config.dictConfig(config)
