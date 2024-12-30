# tests/integration/test_threading.py

# pylint: disable=unused-argument
# pylint: disable=unnecessary-lambda

"""
Test cases for threading.
"""

import asyncio
import threading
import time
import logging
import pytest
from pynnex.core import nx_with_signals, nx_signal, nx_slot

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_different_thread_connection(sender, receiver):
    """Test signal emission from different thread"""

    sender.value_changed.connect(receiver, receiver.on_value_changed)
    sender_done = threading.Event()

    def run_sender():
        """Run the sender thread"""
        for i in range(3):
            sender.emit_value(i)
            time.sleep(0.1)
        sender_done.set()

    sender_thread = threading.Thread(target=run_sender)
    sender_thread.start()

    while not sender_done.is_set() or receiver.received_count < 3:
        await asyncio.sleep(0.1)

    sender_thread.join()

    assert receiver.received_count == 3
    assert receiver.received_value == 2


@pytest.mark.asyncio
async def test_call_slot_from_other_thread(receiver):
    """Test calling slot from different thread"""

    done = threading.Event()

    def other_thread():
        """Run the other thread"""

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def call_slot():
            await receiver.on_value_changed(100)

        loop.run_until_complete(call_slot())
        done.set()
        loop.close()

    thread = threading.Thread(target=other_thread)
    thread.start()

    while not done.is_set():
        await asyncio.sleep(0.1)

    thread.join()
    assert receiver.received_value == 100
    assert receiver.received_count == 1


@pytest.mark.asyncio
async def test_connection_type_with_different_threads():
    """Test connection type is determined correctly for different thread scenarios"""

    @nx_with_signals
    class Sender:
        """Sender class"""

        @nx_signal
        def value_changed(self):
            """Signal emitted when value changes"""

    @nx_with_signals
    class Receiver:
        """Receiver class"""

        def __init__(self):
            super().__init__()
            self.received = False

        @nx_slot
        def on_value_changed(self, value):
            """Slot called when value changes"""

            self.received = True

    # Create receiver in a different thread
    receiver_in_thread = None
    receiver_thread_ready = threading.Event()
    receiver_loop_running = threading.Event()
    receiver_stop_loop_event = threading.Event()

    def create_receiver():
        """Create receiver in a different thread"""

        nonlocal receiver_in_thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def create_receiver_async():
            r = Receiver()
            return r

        receiver_in_thread = loop.run_until_complete(create_receiver_async())
        receiver_thread_ready.set()

        # Keep the loop running after receiver is created
        def keep_running():
            loop.call_soon_threadsafe(lambda: receiver_loop_running.set())
            loop.run_forever()

        loop_thread = threading.Thread(target=keep_running, daemon=True)
        loop_thread.start()

        # Wait until the test is finished
        receiver_stop_loop_event.wait()

        # Stop the event loop
        loop.call_soon_threadsafe(loop.stop)
        loop_thread.join()

    receiver_thread = threading.Thread(target=create_receiver)
    receiver_thread.start()

    receiver_thread_ready.wait()  # Wait for receiver to be created
    receiver_loop_running.wait()  # Wait for receiver loop to be actually running

    sender_in_main_thread = Sender()
    sender_in_main_thread.value_changed.connect(
        receiver_in_thread, receiver_in_thread.on_value_changed
    )
    sender_in_main_thread.value_changed.emit(123)

    time.sleep(1)

    assert (
        receiver_in_thread.received is True
    ), "Slot should be triggered asynchronously (queued)"

    receiver_stop_loop_event.set()
    receiver_thread.join()
