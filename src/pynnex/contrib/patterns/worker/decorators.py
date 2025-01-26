# src/pynnex/contrib/patterns/worker/decorators.py

# pylint: disable=not-callable

"""
Decorator for the worker pattern.

This decorator enhances a class with worker thread functionality, providing:
- A dedicated thread with its own event loop
- Thread-safe task queue with pre-loop buffering
- State machine (CREATED -> STARTING -> STARTED -> STOPPING -> STOPPED)
- Built-in signals (started, stopped)
"""

# pylint: disable=too-many-instance-attributes

import asyncio
from collections import deque
from enum import Enum, auto
import functools
import inspect
import logging
import threading
from pynnex.core import nx_emitter, NxEmitterConstants, NxEmitterObserver

logger_worker = logging.getLogger("pynnex.worker")


def log_worker_operation(func):
    """
    Decorator for logging worker operations.

    Logs the start and completion/failure of worker operations at DEBUG level.
    Thread-safe and handles both sync and async functions.
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if logger_worker.isEnabledFor(logging.DEBUG):
            logger_worker.debug("[Worker:%s] Starting %s", id(self), func.__name__)

        try:
            result = func(self, *args, **kwargs)

            if logger_worker.isEnabledFor(logging.DEBUG):
                logger_worker.debug("[Worker:%s] Completed %s", id(self), func.__name__)

            return result
        except Exception as e:
            logger_worker.exception(
                "[Worker:%s] Failed %s: %s", id(self), func.__name__, e
            )
            raise

    return wrapper


class NxWorkerConstants:
    """Constants for the worker pattern."""

    STOPPED_DONE_FUT = "_nx_stopped_done_fut"


class TaskWrapper:
    """
    Task wrapper for the worker's task queue.

    Wraps a coroutine with a Future for result handling and
    provides thread-safe completion notification.
    """

    def __init__(self, coro):
        self.coro = coro
        self.future = asyncio.Future()
        self.loop = asyncio.get_running_loop()


class WorkerState(Enum):
    """
    Worker state machine states.

    Flow: CREATED -> STARTING -> STARTED -> STOPPING -> STOPPED
    """

    CREATED = auto()
    STARTING = auto()
    STARTED = auto()
    STOPPING = auto()
    STOPPED = auto()


def nx_with_worker(cls):
    """
    Class decorator that adds worker thread functionality.

    Enhances a class with:
    - Dedicated thread with event loop
    - Thread-safe task queue
    - State machine management
    - Started/stopped signals
    - Task queueing capability

    The decorated class will have:
    - start(*args, **kwargs): Starts the worker thread
    - stop(wait=True, timeout=None): Stops the worker thread
    - queue_task(coro): Queues a task to run in the worker thread
    - started: Signal emitted when worker starts
    - stopped: Signal emitted when worker stops

    See Also
    --------
    nx_with_emitters : Base decorator for emitter/listener features
    nx_emitter : Emitter decorator
    nx_listener : Listener decorator
    """

    class WorkerClass(cls):
        """
        Worker class with pre-loop buffering, thread creation, and main loop coroutine handling.
        """

        def __init__(self):
            self.state = WorkerState.CREATED
            self._nx_loop = None
            self._nx_thread = None

            self._nx_preloop_buffer = deque()
            self._nx_lock = threading.RLock()

            self._nx_task_queue = None
            self._nx_main_loop_coro = None
            self._nx_main_loop_task = None
            self._nx_stopped_done_fut = None

            self._nx_affinity = object()
            super().__init__()

        @nx_emitter
        def started(self, *args, **kwargs):
            """Emitter emitted when the worker starts"""

        @nx_emitter
        def stopped(self):
            """Emitter emitted when the worker stops"""

        @log_worker_operation
        def start(self, *args, **kwargs):
            """
            Starts the worker thread and its event loop.

            Parameters
            ----------
            *args : Any
                Positional arguments passed to run().
            **kwargs : Any
                Keyword arguments passed to run().
                run_coro: Optional coroutine to run instead of run().

            Notes
            -----
            - Creates new thread with its own event loop
            - Starts task queue if no run() method defined
            - Emits 'started' emitter when initialized
            """

            def _worker_thread_main():
                loop = asyncio.new_event_loop()
                self._nx_loop = loop
                asyncio.set_event_loop(loop)

                async def _runner():
                    """
                    Prepare event loop:
                    1) Create _task_queue
                    2) Flush pre-loop buffer -> _task_queue
                    3) Register main_loop_coro
                    4) Register started signal task
                    5) Set state=STARTED -> loop.run_forever()
                    """

                    async def _flush_preloop_buffer():
                        """pre-loop buffer -> _task_queue"""

                        with self._nx_lock:
                            while self._nx_preloop_buffer:
                                coro = self._nx_preloop_buffer.popleft()
                                await self._nx_task_queue.put(coro)

                    self._nx_task_queue = asyncio.Queue()

                    await _flush_preloop_buffer()

                    self.started.emit(*args, **kwargs)

                    # Register main_loop_coro as the first task
                    self._nx_main_loop_task = asyncio.create_task(
                        self._nx_main_loop_coro
                    )

                    with self._nx_lock:
                        self.state = WorkerState.STARTED

                # Register necessary initial tasks
                loop.create_task(_runner())

                try:
                    loop.run_forever()
                except KeyboardInterrupt:
                    pass
                finally:
                    loop.close()
                    with self._nx_lock:
                        self._nx_loop = None
                        self.state = WorkerState.STOPPED

            try:
                with self._nx_lock:
                    if self.state != WorkerState.CREATED:
                        raise RuntimeError(
                            f"Worker can only be started once in CREATED state. Current state={self.state}"
                        )
                    self.state = WorkerState.STARTING
                    self._nx_main_loop_coro = self._default_main_loop()
                    self._nx_thread = threading.Thread(
                        target=_worker_thread_main, daemon=True
                    )
                    self._nx_thread.start()
            except Exception as e:
                logger_worker.error("Worker start failed: %s", str(e))
                raise

        @log_worker_operation
        async def _default_main_loop(self):
            """
            Process the task queue: sequentially processes coroutines from self._task_queue
            Exits when state is STOPPING/STOPPED
            """
            try:
                while self.state not in (WorkerState.STOPPING, WorkerState.STOPPED):
                    task_wrapper = await self._nx_task_queue.get()

                    if task_wrapper is None:
                        self._nx_task_queue.task_done()
                        break

                    result = None

                    try:
                        result = await task_wrapper.coro

                        if not task_wrapper.future.done():
                            task_wrapper.loop.call_soon_threadsafe(
                                lambda tw=task_wrapper, res=result: tw.future.set_result(
                                    res
                                )
                            )

                    except asyncio.CancelledError:
                        # In case of cancellation during task execution, cancel the corresponding future
                        if task_wrapper.future:

                            def cancel_future(tw=task_wrapper):
                                tw.future.cancel()

                            task_wrapper.loop.call_soon_threadsafe(cancel_future)

                        # Re-raise to cancel the main loop
                        raise

                    except Exception as e:
                        logger_worker.exception(
                            "Error while awaiting the task_wrapper.coro (type=%s): %s",
                            type(task_wrapper.coro),
                            e,
                        )

                        # In case of exception, set the future.set_exception
                        if task_wrapper.future:
                            task_wrapper.loop.call_soon_threadsafe(
                                lambda ex=e: task_wrapper.future.set_exception(ex)
                            )

                    finally:
                        self._nx_task_queue.task_done()

            except asyncio.CancelledError:
                logger_worker.debug("Main loop got CancelledError, stopping...")
                raise

            finally:
                # Cancel any remaining task_wrapper in the queue after the loop finishes
                while not self._nx_task_queue.empty():
                    tw = self._nx_task_queue.get_nowait()

                    if tw is not None and tw.future and not tw.future.done():
                        tw.loop.call_soon_threadsafe(
                            lambda: tw.future.set_exception(asyncio.CancelledError())
                        )
                    self._nx_task_queue.task_done()

                logger_worker.debug("Default main loop finished.")

        @log_worker_operation
        def queue_task(self, maybe_coro) -> asyncio.Future:
            """
            Schedules a coroutine to run on the worker's event loop.

            Parameters
            ----------
            maybe_coro : coroutine function or callable or coroutine
                Something that results in a coroutine when fully processed.

            Raises
            ------
            RuntimeError
                If worker is not started.
            TypeError
                If argument is neither coroutine, coroutine function, nor callable.

            Notes
            -----
            - Thread-safe: Can be called from any thread
            - Tasks are processed in FIFO order
            - Failed tasks are logged but don't stop queue
            """

            # if maybe_coro is a coroutine function -> call it immediately to make it a coroutine object
            if inspect.iscoroutinefunction(maybe_coro):
                maybe_coro = maybe_coro()

            # Yet not a coroutine object
            elif not asyncio.iscoroutine(maybe_coro):
                # check if maybe_coro is a callable (sync function)
                if callable(maybe_coro):
                    original_func = maybe_coro

                    async def wrapper():
                        val = original_func()  # Perform sync function (or lambda)

                        # If this sync function returns a coroutine object, await it
                        if asyncio.iscoroutine(val):
                            return await val
                        return val

                    # Now maybe_coro is a 'wrapper' coroutine object
                    maybe_coro = wrapper()
                else:
                    raise TypeError(
                        "Task must be a coroutine, coroutine function, or sync function"
                    )

            # Now maybe_coro is a coroutine object
            with self._nx_lock:
                if self.state == WorkerState.CREATED:
                    raise RuntimeError("Worker must be started before queueing tasks")
                if self.state == WorkerState.STARTING:
                    # Not ready yet -> buffer tasks before loop starts
                    task_wrapper = TaskWrapper(maybe_coro)
                    self._nx_preloop_buffer.append(task_wrapper)
                elif self.state == WorkerState.STARTED:
                    # Put immediately into _task_queue
                    task_wrapper = TaskWrapper(maybe_coro)
                    self._nx_loop.call_soon_threadsafe(
                        lambda: self._nx_task_queue.put_nowait(task_wrapper)
                    )
                else:
                    # STOPPING or STOPPED
                    raise RuntimeError(f"Cannot queue task in state={self.state}")

            return task_wrapper.future

        @log_worker_operation
        def stop(self, wait: bool = True, timeout: float = None) -> bool:
            """
            Gracefully stops the worker thread and its event loop.

            Notes
            -----
            - Cancels any running tasks including main run() coroutine
            - Waits for task queue to finish processing
            - Emits 'stopped' emitter before final cleanup
            """

            if self._nx_thread is None or not self._nx_thread.is_alive():
                raise RuntimeError("Worker is not started")

            if self._nx_loop is None or not self._nx_loop.is_running():
                raise RuntimeError("Worker is not running")

            with self._nx_lock:
                if self.state not in (WorkerState.STARTING, WorkerState.STARTED):
                    raise RuntimeError(
                        f"Cannot stop worker in state={self.state}. Must be STARTING or STARTED."
                    )

                self.state = WorkerState.STOPPING

                if self._nx_loop and self._nx_loop.is_running():

                    async def _stop_loop():
                        # Cancel main loop coroutine
                        self._nx_main_loop_task.cancel()

                        # Wait for cancellation
                        try:
                            await self._nx_main_loop_task
                        except asyncio.CancelledError:
                            pass

                        self._nx_stopped_done_fut = self._nx_loop.create_future()

                        observer = NxEmitterObserver()
                        self.stopped.emit(observer=observer)

                        if observer.call_attempts == 0:
                            self._nx_stopped_done_fut.set_result(True)

                        if wait:
                            try:
                                await asyncio.wait_for(
                                    self._nx_stopped_done_fut, timeout=timeout
                                )
                                self._nx_stopped_done_fut = None
                            except asyncio.TimeoutError:
                                logger_worker.warning(
                                    "on_stopped did not finish within 5s. Forcing stop..."
                                )

                        self._nx_loop.stop()

            self._nx_loop.call_soon_threadsafe(
                lambda: self._nx_loop.create_task(_stop_loop())
            )

            if wait and self._nx_thread and self._nx_thread.is_alive():
                logger_worker.debug("Waiting for thread to finish...")

                self._nx_thread.join(timeout=timeout)

                if self._nx_thread.is_alive():
                    logger_worker.debug("Thread did not finish within the timeout.")
                else:
                    logger_worker.debug("Thread finished.")

        def _copy_affinity(self, target):
            """
            Copy this worker's thread affinity to the target.

            Parameters
            ----------
            target : object
                Target object to receive worker's thread affinity.

            Raises
            ------
            RuntimeError
                If worker thread is not started.
            TypeError
                If target is not compatible with emitters.

            Notes
            -----
            Internal method used by move_to_thread().
            """

            with self._nx_lock:
                if not self._nx_thread or not self._nx_loop:
                    raise RuntimeError(
                        "Worker thread not started. "
                        "Cannot move target to this thread."
                    )

            # Assume target is initialized with nx_with_emitters
            # Reset target's _nx_thread, _nx_loop, _nx_affinity
            if not hasattr(target, NxEmitterConstants.THREAD) or not hasattr(
                target, NxEmitterConstants.LOOP
            ):
                raise TypeError(
                    "Target is not compatible. "
                    "Ensure it is decorated with nx_with_emitters or nx_with_worker."
                )

            # Copy worker's _nx_affinity, _nx_thread, _nx_loop to target
            target._nx_thread = self._nx_thread
            target._nx_loop = self._nx_loop
            target._nx_affinity = self._nx_affinity

            if logger_worker.isEnabledFor(logging.DEBUG):
                logger_worker.debug(
                    "Moved %s to worker thread=%s with affinity=%s",
                    target,
                    self._nx_thread,
                    self._nx_affinity,
                )

    return WorkerClass
