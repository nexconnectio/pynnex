<!-- docs/api.md -->

# API Reference

## Requirements

PynneX requires **Python 3.10** or higher, plus a running `asyncio` event loop for any async usage.

## Decorators

For convenience, core decorators (`@nx_with_emitters`, `@nx_emitter`, `@nx_listener`, `@nx_with_worker`) are also available without the `nx_` prefix.

You can use either form:
```python
from pynnex import nx_with_emitters, with_emitters  # both work
from pynnex import nx_emitter, emitter             # both work
from pynnex import nx_listener, listener           # both work
from pynnex import nx_with_worker, worker          # both work

# Qt-style
from pynnex import with_signals, signal, slot

# Pub/Sub style
from pynnex import with_publishers, publisher, subscriber
```

Note that `@nx_property` does not have a prefix-free alias to avoid conflicts with Python's built-in `@property` decorator.

### `@nx_with_emitters`

Aliases:
- `@with_emitters`
- `@with_signals`
- `@with_publishers`

Enables emitter-listener functionality on a class. Classes decorated with `@nx_with_emitters` can define emitters and have their listeners automatically assigned event loops and thread affinity.

**Important**: `@nx_with_emitters` expects that you already have an `asyncio` event loop running (e.g., via `asyncio.run(...)`) unless you only rely on synchronous listeners in a single-thread scenario. When in doubt, wrap your main logic in an async function and call `asyncio.run(main())`.

**Key Methods**:

```python
move_to_thread(target_worker)
```
Moves the instance to another thread by copying thread affinity from a worker. This allows dynamic thread reassignment of emitter-listener objects.

- **Parameters:**
  - **target_worker:** A worker instance decorated with `@nx_with_worker`. The instance will adopt this worker's thread affinity.
- **Raises:**
  - **RuntimeError:** If the target worker's thread is not started.
  - **TypeError:** If the target is not compatible (not decorated with `@nx_with_worker`).

**Usage:**

```python
@nx_with_worker
class Worker:
    async def run(self):
        await self.wait_for_stop()

@nx_with_emitters
class Emitter:
    @nx_emitter
    def value_changed(self):
        pass

worker = Worker()
worker.start()

emitter = Emitter()
emitter.move_to_thread(worker)  # Now emitter runs in worker's thread
```

### `@nx_emitter`

Aliases:
- Qt alias: `@signal`
- Pub/Sub alias: `@publisher`

Defines an emitter within a class that has `@nx_with_emitters`. Emitters are callable attributes that, when emitted, notify all connected listeners.

**Key Methods**:

`emit(*args, **kwargs)`
Emits the emitter, invoking all connected listeners with the provided arguments.

- **Parameters:**
  - ***args:** Positional arguments to pass to the connected listeners.
  - ****kwargs:** Keyword arguments to pass to the connected listeners.

**Usage:**

```python
@nx_emitter
def my_emitter(self):
    pass

# Emission
self.my_emitter.emit(value)
```

### `@nx_listener`

Aliases:
- Qt alias: `@slot`
- Pub/Sub alias: `@subscriber`

Marks a method as a listener. Listeners can be synchronous or asynchronous methods. PynneX automatically handles cross-thread invocation—**but only if there is a running event loop**.  

**Usage:**

```python
@nx_listener
def on_my_emitter(self, value):
    print("Received:", value)

@nx_listener
async def on_async_emitter(self, value):
    await asyncio.sleep(1)
    print("Async Received:", value)
```

**Event Loop Requirement**:
If the decorated listener is async, or if the listener might be called from another thread, PynneX uses asyncio scheduling. That means a running event loop is mandatory. If no loop is found, a RuntimeError is raised.

### `@nx_with_worker`(aliases: `@with_worker`)

Decorates a class to run inside a dedicated worker thread with its own event loop. Ideal for offloading tasks without blocking the main thread. When using @nx_with_worker, the worker thread automatically sets up its own event loop, so calls within that worker are safe. For the main thread, you still need an existing loop if you plan on using async listeners or cross-thread emitters. The worker provides:

- A dedicated event loop in another thread.
- A built-in async task queue via `queue_task`.
- Thread-safe state management (CREATED, STARTING, STARTED, STOPPING, STOPPED)
- Built-in signals (started, stopped)

**Key Methods**:

`start(*args, **kwargs)`

Starts the worker thread and its event loop.

- **Parameters:**
  - ***args:** Positional arguments passed to the worker's `run()` method.
  - ****kwargs:** Keyword arguments passed to the worker's `run()` method.

- **Raises:**
  - **RuntimeError:** If worker is not in CREATED state.

`stop(wait: bool = True, timeout: float = None) -> bool`

Stops the worker thread and its event loop gracefully. Cancels any running tasks and waits for the thread to finish.

- **Parameters:**
  - **wait:** If True, waits for the thread to finish.
  - **timeout:** Maximum time to wait for thread completion.

- **Raises:**
  - **RuntimeError:** If worker is not in STARTING or STARTED state.

**Example:**

```python
worker.start()
worker.stop()
```

`queue_task(maybe_coro) -> asyncio.Future`

