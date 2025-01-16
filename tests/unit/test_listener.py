# tests/unit/test_listener.py

# pylint: disable=duplicate-code
# pylint: disable=no-member

"""
Test cases for the listener pattern.
"""

import asyncio
import threading
import time
import logging
import pytest
from pynnex import with_emitters, listener

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_sync_listener(sender, receiver):
    """Test synchronous listener execution"""

    sender.value_changed.connect(receiver, receiver.on_value_changed_sync)
    sender.emit_value(42)
    assert receiver.received_value == 42
    assert receiver.received_count == 1


@pytest.mark.asyncio
async def test_directly_call_listener(receiver):
    """Test direct listener calls"""

    await receiver.on_value_changed(42)
    assert receiver.received_value == 42
    assert receiver.received_count == 1

    receiver.on_value_changed_sync(43)
    assert receiver.received_value == 43
    assert receiver.received_count == 2


@pytest.mark.asyncio
async def test_listener_exception(sender, receiver):
    """Test exception handling in listeners"""

    @with_emitters
    class ExceptionReceiver:
        """Receiver class for exception testing"""

        @listener
        async def on_value_changed(self, value):
            """Listener for value changed"""
            raise ValueError("Test exception")

    exception_receiver = ExceptionReceiver()
    sender.value_changed.connect(
        exception_receiver, exception_receiver.on_value_changed
    )
    sender.value_changed.connect(receiver, receiver.on_value_changed)

    sender.emit_value(42)
    await asyncio.sleep(0.1)
    assert receiver.received_value == 42
    assert receiver.received_count == 1


@pytest.mark.asyncio
async def test_listener_thread_safety():
    """Test listener direct calls from different threads"""

    @with_emitters
    class ThreadTestReceiver:
        """Receiver class for thread safety testing"""

        def __init__(self):
            super().__init__()
            self.received_value = None
            self.received_count = 0
            self.execution_thread = None

        @listener
        async def async_listener(self, value):
            """Async listener for thread safety testing"""
            self.execution_thread = threading.current_thread()
            await asyncio.sleep(0.1)  # work simulation with sleep
            self.received_value = value
            self.received_count += 1

        @listener
        def sync_listener(self, value):
            """Sync listener for thread safety testing"""
            self.execution_thread = threading.current_thread()
            time.sleep(0.1)  # work simulation with sleep
            self.received_value = value
            self.received_count += 1

    receiver = ThreadTestReceiver()
    task_completed = threading.Event()
    main_thread = threading.current_thread()
    initial_values = {"value": None, "count": 0}  # save initial values

    def background_task():
        """Background task for thread safety testing"""
        try:
            # Before async_listener call
            initial_values["value"] = receiver.received_value
            initial_values["count"] = receiver.received_count

            coro = receiver.async_listener(42)
            future = asyncio.run_coroutine_threadsafe(coro, receiver._nx_loop)
            # Wait for async_listener result
            future.result()

            # verify state change
            assert receiver.received_value != initial_values["value"]
            assert receiver.received_count == initial_values["count"] + 1
            assert receiver.execution_thread == main_thread

            # Before sync_listener call
            initial_values["value"] = receiver.received_value
            initial_values["count"] = receiver.received_count

            receiver.sync_listener(43)

            # verify state change
            assert receiver.received_value != initial_values["value"]
            assert receiver.received_count == initial_values["count"] + 1
            assert receiver.execution_thread == main_thread

        finally:
            task_completed.set()

    async def run_test():
        """Run test for thread safety"""
        thread = threading.Thread(target=background_task)
        thread.start()

        while not task_completed.is_set():
            await asyncio.sleep(0.1)

        thread.join()

        # Cleanup
        pending = asyncio.all_tasks(receiver._nx_loop)
        if pending:
            logger.debug("Cleaning up %d pending tasks", len(pending))
            for task in pending:
                if "test_listener_thread_safety" in str(task.get_coro()):
                    logger.debug("Skipping test function task: %s", task)
                else:
                    logger.debug("Found application task: %s", task)
                    try:
                        await asyncio.gather(task, return_exceptions=True)
                    except Exception as e:
                        logger.error("Error during cleanup: %s", e)
        else:
            logger.debug("No pending tasks to clean up")

    try:
        await run_test()
    except Exception as e:
        logger.error("Error in test: %s", e)
