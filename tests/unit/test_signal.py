# tests/unit/test_signal.py

# pylint: disable=unused-argument
# pylint: disable=unused-variable
# pylint: disable=too-many-locals

"""
Test cases for the Pynnex signal pattern.
"""

import asyncio
import logging
import pytest
from pynnex.core import (
    nx_with_signals,
    nx_signal,
    nx_slot,
    NxSignal,
    NxConnectionType,
    _determine_connection_type,
)
from pynnex.contrib.patterns.worker.decorators import nx_with_worker
from ..conftest import Receiver

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_signal_creation(sender):
    """Test signal creation and initialization"""

    assert hasattr(sender, "value_changed")
    assert isinstance(sender.value_changed, NxSignal)


@pytest.mark.asyncio
async def test_signal_connection(sender, receiver):
    """Test signal connection"""

    sender.value_changed.connect(receiver, receiver.on_value_changed)
    assert len(sender.value_changed.connections) == 1


@pytest.mark.asyncio
async def test_invalid_connection(sender, receiver):
    """Test invalid signal connections"""

    with pytest.raises(AttributeError):
        sender.value_changed.connect(None, receiver.on_value_changed)

    with pytest.raises(TypeError):
        sender.value_changed.connect(receiver, "not a callable")

    with pytest.raises(TypeError):
        non_existent_slot = getattr(receiver, "non_existent_slot", None)
        sender.value_changed.connect(receiver, non_existent_slot)


@pytest.mark.asyncio
async def test_signal_disconnect_all(sender, receiver):
    """Test disconnecting all slots"""

    sender.value_changed.connect(receiver, receiver.on_value_changed)
    sender.value_changed.connect(receiver, receiver.on_value_changed_sync)

    assert len(sender.value_changed.connections) == 2

    # Disconnect all slots
    disconnected = sender.value_changed.disconnect()
    assert disconnected == 2
    assert len(sender.value_changed.connections) == 0

    # Emit should not trigger any slots
    sender.emit_value(42)
    assert receiver.received_value is None
    assert receiver.received_count == 0


@pytest.mark.asyncio
async def test_signal_disconnect_specific_slot(sender, receiver):
    """Test disconnecting a specific slot"""

    sender.value_changed.connect(receiver, receiver.on_value_changed)
    sender.value_changed.connect(receiver, receiver.on_value_changed_sync)

    assert len(sender.value_changed.connections) == 2

    # Disconnect only the sync slot
    disconnected = sender.value_changed.disconnect(slot=receiver.on_value_changed_sync)
    assert disconnected == 1
    assert len(sender.value_changed.connections) == 1

    # Only async slot should remain
    remaining = sender.value_changed.connections[0]
    assert remaining.get_slot_to_call() == receiver.on_value_changed


@pytest.mark.asyncio
async def test_signal_disconnect_specific_receiver(sender, receiver):
    """Test disconnecting a specific receiver"""

    # Create another receiver instance
    receiver2 = Receiver()

    sender.value_changed.connect(receiver, receiver.on_value_changed)
    sender.value_changed.connect(receiver2, receiver2.on_value_changed)

    assert len(sender.value_changed.connections) == 2

    # Disconnect receiver1
    disconnected = sender.value_changed.disconnect(receiver=receiver)
    assert disconnected == 1
    assert len(sender.value_changed.connections) == 1

    # Only receiver2 should get the signal
    sender.emit_value(42)
    await asyncio.sleep(0.1)
    assert receiver.received_value is None
    assert receiver2.received_value == 42


@pytest.mark.asyncio
async def test_signal_disconnect_specific_receiver_and_slot(sender, receiver):
    """Test disconnecting a specific receiver-slot combination"""

    sender.value_changed.connect(receiver, receiver.on_value_changed)
    sender.value_changed.connect(receiver, receiver.on_value_changed_sync)

    assert len(sender.value_changed.connections) == 2

    # Disconnect specific receiver-slot combination
    disconnected = sender.value_changed.disconnect(
        receiver=receiver, slot=receiver.on_value_changed
    )
    assert disconnected == 1
    assert len(sender.value_changed.connections) == 1

    # Only sync slot should remain
    conn = sender.value_changed.connections[0]
    assert conn.get_slot_to_call() == receiver.on_value_changed_sync


