# tests/integration/test_worker_signal.py

# pylint: disable=redefined-outer-name
# pylint: disable=unnecessary-lambda
# pylint: disable=unnecessary-lambda-assignment
# pylint: disable=no-member

"""
Test cases for the worker-signal pattern.
"""

import asyncio
import logging
import pytest
from pynnex import with_worker, signal, NxSignalConstants

logger = logging.getLogger(__name__)


@pytest.fixture
async def signal_worker_lifecycle():
    """Create a signal worker for testing the lifecycle"""
    logger.info("Creating SignalWorker")
    w = SignalWorker()
    yield w


@pytest.fixture
async def signal_worker():
    """Create a signal worker for testing the value changed signal"""
    logger.info("Creating SignalWorker")
    w = SignalWorker()
    yield w
    logger.info("Cleaning up SignalWorker")
    if getattr(w, NxSignalConstants.THREAD, None) and w._nx_thread.is_alive():
        w.stop()


@with_worker
class SignalWorker:
    """Signal worker class"""

    def __init__(self):
        self.value = None
        super().__init__()

    @signal
    def worker_event(self):
        """Signal emitted when the worker event occurs"""

    @signal
    def value_changed(self):
        """Signal emitted when the value changes"""

    def set_value(self, value):
        """Set the value and emit the signal"""
        logger.info("[SignalWorker][set_value]Setting value to: %s", value)
        self.value = value
        self.value_changed.emit(value)


@pytest.mark.asyncio
async def test_signal_lifecycle(signal_worker_lifecycle):
    """Test if the signal emitted from initialize is processed correctly"""
    received = []

    async def on_started():
        logger.info("[on_started]started")
        received.append("started")
        logger.info("[on_started]received: %s", received)

    async def on_stopped():
        logger.info("[on_stopped]stopped")
        received.append("stopped")
        logger.info("[on_stopped]received: %s", received)

    signal_worker_lifecycle.started.connect(on_started)
    signal_worker_lifecycle.stopped.connect(on_stopped)

    signal_worker_lifecycle.start()
    await asyncio.sleep(0.1)
    signal_worker_lifecycle.stop()
    await asyncio.sleep(0.1)

    logger.info("received: %s", received)

    assert "started" in received
    assert "stopped" in received


@pytest.mark.asyncio
async def test_signal_from_worker_thread(signal_worker):
    """Test if the signal emitted from the worker thread is processed correctly"""
    received = []

    async def on_value_changed(value):
        """Callback for the value changed signal"""
        logger.info("[on_value_changed]Received value: %s", value)
        received.append(value)

    signal_worker.value_changed.connect(on_value_changed)

    signal_worker.start()
    await asyncio.sleep(0.1)

    # Emit signal from the worker thread's event loop
    signal_worker.event_loop.call_soon_threadsafe(
        lambda: signal_worker.set_value("test_value")
    )

    await asyncio.sleep(0.1)
    assert "test_value" in received


@pytest.mark.asyncio
async def test_multiple_signals(signal_worker):
    """Test if multiple signals are processed independently"""
    value_changes = []
    worker_events = []

    signal_worker.value_changed.connect(lambda v: value_changes.append(v))
    signal_worker.worker_event.connect(lambda v: worker_events.append(v))

    signal_worker.start()
    await asyncio.sleep(0.1)

    # Emit value_changed signal
    signal_worker.event_loop.call_soon_threadsafe(
        lambda: signal_worker.set_value("test_value")
    )

    # Emit worker_event signal
    signal_worker.event_loop.call_soon_threadsafe(
        lambda: signal_worker.worker_event.emit("worker_event")
    )

    await asyncio.sleep(0.1)

    assert "test_value" in value_changes
    assert "worker_event" in worker_events
    assert len(worker_events) == 1


@pytest.mark.asyncio
async def test_signal_disconnect(signal_worker):
    """Test if signal disconnection works correctly"""
    received = []
    handler = lambda v: received.append(v)

    signal_worker.value_changed.connect(handler)
    signal_worker.start()
    await asyncio.sleep(0.1)

    signal_worker.event_loop.call_soon_threadsafe(
        lambda: signal_worker.set_value("test_value")
    )
    await asyncio.sleep(0.1)

    assert "test_value" in received
    received.clear()

    # Disconnect signal
    signal_worker.value_changed.disconnect(slot=handler)

    signal_worker._nx_loop.call_soon_threadsafe(
        lambda: signal_worker.set_value("after_disconnect")
    )

    await asyncio.sleep(0.1)
    assert len(received) == 0
