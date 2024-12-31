# API Reference

## Requirements
`PynneX` requires Python 3.10 or higher, and a running `asyncio` event loop for any async usage.

## Decorators

For convenience, core decorators (`@nx_with_signals`, `@nx_signal`, `@nx_slot`, `@nx_with_worker`) are also available without the `nx_` prefix. You can use either form:

```python
from pynnex import nx_with_signals, with_signals  # both work
from pynnex import nx_signal, signal              # both work
from pynnex import nx_slot, slot                  # both work
from pynnex import nx_with_worker, worker        # both work
```

Note that `@nx_property` does not have a prefix-free alias to avoid conflicts with Python's built-in `@property` decorator.

### `@nx_with_signals`
Enables signal-slot functionality on a class. Classes decorated with `@nx_with_signals` can define signals and have their slots automatically assigned event loops and thread affinity.

**Important**: `@nx_with_signals` expects that you already have an `asyncio` event loop running (e.g., via `asyncio.run(...)`) unless you only rely on synchronous slots in a single-thread scenario. When in doubt, wrap your main logic in an async function and call `asyncio.run(main())`.

**Usage:**
```python
@nx_with_signals
class MyClass:
    @nx_signal
    def my_signal(self):
        pass
```

### `@nx_signal`
Defines a signal within a class that has `@nx_with_signals`. Signals are callable attributes that, when emitted, notify all connected slots.

**Usage:**

```python
@nx_signal
def my_signal(self):
    pass

# Emission
self.my_signal.emit(value)
```

### `@nx_slot`
Marks a method as a slot. Slots can be synchronous or asynchronous methods. PynneX automatically handles cross-thread invocation—**but only if there is a running event loop**.  

**Usage:**

```python
@nx_slot
def on_my_signal(self, value):
    print("Received:", value)

@nx_slot
async def on_async_signal(self, value):
    await asyncio.sleep(1)
    print("Async Received:", value)
```

**Event Loop Requirement**:
If the decorated slot is async, or if the slot might be called from another thread, PynneX uses asyncio scheduling. That means a running event loop is mandatory. If no loop is found, a RuntimeError is raised.

### `@nx_with_worker`
Decorates a class to run inside a dedicated worker thread with its own event loop. Ideal for offloading tasks without blocking the main thread. When using @nx_with_worker, the worker thread automatically sets up its own event loop, so calls within that worker are safe. For the main thread, you still need an existing loop if you plan on using async slots or cross-thread signals. The worker provides:

- A dedicated event loop in another thread.
- The `run(*args, **kwargs)` coroutine as the main entry point.
- A built-in async task queue via `queue_task`.

**Key Points:**

`run(*args, **kwargs)` is an async method that you can define to perform long-running operations or await a stopping event.
To pass arguments to start(), ensure run() accepts *args, **kwargs.

**Example:**

```python
@nx_with_worker
class Worker:
    @nx_signal
    def finished(self):
        pass

    async def run(self, config=None):
        # run is the main entry point in the worker thread
        print("Worker started with config:", config)
        # Wait until stop is requested
        await self.wait_for_stop()
        self.finished.emit()

    async def do_work(self, data):
        await asyncio.sleep(1)
        return data * 2

worker = Worker()
worker.start(config={'threads': 4})
worker.queue_task(worker.do_work(42))
worker.stop()
```

### `nx_property`
Creates a thread-safe property that can optionally notify a signal when the property’s value changes. Useful for ensuring that property access and mutation occur on the object's designated event loop, maintaining thread safety.

**Key Points:**

- `nx_property` can be used similarly to `property`, but wraps get/set operations in event loop calls if accessed from another thread.
- If the `notify` parameter is set to a signal, that signal is emitted whenever the property value changes.
- Get and set operations from the "wrong" thread are automatically queued to the object's event loop, ensuring thread-safe access.

**Usage:**
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

model = Model()
model.value = 10  # If called from a different thread, queued to model's loop
print(model.value) # Also thread-safe
```

## Classes
### `PynneX`
Represents a signal. Signals are created by `@nx_signal` and accessed as class attributes.

**Key Methods**:

`connect(receiver_or_slot, slot=None, connection_type=NxConnectionType.AUTO_CONNECTION) -> None`

Connects the signal to a slot.

- **Parameters:**
  - **receiver_or_slot:** Either the receiver object and slot method, or just a callable (function/lambda) if slot is None.
  - **slot:** The method in the receiver if a receiver object is provided.
  - **connection_type:** DIRECT_CONNECTION, QUEUED_CONNECTION, or AUTO_CONNECTION.
    - **AUTO_CONNECTION (default):** Determines connection type automatically based on thread affinity and slot type.
  - **weak:** If `True`, the receiver is kept via a weak reference so it can be garbage collected once there are no strong references. The signal automatically removes the connection if the receiver is collected.
  - **one_shot:** If `True`, the connection is automatically disconnected after the first successful emit call. This is useful for events that should only notify a slot once.

**Examples:**

```python
# AUTO_CONNECTION (default) decides connection type automatically
signal.connect(receiver, receiver.on_signal)

