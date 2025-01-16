# tests/integration/test_with_emitter.py

# pylint: disable=duplicate-code

"""
Test cases for the with-emitter pattern.
"""

import asyncio
import pytest
from tests.conftest import Receiver
from pynnex import (
    emitter,
    listener,
    with_emitters,
    signal,
    slot,
    with_signals,
    publisher,
    subscriber,
    with_publishers,
)


@pytest.mark.asyncio
async def test_same_thread_connection(sender, receiver):
    """Test emitter-listener connection in same thread"""

    sender.value_changed.connect(receiver, receiver.on_value_changed)
    sender.emit_value(42)
    await asyncio.sleep(0.1)
    assert receiver.received_value == 42
    assert receiver.received_count == 1


@pytest.mark.asyncio
async def test_multiple_listeners(sender):
    """Test multiple listener connections"""

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
    """Test alias decorators (emitter, listener, with_emitters)"""

    @with_emitters
    class AliasTestSender:
        """Test sender class with alias decorators"""

        @emitter
        def value_changed(self):
            """Emitter that is emitted when the value changes."""

        def emit_value(self, value):
            """Emit the value_changed emitter."""

            self.value_changed.emit(value)

    @with_emitters
    class AliasTestReceiver:
        """Test receiver class with alias decorators"""

        def __init__(self):
            self.received_value = None
            self.received_count = 0

        @listener
        def on_value_changed(self, value):
            """Listener that handles value changes."""

            self.received_value = value
            self.received_count += 1

    sender = AliasTestSender()
    receiver = AliasTestReceiver()

    sender.value_changed.connect(receiver, receiver.on_value_changed)
    sender.emit_value(42)

    await asyncio.sleep(0.1)
    assert receiver.received_value == 42
    assert receiver.received_count == 1

    # @with_signals, @signal, @slot
    @with_signals
    class SignalAliasTestSender:
        """Test sender class with alias decorators"""

        @signal
        def value_changed(self):
            """Emitter that is emitted when the value changes."""

        def emit_value(self, value):
            """Emit the value_changed emitter."""

            self.value_changed.emit(value)

    @with_signals
    class SignalAliasTestReceiver:
        """Test receiver class with alias decorators"""

        def __init__(self):
            self.received_value = None
            self.received_count = 0

        @slot
        def on_value_changed(self, value):
            """Listener that handles value changes."""

            self.received_value = value
            self.received_count += 1

    sender = SignalAliasTestSender()
    receiver = SignalAliasTestReceiver()

    sender.value_changed.connect(receiver, receiver.on_value_changed)
    sender.emit_value(42)

    await asyncio.sleep(0.1)
    assert receiver.received_value == 42
    assert receiver.received_count == 1

    # @with_publishers, @publisher, @subscriber
    @with_publishers
    class PublisherAliasTestSender:
        """Test sender class with alias decorators"""

        @publisher
        def value_changed(self):
            """Emitter that is emitted when the value changes."""

        def emit_value(self, value):
            """Emit the value_changed emitter."""

            self.value_changed.emit(value)

    @with_publishers
    class PublisherAliasTestReceiver:
        """Test receiver class with alias decorators"""

        def __init__(self):
            self.received_value = None
            self.received_count = 0

        @slot
        def on_value_changed(self, value):
            """Listener that handles value changes."""

            self.received_value = value
            self.received_count += 1

    sender = PublisherAliasTestSender()
    receiver = PublisherAliasTestReceiver()

    sender.value_changed.connect(receiver, receiver.on_value_changed)
    sender.emit_value(42)

    await asyncio.sleep(0.1)
    assert receiver.received_value == 42
    assert receiver.received_count == 1
