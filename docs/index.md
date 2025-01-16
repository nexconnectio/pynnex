# PynneX

PynneX is a lightweight, pure-Python **emitter-listener** (signal-slot) library that provides thread-safe, asyncio-compatible event handling. It enables clean decoupling of components, seamless thread-to-thread communication, and flexible asynchronous/synchronous listener handling. If you prefer Qt-style naming, **signal-slot** aliases are also available, as well as **publisher-subscriber** for a Pub/Sub feel.

## Key Features

- **Pure Python**: No external dependencies needed.
- **Async/Await Friendly**: Listeners can be synchronous or asynchronous, integrating naturally with `asyncio`.
- **Thread-Safe**: Emissions and listener executions are automatically managed across threads.
- **Flexible Connection Types**: Direct or queued connections, chosen based on thread context (caller vs. callee).
- **Worker Thread Pattern**: Easily spin up a background event loop with a built-in worker decorator.
- **Familiar Decorators**:
  - Core decorators:
    - `@nx_with_emitters`, `@nx_emitter`, `@nx_listener`, `@nx_with_worker`
    - Also available without `nx_` prefix
  - Qt-style aliases:
    - `@with_signals`, `@signal`, `@slot`
  - Pub/Sub aliases:
    - `@with_publishers`, `@publisher`, `@subscriber`

- **Thread-Safe Properties**: The `@nx_property` decorator offers property access with automatic emitter notification on changes.
- **Weak Reference**:
  - By setting `weak=True` when connecting a listener, the library holds a weak reference to the receiver object. If no other strong reference exists, garbage collection removes both the object and its connection, avoiding stale references.

## Why PynneX?

Modern Python applications often combine asynchronous operations and multithreading. Many event-driven frameworks come with large dependencies or limited async/thread support. PynneX aims to fill the gap by offering:

- A **lightweight**, dependency-free solution for event-driven architectures.
- **Effortless async** workflows via `asyncio` compatibility.
- **Automatic thread affinity** so cross-thread events “just work.”
- **Clear** decorator-based API for easy maintenance.

### Key Benefits

**Async-Ready**
- Built for `asyncio` workflows
- Define async listeners that won’t block the event loop

**Thread-Safe by Design**
- Automatically routes emitter calls to the correct thread or event loop
- No manual locks required

**Flexible Listeners**
- Connect to class methods, standalone functions, or lambdas
- Strong or weak references supported

**Robust Testing & Examples**
- Comprehensive test coverage
- Real-world scenarios including CLI, GUI, and distributed patterns
- Best practices demonstrated throughout

## Installation

PynneX requires **Python 3.10+** for stable `asyncio` operations:

```bash
git clone https://github.com/nexconnectio/pynnex.git
cd pynnex
pip install -e .
```

For development (includes tests and linting tools):

```bash
pip install -e ".[dev]"
```

## Quick Start

### Basic Example

```python
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

# Connect and use
counter = Counter()
display = Display()
counter.count_changed.connect(display, display.on_count_changed)
counter.increment()  # Will print: "Count is now: 1"
```

### Asynchronous Listener Example

```python
@with_emitters
class AsyncDisplay:
    @listener
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

### Emitters and Listeners (Signal/Slot Aliases Available)

- Emitters: Declared with `@emitter`. They’re callable attributes in a class that can emit events to notify interested listeners.
- Listeners: Declared with `@listener`. They’re methods that respond to an emitter’s event. Both sync and async are supported.
- Connections: Use `emitter.connect(receiver, listener)` to wire them up. You can also connect standalone functions or lambdas.

### Thread Safety and Connection Types

PynneX detects whether the emitter call and listener execution happen in the same thread or different ones:

- **Auto Connection**: Default. If both share the same thread and listener is sync, it uses direct connection. Otherwise, it uses a queued connection.
- **Direct Connection**: The listener is called immediately if emitter and listener share the same thread affinity.
- **Queued Connection**: If they differ, the listener call is queued to its thread/event loop, ensuring thread safety.
No manual dispatching needed—PynneX does it behind the scenes.

### Worker Threads

For background work, PynneX provides a `@nx_with_worker`(alias `@with_worker`) decorator that:

- Spawns a dedicated event loop in a worker thread.
- Allows you to queue async tasks to this worker.
- Enables easy start/stop lifecycle management.
- Integrates with signals and slots for thread-safe updates to the main 

** Worker Example **

```python
from pynnex import with_worker, emitter

