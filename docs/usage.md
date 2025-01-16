<!-- docs/usage.md -->

# Usage Guide

## Requirements

PynneX requires **Python 3.10** or higher, plus a running `asyncio` event loop for any async usage. 

# Table of Contents

- [Usage Guide](#usage-guide)
  - [Requirements](#requirements)
- [Table of Contents](#table-of-contents)
  - [**Requires an Existing Event Loop**](#requires-an-existing-event-loop)
  - [**Basic Concepts**](#basic-concepts)
  - [**Emitters**](#emitters)
    - [**Defining Emitters**](#defining-emitters)
    - [**Emitting Emitters**](#emitting-emitters)
  - [Listeners](#listeners)
    - [Defining Listeners](#defining-listeners)
  - [**Listeners**](#listeners-1)
    - [**Defining Listeners**](#defining-listeners-1)
    - [**Async Listeners**](#async-listeners)
  - [**Properties (nx\_property)**](#properties-nx_property)
  - [**Connection Types**](#connection-types)
    - [**AUTO\_CONNECTION**](#auto_connection)
    - [**Forcing Connection Type**](#forcing-connection-type)
  - [**Threading and Async**](#threading-and-async)
  - [Best Practices](#best-practices)
  - [**Worker Thread Pattern**](#worker-thread-pattern)
  - [**Putting It All Together**](#putting-it-all-together)

## **Requires an Existing Event Loop**

PynneX depends on Python’s `asyncio`. You **must** have a running event loop (e.g., via `asyncio.run(...)`) for certain features like async listeners or cross-thread calls. If there’s no existing loop, PynneX raises a `RuntimeError` instead of silently creating one, ensuring concurrency remains predictable. Typically, you’ll handle it in one of two ways:

1. **Inside asyncio.run(...):**  
   For example:
   
```python
   async def main():
       # Create objects, connect emitters/listeners
       # Perform your logic
       ...
   asyncio.run(main()) # Launches the event loop and runs 'main'
```

2. `@nx_with_worker` **Decorator:**(aliases: `@with_worker`)

When you decorate a class with `@nx_with_worker`, PynneX automatically creates a dedicated worker thread with its own event loop. This worker loop is isolated to that thread, so any async usage in the main thread still requires its own loop or `asyncio.run(...)`. You can queue tasks into the worker without manually configuring additional event loops.

## **Basic Concepts**

PynneX implements an emitter-listener pattern, allowing loose coupling between components. Core ideas:

- **Emitter**: An event source that can be emitted.
- **Listener**: A function/method that responds to an emitter.
- **Connection**: A link binding emitters to listeners.

## **Emitters**

### **Defining Emitters**

Use `@nx_with_emitters` on a class and `@nx_emitter` on a method to define an emitter:

aliases for `@nx_with_emitters`:
- `@with_emitters`
- `@with_signals`
- `@with_publishers`

aliases for `@nx_emitter`:
- `@emitter`
- `@signal`
- `@publisher`

```python
from pynnex import nx_with_emitters, nx_emitter

@nx_with_emitters
class Button:
    @nx_emitter
    def clicked(self):
        """Emitted when the button is clicked."""
        pass

    def click(self):
        self.clicked.emit()
```

### **Emitting Emitters**

Emit emitters using `.emit()`:

```python
self.clicked.emit()  # No args
self.data_ready.emit(value, timestamp)  # With args
```

## Listeners
### Defining Listeners

Use `@nx_listener` to mark a method as a listener:
```python
@nx_listener
def on_clicked(self):
    print("Button clicked")
```

---
## **Listeners**
### **Defining Listeners**

Use `@nx_listener` to mark a method as a listener:

```python
from pynnex import nx_listener

@nx_with_emitters
class Display:
    @nx_listener
    def on_clicked(self):
        print("Button was clicked!")
```

### **Async Listeners**

Listeners can be async, integrating seamlessly with `asyncio`:

```python
@nx_with_emitters
class DataProcessor:
    @nx_listener
    async def on_data_ready(self, data):
        # Perform async operations
        await asyncio.sleep(1)
        print("Data processed:", data)
```

---
## **Properties (nx_property)**

`nx_property` provides thread-safe, event-loop-aware properties that can emit emitters on change:

```python
from pynnex.contrib.extensions.property import nx_property

@nx_with_emitters
class Model:
    @nx_emitter
    def value_changed(self):
        pass

    @nx_property(notify=value_changed)
    def value(self):
        return self._value

    @value.setter
    def value(self, new_val):
        self._value = new_val
```
- Accessing or modifying `value` from another thread is **safely queued** to the owner's event loop.
- If `notify` is set, the specified emitter is emitted when the property changes.

---
## **Connection Types**
### **AUTO_CONNECTION**

By default, when you `connect()` an emitter to a listener, `AUTO_CONNECTION` is used. It automatically chooses:

- **Direct Connection** if emitter and listener share the same thread and listener is synchronous.
- **Queued Connection** if crossing threads or listener is async, queuing the call in the listener's event loop.

### **Forcing Connection Type**

You can force a specific connection type using the `connection_type` parameter:

```python
from pynnex.core import NxConnectionType

# Force a direct connection
emitter.connect(receiver, receiver.on_listener, connection_type=NxConnectionType.DIRECT_CONNECTION)

# Force a queued connection
emitter.connect(receiver, receiver.on_listener, connection_type=NxConnectionType.QUEUED_CONNECTION)

```
---
## **Threading and Async**

**Thread Safety**

PynneX ensures thread-safe emitter emissions. Emitters can be emitted from any thread. Listeners execute in their designated event loop (often the thread they were created in).

**Async Integration**

Most PynneX features integrate with Python’s `asyncio`. Typically you’ll have an `async def main():` function that sets up your objects and emitters, then call `asyncio.run(main())` to start the loop. If you use `@nx_with_worker`, that worker thread and event loop is automatically managed.

```python
async def main():
    # Create objects and connect emitters/listeners
    # Emit emitters and await async listener completions indirectly
    await asyncio.sleep(1)

asyncio.run(main())
```

## Best Practices

1. **Naming Conventions:**
   - Emitters: value_changed, data_ready, operation_completed
   - Listeners: on_value_changed, on_data_ready
2. **Disconnect Unused Emitters:**
   Before destroying objects or changing system states, disconnect emitters to prevent unwanted listener executions.
3. **Error Handling in Listeners:**
   Handle exceptions in listeners to prevent crashes:

```python
@nx_listener
def on_data_received(self, data):
    try:
        self.process_data(data)
    except Exception as e:
        logger.error(f"Error processing: {e}")
```

4. **Resource Cleanup:** Disconnect emitters before cleanup or shutdown to ensure no pending queued calls to cleaned-up resources.

---
## **Worker Thread Pattern**

The `@nx_with_worker` decorator creates an object with its own thread and event loop, enabling you to queue async tasks and offload work:

**Basic Worker**

```python
from pynnex import nx_with_worker, nx_emitter

@nx_with_worker
class BackgroundWorker:
    @nx_emitter
    def work_done(self):
        pass

    async def run(self, *args, **kwargs):
        # The main entry point in the worker thread.
        # Wait until stopped
        await self.wait_for_stop()

    async def heavy_task(self, data):
        await asyncio.sleep(2)  # Simulate heavy computation
        self.work_done.emit(data * 2)

worker = BackgroundWorker()
worker.start()
worker.queue_task(worker.heavy_task(10))
worker.stop()
```

** Key Points for Workers**
- Define `async def run(self, *args, **kwargs)` as the main loop of the worker.
- Call `start(*args, **kwargs)` to launch the worker with optional arguments passed to `run()`.
- Use `queue_task(coro)` to run async tasks in the worker’s event loop.
- Use `stop()` to request a graceful shutdown, causing `run()` to return after `_nx_stopping` is set.

**Passing Arguments to run()**
If `run()` accepts additional parameters, simply provide them to `start()`:

```python
async def run(self, config=None):
    # Use config here
    await self.wait_for_stop()
```

```python
worker.start(config={'threads':4})
```

---
## **Putting It All Together**

PynneX allows you to:

- Define emitters and listeners easily.
- Connect them across threads and async contexts without manual synchronization.
- Use worker threads for background tasks with seamless emitter/listener integration.
- Manage properties thread-safely with `nx_property`.

This ensures a clean, maintainable, and scalable architecture for event-driven Python applications.
