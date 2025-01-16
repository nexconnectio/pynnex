# tests/integration/test_worker_emitter.py

# pylint: disable=redefined-outer-name
# pylint: disable=unnecessary-lambda
# pylint: disable=unnecessary-lambda-assignment
# pylint: disable=no-member

"""
Test cases for the worker-emitter pattern.
"""

import asyncio
import logging
import pytest
from pynnex import with_worker, emitter, NxEmitterConstants

logger = logging.getLogger(__name__)


@pytest.fixture
async def emitter_worker_lifecycle():
    """Create an emitter worker for testing the lifecycle"""
    logger.info("Creating EmitterWorker")
    w = EmitterWorker()
    yield w


@pytest.fixture
async def emitter_worker():
    """Create an emitter worker for testing the value changed emitter"""
    logger.info("Creating EmitterWorker")
    w = EmitterWorker()
    yield w
    logger.info("Cleaning up EmitterWorker")
    if getattr(w, NxEmitterConstants.THREAD, None) and w._nx_thread.is_alive():
        w.stop()


@with_worker
class EmitterWorker:
    """Emitter worker class"""

    def __init__(self):
        self.value = None
        super().__init__()

    @emitter
    def worker_event(self):
        """Emitter emitted when the worker event occurs"""

    @emitter
    def value_changed(self):
        """Emitter emitted when the value changes"""

    def set_value(self, value):
        """Set the value and emit the emitter"""
        logger.info("[EmitterWorker][set_value]Setting value to: %s", value)
        self.value = value
        self.value_changed.emit(value)


@pytest.mark.asyncio
async def test_emitter_lifecycle(emitter_worker_lifecycle):
    """Test if the emitter emitted from initialize is processed correctly"""
    received = []

    async def on_started():
        logger.info("[on_started]started")
        received.append("started")
        logger.info("[on_started]received: %s", received)

    async def on_stopped():
        logger.info("[on_stopped]stopped")
        received.append("stopped")
        logger.info("[on_stopped]received: %s", received)

    emitter_worker_lifecycle.started.connect(on_started)
    emitter_worker_lifecycle.stopped.connect(on_stopped)

    emitter_worker_lifecycle.start()
    await asyncio.sleep(0.1)
    emitter_worker_lifecycle.stop()
    await asyncio.sleep(0.1)

    logger.info("received: %s", received)

    assert "started" in received
    assert "stopped" in received


@pytest.mark.asyncio
async def test_emitter_from_worker_thread(emitter_worker):
    """Test if the emitter emitted from the worker thread is processed correctly"""
    received = []

    async def on_value_changed(value):
        """Callback for the value changed emitter"""
        logger.info("[on_value_changed]Received value: %s", value)
        received.append(value)

    emitter_worker.value_changed.connect(on_value_changed)

    emitter_worker.start()
    await asyncio.sleep(0.1)

    # Emit emitter from the worker thread's event loop
    emitter_worker.event_loop.call_soon_threadsafe(
        lambda: emitter_worker.set_value("test_value")
    )

    await asyncio.sleep(0.1)
    assert "test_value" in received


@pytest.mark.asyncio
async def test_multiple_emitters(emitter_worker):
    """Test if multiple emitters are processed independently"""
    value_changes = []
    worker_events = []

    emitter_worker.value_changed.connect(lambda v: value_changes.append(v))
    emitter_worker.worker_event.connect(lambda v: worker_events.append(v))

    emitter_worker.start()
    await asyncio.sleep(0.1)

    # Emit value_changed emitter
    emitter_worker.event_loop.call_soon_threadsafe(
        lambda: emitter_worker.set_value("test_value")
    )

    # Emit worker_event emitter
    emitter_worker.event_loop.call_soon_threadsafe(
        lambda: emitter_worker.worker_event.emit("worker_event")
    )

    await asyncio.sleep(0.1)

    assert "test_value" in value_changes
    assert "worker_event" in worker_events
    assert len(worker_events) == 1


@pytest.mark.asyncio
async def test_emitter_disconnect(emitter_worker):
    """Test if emitter disconnection works correctly"""
    received = []
    handler = lambda v: received.append(v)

    emitter_worker.value_changed.connect(handler)
    emitter_worker.start()
    await asyncio.sleep(0.1)

    emitter_worker.event_loop.call_soon_threadsafe(
        lambda: emitter_worker.set_value("test_value")
    )
    await asyncio.sleep(0.1)

    assert "test_value" in received
    received.clear()

    # Disconnect emitter
    emitter_worker.value_changed.disconnect(listener=handler)

    emitter_worker._nx_loop.call_soon_threadsafe(
        lambda: emitter_worker.set_value("after_disconnect")
    )

    await asyncio.sleep(0.1)
    assert len(received) == 0