# Force direct connection
signal.connect(receiver, receiver.on_signal, connection_type=NxConnectionType.DIRECT_CONNECTION)

# Force queued connection
signal.connect(receiver, receiver.on_signal, connection_type=NxConnectionType.QUEUED_CONNECTION)

# Connect to a standalone function
signal.connect(print)
```

`disconnect(receiver=None, slot=None) -> int`

Disconnects a previously connected slot. Returns the number of disconnected connections.

- **Parameters:**
  - receiver: The object whose slot is connected. If receiver is None, all receivers are considered.
  - slot: The specific slot to disconnect from the signal. If slot is None, all slots for the given receiver (or all connections if receiver is also None) are disconnected.
- **Returns:** The number of connections that were disconnected.- 

**Examples:**
```python
# Disconnect all connections
signal.disconnect()

# Disconnect all slots from a specific receiver
signal.disconnect(receiver=my_receiver)

# Disconnect a specific slot from a specific receiver
signal.disconnect(receiver=my_receiver, slot=my_receiver.some_slot)

# Disconnect a standalone function
signal.disconnect(slot=my_function)
```

`emit(*args, **kwargs) -> None`

Emits the signal, invoking all connected slots either directly or via the event loop of the slot’s associated thread, depending on the connection type. If a connection is marked one_shot, it is automatically removed right after invocation.

`NxConnectionType`

Defines how a slot is invoked relative to the signal emitter’s thread.

- `DIRECT_CONNECTION`: The slot is called immediately in the emitter's thread.
- `QUEUED_CONNECTION`: The slot invocation is queued in the slot's thread/event loop.
- `AUTO_CONNECTION`: Automatically chooses direct or queued based on thread affinity and slot type (sync/async).

## Asynchronous Support
Slots can be async. When a signal with an async slot is emitted:
- The slot runs on the event loop associated with that slot.
- `AUTO_CONNECTION` typically results in queued connections for async slots.
- `emit()` returns immediately; slots run asynchronously without blocking the caller.

## Worker Threads
- `@nx_with_worker` provides a dedicated thread and event loop.
- `run(*args, **kwargs)` defines the worker’s main logic.
- `queue_task(coro)` schedules coroutines on the worker's event loop.
- `stop()` requests a graceful shutdown, causing `run()` to end after `_pynnex_stopping` is triggered.
- `wait_for_stop()` is a coroutine that waits for the worker to stop.

**Signature Match for** ``run()``:

- Use `async def run(self, *args, **kwargs):`.
- Passing parameters to `start()` must align with `run()`’s signature.

## Error Handling
- `TypeError`: If slot is not callable or signature issues occur.
- `RuntimeError`: If no event loop is available for async operations.
- `AttributeError`: If connecting to a nonexistent slot or missing receiver.

## Examples
**Basic Signal-Slot**

```python
@nx_with_signals
class Sender:
    @nx_signal
    def value_changed(self):
        pass

@nx_with_signals
class Receiver:
    @nx_slot
    def on_value_changed(self, value):
        print("Value:", value)

sender = Sender()
receiver = Receiver()
sender.value_changed.connect(receiver, receiver.on_value_changed)
sender.value_changed.emit(100)
```

**Async Slot**

```python
@nx_with_signals
class AsyncReceiver:
    @nx_slot
    async def on_value_changed(self, value):
        await asyncio.sleep(1)
        print("Async Value:", value)

sender = Sender()
async_receiver = AsyncReceiver()
sender.value_changed.connect(async_receiver, async_receiver.on_value_changed)
sender.value_changed.emit(42)
# "Async Value: 42" printed after ~1 
```

**Worker Pattern**

```python
@nx_with_worker
class BackgroundWorker:
    @nx_signal
    def task_done(self):
        pass

    async def run(self):
        # Just wait until stopped
        await self.wait_for_stop()

    async def heavy_task(self, data):
        await asyncio.sleep(2)  # Simulate heavy computation
        self.task_done.emit(data * 2)

worker = BackgroundWorker()
worker.start()
worker.queue_task(worker.heavy_task(10))
worker.stop()
```

**Thread-Safe Property with Notification**

```python
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

model = Model()
model.value = 42  # If called from another thread, it's queued safely
```

