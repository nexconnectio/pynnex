# tests/integration/test_worker.py

# pylint: disable=no-member
# pylint: disable=redefined-outer-name
# pylint: disable=unused-variable
# pylint: disable=unused-argument

"""
Test cases for the worker pattern.
"""

import asyncio
import logging
import pytest
from pynnex import with_worker, listener, emitter

logger = logging.getLogger(__name__)


@pytest.fixture
async def worker():
    """Create a worker"""

    w = TestWorker()
    yield w

    if w._nx_thread is not None and w._nx_thread.is_alive():
        w.stop()


@with_worker
class TestWorker:
    """Test worker class"""

    def __init__(self):
        self.run_called = False
        self.data = []
        self.started.connect(self.on_started)

    @listener
    def on_started(self, *args, **kwargs):
        """Listener for started signal"""

        self.run_called = True
        initial_value = args[0] if args else kwargs.get("initial_value", None)

        if initial_value:
            self.data.append(initial_value)


@pytest.mark.asyncio
async def test_worker_basic():
    """Test the worker basic functionality"""

    result = None

    @with_worker
    class BackgroundWorker:
        """Background worker class"""

        def __init__(self):
            self.started.connect(self.on_started)
            self.work_done.connect(self.on_work_done)

        @emitter
        def work_done(self):
            """Emitter for work done"""

        @listener
        async def on_started(self, *args, **kwargs):
            """Listener for started signal"""

            # Initialize resources and start processing
            await self.heavy_task(10)

        @listener
        def on_work_done(self, value):
            """Listener for work done signal"""

            nonlocal result
            result = value

        async def heavy_task(self, data):
            """Heavy task"""

            await asyncio.sleep(2)  # Simulate heavy computation
            self.work_done.emit(data * 2)

    worker = BackgroundWorker()
    worker.start()

    # Wait for work to complete
    await asyncio.sleep(2.5)  # Slightly longer than heavy_task sleep

    worker.stop()

    # Verify the computation result
    assert result == 20, f"Expected result to be 20, but got {result}"
    # Verify worker stopped properly
    assert (
        not worker._nx_thread.is_alive()
    ), "Worker thread should not be alive after stop"


@pytest.mark.asyncio
async def test_worker_lifecycle(worker):
    """Test the worker lifecycle"""

    initial_value = "test"

    assert worker._nx_thread is None
    assert worker._nx_loop is None
    assert not worker.run_called

    worker.start(initial_value)

    for i in range(10):
        if worker.run_called:
            break

        await asyncio.sleep(0.1)
    else:
        pytest.fail("Worker did not run in time")

    assert worker.run_called
    assert worker.data == [initial_value]

    worker.stop()


@with_worker
class AliasTestWorker:
    """Test worker class using alias decorator"""

    def __init__(self):
        self.run_called = False
        self.data = []
        self.started.connect(self.on_started)

    @listener
    def on_started(self, *args, **kwargs):
        """Listener for started signal"""

        self.run_called = True
        initial_value = args[0] if args else kwargs.get("initial_value", None)

        if initial_value:
            self.data.append(initial_value)


@pytest.mark.asyncio
async def test_worker_alias_lifecycle():
    """Test the worker lifecycle using alias decorator"""

    initial_value = "test_alias"

    worker = AliasTestWorker()

    assert worker._nx_thread is None
    assert worker._nx_loop is None
    assert not worker.run_called

    worker.start(initial_value)

    for i in range(10):
        if worker.run_called:
            break

        await asyncio.sleep(0.1)
    else:
        pytest.fail("Worker did not run in time")

    assert worker.run_called
    assert worker.data == [initial_value]

    worker.stop()
