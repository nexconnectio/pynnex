# Usage Guide

## Requirements
Pynnex requires Python 3.10 or higher.

## Table of Contents
1. [Basic Concepts](#basic-concepts)
2. [Signals](#signals)
3. [Slots](#slots)
4. [Properties (nx_property)](#properties-nx_property)
5. [Connection Types](#connection-types)
6. [Threading and Async](#threading-and-async)
7. [Best Practices](#best-practices)
8. [Worker Thread Pattern](#worker-thread-pattern)

## Basic Concepts
Pynnex implements a signal-slot pattern, allowing loose coupling between components. Core ideas:

- **Signal**: An event source that can be emitted.
- **Slot**: A function/method that responds to a signal.
- **Connection**: A link binding signals to slots.

## Signals

### Defining Signals
Use `@nx_with_signals` on a class and `@nx_signal` on a method to define a signal:
```python
from pynnex import nx_with_signals, nx_signal

@nx_with_signals
class Button:
    @nx_signal
    def clicked(self):
        """Emitted when the button is clicked."""
        pass

    def click(self):
        self.clicked.emit()
```
## Emitting Signals
Emit signals using `.emit()`:
```python
self.clicked.emit()  # No args
self.data_ready.emit(value, timestamp)  # With args
```

## Slots
### Defining Slots
Use `@nx_slot` to mark a method as a slot:
```python
@nx_slot
def on_clicked(self):
    print("Button clicked")
```

## Async Slots
Slots can be async, integrating seamlessly with asyncio:
```python
@nx_with_signals
class DataProcessor:
    @nx_slot
    async def on_data_ready(self, data):
        # Perform async operations
        await asyncio.sleep(1)
        print("Data processed:", data)
```
## Properties (nx_property)
nx_property provides thread-safe, event-loop-aware properties that can emit signals on change:

```python
from pynnex.contrib.extensions.property import nx_property

@nx_with_signals
class Model:
    @nx_signal
    def value_changed(self):
        pass

    @nx_property(notify=value_changed)
    def value(self):
        return self._value

    @value.setter
    def value(self, new_val):
        self._value = new_val
```
- Accessing or modifying value from another thread is safely queued to the owner's event loop.
- If notify is set, the specified signal is emitted when the property changes.

## Connection Types
### AUTO_CONNECTION
By default, when you connect() a signal to a slot, AUTO_CONNECTION is used. It automatically chooses:

- Direct Connection if signal and slot share the same thread and slot is synchronous.
- Queued Connection if crossing threads or slot is async, queuing the call in the slot's event loop.

### Forcing Connection Type
You can force a specific connection type using the `connection_type` parameter:
```python
self.clicked.connect(on_clicked, connection_type=DIRECT_CONNECTION)
```

Request for o1 pro mode
Finished thinking
md
Copy code
# Usage Guide

## Requirements
Pynnex requires Python 3.10 or higher.

## Table of Contents
1. [Basic Concepts](#basic-concepts)
2. [Signals](#signals)
3. [Slots](#slots)
4. [Properties (nx_property)](#properties-nx_property)
5. [Connection Types](#connection-types)
6. [Threading and Async](#threading-and-async)
7. [Best Practices](#best-practices)
8. [Worker Thread Pattern](#worker-thread-pattern)

## Basic Concepts
Pynnex implements a signal-slot pattern, allowing loose coupling between components. Core ideas:

- **Signal**: An event source that can be emitted.
- **Slot**: A function/method that responds to a signal.
- **Connection**: A link binding signals to slots.

## Signals

### Defining Signals
Use `@nx_with_signals` on a class and `@nx_signal` on a method to define a signal:
```python
from pynnex import nx_with_signals, nx_signal

@nx_with_signals
class Button:
    @nx_signal
    def clicked(self):
        """Emitted when the button is clicked."""
        pass

    def click(self):
        self.clicked.emit()
```    
## Emitting Signals
Emit signals using `.emit()`:
```python
self.clicked.emit()  # No args
self.data_ready.emit(value, timestamp)  # With args
```
## Slots
**Defining Slots**

Use `@nx_slot` to mark a method as a slot:

```python
from pynnex import nx_slot

@nx_with_signals
class Display:
    @nx_slot
    def on_clicked(self):
        print("Button was clicked!")
```

## Async Slots
Slots can be async, integrating seamlessly with asyncio:

```python
@nx_with_signals
class DataProcessor:
    @nx_slot
    async def on_data_ready(self, data):
        # Perform async operations
        await asyncio.sleep(1)
        print("Data processed:", data)
```

## Properties (nx_property)
`nx_property` provides thread-safe, event-loop-aware properties that can emit signals on change:

```python
from pynnex.contrib.extensions.property import nx_property

@nx_with_signals
class Model:
    @nx_signal
    def value_changed(self):
        pass

    @nx_property(notify=value_changed)
    def value(self):
        return self._value

    @value.setter
    def value(self, new_val):
        self._value = new_val
```        
- Accessing or modifying `value` from another thread is safely queued to the owner's event loop.
- If `notify` is set, the specified signal is emitted when the property changes.

## Connection Types
**AUTO_CONNECTION**

By default, when you `connect()` a signal to a slot, `AUTO_CONNECTION` is used. It automatically chooses:

- **Direct Connection** if signal and slot share the same thread and slot is synchronous.
- **Queued Connection** if crossing threads or slot is async, queuing the call in the slot's event loop.

## Forcing Connection Type
```python
from pynnex.core import NxConnectionType

signal.connect(receiver, receiver.on_slot, connection_type=NxConnectionType.DIRECT_CONNECTION)
signal.connect(receiver, receiver.on_slot, connection_type=NxConnectionType.QUEUED_CONNECTION)
```

## Threading and Async
**Thread Safety**

Pynnex ensures thread-safe signal emissions. Signals can be emitted from any thread. Slots execute in their designated event loop (often the thread they were created in).

**Async Integration**

Pynnex works with asyncio event loops:

```python
async def main():
    # Create objects and connect signals/slots
    # Emit signals and await async slot completions indirectly
    await asyncio.sleep(1)

asyncio.run(main())
```
## Best Practices
1. **Naming Conventions:**
   - Signals: value_changed, data_ready, operation_completed
   - Slots: on_value_changed, on_data_ready
2. **Disconnect Unused Signals:**
   Before destroying objects or changing system states, disconnect signals to prevent unwanted slot executions.
3. **Error Handling in Slots:**
   Handle exceptions in slots to prevent crashes:

```python
@nx_slot
def on_data_received(self, data):
    try:
        self.process_data(data)
    except Exception as e:
        logger.error(f"Error processing: {e}")
```

4. **Resource Cleanup:** Disconnect signals before cleanup or shutdown to ensure no pending queued calls to cleaned-up resources.

## Worker Thread Pattern
The `@nx_with_worker` decorator creates an object with its own thread and event loop, enabling you to queue async tasks and offload work:

**Basic Worker**
```python
from pynnex import nx_with_worker, nx_signal

@nx_with_worker
class BackgroundWorker:
    @nx_signal
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

## Putting It All Together
Pynnex allows you to:

- Define signals and slots easily.
- Connect them across threads and async contexts without manual synchronization.
- Use worker threads for background tasks with seamless signal/slot integration.
- Manage properties thread-safely with `nx_property`.

This ensures a clean, maintainable, and scalable architecture for event-driven Python applications.
