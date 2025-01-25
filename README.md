<!-- README.md -->

[![PyPI Version](https://img.shields.io/pypi/v/pynnex.svg)](https://pypi.org/project/pynnex/)
[![License](https://img.shields.io/github/license/nexconnectio/pynnex.svg)](https://github.com/nexconnectio/pynnex/blob/main/LICENSE)
[![Build Status](https://img.shields.io/github/actions/workflow/status/nexconnectio/pynnex/tests.yml?branch=main)](https://github.com/nexconnectio/pynnex/actions)
[![Downloads](https://img.shields.io/pypi/dm/pynnex)](https://pypi.org/project/pynnex/)

# PynneX

**Looking for a lightweight alternative to heavier event-driven, signal-slot, or concurrency libraries in Python?**  
PynneX is a pure-Python (asyncio-based) library that streamlines event-driven concurrency without forcing you to adopt large frameworks or external dependencies.

---

## Why PynneX?

Modern Python applications often combine async I/O and multithreading. Many existing event libraries or frameworks can bring in extra dependencies or complexities, especially if you only need clean, concurrency-focused event handling. PynneX offers a **focused** approach:

- **Decorator-based emitters and listeners** for writing succinct, event-driven code  
- **Built-in thread safety**—no need to manually handle locks or queues  
- **Easy background tasks** via `@nx_with_worker` decorator  
- **Asyncio integration**: either async or sync listeners work seamlessly  
- **No external dependencies** beyond Python 3.10+ (for improved asyncio support) 

**PynneX** can also serve as a **lightweight** alternative to more complex concurrency or distributed event frameworks, letting you scale from simple local threads up to multi-threaded or async scenarios without overhead.

---

## Key Features

- **Pure Python**: No external dependencies needed
- **Event Decorators**: `@nx_emitter` and `@nx_listener` for intuitive event-based design
- **Multiple Aliases Available**: Prefer different terminology?
  - Use `@nx_signal` and `@nx_slot` if you like Qt-style signal-slots
  - Use `@nx_publisher` and `@nx_subscriber` if you’re coming from a Pub/Sub background
  - All aliases share the same underlying mechanics
  - Use `@emitter`, `@listener`, `@signal`, `@slot`, `@publisher`, `@subscriber` interchangeably without prefix `nx_`
- **Thread-Safe**: Automatic cross-thread invocation ensures concurrency safety
- **asyncio-Friendly**: Support for both synchronous and asynchronous listeners
- **Background Workers**: `@nx_with_worker` provides a dedicated event loop in a separate thread
- **Weak Reference**: If you connect a listener with `weak=True`, the connection is removed automatically once the receiver is garbage-collected

### **Requires an Existing Event Loop**

PynneX depends on Python’s `asyncio`. You **must** have a running event loop (e.g., `asyncio.run(...)`) for certain features like async listeners or cross-thread calls.  
If no event loop is running, PynneX raises a `RuntimeError` instead of creating one behind the scenes—this ensures predictable concurrency behavior.

## Installation

```bash
pip install pynnex
```

PynneX requires **Python 3.10+**, leveraging newer asyncio improvements.
Alternatively, clone from GitHub and install locally: 

```bash
git clone https://github.com/nexconnectio/pynnex.git
cd pynnex
pip install -e .
```

For development (includes tests and linting tools):
```
pip install -e ".[dev]"
```

## Quick Hello (Emitters/Listeners)

Here’s the simplest “Hello, Emitters/Listeners” example. Once installed, run the snippet below:

```python
# hello_pynnex.py
import asyncio
from pynnex import with_emitters, emitter, listener


@with_emitters
class Greeter:
    @emitter
    def greet(self):
        """Emitter emitted when greeting happens."""

    def say_hello(self):
        self.greet.emit("Hello from PynneX!")


@with_emitters
class Printer:
    @listener
    def on_greet(self, message):
        print(message)


async def main():
    # The following code needs to be inside async main() as it requires a running event loop
    greeter = Greeter()
    printer = Printer()

    # Connect the emitter to the listener
    greeter.greet.connect(printer, printer.on_greet)

    # Fire the emitter
    greeter.say_hello()


if __name__ == "__main__":
    asyncio.run(main())
```

**Output:**
```
Hello from PynneX!
```

By simply defining `emitter` and `listener`, you can set up intuitive event handling that also works smoothly in multithreaded contexts.

If you come from a Qt background or prefer “signal-slot” naming, use:

```python
import asyncio
from pynnex import with_signals, signal, slot


@with_signals
class Greeter:
    @signal
    def greet(self):
        """Emitter emitted when greeting happens."""

    def say_hello(self):
        self.greet.emit("Hello from PynneX!")


@with_signals
class Printer:
    @slot
    def on_greet(self, message):
        print(message)


async def main():
    # The following code needs to be inside async main() as it requires a running event loop
    greeter = Greeter()
    printer = Printer()

    # Connect the emitter to the listener
    greeter.greet.connect(printer, printer.on_greet)

    # Fire the emitter
    greeter.say_hello()


if __name__ == "__main__":
    asyncio.run(main())
```

If you prefer a Pub/Sub style, use:

```python
import asyncio
from pynnex import with_publishers, publisher, subscriber


@with_publishers
class Greeter:
    @publisher
    def greet(self):
        """Emitter emitted when greeting happens."""

    def say_hello(self):
        self.greet.publish("Hello from PynneX!")


@with_publishers
class Printer:
    @subscriber
    def on_greet(self, message):
        print(message)


async def main():
    # The following code needs to be inside async main() as it requires a running event loop
    greeter = Greeter()
    printer = Printer()

    # Connect the emitter to the listener
    greeter.greet.connect(printer, printer.on_greet)

    # Fire the emitter
    greeter.say_hello()


if __name__ == "__main__":
    asyncio.run(main())
```

They’re all interchangeable aliases pointing to the same core functionality.

---

## Usage & Examples

Below are some brief examples. For more, see the [docs/](https://github.com/nexconnectio/pynnex/blob/main/docs/) directory.

### Asynchronous Listener Example
```python
import asyncio
from pynnex import with_emitters, emitter, listener


@with_emitters
class Counter:
    def __init__(self):
        self.count = 0

    @emitter
    def count_changed(self):
        pass

    def increment(self):
        self.count += 1
        self.count_changed.emit(self.count)


@with_emitters
class Display:
    @listener
    async def on_count_changed(self, value):
        print(f"Count is now: {value}")


async def main():
    # Connect and use
    counter = Counter()
    display = Display()
    counter.count_changed.connect(display, display.on_count_changed)
    counter.increment()  # Will print: "Count is now: 1"

    # Wait a bit to allow async listener to execute
    await asyncio.sleep(0.1)


if __name__ == "__main__":
    asyncio.run(main())

```

## Core Concepts

### Emitters and Listeners
- Emitters: Declared with `@nx_emitter`. Emitters are attributes of a class that can be emitted to notify interested parties.
- Listeners: Declared with `@nx_listener`. Listeners are methods that respond to emitters. Listeners can be synchronous or async functions.
- Connections: Use `emitter.connect(receiver, listener)` to link emitters to listeners. Connections can also be made directly to functions or lambdas.

### Thread Safety and Connection Types
PynneX automatically detects whether the emitter emission and listener execution occur in the same thread or different threads:

- **Auto Connection**: When connection_type is AUTO_CONNECTION (default), PynneX checks whether the listener is a coroutine function or whether the caller and callee share the same thread affinity. If they are the same thread and listener is synchronous, it uses direct connection. Otherwise, it uses queued connection.
- **Direct Connection**: If emitter and listener share the same thread affinity, the listener is invoked directly.
- **Queued Connection**: If they differ, the call is queued to the listener’s thread/event loop, ensuring thread safety.

This mechanism frees you from manually dispatching calls across threads.

### Thread-Safe Properties
The `@nx_property` decorator provides thread-safe property access with automatic emitter emission:

```python
import asyncio
from pynnex import with_emitters, emitter, nx_property


@with_emitters
class Example:
    def __init__(self):
        super().__init__()
        self._data = None

    @emitter
    def updated(self):
        """Emitter emitted when data changes."""

    @nx_property(notify=updated)
    def data(self):
        """Thread-safe property with change notification."""
        return self._data

    @data.setter
    def data(self, value):
        self._data = value
        print(f"Data set to: {value}")


async def main():
    example = Example()
    example.data = 42  # Thread-safe property set; emits 'updated' emitter on change
    await asyncio.sleep(0.1)


if __name__ == "__main__":
    asyncio.run(main())
```

### Worker Threads
For background work, PynneX provides a `@nx_with_worker` decorator that:

- Spawns a dedicated event loop in a worker thread.
- Allows you to queue async tasks to this worker.
- Enables easy start/stop lifecycle management.
- Integrates with emitters and listeners for thread-safe updates to the main 

**Worker Example**
```python
import asyncio
from pynnex import with_worker, emitter, listener


@with_worker
class DataProcessor:
    def __init__(self):
        self.started.connect(self.on_started)
        self.processing_done.connect(self.on_processing_done)
        self.result = None

    @emitter
    def processing_done(self):
        """Emitted when processing completes"""

    @listener
    async def on_started(self, *args, **kwargs):
        """Called when worker starts"""
        print("Worker started, processing data...")
        await self.process_data(42)

    @listener
    def on_processing_done(self, result):
        """Called when processing completes"""
        self.result = result
        print(f"Processing complete! Result: {result}")

    async def process_data(self, data):
        """Perform heavy computation in the worker thread"""
        await asyncio.sleep(2)  # Simulate heavy computation
        result = data * 2
        self.processing_done.emit(result)


async def main():
    # Create and start the processor
    processor = DataProcessor()
    processor.start()

    # Wait for processing to complete
    await asyncio.sleep(3)

    # Stop the worker gracefully
    processor.stop()

    # Verify the result
    assert processor.result == 84, f"Expected 84, got {processor.result}"
    print("Worker example completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
```

## Documentation and Example
- [Usage Guide](https://github.com/nexconnectio/pynnex/blob/main/docs/usage.md): Learn how to define emitters/listeners, manage threads, and structure your event-driven code.
- [API Reference](https://github.com/nexconnectio/pynnex/blob/main/docs/api.md): Detailed documentation of classes, decorators, and functions.
- [Examples](https://github.com/nexconnectio/pynnex/blob/main/docs/examples.md): Practical use cases, including UI integration, async operations, and worker pattern usage.
- [Logging Guidelines](https://github.com/nexconnectio/pynnex/blob/main/docs/logging.md): Configure logging levels and handlers for debugging.
- [Testing Guide](https://github.com/nexconnectio/pynnex/blob/main/docs/testing.md): earn how to run tests and contribute safely.

## Logging
Configure logging to diagnose issues:

```python
import logging
logging.getLogger('pynnex').setLevel(logging.DEBUG)
```

For more details, see the [Logging Guidelines](https://github.com/nexconnectio/pynnex/blob/main/docs/logging.md).

## Testing

PynneX uses `pytest` for testing:

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_emitter.py
```

See the [Testing Guide](https://github.com/nexconnectio/pynnex/blob/main/docs/testing.md) for more details.

## Contributing
We welcome contributions! Please read our [Contributing Guidelines](https://github.com/nexconnectio/pynnex/blob/main/CONTRIBUTING.md) before submitting PRs.

## Sponsorship & Donations
If PynneX has helped simplify your async/multithreaded workflows, please consider [sponsoring us](https://github.com/nexconnectio/pynnex/blob/main/.github/FUNDING.yml). All funds go toward infrastructure, documentation, and future development.

Please note that financial contributions support only the project's maintenance and do not grant financial rewards to individual contributors.

## License
`PynneX` is licensed under the MIT License. See [LICENSE](https://github.com/nexconnectio/pynnex/blob/main/LICENSE) for details.
