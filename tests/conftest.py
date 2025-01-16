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
from pynnex import with_emitters, emitter, listener

# Only creating the logger without configuration
logger = logging.getLogger(__name__)


@with_emitters
class Sender:
    """Sender class"""

    def __str__(self):
        return f"Sender(id={id(self)})"

    @emitter
    def value_changed(self, value):
        """Emitter for value changes"""

    def emit_value(self, value):
        """Emit a value change emitter"""
        self.value_changed.emit(value)


@with_emitters
class Receiver:
    """Receiver class"""

    def __init__(self):
        super().__init__()
        self.id = id(self)

        logger.debug("[Receiver][__init__] self=%s", self)

        self.received_value = None
        self.received_count = 0
        logger.info("Created Receiver[%d]", self.id)

    def __str__(self):
        return f"Receiver(id={self.id})"

    @listener
    async def on_value_changed(self, value: int):
        """Listener for value changes"""
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

    @listener
    def on_value_changed_sync(self, value: int):
        """Sync listener for value changes"""
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
        "%(asctime)s - %(name)s - [%(filename)s:%(funcName)s] - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    # Setting package logger levels
    logging.getLogger("pynnex").setLevel(default_level)
    logging.getLogger("tests").setLevel(default_level)

    # Disable trace logging
    logging.getLogger("pynnex.emitter").setLevel(logging.WARNING)
    logging.getLogger("pynnex.listener").setLevel(logging.WARNING)
    logging.getLogger("pynnex.emitter.trace").setLevel(logging.WARNING)
    logging.getLogger("pynnex.listener.trace").setLevel(logging.WARNING)

    # For debugging
    # root.setLevel(logging.DEBUG)
    # console_handler.setLevel(logging.DEBUG)
    # logging.getLogger("pynnex").setLevel(logging.DEBUG)
    # logging.getLogger("tests").setLevel(logging.DEBUG)
    # logging.getLogger("pynnex.emitter").setLevel(logging.DEBUG)
    # logging.getLogger("pynnex.listener").setLevel(logging.DEBUG)
    # logging.getLogger("pynnex.emitter.trace").setLevel(logging.DEBUG)
    # logging.getLogger("pynnex.listener.trace").setLevel(logging.DEBUG)
