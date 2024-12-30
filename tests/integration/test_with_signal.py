# tests/integration/test_with_signal.py

# pylint: disable=duplicate-code

"""
Test cases for the with-signal pattern.
"""

import asyncio
import pytest
from tests.conftest import Receiver
from pynnex import signal, slot, with_signals

@pytest.mark.asyncio
async def test_same_thread_connection(sender, receiver):
    """Test signal-slot connection in same thread"""

    sender.value_changed.connect(receiver, receiver.on_value_changed)
    sender.emit_value(42)
    await asyncio.sleep(0.1)
    assert receiver.received_value == 42
    assert receiver.received_count == 1


@pytest.mark.asyncio
async def test_multiple_slots(sender):
    """Test multiple slot connections"""

    receiver1 = Receiver()
    receiver2 = Receiver()

    sender.value_changed.connect(receiver1, receiver1.on_value_changed)
    sender.value_changed.connect(receiver2, receiver2.on_value_changed)

    sender.emit_value(42)
    await asyncio.sleep(0.1)
    assert receiver1.received_value == 42
    assert receiver1.received_count == 1
    assert receiver2.received_value == 42
    assert receiver2.received_count == 1

@pytest.mark.asyncio
async def test_alias_decorators():
    """Test alias decorators (signal, slot, with_signals)"""
    
    @with_signals
    class AliasTestSender:
        @signal
        def value_changed(self):
            """Signal that is emitted when the value changes."""
            pass

        def emit_value(self, value):
            """Emit the value_changed signal."""
            self.value_changed.emit(value)

    @with_signals
    class AliasTestReceiver:
        def __init__(self):
            self.received_value = None
            self.received_count = 0

        @slot
        def on_value_changed(self, value):
            """Slot that handles value changes."""
            self.received_value = value
            self.received_count += 1

    sender = AliasTestSender()
    receiver = AliasTestReceiver()

    sender.value_changed.connect(receiver, receiver.on_value_changed)
    sender.emit_value(42)
    
    await asyncio.sleep(0.1)
    assert receiver.received_value == 42
    assert receiver.received_count == 1
