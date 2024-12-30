# examples/signal_function_slots.py

"""
Signal-Function Slots Example

This example demonstrates how to connect a signal to a standalone function 
(not a class method). This highlights that slots can be any callable, not just methods.

Steps:
1. Define a signal in a class (Counter) that emits when its count changes.
2. Define a standalone function that processes the emitted value.
3. Connect the signal to this standalone function as a slot.
4. Emit the signal by incrementing the counter and observe the function being called.

Key Points:
- Illustrates flexibility in choosing slots.
- Standalone functions can serve as slots without additional decorators.
"""

import asyncio
from pynnex.core import with_signals, signal
from utils import logger_setup

logger_setup("pynnex")
logger = logger_setup(__name__)

@with_signals
class Counter:
    """A simple counter class that emits a signal when its count changes."""

    def __init__(self):
        self.count = 0

    @signal
    def count_changed(self):
        """Emitted when the count changes."""

    def increment(self):
        """Increment the counter and emit the signal."""

        self.count += 1
        logger.debug("[Counter] Incremented to: %d", self.count)
        self.count_changed.emit(self.count)


def print_value(value):
    """A standalone function acting as a slot."""

    logger.debug("[print_value] Received value: %d", value)


async def main():
    """Main function to run the signal-function slots example."""

    counter = Counter()
    # Connect the signal to the standalone function slot
    counter.count_changed.connect(print_value)

    print("Press Enter to increment counter, or 'q' to quit.")

    while True:
        line = input("> ")

        if line.lower() == "q":
            break
        counter.increment()


if __name__ == "__main__":
    asyncio.run(main())
