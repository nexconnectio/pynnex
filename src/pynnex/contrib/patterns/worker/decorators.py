# src/pynnex/contrib/patterns/worker/decorators.py

# pylint: disable=not-callable

"""
Decorator for the worker pattern.

This decorator enhances a class to support a worker pattern, allowing for
asynchronous task processing in a separate thread. It ensures that the
class has the required asynchronous `initialize` and `finalize` methods,
facilitating the management of worker threads and task queues.
"""

import asyncio
import inspect
import logging
import threading
from pynnex.core import nx_emitter, NxEmitterConstants

logger = logging.getLogger(__name__)


class _WorkerConstants:
    """Constants for the worker pattern."""

    RUN_CORO = "run_coro"
    RUN = "run"


def nx_with_worker(cls):
    """
    Class decorator that adds worker thread functionality.

    Parameters
    ----------
    cls : class
        Class to be decorated.

    Returns
    -------
    class
        Decorated class with worker thread support.

    Notes
    -----
    - Creates dedicated thread with event loop
    - Provides task queue for async operations
    - Supports emitter/listener communication
    - Emits started/stopped emitters
    - Manages worker lifecycle via start/stop methods

    See Also
    --------
    nx_with_emitters : Base decorator for emitter/listener features
    nx_emitter : Emitter decorator
    nx_listener : Listener decorator
    """

    class WorkerClass(cls):
        """
        Worker class for the worker pattern.
        """

        def __init__(self):
            self._nx_loop = None
            self._nx_thread = None

            """
            _nx_lifecycle_lock:
                A re-entrant lock that protects worker's lifecycle state (event loop and thread).
                All operations that access or modify worker's lifecycle state must be
                performed while holding this lock.
            """
            self._nx_lifecycle_lock = threading.RLock()
            self._nx_stopping = asyncio.Event()
            self._nx_affinity = object()
            self._nx_process_queue_task = None
            self._nx_task_queue = None
            super().__init__()

        @property
        def event_loop(self) -> asyncio.AbstractEventLoop:
            """Returns the worker's event loop"""

            if not self._nx_loop:
                raise RuntimeError("Worker not started")

            return self._nx_loop

        @nx_emitter
        def started(self):
            """Emitter emitted when the worker starts"""

        @nx_emitter
        def stopped(self):
            """Emitter emitted when the worker stops"""

        async def run(self, *args, **kwargs):
            """Run the worker."""

            logger.debug("Calling super")

            super_run = getattr(super(), _WorkerConstants.RUN, None)
            is_super_run_called = False

            if super_run is not None and inspect.iscoroutinefunction(super_run):
                sig = inspect.signature(super_run)

                try:
                    logger.debug("sig: %s", sig)
                    sig.bind(self, *args, **kwargs)
                    await super_run(*args, **kwargs)
                    logger.debug("super_run called")
                    is_super_run_called = True
                except TypeError:
                    logger.warning(
                        "Parent run() signature mismatch. "
                        "Expected: async def run(*args, **kwargs) but got %s",
                        sig,
                    )

            if not is_super_run_called:
                logger.debug("super_run not called, starting queue")
                await self.start_queue()

        async def _process_queue(self):
            """Process the task queue."""

            while not self._nx_stopping.is_set():
                coro = await self._nx_task_queue.get()

                try:
                    await coro
                except Exception as e:
                    logger.error(
                        "Task failed: %s",
                        e,
                        exc_info=True,
                    )
                finally:
                    self._nx_task_queue.task_done()

        async def start_queue(self):
            """Start the task queue processing. Returns the queue task."""

            self._nx_process_queue_task = asyncio.create_task(self._process_queue())

        def queue_task(self, coro):
            """
            Schedules a coroutine to run on the worker's event loop.

            Parameters
            ----------
            coro : coroutine
                Coroutine to be executed in the worker thread.

            Raises
            ------
            RuntimeError
                If worker is not started.
            ValueError
                If argument is not a coroutine object.

            Notes
            -----
            - Thread-safe: Can be called from any thread
            - Tasks are processed in FIFO order
            - Failed tasks are logged but don't stop queue
            """

            if not asyncio.iscoroutine(coro):
                logger.error(
                    "Task must be a coroutine object: %s",
                    coro,
                )
                return

            with self._nx_lifecycle_lock:
                loop = self._nx_loop

            loop.call_soon_threadsafe(lambda: self._nx_task_queue.put_nowait(coro))

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

            run_coro = kwargs.pop(_WorkerConstants.RUN_CORO, None)

            if run_coro is not None and not asyncio.iscoroutine(run_coro):
                logger.error(
                    "Must be a coroutine object: %s",
                    run_coro,
                )
                return

            def thread_main():
                """Thread main function."""

                self._nx_task_queue = asyncio.Queue()

                with self._nx_lifecycle_lock:
                    self._nx_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self._nx_loop)

                async def runner():
                    """Runner function."""

                    self.started.emit()

                    if run_coro is not None:
                        run_task = asyncio.create_task(run_coro(*args, **kwargs))
                    else:
                        run_task = asyncio.create_task(self.run(*args, **kwargs))

                    try:
                        await self._nx_stopping.wait()

                        run_task.cancel()

                        try:
                            await run_task
                        except asyncio.CancelledError:
                            pass

                        if (
                            self._nx_process_queue_task
                            and not self._nx_process_queue_task.done()
                        ):
                            self._nx_process_queue_task.cancel()

                            try:
                                await self._nx_process_queue_task
                            except asyncio.CancelledError:
                                logger.debug("_process_queue_task cancelled")

                    finally:
                        self.stopped.emit()
                        # Give the event loop a chance to emit the emitter
                        await asyncio.sleep(0)
                        logger.debug("emit stopped")

                with self._nx_lifecycle_lock:
                    loop = self._nx_loop

                loop.create_task(runner())
                loop.run_forever()
                loop.close()

                with self._nx_lifecycle_lock:
                    self._nx_loop = None

            # Protect thread creation and assignment under the same lock
            with self._nx_lifecycle_lock:
                self._nx_thread = threading.Thread(target=thread_main, daemon=True)

            with self._nx_lifecycle_lock:
                self._nx_thread.start()

        def stop(self):
            """
            Gracefully stops the worker thread and its event loop.

            Notes
            -----
            - Cancels any running tasks including main run() coroutine
            - Waits for task queue to finish processing
            - Emits 'stopped' emitter before final cleanup
            - Thread is joined with a 2-second timeout
            """

            logger.debug("Starting worker shutdown")

            # Acquire lock to safely access _nx_loop and _nx_thread
            with self._nx_lifecycle_lock:
                loop = self._nx_loop
                thread = self._nx_thread

            if loop and thread and thread.is_alive():
                logger.debug("Setting stop flag")
                loop.call_soon_threadsafe(self._nx_stopping.set)
                logger.debug("Waiting for thread to join")
                thread.join(timeout=2)
                logger.debug("Thread joined")

                with self._nx_lifecycle_lock:
                    self._nx_loop = None
                    self._nx_thread = None

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

            with self._nx_lifecycle_lock:
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

            logger.debug(
                "Moved %s to worker thread=%s with affinity=%s",
                target,
                self._nx_thread,
                self._nx_affinity,
            )

        async def wait_for_stop(self):
            """Wait for the worker to stop."""

            await self._nx_stopping.wait()

    return WorkerClass
