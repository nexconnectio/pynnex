# tests/integration/test_worker_queue.py

# pylint: disable=no-member
# pylint: disable=redefined-outer-name

"""
Test cases for the worker-queue pattern.
"""

import asyncio
import logging
import pytest
from pynnex import nx_signal
from pynnex.contrib.patterns.worker.decorators import nx_with_worker

logger = logging.getLogger(__name__)


@pytest.fixture
async def queue_worker():
    """Create a queue worker"""

    logger.info("Creating QueueWorker")
    w = QueueWorker()
    yield w
    logger.info("Cleaning up QueueWorker")
    w.stop()


@nx_with_worker
class QueueWorker:
    """Queue worker class"""

    def __init__(self):
        self.processed_items = []
        super().__init__()

    async def process_item(self, item):
        """Process an item"""

        logger.info(
            "[QueueWorker][process_item] processing item: %s processed_items: %s",
            item,
            self.processed_items,
        )

        await asyncio.sleep(0.1)  # Simulate work
        self.processed_items.append(item)

        logger.info(
            "[QueueWorker][process_item] processed item: %s processed_items: %s",
            item,
            self.processed_items,
        )


@pytest.mark.asyncio
async def test_basic_queue_operation(queue_worker):
    """Basic queue operation test"""

    logger.info("Starting queue worker")
    queue_worker.start()
    logger.info("Queue worker started")
    await asyncio.sleep(0.1)

    logger.info("Queueing tasks")
    queue_worker.queue_task(queue_worker.process_item("item1"))
    logger.info("Task queued: item1")
    queue_worker.queue_task(queue_worker.process_item("item2"))
    logger.info("Task queued: item2")

    logger.info("Waiting for tasks to complete")
    await asyncio.sleep(0.5)

    logger.info("Checking processed items: %s", queue_worker.processed_items)
    assert "item1" in queue_worker.processed_items
    assert "item2" in queue_worker.processed_items
    assert len(queue_worker.processed_items) == 2


@pytest.mark.asyncio
async def test_queue_order(queue_worker):
    """Test for ensuring the order of the task queue"""

    queue_worker.start()
    await asyncio.sleep(0.1)

    items = ["first", "second", "third"]

    for item in items:
        queue_worker.queue_task(queue_worker.process_item(item))

    await asyncio.sleep(0.5)

    assert queue_worker.processed_items == items


@pytest.mark.asyncio
async def test_queue_error_handling(queue_worker):
    """Test for error handling in the task queue"""

    async def failing_task():
        raise ValueError("Test error")

    queue_worker.start()
    await asyncio.sleep(0.1)

    # Add normal and failing tasks
    queue_worker.queue_task(queue_worker.process_item("good_item"))
    queue_worker.queue_task(failing_task())
    queue_worker.queue_task(queue_worker.process_item("after_error"))

    await asyncio.sleep(0.5)

    # The error should not prevent the next task from being processed
    print("[test_queue_error_handling] processed_items: ", queue_worker.processed_items)
    assert "good_item" in queue_worker.processed_items
    assert "after_error" in queue_worker.processed_items


@pytest.mark.asyncio
async def test_queue_cleanup_on_stop(queue_worker):
    """Test for queue cleanup when worker stops"""

    queue_worker.start()
    await asyncio.sleep(0.1)

    # Add a long task
    async def long_task():
        await asyncio.sleep(0.5)
        queue_worker.processed_items.append("long_task")

    queue_worker.queue_task(long_task())

    await asyncio.sleep(1)  # Wait for the task to start
    assert "long_task" in queue_worker.processed_items

    # Stop the worker while the task is running
    queue_worker.stop()

    # Check if the worker exited normally
    assert not queue_worker._nx_thread


@pytest.mark.asyncio
async def test_mixed_signal_and_queue(queue_worker):
    """Test for simultaneous use of signals and task queue"""

    # Add a signal
    @nx_signal
    def task_completed():
        pass

    queue_worker.task_completed = task_completed.__get__(queue_worker)
    signal_received = []
    queue_worker.task_completed.connect(lambda: signal_received.append(True))

    queue_worker.start()
    await asyncio.sleep(0.1)

    # Add a task and emit the signal
    async def task_with_signal():
        await asyncio.sleep(0.1)
        queue_worker.processed_items.append("signal_task")
        queue_worker.task_completed.emit()

    queue_worker.queue_task(task_with_signal())
    await asyncio.sleep(0.3)

    assert "signal_task" in queue_worker.processed_items
    assert signal_received == [True]