@pytest.mark.asyncio
async def test_signal_disconnect_nonexistent(sender, receiver):
    """Test disconnecting slots that don't exist"""

    sender.value_changed.connect(receiver, receiver.on_value_changed)

    # Try to disconnect nonexistent slot
    disconnected = sender.value_changed.disconnect(
        receiver=receiver, slot=receiver.on_value_changed_sync
    )
    assert disconnected == 0
    assert len(sender.value_changed.connections) == 1

    # Try to disconnect nonexistent receiver
    other_receiver = Receiver()  # Create another instance
    disconnected = sender.value_changed.disconnect(receiver=other_receiver)
    assert disconnected == 0
    assert len(sender.value_changed.connections) == 1


@pytest.mark.asyncio
async def test_signal_disconnect_during_emit(sender, receiver):
    """Test disconnecting slots while emission is in progress"""

    @nx_with_signals
    class SlowReceiver:
        """Receiver class for slow slot"""

        def __init__(self):
            self.received_value = None

        @nx_slot
        async def on_value_changed(self, value):
            """Slot for value changed"""
            await asyncio.sleep(0.1)
            self.received_value = value

    slow_receiver = SlowReceiver()
    sender.value_changed.connect(slow_receiver, slow_receiver.on_value_changed)
    sender.value_changed.connect(receiver, receiver.on_value_changed)

    # Disconnect first, then emit
    sender.value_changed.disconnect(receiver=receiver)
    sender.emit_value(42)  # Changed emission order

    await asyncio.sleep(0.2)

    assert slow_receiver.received_value == 42
    assert receiver.received_value is None


def test_direct_function_connection(sender):
    """Test direct connection of lambda and regular functions"""

    received_values = []

    def collect_value(value):
        """Slot for value changed"""
        received_values.append(value)

    # Connect lambda function
    sender.value_changed.connect(lambda v: received_values.append(v * 2))

    # Connect regular function
    sender.value_changed.connect(collect_value)

    # Emit signal
    sender.emit_value(42)

    assert 42 in received_values  # Added by collect_value
    assert 84 in received_values  # Added by lambda function (42 * 2)
    assert len(received_values) == 2


@pytest.mark.asyncio
async def test_direct_async_function_connection(sender):
    """Test direct connection of async functions"""

    received_values = []

    async def async_collector(value):
        """Slot for value changed"""
        await asyncio.sleep(0.1)
        received_values.append(value)

    # Connect async function
    sender.value_changed.connect(async_collector)

    # Emit signal
    sender.emit_value(42)

    # Wait for async processing
    await asyncio.sleep(0.2)

    assert received_values == [42]


@pytest.mark.asyncio
async def test_direct_function_disconnect(sender):
    """Test disconnection of directly connected functions"""

    received_values = []

    def collector(v):
        """Slot for value changed"""
        received_values.append(v)

    sender.value_changed.connect(collector)

    # First emit
    sender.emit_value(42)
    assert received_values == [42]

    # Disconnect
    disconnected = sender.value_changed.disconnect(slot=collector)
    assert disconnected == 1

    # Second emit - should not add value since connection is disconnected
    sender.emit_value(43)
    assert received_values == [42]


@pytest.mark.asyncio
async def test_method_connection_with_signal_attributes(sender):
    """Test connecting a method with _nx_thread and _nx_loop attributes automatically sets up receiver"""

    received_values = []

    @nx_with_signals
    class SignalReceiver:
        """Receiver class for signal attributes"""

        def collect_value(self, value):
            """Slot for value changed"""

            received_values.append(value)

    class RegularClass:
        """Regular class for value changed"""

        def collect_value(self, value):
            """Slot for value changed"""

            received_values.append(value * 2)

    signal_receiver = SignalReceiver()
    signal = sender.value_changed
    regular_receiver = RegularClass()

    signal.connect(signal_receiver.collect_value)
    signal.connect(regular_receiver.collect_value)

    # The connection type of signal_receiver's method is DIRECT_CONNECTION
    # because it has the same thread affinity as the signal
    conn = signal.connections[-1]
    actual_type = _determine_connection_type(
        conn.conn_type, conn.get_receiver(), signal.owner, conn.is_coro_slot
    )
    assert actual_type == NxConnectionType.DIRECT_CONNECTION

    # The connection type of regular class's method is DIRECT_CONNECTION
    # because it has the same thread affinity as the signal
    conn = signal.connections[-1]
    actual_type = _determine_connection_type(
        conn.conn_type, conn.get_receiver(), signal.owner, conn.is_coro_slot
    )
    assert actual_type == NxConnectionType.DIRECT_CONNECTION

    signal.emit(42)

    assert 42 in received_values
    assert 84 in received_values


