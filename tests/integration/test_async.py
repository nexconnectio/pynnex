# tests/integration/test_async.py

"""
Test cases for asynchronous operations.
"""

import asyncio
import logging
import pytest

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_multiple_async_slots(sender, receiver):
    """Test multiple async slots receiving signals"""

    logger.info("Test starting with receiver[%s]", receiver.id)
    receiver2 = receiver.__class__()
    logger.info("Created receiver2[%s]", receiver2.id)

    logger.info("Connecting receiver[%s] to signal", receiver.id)
    sender.value_changed.connect(receiver, receiver.on_value_changed)
    logger.info("Connecting receiver2[%s] to signal", receiver2.id)
    sender.value_changed.connect(receiver2, receiver2.on_value_changed)

    logger.info("Emitting value 42")
    sender.emit_value(42)

    for i in range(5):
        logger.info("Wait iteration %d", i + 1)
        if receiver.received_value is not None and receiver2.received_value is not None:
            logger.info("Both receivers have received values")
            break
        await asyncio.sleep(0.1)

    logger.info(
        "Final state - receiver1[%s]: value=%d",
        receiver.id,
        receiver.received_value,
    )
    logger.info(
        "Final state - receiver2[%s]: value=%d",
        receiver2.id,
        receiver2.received_value,
    )

    assert receiver.received_value == 42
    assert receiver2.received_value == 42


@pytest.mark.asyncio
async def test_async_slot_execution(sender, receiver):
    """Test async slot execution with event loop"""

    logger.info("Starting test_async_slot_execution")
    sender.value_changed.connect(receiver, receiver.on_value_changed)

    logger.info("Emitting value")
    sender.emit_value(42)

    for _ in range(5):
        if receiver.received_value is not None:
            break
        await asyncio.sleep(0.1)

    logger.info("Receiver value: %d", receiver.received_value)
    assert receiver.received_value == 42
