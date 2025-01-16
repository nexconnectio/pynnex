# examples/emitter_async.py

"""
Async Emitter Example

This example demonstrates the basic usage of PynneX with async listeners:
1. Creating an emitter
2. Connecting an async listener
3. Emitting an emitter to async handler

Key Points:
- Demonstrates asynchronous emitter-listener communication
- Shows how to use @nx_listener decorator with async functions
- Illustrates handling of async listener execution in event loop
- Explains integration of emitters with asyncio for non-blocking operations
"""

import asyncio
from pynnex import with_emitters, emitter, listener
from utils import logger_setup

logger_setup("pynnex")
logger = logger_setup(__name__)


@with_emitters
class Counter:
    """
    A simple counter class that emits an emitter when its count changes.
    """

    def __init__(self):
        self.count = 0

    @emitter
    def count_changed(self):
        """Emitter emitted when count changes"""

    def increment(self):
        """Increment counter and emit emitter"""

        self.count += 1
        print(f"Counter incremented to: {self.count}")
        self.count_changed.emit(self.count)


@with_emitters
class AsyncDisplay:
    """
    A simple display class that receives count updates and processes them asynchronously.
    """

    def __init__(self):
        self.last_value = None

    @listener
    async def on_count_changed(self, value):
        """Async listener that receives count updates"""
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

    # Connect emitter to async listener
    counter.count_changed.connect(display, display.on_count_changed)

    print("Starting async counter example...")
    print("Press Enter to increment counter, or 'q' to quit")
    print("(Notice the 1 second delay in processing)")

    while True:
        # Get input asynchronously
        line = await asyncio.get_event_loop().run_in_executor(None, input, "> ")

        if line.lower() == "q":
            break

        # Increment counter which will emit emitter
        counter.increment()

        # Give some time for async processing to complete
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    asyncio.run(main())
