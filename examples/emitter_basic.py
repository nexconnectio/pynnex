# examples/emitter_basic.py

"""
Basic Emitter-Listener Example

This example demonstrates the fundamental usage of PynneX with a synchronous listener:
1. Creating an emitter
2. Connecting a regular method as a listener (without @nx_listener)
3. Emitting an emitter to trigger listener execution

Key Points:
- Showcases the most basic form of emitter-listener connection.
- The listener is a normal instance method of a class, not decorated with @nx_listener.
- Emphasizes that even without @nx_listener, a callable method can act as a listener.
- Introduces the concept of emitter emission and immediate listener execution.
"""

import asyncio
import time
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
        logger.debug("[Counter] Incremented to: %d", self.count)
        self.count_changed.emit(self.count)


@with_emitters
class Display:
    """
    A simple display class that receives count updates and processes them.
    """

    def __init__(self):
        self.last_value = None

    def on_count_changed(self, value):
        """listener that receives count updates"""
        print(f"[Display] Processing count: {value}")
        # Simulate some heavy processing
        time.sleep(1)
        self.last_value = value
        print(f"[Display] Finished processing: {value}")


async def main():
    """
    Main function to run the async counter example.
    """

    # Create instances
    counter = Counter()
    display = Display()

    # Connect emitter to listener
    counter.count_changed.connect(display.on_count_changed)

    print("[main] Starting counter example...")
    print("[main] Press Enter to increment counter, or 'q' to quit")
    print("[main] (Notice the 1 second delay in processing)")

    while True:
        line = input("> (q to quit)")

        if line.lower() == "q":
            break

        # Increment counter which will emit emitter
        counter.increment()


if __name__ == "__main__":
    asyncio.run(main())
