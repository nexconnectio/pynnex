# examples/signal_async.py

"""
Async Signal Example

This example demonstrates the basic usage of Pynnex with async slots:
1. Creating a signal
2. Connecting an async slot
3. Emitting a signal to async handler

Key Points:
- Demonstrates asynchronous signal-slot communication
- Shows how to use @nx_slot decorator with async functions
- Illustrates handling of async slot execution in event loop
- Explains integration of signals with asyncio for non-blocking operations
"""

import asyncio
from pynnex import with_signals, signal, slot
from utils import logger_setup

logger_setup("pynnex")
logger = logger_setup(__name__)

@with_signals
class Counter:
    """
    A simple counter class that emits a signal when its count changes.
    """

    def __init__(self):
        self.count = 0

    @signal
    def count_changed(self):
        """Signal emitted when count changes"""

    def increment(self):
        """Increment counter and emit signal"""

        self.count += 1
        print(f"Counter incremented to: {self.count}")
        self.count_changed.emit(self.count)


@with_signals
class AsyncDisplay:
    """
    A simple display class that receives count updates and processes them asynchronously.
    """

    def __init__(self):
        self.last_value = None

    @slot
    async def on_count_changed(self, value):
        """Async slot that receives count updates"""
        logger.debug("[DataDisplay] Processing count: %d", value)
        # Simulate some async processing
        await asyncio.sleep(1)
        self.last_value = value
        logger.debug("[DataDisplay] Finished processing: %d", value)


async def main():
    """
    Main function to run the async counter example.
    """

    # Create instances
    counter = Counter()
    display = AsyncDisplay()

    # Connect signal to async slot
    counter.count_changed.connect(display, display.on_count_changed)

    print("Starting async counter example...")
    print("Press Enter to increment counter, or 'q' to quit")
    print("(Notice the 1 second delay in processing)")

    while True:
        # Get input asynchronously
        line = await asyncio.get_event_loop().run_in_executor(None, input, "> ")

        if line.lower() == "q":
            break

        # Increment counter which will emit signal
        counter.increment()

        # Give some time for async processing to complete
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    asyncio.run(main())
