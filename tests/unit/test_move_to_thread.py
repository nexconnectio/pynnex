# tests/unit/test_move_to_thread.py

# pylint: disable=no-member
# pylint: disable=unnecessary-lambda
# pylint: disable=useless-with-lock
# pylint: disable=unused-argument
# pylint: disable=redefined-outer-name
# pylint: disable=import-outside-toplevel

"""
Move to thread test.
"""

import asyncio
import logging
import threading
import pytest
from pynnex import emitter, listener, with_emitters, with_worker

logger = logging.getLogger(__name__)


@with_worker
class WorkerA:
    """First worker thread."""

    async def run(self, *args, **kwargs):
        """Run the worker thread."""

        logger.info("[WorkerA] run() started")
        await self.start_queue()


@with_worker
class WorkerB:
    """Second worker thread."""

    async def run(self, *args, **kwargs):
        """Run the worker thread."""

        logger.info("[WorkerB] run() started")
        await self.start_queue()


@with_emitters
class Mover:
    """
    move_to_thread test object.
    Created in main thread, then moved to WorkerA -> WorkerB,
    to check emitter behavior.
    """

    @emitter
    def data_ready(self, value):
        """Emitter for data ready."""

    def __init__(self):
        super().__init__()
        self.emitted_values = []

    def do_work(self, value):
        """
        Assume some work is done in a separate thread (or main thread),
        and emit an emitter.
        """

        logger.info(
            "[Mover][do_work] value=%s (thread=%s)",
            value,
            threading.current_thread().name,
        )
        self.data_ready.emit(value)

    @listener
    def on_data_ready(self, value):
        """
        Listener for data_ready emitter.
        """

        logger.info(
            "[Mover][on_data_ready] value=%s (thread=%s)",
            value,
            threading.current_thread().name,
        )
        self.emitted_values.append(value)


@pytest.mark.asyncio
async def test_move_to_thread():
    """
    1) Create Mover object in main thread
    2) Move to WorkerA thread
    3) Move to WorkerB thread
    Check if emitter is emitted/received correctly in each step
    """

    logger.info("=== test_move_to_thread START ===")

    # 1) Create Mover object in main thread
    mover = Mover()

    # Connect emitter to mover's on_data_ready method
    mover.data_ready.connect(mover, mover.on_data_ready)

    # 2) Prepare WorkerA
    worker_a = WorkerA()
    worker_a.start()  # Start thread + event loop
    await asyncio.sleep(0.2)  # Wait for worker_a run() to start

    # move_to_thread
    mover.move_to_thread(worker_a)
    logger.info("Mover moved to WorkerA thread")

    # Call do_work -> WorkerA thread emits emitter
    mover.do_work("from WorkerA")
    await asyncio.sleep(0.3)  # Wait for emitter to be processed

    assert (
        "from WorkerA" in mover.emitted_values
    ), "The data emitted from WorkerA should be received"

    # 3) Prepare WorkerB
    worker_b = WorkerB()
    worker_b.start()
    await asyncio.sleep(0.2)

    mover.move_to_thread(worker_b)
    logger.info("Mover moved to WorkerB thread")

    # do_work -> Now WorkerB emits emitter
    mover.do_work("from WorkerB")
    await asyncio.sleep(0.3)

    assert (
        "from WorkerB" in mover.emitted_values
    ), "The data emitted from WorkerB should be received"

    # Clean up
    worker_a.stop()
    worker_b.stop()

    logger.info("=== test_move_to_thread DONE ===")