@pytest.mark.asyncio
async def test_connection_type_determination():
    """Test connection type is correctly determined for different scenarios"""

    # Regular function should use DIRECT_CONNECTION
    def regular_handler(value):
        """Regular handler"""

    # Async function should use QUEUED_CONNECTION
    async def async_handler(value):
        """Async handler"""

    # Regular class with no thread/loop attributes
    class RegularClass:
        """Regular class"""

        def handler(self, value):
            """Handler"""

    # Regular class with thread/loop attributes
    @nx_with_signals
    class RegularClassWithSignal:
        """Regular class with signal"""

        @nx_signal
        def test_signal(self):
            """Signal"""

    # Class with thread/loop but not worker
    @nx_with_signals
    class ThreadedClass:
        """Threaded class"""

        @nx_slot
        def sync_handler(self, value):
            """Sync handler"""

        @nx_slot
        async def async_handler(self, value):
            """Async handler"""

    # Worker class
    @nx_with_worker
    class WorkerClass:
        """Worker class"""

        @nx_slot
        def sync_handler(self, value):
            """Sync handler"""

        @nx_slot
        async def async_handler(self, value):
            """Async handler"""

    regular_obj = RegularClass()
    regular_with_signal_obj = RegularClassWithSignal()
    threaded_obj = ThreadedClass()
    worker_obj = WorkerClass()

    signal = regular_with_signal_obj.test_signal
    signal.connect(regular_handler)

    # Test sync function connections
    conn = signal.connections[-1]
    actual_type = _determine_connection_type(
        conn.conn_type, conn.get_receiver(), signal.owner, conn.is_coro_slot
    )
    assert actual_type == NxConnectionType.DIRECT_CONNECTION

    # Test async function connections
    signal.connect(async_handler)
    conn = signal.connections[-1]
    actual_type = _determine_connection_type(
        conn.conn_type, conn.get_receiver(), signal.owner, conn.is_coro_slot
    )
    assert actual_type == NxConnectionType.QUEUED_CONNECTION

    # Test regular class method
    signal.connect(regular_obj.handler)
    conn = signal.connections[-1]
    actual_type = _determine_connection_type(
        conn.conn_type, conn.get_receiver(), signal.owner, conn.is_coro_slot
    )
    assert actual_type == NxConnectionType.DIRECT_CONNECTION

    # Test threaded class with sync method
    signal.connect(threaded_obj, threaded_obj.sync_handler)
    conn = signal.connections[-1]
    actual_type = _determine_connection_type(
        conn.conn_type, conn.get_receiver(), signal.owner, conn.is_coro_slot
    )
    assert actual_type == NxConnectionType.DIRECT_CONNECTION

    # Test threaded class with async method
    signal.connect(threaded_obj, threaded_obj.async_handler)
    conn = signal.connections[-1]
    actual_type = _determine_connection_type(
        conn.conn_type, conn.get_receiver(), signal.owner, conn.is_coro_slot
    )
    assert actual_type == NxConnectionType.QUEUED_CONNECTION

    # Test worker class with sync method
    signal.connect(worker_obj.sync_handler)
    conn = signal.connections[-1]
    actual_type = _determine_connection_type(
        conn.conn_type, conn.get_receiver(), signal.owner, conn.is_coro_slot
    )
    assert actual_type == NxConnectionType.QUEUED_CONNECTION

    # Test worker class with async method
    signal.connect(worker_obj.async_handler)
    conn = signal.connections[-1]
    actual_type = _determine_connection_type(
        conn.conn_type, conn.get_receiver(), signal.owner, conn.is_coro_slot
    )
    assert actual_type == NxConnectionType.QUEUED_CONNECTION


async def test_one_shot():
    """
    Verifies that one_shot connections are triggered exactly once,
    then removed automatically upon the first call.
    """

    @nx_with_signals
    class OneShotSender:
        """
        A class that sends one-shot events.
        """

        @nx_signal
        def one_shot_event(self, value):
            """
            One-shot event signal.
            """

    class OneShotReceiver:
        """
        A class that receives one-shot events.
        """

        def __init__(self):
            self.called_count = 0

        def on_event(self, value):
            """
            Event handler.
            """

            self.called_count += 1

    sender = OneShotSender()
    receiver = OneShotReceiver()

    sender.one_shot_event.connect(receiver, receiver.on_event, one_shot=True)

    sender.one_shot_event.emit(123)
    # Ensure all processing is complete
    await asyncio.sleep(1)

    # Already called once, so second emit should not trigger on_event
    sender.one_shot_event.emit(456)
    await asyncio.sleep(1)

    # Check if it was called only once
    assert (
        receiver.called_count == 1
    ), "Receiver should only be called once for a one_shot connection"
