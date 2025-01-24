# tests/integration/test_worker_queue.py

# pylint: disable=no-member
# pylint: disable=redefined-outer-name

"""
Test cases for the worker-queue pattern.
"""

import asyncio
import logging
import pytest
from pynnex import emitter, with_worker

logger = logging.getLogger(__name__)


@pytest.fixture
async def queue_worker():
    """Create a queue worker"""

    logger.info("Creating QueueWorker")
    w = QueueWorker()
    yield w
    logger.info("Cleaning up QueueWorker")

    if w._nx_thread is not None and w._nx_thread.is_alive():
        w.stop()


@with_worker
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

    queue_worker.start()
    await asyncio.sleep(0.1)

    queue_worker.queue_task(queue_worker.process_item("item1"))
    queue_worker.queue_task(queue_worker.process_item("item2"))

    await asyncio.sleep(0.5)

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
    assert not queue_worker._nx_thread.is_alive()


@pytest.mark.asyncio
async def test_mixed_emitter_and_queue(queue_worker):
    """Test for simultaneous use of emitters and task queue"""

    # Add an emitter
    @emitter
    def task_completed():
        pass

    queue_worker.task_completed = task_completed.__get__(queue_worker)
    emitter_received = []
    queue_worker.task_completed.connect(lambda: emitter_received.append(True))

    queue_worker.start()
    await asyncio.sleep(0.1)

    # Add a task and emit the emitter
    async def task_with_emitter():
        await asyncio.sleep(0.1)
        queue_worker.processed_items.append("emitter_task")
        queue_worker.task_completed.emit()

    queue_worker.queue_task(task_with_emitter())
    await asyncio.sleep(0.3)

    assert "emitter_task" in queue_worker.processed_items
    assert emitter_received == [True]
