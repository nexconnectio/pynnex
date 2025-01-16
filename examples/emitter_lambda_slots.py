# examples/emitter_lambda_listeners.py

"""
Emitter-Lambda Listeners Example

This example demonstrates connecting an emitter to a lambda function listener.
It shows that you can quickly define inline, anonymous listeners for simple tasks.

Steps:
1. Define an emitter in a class (Counter) that emits when its count changes.
2. Connect the emitter to a lambda function that prints the received value.
3. Increment the counter and observe the lambda being called.

Key Points:
- Demonstrates that listeners can be lambdas (anonymous functions).
- Useful for quick, inline actions without defining a separate function or method.
"""

import asyncio
from pynnex.core import with_emitters, emitter
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
        print(f"[Counter] incremented to: {self.count}")
        self.count_changed.emit(self.count)


async def main():
    """Main function to run the emitter-lambda listeners example."""

    counter = Counter()
    # Connect the emitter to a lambda listener
    counter.count_changed.connect(lambda v: print(f"Lambda Listener received: {v}"))

    print("Press Enter to increment counter, or 'q' to quit.")

    while True:
        line = input("> ")

        if line.lower() == "q":
            break
        counter.increment()


if __name__ == "__main__":
    asyncio.run(main())
