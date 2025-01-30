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
from pynnex.contrib.patterns.worker.decorators import WorkerState

logger = logging.getLogger(__name__)


@pytest.fixture
async def worker():
    """Create a worker"""

    w = TestWorker()
    yield w

    if (
        w._nx_thread is not None
        and w._nx_thread.is_alive()
        and w._nx_loop is not None
        and w._nx_loop.is_running()
    ):
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


@pytest.mark.asyncio
async def test_not_started(worker):
    """
    Test the worker not started state
    """
    with pytest.raises(RuntimeError):
        worker.queue_task(asyncio.sleep(0.1))


@pytest.mark.asyncio
async def test_start_stop_immediate(worker):
    """
    Test the worker start() and stop() immediately
    """
    worker.start()

    with pytest.raises(RuntimeError):
        worker.stop()


@pytest.mark.asyncio
async def test_simple_tasks(worker):
    """
    Test the worker with simple tasks
    """

    worker.start()

    async def task1():
        await asyncio.sleep(0.1)
        return "task1_done"

    async def task2():
        await asyncio.sleep(0.2)
        return "task2_done"

    f1 = worker.queue_task(task1())
    f2 = worker.queue_task(task2())
    r1, r2 = await asyncio.gather(f1, f2)
    assert r1 == "task1_done"
    assert r2 == "task2_done"

    worker.stop()
    assert worker.state == WorkerState.STOPPED


@pytest.mark.asyncio
async def test_stop_before_tasks_finish(worker):
    """
    Test the worker with long task and stop() immediately
    """

    worker.start()

    async def long_task():
        await asyncio.sleep(5)
        return "long_done"

    f = worker.queue_task(long_task())
    with pytest.raises(RuntimeError):
        worker.stop()


@pytest.mark.asyncio
async def test_queue_after_stop(worker):
    """
    Test the worker queue_task() after stop()
    """

    worker.start()

    await asyncio.sleep(1)

    with pytest.raises(RuntimeError):
        worker.stop()
        worker.queue_task(asyncio.sleep(0.1))


#


@pytest.mark.asyncio
async def test_multiple_start(worker):
    """
    Test the worker multiple start()
    """

    worker.start()

    # Call start() while state is STARTING -> STARTED
    with pytest.raises(RuntimeError):
        worker.start()


@pytest.mark.asyncio
async def test_multiple_stop(worker):
    """
    Test if stop() is ignored when called multiple times
    """

    worker.start()
    await asyncio.sleep(0.1)
    with pytest.raises(RuntimeError):
        worker.stop()
        worker.stop()


@pytest.mark.asyncio
async def test_task_exception(worker):
    """
    Test if the task exception is set to the future
    """

    worker.start()

    async def error_task():
        raise ValueError("Something bad happened")

    f = worker.queue_task(error_task())
    with pytest.raises(ValueError) as exc:
        await f

    assert "Something bad happened" in str(exc.value)

    worker.stop()


@pytest.mark.asyncio
async def test_task_cancellation(worker):
    """
    Test if the task is cancelled when worker is stopped while the task is running
    """

    worker.start()

    async def long_task():
        logger.debug("[Worker] long_task() #1")
        await asyncio.sleep(5)
        logger.debug("[Worker] long_task() #2")

    f = worker.queue_task(long_task())
    await asyncio.sleep(0.1)
    worker.stop()

    logger.debug("[Worker] test_task_cancellation() #1")
    try:
        await f
    except asyncio.CancelledError:
        logger.debug("[Worker] test_task_cancellation() #2")
    assert f.cancelled()
    logger.debug("[Worker] test_task_cancellation() #3")