@with_worker
class DataProcessor:
    @emitter
    def processing_done(self):
        pass

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

## From Basics to Practical Use Cases
We’ve expanded PynneX’s examples to guide you from simple demos to full-fledged applications. Each example has its own GitHub link with fully commented code.

For detailed explanations, code walkthroughs, and architecture diagrams of these examples, check out our [Examples Documentation](https://github.com/nexconnectio/pynnex/blob/main/docs/examples.md).

### Basic Examples

- [emitter_basic.py](https://github.com/nexconnectio/pynnex/blob/main/examples/emitter_basic.py) and [emitter_async.py](https://github.com/nexconnectio/pynnex/blob/main/examples/emitter_async.py)
  - demonstrate how to define simple synchronous and async listeners.

- [emitter_function_slots.py](https://github.com/nexconnectio/pynnex/blob/main/examples/emitter_function_slots.py) and [emitter_lambda_slots.py](https://github.com/nexconnectio/pynnex/blob/main/examples/emitter_lambda_slots.py)
  - show how you can connect emitters to standalone functions and lambdas.

### Multi-Threading and Workers

- [thread_basic.py](https://github.com/nexconnectio/pynnex/blob/main/examples/thread_basic.py) and [thread_worker.py](https://github.com/nexconnectio/pynnex/blob/main/examples/thread_worker.py)
  - walk you through multi-threaded setups, including background tasks and worker loops.
  - You’ll see how signals emitted from a background thread are properly handled in the main event loop or another thread’s loop.

### Real-Time Stock Monitors (Console & GUI)

- [stock_monitor_simple.py](https://github.com/nexconnectio/pynnex/blob/main/examples/stock_monitor_simple.py)
  - A minimal stock monitor that periodically updates a display. Perfect for learning how PynneX can orchestrate real-time updates without blocking.
- [stock_monitor_console.py](https://github.com/nexconnectio/pynnex/blob/main/examples/stock_monitor_console.py)
  - A CLI-based interface that lets you type commands to set alerts, list them, and watch stock data update in real time.  
<div align="center">
  <img src="https://raw.githubusercontent.com/nexconnectio/pynnex/refs/heads/main/docs/images/stock_monitor_console.png" alt="Stock Monitor Console" width="800"/>
  <p><em>Stock Monitor Console: Real-time price updates, alert configuration, and notification history in action</em></p>
</div>
- [stock_monitor_ui.py](https://github.com/nexconnectio/pynnex/blob/main/examples/stock_monitor_ui.py)
  - A more elaborate Kivy-based UI example showcasing real-time stock monitoring. You'll see how PynneX updates the interface instantly without freezing the GUI. This example underscores how PynneX’s thread and event-loop management keeps your UI responsive and your background tasks humming.
<div align="center">
  <img src="https://raw.githubusercontent.com/nexconnectio/pynnex/refs/heads/main/docs/images/stock_monitor_ui.png" alt="Stock Monitor UI" width="800"/>
  <p><em>Stock Monitor UI: Real-time price updates, alert configuration, and notification history in action</em></p>
</div>

## Documentation and Examples

- [Usage Guide](https://github.com/nexconnectio/pynnex/blob/main/docs/usage.md): Learn how to define signals/slots, manage threads, and structure your event-driven code.
- [API Reference](https://github.com/nexconnectio/pynnex/blob/main/docs/api.md): Detailed documentation of classes, decorators, and functions.
- [Examples](https://github.com/nexconnectio/pynnex/blob/main/docs/examples.md): Practical use cases, including UI integration, async operations, and worker pattern usage.
- [Logging Guidelines](https://github.com/nexconnectio/pynnex/blob/main/docs/logging.md): Configure logging levels and handlers for debugging.
- [Testing Guide](https://github.com/nexconnectio/pynnex/blob/main/docs/testing.md): earn how to run tests and contribute safely.

## Get Started

1. **Visit the** [GitHub Repository](https://github.com/nexconnectio/pynnex)
2. **Install via** `pip install pynnex` (**Python 3.10+**)
3. **Explore the** [examples and documentation](https://github.com/nexconnectio/pynnex/blob/main/docs/examples.md) for real-world use cases
4. **Contribute / Feedback:** Check our [Contributing Guidelines](https://github.com/nexconnectio/pynnex/blob/main/CONTRIBUTING.md)
   
## License

PynneX is licensed under the MIT License. See [LICENSE](https://github.com/nexconnectio/pynnex/blob/main/LICENSE) for details.