Schedules a coroutine to run on the worker's event loop.

- **Parameters:**
  - **maybe_coro:** A coroutine, coroutine function, or callable.

- **Returns:**
  - **asyncio.Future:** A Future that completes when the task is done.

- **Raises:**
  - **RuntimeError:** If the worker is not started.
  - **TypeError:** If argument is not a valid task type.

**Example:**

```python
@nx_with_worker
class Worker:
    @nx_emitter
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

Creates a thread-safe property that can optionally notify an emitter when the property’s value changes. Useful for ensuring that property access and mutation occur on the object's designated event loop, maintaining thread safety.

**Key Points:**

- `nx_property` can be used similarly to `property`, but wraps get/set operations in event loop calls if accessed from another thread.
- If the `notify` parameter is set to an emitter, that emitter is emitted whenever the property value changes.
- Get and set operations from the "wrong" thread are automatically queued to the object's event loop, ensuring thread-safe access.

**Usage:**

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

model = Model()
model.value = 10  # If called from a different thread, queued to model's loop
print(model.value) # Also thread-safe
```

## Classes
### `NxEmitter`

Represents an emitter. Emitters are created by `@nx_emitter` and accessed as class attributes.

**Key Methods**:

`connect(receiver_or_listener, listener=None, connection_type=NxConnectionType.AUTO_CONNECTION) -> None`

Connects the emitter to a listener.

- **Parameters:**
  - **receiver_or_listener:** Either the receiver object and listener method, or just a callable (function/lambda) if listener is None.
  - **listener:** The method in the receiver if a receiver object is provided.
  - **connection_type:** DIRECT_CONNECTION, QUEUED_CONNECTION, or AUTO_CONNECTION.
    - **AUTO_CONNECTION (default):** Determines connection type automatically based on thread affinity and listener type.
  - **weak:** If `True`, the receiver is kept via a weak reference so it can be garbage collected once there are no strong references. The emitter automatically removes the connection if the receiver is collected.
  - **one_shot:** If `True`, the connection is automatically disconnected after the first successful emit call. This is useful for events that should only notify a listener once.

**Examples:**

```python
# AUTO_CONNECTION (default) decides connection type automatically
emitter.connect(receiver, receiver.on_emitter)

# Force direct connection
emitter.connect(receiver, receiver.on_emitter, connection_type=NxConnectionType.DIRECT_CONNECTION)

# Force queued connection
emitter.connect(receiver, receiver.on_emitter, connection_type=NxConnectionType.QUEUED_CONNECTION)

# Connect to a standalone function
emitter.connect(print)
```

`disconnect(receiver=None, listener=None) -> int`

Disconnects a previously connected listener. Returns the number of disconnected connections.

- **Parameters:**
  - receiver: The object whose listener is connected. If receiver is None, all receivers are considered.
  - listener: The specific listener to disconnect from the emitter. If listener is None, all listeners for the given receiver (or all connections if receiver is also None) are disconnected.
- **Returns:** The number of connections that were disconnected.- 

**Examples:**
```python
# Disconnect all connections
emitter.disconnect()

# Disconnect all listeners from a specific receiver
emitter.disconnect(receiver=my_receiver)

# Disconnect a specific listener from a specific receiver
emitter.disconnect(receiver=my_receiver, listener=my_receiver.some_listener)

# Disconnect a standalone function
emitter.disconnect(listener=my_function)
```

`emit(*args, **kwargs) -> None`

Emits the emitter, invoking all connected listeners either directly or via the event loop of the listener’s associated thread, depending on the connection type. If a connection is marked one_shot, it is automatically removed right after invocation.

`NxConnectionType`

Defines how a listener is invoked relative to the emitter’s thread.

- `DIRECT_CONNECTION`: The listener is called immediately in the emitter's thread.
- `QUEUED_CONNECTION`: The listener invocation is queued in the listener's thread/event loop.
- `AUTO_CONNECTION`: Automatically chooses direct or queued based on thread affinity and listener type (sync/async).

## Asynchronous Support

Listeners can be async. When an emitter with an async listener is emitted:
- The listener runs on the event loop associated with that listener.
- `AUTO_CONNECTION` typically results in queued connections for async listeners.
- `emit()` returns immediately; listeners run asynchronously without blocking the caller.

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

- `TypeError`: If listener is not callable or signature issues occur.
- `RuntimeError`: If no event loop is available for async operations.
- `AttributeError`: If connecting to a nonexistent listener or missing receiver.

## Examples

**Basic Emitter-Listener**

```python
@nx_with_emitters
class Sender:
    @nx_emitter
    def value_changed(self):
        pass

@nx_with_emitters
class Receiver:
    @nx_listener
    def on_value_changed(self, value):
        print("Value:", value)

sender = Sender()
receiver = Receiver()
sender.value_changed.connect(receiver, receiver.on_value_changed)
sender.value_changed.emit(100)
```

**Async Listener**

```python
@nx_with_emitters
class AsyncReceiver:
    @nx_listener
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
    @nx_emitter
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

model = Model()
model.value = 42  # If called from another thread, it's queued safely
```