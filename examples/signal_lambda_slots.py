# examples/signal_lambda_slots.py

"""
Signal-Lambda Slots Example

This example demonstrates connecting a signal to a lambda function slot.
It shows that you can quickly define inline, anonymous slots for simple tasks.

Steps:
1. Define a signal in a class (Counter) that emits when its count changes.
2. Connect the signal to a lambda function that prints the received value.
3. Increment the counter and observe the lambda being called.

Key Points:
- Demonstrates that slots can be lambdas (anonymous functions).
- Useful for quick, inline actions without defining a separate function or method.
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
        print(f"[Counter] incremented to: {self.count}")
        self.count_changed.emit(self.count)


async def main():
    """Main function to run the signal-lambda slots example."""

    counter = Counter()
    # Connect the signal to a lambda slot
    counter.count_changed.connect(lambda v: print(f"Lambda Slot received: {v}"))

    print("Press Enter to increment counter, or 'q' to quit.")

    while True:
        line = input("> ")

        if line.lower() == "q":
            break
        counter.increment()


if __name__ == "__main__":
    asyncio.run(main())
