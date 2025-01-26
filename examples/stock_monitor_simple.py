# examples/stock_monitor_simple.py

# pylint: disable=no-member
# pylint: disable=unused-argument

"""
Stock monitor simple example.

This module shows a straightforward example of using a worker (`DataWorker`)
to generate data continuously and a display (`DataDisplay`) to process and
log that data on the main thread. It's a minimal demonstration of PynneX's
thread-safe emitter/listener invocation.
"""

import asyncio
import threading
import time
from utils import logger_setup
from pynnex import with_emitters, emitter, listener, with_worker

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

    Emitters
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
        self.started.connect(self.on_started)
        self.stopped.connect(self.on_stopped)

    @emitter
    def data_processed(self):
        """
        Emitter emitted when data is processed.

        Receives an integer count.
        """

    @listener
    async def on_started(self, *args, **kwargs):
        """Called when worker starts."""

        print(f"[DataWorker][on_started] thread: {threading.current_thread().name}")
        self._running = True
        self._update_task = self.queue_task(self.process_data())

    @listener
    async def on_stopped(self):
        """Called when worker stops."""

        self._running = False
        print(f"[DataWorker][on_stopped] thread: {threading.current_thread().name}")

    async def process_data(self):
        count = 0

        while self._running:
            print(
                f"[DataWorker][process_data] data {count} thread: {threading.current_thread().name}"
            )

            self.data_processed.emit(count)
            count += 1
            await asyncio.sleep(1)

        print(
            f"[DataWorker][process_data] END thread: {threading.current_thread().name}"
        )


@with_emitters
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
        logger.info(
            "[DataDisplay] Created in thread: %s", threading.current_thread().name
        )

    @listener
    def on_data_processed(self, value):
        """
        Listener called when data is processed.

        Logs the received value and simulates a brief processing delay.
        """

        print(
            f"[DataDisplay][on_data_processed] START in thread: {threading.current_thread().name}"
        )
        self.last_value = value
        time.sleep(0.1)  # simulate heavy processing
        print(f"[DataDisplay][on_data_processed] END value {value}")


async def main():
    """
    Main function demonstrating how to set up and run the worker and display.
    """

    logger.info("Starting in thread: %s", threading.current_thread().name)

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
