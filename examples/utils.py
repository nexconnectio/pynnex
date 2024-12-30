# examples/utils.py

"""
Utility functions for example applications
"""

import logging
import sys


def logger_setup(name: str, level: int = logging.INFO):
    """setup logging for example application"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.hasHandlers():
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger
