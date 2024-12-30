# examples/stock_monitor_simple.py

# pylint: disable=no-member
# pylint: disable=unused-argument

"""
Stock monitor simple example.

This module shows a straightforward example of using a worker (`DataWorker`)
to generate data continuously and a display (`DataDisplay`) to process and
log that data on the main thread. It's a minimal demonstration of Pynnex's
thread-safe signal/slot invocation.
"""

import asyncio
import threading
import time
from utils import logger_setup
from pynnex import with_signals, signal, slot, with_worker

logger_setup("pynnex")
logger = logger_setup(__name__)

@with_worker
class DataWorker:
    """
    A simple data worker that emits incrementing integers every second.

    Attributes
    ----------
    _running : bool
        Indicates whether the update loop is active.
    _update_task : asyncio.Task, optional
        The asynchronous task that updates and emits data.

    Signals
    -------
    data_processed
        Emitted with the incremented integer each time data is processed.

    Lifecycle
    ---------
    - `run(...)` is called automatically in the worker thread.
    - `stop()` stops the worker, cancelling the update loop.
    """

    def __init__(self):
        self._running = False
        self._update_task = None

    @signal
    def data_processed(self):
        """
        Signal emitted when data is processed.

        Receives an integer count.
        """

    async def run(self, *args, **kwargs):
        """
        Worker initialization and main event loop.

        Creates the update loop task and waits until the worker is stopped.
        """

        logger.info("[DataWorker][run] Starting")

        self._running = True
        self._update_task = asyncio.create_task(self.update_loop())
        # Wait until run() is finished
        await self.wait_for_stop()
        # Clean up
        self._running = False

        if self._update_task:
            self._update_task.cancel()

            try:
                await self._update_task
            except asyncio.CancelledError:
                pass

    async def update_loop(self):
        """
        Periodically emits a counter value.

        Every second, the counter increments and `data_processed` is emitted.
        """

        count = 0

        while self._running:
            logger.debug("[DataWorker] Processing data %d", count)
            self.data_processed.emit(count)

            count += 1

            await asyncio.sleep(1)


@with_signals
class DataDisplay:
    """
    A display class that receives the processed data from the worker.

    Attributes
    ----------
    last_value : int or None
        Stores the last received value from the worker.
    """

    def __init__(self):
        self.last_value = None
        logger.debug("[DataDisplay] Created in thread: %s", threading.current_thread().name)

    @slot
    def on_data_processed(self, value):
        """
        Slot called when data is processed.

        Logs the received value and simulates a brief processing delay.
        """

        current_thread = threading.current_thread()
        logger.debug(
            "[DataDisplay] Received value %d in thread: %s", value, current_thread.name
        )
        self.last_value = value
        # Add a small delay to check the result
        time.sleep(0.1)
        logger.debug("[DataDisplay] Processed value %d", value)


async def main():
    """
    Main function demonstrating how to set up and run the worker and display.
    """

    logger.debug("Starting in thread: %s", threading.current_thread().name)

    worker = DataWorker()
    display = DataDisplay()

    # Both are in the main thread at the connection point
    worker.data_processed.connect(display, display.on_data_processed)

    worker.start()

    try:
        await asyncio.sleep(3)  # Run for 3 seconds
    finally:
        worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
