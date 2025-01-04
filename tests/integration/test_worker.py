# tests/integration/test_worker.py

# pylint: disable=no-member
# pylint: disable=redefined-outer-name
# pylint: disable=unused-variable

"""
Test cases for the worker pattern.
"""

import asyncio
import logging
import pytest
from pynnex import NxSignalConstants, with_worker

logger = logging.getLogger(__name__)


@pytest.fixture
async def worker():
    """Create a worker"""

    w = TestWorker()
    yield w

    if getattr(w, NxSignalConstants.THREAD, None) and w._nx_thread.is_alive():
        w.stop()

@with_worker
class TestWorker:
    """Test worker class"""

    def __init__(self):
        self.run_called = False
        self.data = []
        super().__init__()

    async def run(self, *args, **kwargs):
        """Run the worker"""

        self.run_called = True
        initial_value = args[0] if args else kwargs.get("initial_value", None)

        if initial_value:
            self.data.append(initial_value)

        await self.start_queue()


@pytest.mark.asyncio
async def test_worker_lifecycle(worker):
    """Test the worker lifecycle"""

    logger.info("Starting test_worker_lifecycle")
    initial_value = "test"

    logger.info("Checking initial state")
    assert worker._nx_thread is None
    assert worker._nx_loop is None
    assert not worker.run_called

    logger.info("Starting worker")
    worker.start(initial_value)

    logger.info("Waiting for worker initialization")
    for i in range(10):
        if worker.run_called:
            logger.info("Worker run called after %d attempts", i + 1)
            break
        logger.info("Waiting attempt %d", i + 1)
        await asyncio.sleep(0.1)
    else:
        logger.error("Worker failed to run")
        pytest.fail("Worker did not run in time")

    logger.info("Checking worker state")
    assert worker.run_called
    assert worker.data == [initial_value]

    logger.info("Stopping worker")
    worker.stop()

@with_worker
class AliasTestWorker:
    """Test worker class using alias decorator"""

    def __init__(self):
        self.run_called = False
        self.data = []
        super().__init__()

    async def run(self, *args, **kwargs):
        """Run the worker"""

        self.run_called = True
        initial_value = args[0] if args else kwargs.get("initial_value", None)
        if initial_value:
            self.data.append(initial_value)
        await self.start_queue()

@pytest.mark.asyncio
async def test_worker_alias_lifecycle():
    """Test the worker lifecycle using alias decorator"""

    logger.info("Starting test_worker_alias_lifecycle")
    initial_value = "test_alias"

    worker = AliasTestWorker()

    logger.info("Checking initial state")
    assert worker._nx_thread is None
    assert worker._nx_loop is None
    assert not worker.run_called

    logger.info("Starting worker")
    worker.start(initial_value)

    logger.info("Waiting for worker initialization")
    for i in range(10):
        if worker.run_called:
            logger.info("Worker run called after %d attempts", i + 1)
            break
        logger.info("Waiting attempt %d", i + 1)
        await asyncio.sleep(0.1)
    else:
        logger.error("Worker failed to run")
        pytest.fail("Worker did not run in time")

    logger.info("Checking worker state")
    assert worker.run_called
    assert worker.data == [initial_value]

    logger.info("Stopping worker")
    worker.stop()
