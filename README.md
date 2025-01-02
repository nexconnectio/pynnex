<!-- README.md -->

[![PyPI Version](https://img.shields.io/pypi/v/pynnex.svg)](https://pypi.org/project/pynnex/)
[![License](https://img.shields.io/github/license/nexconnectio/pynnex.svg)](https://github.com/nexconnectio/pynnex/blob/main/LICENSE)
[![Build Status](https://img.shields.io/github/actions/workflow/status/nexconnectio/pynnex/tests.yml?branch=main)](https://github.com/nexconnectio/pynnex/actions)
[![Downloads](https://img.shields.io/pypi/dm/pynnex)](https://pypi.org/project/pynnex/)

# PynneX

**Looking for a lightweight alternative to heavy Signals/Slots libraries in an asynchronous and multi-threaded environment?**  
PynneX is a pure-Python (asyncio-based) library that streamlines event-driven concurrency without the overhead of larger GUI frameworks or external dependencies.

---

## Why PynneX?

Modern Python applications often blend async I/O and multithreading. Typical Signals/Slots solutions from GUI toolkits or external libraries can impose extra dependencies, especially when you only need concurrency handling rather than full UI features.

PynneX offers a **focused** approach:
- Decorator-based signals and slots for clean, event-driven code
- Built-in **thread-safety**, so you don’t manually deal with locks or queues
- Easy background task handling via `@nx_with_worker`
- Seamless integration with **asyncio** (async or sync slots)
- No external dependencies beyond Python 3.10+ (for improved asyncio support)

As a result, events flow safely across threads and coroutines without “callback spaghetti,” giving you a cleaner concurrency model in pure Python.

---

## Key Features

- **Pure Python**: No external dependencies needed  
- **Async/Await Friendly**: Slots can be synchronous or asynchronous, integrating naturally with `asyncio`  
- **Thread-Safe**: Automatically manages signal emissions and slot executions across thread boundaries  
- **Flexible Connection Types**: Direct or queued connections, chosen based on whether caller/callee share the same thread  
- **Worker Thread Pattern**: Decorator `@nx_with_worker` provides a dedicated thread & event loop, simplifying background tasks  
- **Familiar Decorators**: `@nx_signal`, `@nx_slot`, `@nx_with_worker`; also available without `nx_` prefix  
- **Thread-Safe Properties**: Use `@nx_property` to emit signals on value changes, with automatic thread dispatch  
- **Weak Reference**: If you connect a slot with `weak=True`, the connection is removed automatically once the receiver is garbage-collected

### **Requires an Existing Event Loop**

PynneX depends on Python’s `asyncio`. You **must** have a running event loop (e.g., `asyncio.run(...)`) for certain features like async slots or cross-thread calls.  
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
pip install -e ".[dev]
```

## Quick Hello (Signals/Slots)

Here’s the simplest “Hello, Signals/Slots” example. Once installed, run the snippet below:

```python
# hello_pynnex.py
from pynnex import with_signals, signal, slot

@with_signals
class Greeter:
    @signal
    def greet(self):
        """Signal emitted when greeting happens."""
        pass

    def say_hello(self):
        self.greet.emit("Hello from PynneX!")

@with_signals
class Printer:
    @slot
    def on_greet(self, message):
        print(message)

greeter = Greeter()
printer = Printer()

# Connect the signal to the slot
greeter.greet.connect(printer, printer.on_greet)

# Fire the signal
greeter.say_hello()
```

**Output:**
```
Hello from PynneX!
```

By simply defining `signal` and `slot`, you can set up intuitive event handling that also works smoothly in multithreaded contexts.

---

## Usage & Examples

Below are some brief examples. For more, see the [docs/](https://github.com/nexconnectio/pynnex/blob/main/docs/) directory.

### Basic Counter & Display
```python
from pynnex import with_signals, signal, slot

@with_signals
class Counter:
    def __init__(self):
        self.count = 0
    
    @signal
    def count_changed(self):
        pass
    
    def increment(self):
        self.count += 1
        self.count_changed.emit(self.count)

@with_signals
class Display:
    @slot
    async def on_count_changed(self, value):
        print(f"Count is now: {value}")

# Connect and use
counter = Counter()
display = Display()
counter.count_changed.connect(display, display.on_count_changed)
counter.increment()  # Will print: "Count is now: 1"
```

### Asynchronous Slot Example
```python
@with_signals
class AsyncDisplay:
    @slot
    async def on_count_changed(self, value):
        await asyncio.sleep(1)  # Simulate async operation
        print(f"Count updated to: {value}")

# Usage in async context
async def main():
    counter = Counter()
    display = AsyncDisplay()
    
    counter.count_changed.connect(display, display.on_count_changed)
    counter.increment()
    
    # Wait for async processing
    await asyncio.sleep(1.1)

asyncio.run(main())
```

## Core Concepts

### Signals and Slots
- Signals: Declared with `@nx_signal`. Signals are attributes of a class that can be emitted to notify interested parties.
- Slots: Declared with `@nx_slot`. Slots are methods that respond to signals. Slots can be synchronous or async functions.
- Connections: Use `signal.connect(receiver, slot)` to link signals to slots. Connections can also be made directly to functions or lambdas.

### Thread Safety and Connection Types
PynneX automatically detects whether the signal emission and slot execution occur in the same thread or different threads:

- **Auto Connection**: When connection_type is AUTO_CONNECTION (default), PynneX checks whether the slot is a coroutine function or whether the caller and callee share the same thread affinity. If they are the same thread and slot is synchronous, it uses direct connection. Otherwise, it uses queued connection.
- **Direct Connection**: If signal and slot share the same thread affinity, the slot is invoked directly.
- **Queued Connection**: If they differ, the call is queued to the slot’s thread/event loop, ensuring thread safety.

This mechanism frees you from manually dispatching calls across threads.

### Thread-Safe Properties
The `@nx_property` decorator provides thread-safe property access with automatic signal emission:

```python
@with_signals
class Example:
    def __init__(self):
        super().__init__()
        self._data = None
    
    @signal
    def updated(self):
        """Signal emitted when data changes."""
        pass
    
    @nx_property(notify=updated)
    def data(self):
        """Thread-safe property with change notification."""
        return self._data
    
    @data.setter
    def data(self, value):
        self._data = value

e = Example()
e.data = 42  # Thread-safe property set; emits 'updated' signal on change
```

### Worker Threads
For background work, PynneX provides a `@nx_with_worker` decorator that:

- Spawns a dedicated event loop in a worker thread.
- Allows you to queue async tasks to this worker.
- Enables easy start/stop lifecycle management.
- Integrates with signals and slots for thread-safe updates to the main 

**Worker Example**
```python
from pynnex import nx_with_worker, nx_signal

@with_worker
class DataProcessor:
    @signal
    def processing_done(self):
        """Emitted when processing completes"""

    async def run(self, *args, **kwargs):
        # The main entry point for the worker thread’s event loop
        # Wait for tasks or stopping signal
        await self.wait_for_stop()

    async def process_data(self, data):
        # Perform heavy computation in the worker thread
        result = await heavy_computation(data)
        self.processing_done.emit(result)

processor = DataProcessor()
processor.start()

# Queue a task to run in the worker thread:
processor.queue_task(processor.process_data(some_data))

# Stop the worker gracefully
processor.stop()
```

## Documentation and Example
- [Usage Guide](https://github.com/nexconnectio/pynnex/blob/main/docs/usage.md): Learn how to define signals/slots, manage threads, and structure your event-driven code.
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

Pynnex uses `pytest` for testing:

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_signal.py
```

See the [Testing Guide](https://github.com/nexconnectio/pynnex/blob/main/docs/testing.md) for more details.

## Contributing
We welcome contributions! Please read our [Contributing Guidelines](https://github.com/nexconnectio/pynnex/blob/main/CONTRIBUTING.md) before submitting PRs.

## Sponsorship & Donations
If PynneX has helped simplify your async/multithreaded workflows, please consider [sponsoring us](https://github.com/nexconnectio/pynnex/blob/main/.github/FUNDING.yml). All funds go toward infrastructure, documentation, and future development.

Please note that financial contributions support only the project's maintenance and do not grant financial rewards to individual contributors.

## License
`PynneX` is licensed under the MIT License. See [LICENSE](https://github.com/nexconnectio/pynnex/blob/main/LICENSE) for details.
