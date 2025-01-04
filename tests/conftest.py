# tests/conftest.py

"""
Shared fixtures for tests.
"""

# pylint: disable=no-member
# pylint: disable=redefined-outer-name
# pylint: disable=unused-variable
# pylint: disable=unused-argument
# pylint: disable=property-with-parameters

import os
import sys
import asyncio
import threading
import logging
import pytest
import pytest_asyncio
from pynnex import with_signals, signal, slot

# Only creating the logger without configuration
logger = logging.getLogger(__name__)


@with_signals
class Sender:
    """Sender class"""

    @signal
    def value_changed(self, value):
        """Signal for value changes"""

    def emit_value(self, value):
        """Emit a value change signal"""
        self.value_changed.emit(value)


@with_signals
class Receiver:
    """Receiver class"""

    def __init__(self):
        super().__init__()

        logger.debug("[Receiver][__init__] self=%s", self)

        self.received_value = None
        self.received_count = 0
        self.id = id(self)
        logger.info("Created Receiver[%d]", self.id)

    @slot
    async def on_value_changed(self, value: int):
        """Slot for value changes"""
        logger.info(
            "Receiver[%d] on_value_changed called with value: %d", self.id, value
        )
        logger.info("Current thread: %s", threading.current_thread().name)
        logger.info("Current event loop: %s", asyncio.get_running_loop())
        self.received_value = value
        self.received_count += 1
        logger.info(
            "Receiver[%d] updated: value=%d, count=%d",
            self.id,
            self.received_value,
            self.received_count,
        )

    @slot
    def on_value_changed_sync(self, value: int):
        """Sync slot for value changes"""
        logger.info(
            "Receiver[%d] on_value_changed_sync called with value: %d", self.id, value
        )
        self.received_value = value
        self.received_count += 1
        logger.info(
            "Receiver[%d] updated (sync): value=%d, count=%d",
            self.id,
            self.received_value,
            self.received_count,
        )


@pytest_asyncio.fixture
async def receiver():
    """Create a receiver"""
    logger.info("Creating receiver. event loop: %s", asyncio.get_running_loop())
    return Receiver()


@pytest_asyncio.fixture
async def sender():
    """Create a sender"""
    logger.info("Creating receiver. event loop: %s", asyncio.get_running_loop())
    return Sender()


@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    """Configure logging for tests"""
    # Setting up the root logger
    root = logging.getLogger()

    # Setting to WARNING level by default
    default_level = logging.WARNING
    # default_level = logging.DEBUG

    # Can enable DEBUG mode via environment variable

    if os.environ.get("PYNNEX_DEBUG"):
        default_level = logging.DEBUG

    root.setLevel(default_level)
    logger.debug("Logging level set to: %s", default_level)

    # Removing existing handlers
    for handler in root.handlers:
        root.removeHandler(handler)

    # Setting up console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(default_level)

    # Setting formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    # Setting package logger levels
    logging.getLogger("pynnex").setLevel(default_level)
    logging.getLogger("tests").setLevel(default_level)
