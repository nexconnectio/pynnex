# Pynnex

```bash
# New package installation:
pip install pynnex
```

Pynnex is a lightweight, pure-Python signal/slot library that provides thread-safe, asyncio-compatible event handling. It enables clean decoupling of components, seamless thread-to-thread communication, and flexible asynchronous/synchronous slot handling.

## Key Features

- **Pure Python**: No external dependencies needed.
- **Async/Await Friendly**: Slots can be synchronous or asynchronous, and integrate seamlessly with asyncio.
- **Thread-Safe**: Signal emissions and slot executions are automatically managed for thread safety.
- **Flexible Connection Types**: Direct or queued connections, automatically chosen based on the caller and callee threads.
- **Worker Thread Pattern**: Simplify background task execution with a built-in worker pattern that provides an event loop and task queue in a dedicated thread.
- **Familiar Decorators**: Simple decorators let you define signals and slots declaratively. Core decorators (`@nx_with_signals`, `@nx_signal`, `@nx_slot`, `@nx_with_worker`) are also available without the `nx_` prefix for convenience.
- **Thread-Safe Properties**: The `@nx_property` decorator provides thread-safe property access with automatic signal emission on changes.
- **Weak Reference**: 
  - By setting `weak=True` when connecting a slot, the library holds a weak reference to the receiver object. This allows the receiver to be garbage-collected if there are no other strong references to it. Once garbage-collected, the connection is automatically removed, preventing stale references.

### **Requires an Existing Event Loop**

Since Pynnex relies on Python’s `asyncio` infrastructure for scheduling async slots and cross-thread calls, you **must** have a running event loop before using Pynnex’s decorators like `@nx_with_signals` or `@nx_slot`. Typically, this means:

1. **Inside `asyncio.run(...)`:**  
   For example:
   ```python
   async def main():
       # create objects, do your logic
       ...
   asyncio.run(main())
   ```

2. **@nx_with_worker Decorator:**
   If you decorate a class with `@nx_with_worker`, it automatically creates a worker thread with its own event loop. That pattern is isolated to the worker context, so any other async usage in the main thread also needs its own loop.

If no event loop is running when a slot is called, Pynnex will raise a RuntimeError instead of creating a new loop behind the scenes. This ensures consistent concurrency behavior and avoids hidden loops that might never process tasks.

## Why Pynnex?

Modern Python applications often rely on asynchronous operations and multi-threading. Traditional event frameworks either require large external dependencies or lack seamless async/thread support. Pynnex provides:

- A minimal, dependency-free solution for event-driven architectures.
- Smooth integration with asyncio for modern async Python code.
- Automatic thread-affinity handling so cross-thread signals "just work."
- Decorator-based API that’s intuitive and maintainable.

## Installation

Pynnex requires Python 3.10 or higher. This requirement ensures stable asyncio operations, as Python 3.10 introduced important improvements including:

- Enhanced asyncio task cancellation and exception handling
- More reliable coroutine execution and cleanup mechanisms

```bash
git clone https://github.com/nexconnectio/pynnex.git
cd pynnex
pip install -e .
```

For development (includes tests and linting tools):
```
pip install -e ".[dev]
```

## Quick Start

### Basic Example
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
Pynnex automatically detects whether the signal emission and slot execution occur in the same thread or different threads:

- **Auto Connection**: When connection_type is AUTO_CONNECTION (default), Pynnex checks whether the slot is a coroutine function or whether the caller and callee share the same thread affinity. If they are the same thread and slot is synchronous, it uses direct connection. Otherwise, it uses queued connection.
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
For background work, Pynnex provides a `@nx_with_worker` decorator that:

- Spawns a dedicated event loop in a worker thread.
- Allows you to queue async tasks to this worker.
- Enables easy start/stop lifecycle management.
- Integrates with signals and slots for thread-safe updates to the main 

**Worker Example**
```python
from pynnex import nx_with_worker, nx_signal

@nx_with_worker
class DataProcessor:
    @nx_signal
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
Any donations or sponsorships received will be used solely for project maintenance and improvement, such as:
- Infrastructure costs (hosting, CI/CD, etc.)
- Documentation and testing improvements
- Project development and maintenance

Please note that financial contributions support only the project's maintenance and do not grant financial rewards to individual contributors.

## License
Pynnex is licensed under the MIT License. See [LICENSE](https://github.com/nexconnectio/pynnex/blob/main/LICENSE) for details.
