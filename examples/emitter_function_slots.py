# examples/emitter_function_listeners.py

"""
Emitter-Function Listeners Example

This example demonstrates how to connect an emitter to a standalone function 
(not a class method). This highlights that listeners can be any callable, not just methods.

Steps:
1. Define an emitter in a class (Counter) that emits when its count changes.
2. Define a standalone function that processes the emitted value.
3. Connect the emitter to this standalone function as a listener.
4. Emit the emitter by incrementing the counter and observe the function being called.

Key Points:
- Illustrates flexibility in choosing listeners.
- Standalone functions can serve as listeners without additional decorators.
"""

import asyncio
from pynnex import with_emitters, emitter
from utils import logger_setup

logger_setup("pynnex")
logger = logger_setup(__name__)


@with_emitters
class Counter:
    """A simple counter class that emits an emitter when its count changes."""

    def __init__(self):
        self.count = 0

    @emitter
    def count_changed(self):
        """Emitted when the count changes."""

    def increment(self):
        """Increment the counter and emit the emitter."""

        self.count += 1
        print(f"[Counter] Incremented to: {self.count}")
        self.count_changed.emit(self.count)


def print_value(value):
    """A standalone function acting as a listener."""

    print(f"[print_value] Received value: {value}")


async def main():
    """Main function to run the emitter-function listeners example."""

    counter = Counter()
    # Connect the emitter to the standalone function listener
    counter.count_changed.connect(print_value)

    print("Press Enter to increment counter, or 'q' to quit.")

    while True:
        line = input("> (q to quit)")

        if line.lower() == "q":
            break
        counter.increment()


if __name__ == "__main__":
    asyncio.run(main())
