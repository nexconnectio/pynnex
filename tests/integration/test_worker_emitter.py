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

    w = EmitterWorker()
    yield w

    if getattr(w, NxEmitterConstants.THREAD, None) and w._nx_thread.is_alive():
        w.stop()
        await asyncio.sleep(0.1)


@with_worker
class EmitterWorker:
    """Emitter worker class"""

    def __init__(self):
        self.value = None

    @emitter
    def worker_event(self):
        """Emitter emitted when the worker event occurs"""

    @emitter
    def value_changed(self):
        """Emitter emitted when the value changes"""

    def set_value(self, value):
        """Set the value and emit the emitter"""

        self.value = value
        self.value_changed.emit(value)


@pytest.mark.asyncio
async def test_emitter_lifecycle(emitter_worker_lifecycle):
    """Test if the emitter emitted from initialize is processed correctly"""
    received = []

    async def on_started():
        received.append("started")

    async def on_stopped():
        received.append("stopped")

    emitter_worker_lifecycle.started.connect(on_started)
    emitter_worker_lifecycle.stopped.connect(on_stopped)

    emitter_worker_lifecycle.start()
    await asyncio.sleep(0.1)
    emitter_worker_lifecycle.stop()
    await asyncio.sleep(0.1)

    assert "started" in received
    assert "stopped" in received


@pytest.mark.asyncio
async def test_emitter_from_worker_thread(emitter_worker):
    """Test if the emitter emitted from the worker thread is processed correctly"""

    received = []

    async def on_value_changed(value):
        """Callback for the value changed emitter"""

        received.append(value)

    emitter_worker.value_changed.connect(on_value_changed)

    emitter_worker.start()
    await asyncio.sleep(0.1)

    emitter_worker.queue_task(lambda: emitter_worker.set_value("test_value"))
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
    emitter_worker.queue_task(lambda: emitter_worker.set_value("test_value"))

    # Emit worker_event emitter
    emitter_worker.queue_task(lambda: emitter_worker.worker_event.emit("worker_event"))
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

    emitter_worker.queue_task(lambda: emitter_worker.set_value("test_value"))
    await asyncio.sleep(0.1)

    assert "test_value" in received
    received.clear()

    # Disconnect emitter
    emitter_worker.value_changed.disconnect(listener=handler)

    emitter_worker.queue_task(lambda: emitter_worker.set_value("after_disconnect"))

    await asyncio.sleep(0.1)
    assert len(received) == 0
