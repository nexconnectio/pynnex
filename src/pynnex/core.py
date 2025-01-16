# src/pynnex/core.py

# pylint: disable=unnecessary-dunder-call
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
# pylint: disable=too-many-branches
# pylint: disable=too-many-positional-arguments

"""
Implementation of the Emitter class for pynnex.

Provides emitter-listener communication pattern for event handling, supporting both
synchronous and asynchronous operations in a thread-safe manner.
"""

from enum import Enum
import asyncio
import concurrent.futures
import contextvars
from dataclasses import dataclass
import functools
import logging
import weakref
from weakref import WeakMethod
import threading
import time
from typing import Callable, Optional
from pynnex.utils import nx_log_and_raise_error

logger = logging.getLogger("pynnex")
logger_emitter = logging.getLogger("pynnex.emitter")
logger_listener = logging.getLogger("pynnex.listener")
logger_emitter_trace = logging.getLogger("pynnex.emitter.trace")
logger_listener_trace = logging.getLogger("pynnex.listener.trace")


class NxEmitterConstants:
    """Constants for emitter-listener communication."""

    FROM_EMIT = "_nx_from_emit"
    THREAD = "_nx_thread"
    LOOP = "_nx_loop"
    AFFINITY = "_nx_affinity"
    WEAK_DEFAULT = "_nx_weak_default"


_nx_from_emit = contextvars.ContextVar(NxEmitterConstants.FROM_EMIT, default=False)


def _get_func_name(func):
    """Get a clean function name for logging"""
    if hasattr(func, "__name__"):
        return func.__name__
    return str(func)


class NxConnectionType(Enum):
    """Connection type for emitter-listener connections."""

    DIRECT_CONNECTION = 1
    QUEUED_CONNECTION = 2
    AUTO_CONNECTION = 3


@dataclass
class NxConnection:
    """Connection class for emitter-listener connections."""

    receiver_ref: Optional[object]
    listener_func: Callable
    conn_type: NxConnectionType
    is_coro_listener: bool
    is_bound: bool
    is_weak: bool
    is_one_shot: bool = False

    def get_receiver(self):
        """If receiver_ref is a weakref, return the actual receiver. Otherwise, return the receiver_ref as is."""

        if self.is_weak and isinstance(self.receiver_ref, weakref.ref):
            return self.receiver_ref()
        return self.receiver_ref

    def is_valid(self):
        """Check if the receiver is alive if it's a weakref."""

        if self.is_weak and isinstance(self.receiver_ref, weakref.ref):
            return self.receiver_ref() is not None

        return True

    def get_listener_to_call(self):
        """
        Return the listener to call at emit time.
        For weakref bound method connections, reconstruct the bound method after recovering the receiver.
        For strong reference, it's already a bound method, so return it directly.
        For standalone functions, return them directly.
        """

        if self.is_weak and isinstance(self.listener_func, WeakMethod):
            real_method = self.listener_func()
            return real_method

        if not self.is_bound:
            return self.listener_func

        receiver = self.get_receiver()
        if receiver is None:
            return None

        # bound + weak=False or bound + weak=True (already not a WeakMethod) case
        return self.listener_func


def _wrap_standalone_function(func, is_coroutine):
    """Wrap standalone function"""

    @functools.wraps(func)
    def wrap(*args, **kwargs):
        """Wrap standalone function"""

        # pylint: disable=no-else-return
        if is_coroutine:
            # Call coroutine function -> return coroutine object
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                nx_log_and_raise_error(
                    logger,
                    RuntimeError,
                    (
                        "No running event loop found. "
                        "A running loop is required for coroutine listeners."
                    ),
                )

        return func(*args, **kwargs)

    return wrap


def _determine_connection_type(conn_type, receiver, owner, is_coro_listener):
    """
    Determine the actual connection type based on the given parameters.
    This logic was originally inside emit, but is now extracted for easier testing.
    """
    actual_conn_type = conn_type

    if conn_type == NxConnectionType.AUTO_CONNECTION:
        if is_coro_listener:
            actual_conn_type = NxConnectionType.QUEUED_CONNECTION
            logger.debug(
                "Connection determined: type=%s, reason=is_coro_listener_and_has_receiver",
                actual_conn_type,
            )
        else:
            receiver = receiver() if isinstance(receiver, weakref.ref) else receiver

            is_receiver_valid = receiver is not None
            has_thread = hasattr(receiver, NxEmitterConstants.THREAD)
            has_affinity = hasattr(receiver, NxEmitterConstants.AFFINITY)
            has_owner_thread = hasattr(owner, NxEmitterConstants.THREAD)
            has_owner_affinity = hasattr(owner, NxEmitterConstants.AFFINITY)

            if (
                is_receiver_valid
                and has_thread
                and has_owner_thread
                and has_affinity
                and has_owner_affinity
            ):
                if receiver._nx_affinity == owner._nx_affinity:
                    actual_conn_type = NxConnectionType.DIRECT_CONNECTION
                    logger.debug(
                        "Connection determined: type=%s, reason=same_thread",
                        actual_conn_type,
                    )
                else:
                    actual_conn_type = NxConnectionType.QUEUED_CONNECTION
                    logger.debug(
                        "Connection determined: type=%s, reason=different_thread",
                        actual_conn_type,
                    )
            else:
                actual_conn_type = NxConnectionType.DIRECT_CONNECTION
                logger.debug(
                    "Connection determined: type=%s, reason=no_receiver or invalid thread or affinity "
                    "is_receiver_valid=%s has_thread=%s has_affinity=%s has_owner_thread=%s has_owner_affinity=%s",
                    actual_conn_type,
                    is_receiver_valid,
                    has_thread,
                    has_affinity,
                    has_owner_thread,
                    has_owner_affinity,
                )

    return actual_conn_type


def _extract_unbound_function(callable_obj):
    """
    Extract the unbound function from a bound method.
    If the listener is a bound method, return the unbound function (__func__), otherwise return the listener as is.
    """

    return getattr(callable_obj, "__func__", callable_obj)


class NxEmitter:
    """Emitter class for pynnex."""

    def __init__(self):
        self.connections = []
        self.owner = None
        self.connections_lock = threading.RLock()

    def connect(
        self,
        receiver_or_listener,
        listener=None,
        conn_type=NxConnectionType.AUTO_CONNECTION,
        weak=None,
        one_shot=False,
    ):
        """
        Connect this emitter to a listener (callable).

        Parameters
        ----------
        receiver_or_listener : object or callable
            Receiver object or callable listener.
        listener : callable, optional
            Method to connect when receiver_or_listener is an object.
        conn_type : NxConnectionType, optional
            Connection type (AUTO, DIRECT, or QUEUED).
        weak : bool, optional
            Use weak reference if True.
        one_shot : bool, optional
            Disconnect after first emission if True.

        Raises
        ------
        TypeError
            If listener is not callable.
        AttributeError
            If receiver is None with listener provided.
        ValueError
        """

        logger.debug(
            "Emitter connection: class=%s, receiver=%s, listener=%s",
            self.__class__.__name__,
            getattr(receiver_or_listener, "__name__", str(receiver_or_listener)),
            getattr(listener, "__name__", str(listener)),
        )

        if weak is None and self.owner is not None:
            weak = getattr(self.owner, NxEmitterConstants.WEAK_DEFAULT, False)

        if listener is None:
            if not callable(receiver_or_listener):
                nx_log_and_raise_error(
                    logger,
                    TypeError,
                    "receiver_or_listener must be callable.",
                )

            receiver = None
            is_bound_method = hasattr(receiver_or_listener, "__self__")
            maybe_listener = (
                receiver_or_listener.__func__
                if is_bound_method
                else receiver_or_listener
            )
            is_coro_listener = asyncio.iscoroutinefunction(maybe_listener)

            if is_bound_method:
                obj = receiver_or_listener.__self__

                if hasattr(obj, NxEmitterConstants.THREAD) and hasattr(
                    obj, NxEmitterConstants.LOOP
                ):
                    receiver = obj
                    listener = receiver_or_listener
                else:
                    listener = _wrap_standalone_function(
                        receiver_or_listener, is_coro_listener
                    )
            else:
                listener = _wrap_standalone_function(
                    receiver_or_listener, is_coro_listener
                )
        else:
            # when both receiver and listener are provided
            if receiver_or_listener is None:
                nx_log_and_raise_error(
                    logger,
                    AttributeError,
                    "Receiver cannot be None.",
                )

            if not callable(listener):
                nx_log_and_raise_error(logger, TypeError, "Listener must be callable.")

            receiver = receiver_or_listener
            is_coro_listener = asyncio.iscoroutinefunction(listener)

        # when conn_type is AUTO, it is not determined here.
        # it is determined at emit time, so it is just stored.
        # If DIRECT or QUEUED is specified, it is used as it is.
        # However, when AUTO is specified, it is determined by thread comparison at emit time.
        if conn_type not in (
            NxConnectionType.AUTO_CONNECTION,
            NxConnectionType.DIRECT_CONNECTION,
            NxConnectionType.QUEUED_CONNECTION,
        ):
            nx_log_and_raise_error(logger, ValueError, "Invalid connection type.")

        is_bound = False
        bound_self = getattr(listener, "__self__", None)

        if bound_self is not None:
            is_bound = True

            if weak and receiver is not None:
                wm = WeakMethod(listener)
                receiver_ref = weakref.ref(bound_self, self._cleanup_on_ref_dead)
                conn = NxConnection(
                    receiver_ref,
                    wm,
                    conn_type,
                    is_coro_listener,
                    is_bound=True,
                    is_weak=True,
                    is_one_shot=one_shot,
                )
            else:
                # strong ref
                conn = NxConnection(
                    bound_self,
                    listener,
                    conn_type,
                    is_coro_listener,
                    is_bound,
                    False,
                    one_shot,
                )
        else:
            # standalone function or lambda
            # weak not applied to function itself, since no receiver
            conn = NxConnection(
                None,
                listener,
                conn_type,
                is_coro_listener,
                is_bound=False,
                is_weak=False,
                is_one_shot=one_shot,
            )

        with self.connections_lock:
            self.connections.append(conn)

    def _cleanup_on_ref_dead(self, ref):
        """Cleanup connections on weak reference death."""

        logger.info("Cleaning up dead reference: %s", ref)

        # ref is a weak reference to the receiver
        # Remove connections associated with the dead receiver
        with self.connections_lock:
            before_count = len(self.connections)

            self.connections = [
                conn for conn in self.connections if conn.receiver_ref is not ref
            ]

            after_count = len(self.connections)

            logger.info(
                "Removed %d connections (before: %d, after: %d)",
                before_count - after_count,
                before_count,
                after_count,
            )

    def disconnect(self, receiver: object = None, listener: Callable = None) -> int:
        """
        Disconnects listeners from the emitter.

        Parameters
        ----------
        receiver : object, optional
            Receiver object to disconnect. If None, matches any receiver.
        listener : Callable, optional
            Listener to disconnect. If None, matches any listener.

        Returns
        -------
        int
            Number of disconnected connections.

        Notes
        -----
        If neither receiver nor listener is specified, all connections are removed.
        If only one is specified, matches any connection with that receiver or listener.
        If both are specified, matches connections with both that receiver and listener.
        """

        with self.connections_lock:
            if receiver is None and listener is None:
                count = len(self.connections)
                self.connections.clear()
                return count

            original_count = len(self.connections)
            new_connections = []

            # When disconnecting, if the listener_func is a WeakMethod, it must also be processed,
            # so real_method is obtained and compared.
            listener_unbound = _extract_unbound_function(listener) if listener else None

            for conn in self.connections:
                conn_receiver = conn.get_receiver()

                # If receiver is None, accept unconditionally, otherwise compare conn_receiver == receiver
                receiver_match = receiver is None or conn_receiver == receiver

                # If listener is None, accept unconditionally, otherwise compare unboundfunc
                if listener_unbound is None:
                    listener_match = True
                else:
                    if isinstance(conn.listener_func, WeakMethod):
                        # Get the actual method from WeakMethod
                        real_method = conn.listener_func()

                        if real_method is None:
                            # The method has already disappeared -> consider it as listener_match (can be disconnected)
                            listener_match = True
                        else:
                            listener_match = (
                                _extract_unbound_function(real_method)
                                == listener_unbound
                                or getattr(real_method, "__wrapped__", None)
                                == listener_unbound
                            )
                    else:
                        # General function or bound method
                        listener_match = (
                            _extract_unbound_function(conn.listener_func)
                            == listener_unbound
                            or getattr(conn.listener_func, "__wrapped__", None)
                            == listener_unbound
                        )

                # Both True means this conn is a target for disconnection, otherwise keep
                if receiver_match and listener_match:
                    continue

                new_connections.append(conn)

            self.connections = new_connections
            disconnected = original_count - len(self.connections)
            return disconnected

    def emit(self, *args, **kwargs):
        """
        Emit the emitter with the specified arguments.

        Parameters
        ----------
        *args : Any
            Positional arguments for connected listeners.
        **kwargs : Any
            Keyword arguments for connected listeners.

        Notes
        -----
        - One-shot listeners are disconnected after first invocation
        - Weak references are cleaned up if receivers are gone
        - Async listeners use queued connections in AUTO mode
        - Exceptions in listeners are logged but don't stop emission
        """

        if logger.isEnabledFor(logging.DEBUG):
            # Emitter meta info
            emitter_name = getattr(self, "emitter_name", "<anonymous>")
            owner_class = type(self.owner).__name__ if self.owner else "<no_owner>"
            thread_name = threading.current_thread().name
            payload_repr = f"args={args}, kwargs={kwargs}"

            logger.debug(
                "Emitter emit started: name=%s, owner=%s, thread=%s, payload=%s",
                emitter_name,
                owner_class,
                thread_name,
                payload_repr,
            )

            start_ts = time.monotonic()

        if logger_emitter_trace.isEnabledFor(logging.DEBUG):
            connections_info = []
            if hasattr(self, "connections"):
                for i, conn in enumerate(self.connections):
                    connections_info.append(
                        f"    #{i}: type={type(conn.receiver_ref)}, "
                        f"alive={conn.get_receiver() is not None}, "
                        f"listener={conn.listener_func}"
                    )

            trace_msg = (
                "Emitter Trace:\n"
                f"  name: {getattr(self, 'emitter_name', '<anonymous>')}\n"
                f"  owner: {self.owner}\n"
                f"  connections ({len(self.connections)}):\n"
                "{}".format(
                    "\n".join(
                        f"    #{i}: type={type(conn.receiver_ref)}, "
                        f"alive={conn.get_receiver() is not None}, "
                        f"listener={_get_func_name(conn.listener_func)}"
                        for i, conn in enumerate(self.connections)
                    )
                    if self.connections
                    else "    none"
                )
            )

            logger_emitter_trace.debug(trace_msg)

        token = _nx_from_emit.set(True)

        with self.connections_lock:
            # copy list to avoid iteration issues during emit
            current_conns = list(self.connections)

        # pylint: disable=too-many-nested-blocks
        try:
            for conn in current_conns:
                if conn.is_bound and not conn.is_valid():
                    with self.connections_lock:
                        if conn in self.connections:
                            self.connections.remove(conn)
                    continue

                listener_to_call = conn.get_listener_to_call()

                if listener_to_call is None:
                    # Unable to call bound method due to receiver GC or other reasons
                    continue

                actual_conn_type = _determine_connection_type(
                    conn.conn_type,
                    conn.get_receiver(),
                    self.owner,
                    conn.is_coro_listener,
                )

                self._invoke_listener(
                    conn, listener_to_call, actual_conn_type, *args, **kwargs
                )

                if conn.is_one_shot:
                    with self.connections_lock:
                        if conn in self.connections:
                            self.connections.remove(conn)

        finally:
            _nx_from_emit.reset(token)

            if logger_emitter.isEnabledFor(logging.DEBUG):
                emitter_name = getattr(self, "emitter_name", "<anonymous>")
                # pylint: disable=possibly-used-before-assignment
                elapsed_ms = (time.monotonic() - start_ts) * 1000
                # pylint: enable=possibly-used-before-assignment

                if elapsed_ms > 0:
                    logger.debug(
                        'Emitter emit completed: name="%s", elapsed=%.2fms',
                        emitter_name,
                        elapsed_ms,
                    )
                else:
                    logger.debug('Emitter emit completed: name="%s"', emitter_name)

    def _invoke_listener(
        self, conn, listener_to_call, actual_conn_type, *args, **kwargs
    ):
        """Invoke the listener once."""

        if logger_listener.isEnabledFor(logging.DEBUG):
            emitter_name = getattr(self, "emitter_name", "<anonymous>")
            listener_name = getattr(
                listener_to_call, "__name__", "<anonymous_listener>"
            )
            receiver_obj = conn.get_receiver()
            receiver_class = (
                type(receiver_obj).__name__ if receiver_obj else "<no_receiver>"
            )

        if logger_listener_trace.isEnabledFor(logging.DEBUG):
            trace_msg = (
                f"Listener Invoke Trace:\n"
                f"  emitter: {getattr(self, 'emitter_name', '<anonymous>')}\n"
                f"  connection details:\n"
                f"    receiver_ref type: {type(conn.receiver_ref)}\n"
                f"    receiver alive: {conn.get_receiver() is not None}\n"
                f"    listener_func: {_get_func_name(conn.listener_func)}\n"
                f"    is_weak: {conn.is_weak}\n"
                f"  listener to call:\n"
                f"    type: {type(listener_to_call)}\n"
                f"    name: {_get_func_name(listener_to_call)}\n"
                f"    qualname: {getattr(listener_to_call, '__qualname__', '<unknown>')}\n"
                f"    module: {getattr(listener_to_call, '__module__', '<unknown>')}"
            )

            logger_listener_trace.debug(trace_msg)

        try:
            if actual_conn_type == NxConnectionType.DIRECT_CONNECTION:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Calling listener directly")

                if logger_listener.isEnabledFor(logging.DEBUG):
                    start_ts = time.monotonic()
                    logger.debug(
                        'Listener invoke started: "%s" -> %s.%s, connection=direct',
                        emitter_name,
                        receiver_class,
                        listener_name,
                    )

                result = listener_to_call(*args, **kwargs)

                if logger_listener.isEnabledFor(logging.DEBUG):
                    exec_ms = (time.monotonic() - start_ts) * 1000
                    logger.debug(
                        'Listener invoke completed: "%s" -> %s.%s, connection=direct, exec_time=%.2fms, result=%s',
                        emitter_name,
                        receiver_class,
                        listener_name,
                        exec_ms,
                        result,
                    )

                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        "result=%s result_type=%s",
                        result,
                        type(result),
                    )
            else:
                # Handle QUEUED CONNECTION
                queued_at = time.monotonic()

                receiver = conn.get_receiver()

                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        "Scheduling listener: name=%s, receiver=%s, connection=%s, is_coro=%s",
                        listener_to_call.__name__,
                        getattr(listener_to_call, "__self__", "<no_receiver>"),
                        actual_conn_type,
                        conn.is_coro_listener,
                    )

                if receiver is not None:
                    receiver_loop = getattr(receiver, NxEmitterConstants.LOOP, None)
                    receiver_thread = getattr(receiver, NxEmitterConstants.THREAD, None)

                    if not receiver_loop:
                        logger.error(
                            "No event loop found for receiver. receiver=%s",
                            receiver,
                            stack_info=True,
                        )
                        return
                else:
                    try:
                        receiver_loop = asyncio.get_running_loop()
                    except RuntimeError:
                        nx_log_and_raise_error(
                            logger,
                            RuntimeError,
                            "No running event loop found for queued connection.",
                        )

                    receiver_thread = None

                if not receiver_loop.is_running():
                    logger.warning(
                        "receiver loop not running. Emitters may not be delivered. receiver=%s",
                        receiver.__class__.__name__,
                    )
                    return

                if receiver_thread and not receiver_thread.is_alive():
                    logger.warning(
                        "The receiver's thread is not alive. Emitters may not be delivered. receiver=%s",
                        receiver.__class__.__name__,
                    )

                def dispatch(
                    is_coro_listener=conn.is_coro_listener,
                    listener_to_call=listener_to_call,
                ):
                    if is_coro_listener:
                        returned = asyncio.create_task(
                            listener_to_call(*args, **kwargs)
                        )
                    else:
                        returned = listener_to_call(*args, **kwargs)

                    if logger_listener.isEnabledFor(logging.DEBUG):
                        wait_ms = (time.monotonic() - queued_at) * 1000
                        logger.debug(
                            'Listener invoke started: "%s" -> %s.%s, connection=queued, queue_wait=%.2fms',
                            emitter_name,
                            receiver_class,
                            listener_name,
                            wait_ms,
                        )

                    if logger.isEnabledFor(logging.DEBUG):
                        task_id = getattr(returned, "get_name", lambda: "<no_task>")()
                        logger.debug(
                            'Task created: id=%s, listener="%s" -> %s.%s',
                            task_id,
                            emitter_name,
                            receiver_class,
                            listener_name,
                        )

                    return returned

                receiver_loop.call_soon_threadsafe(dispatch)

        except Exception as e:
            logger.error("error in emission: %s", e, exc_info=True)


# property is used for lazy initialization of the emitter.
# The emitter object is created only when first accessed, and a cached object is returned thereafter.
class NxEmitterProperty(property):
    """Emitter property class for pynnex."""

    def __init__(self, fget, emitter_name):
        super().__init__(fget)
        self.emitter_name = emitter_name

    def __get__(self, obj, objtype=None):
        emitter = super().__get__(obj, objtype)

        if obj is not None:
            emitter.owner = obj

        return emitter


def nx_emitter(func):
    """
    Decorator that defines an emitter attribute within a class.

    Parameters
    ----------
    func : function
        Placeholder function defining emitter name and docstring.

    Returns
    -------
    NxEmitterProperty
        Property-like descriptor returning NxEmitter object.

    Notes
    -----
    Must be used within a class decorated with @nx_with_emitters.
    Emitter object is created lazily on first access.

    See Also
    --------
    nx_with_emitters : Class decorator for emitter/listener features
    NxEmitter : Emitter class implementation
    """

    sig_name = func.__name__

    def wrap(self):
        """Wrap emitter"""

        if not hasattr(self, f"_{sig_name}"):
            setattr(self, f"_{sig_name}", NxEmitter())

        return getattr(self, f"_{sig_name}")

    return NxEmitterProperty(wrap, sig_name)


def nx_listener(func):
    """
    Decorator that marks a method as a listener.

    Parameters
    ----------
    func : function or coroutine
        Method to be decorated as a listener.

    Returns
    -------
    function or coroutine
        Wrapped version of the listener with thread-safe handling.

    Notes
    -----
    - Supports both sync and async methods
    - Ensures thread-safe execution via correct event loop
    - Handles cross-thread invocation automatically

    See Also
    --------
    nx_with_emitters : Class decorator for emitter/listener features
    """

    is_coroutine = asyncio.iscoroutinefunction(func)

    if is_coroutine:

        @functools.wraps(func)
        async def wrap(self, *args, **kwargs):
            """Wrap coroutine listeners"""

            try:
                asyncio.get_running_loop()
            except RuntimeError:
                nx_log_and_raise_error(
                    logger,
                    RuntimeError,
                    "No running loop in coroutine.",
                )

            if not hasattr(self, NxEmitterConstants.THREAD):
                self._nx_thread = threading.current_thread()

            if not hasattr(self, NxEmitterConstants.LOOP):
                try:
                    self._nx_loop = asyncio.get_running_loop()
                except RuntimeError:
                    nx_log_and_raise_error(
                        logger,
                        RuntimeError,
                        "No running event loop found.",
                    )

            if not _nx_from_emit.get():
                current_thread = threading.current_thread()

                if current_thread != self._nx_thread:
                    future = asyncio.run_coroutine_threadsafe(
                        func(self, *args, **kwargs), self._nx_loop
                    )

                    return await asyncio.wrap_future(future)

            return await func(self, *args, **kwargs)

    else:

        @functools.wraps(func)
        def wrap(self, *args, **kwargs):
            """Wrap regular listeners"""

            if not hasattr(self, NxEmitterConstants.THREAD):
                self._nx_thread = threading.current_thread()

            if not hasattr(self, NxEmitterConstants.LOOP):
                try:
                    self._nx_loop = asyncio.get_running_loop()
                except RuntimeError:
                    nx_log_and_raise_error(
                        logger,
                        RuntimeError,
                        "No running event loop found.",
                    )

            if not _nx_from_emit.get():
                current_thread = threading.current_thread()

                if current_thread != self._nx_thread:
                    future = concurrent.futures.Future()

                    def callback():
                        """Callback function for thread-safe execution"""

                        try:
                            result = func(self, *args, **kwargs)
                            future.set_result(result)
                        except Exception as e:
                            future.set_exception(e)

                    self._nx_loop.call_soon_threadsafe(callback)

                    return future.result()

            return func(self, *args, **kwargs)

    return wrap


def nx_with_emitters(cls=None, *, loop=None, weak_default=True):
    """
    Class decorator that enables emitter/listener features.

    Parameters
    ----------
    cls : class, optional
        Class to be decorated.
    loop : asyncio.AbstractEventLoop, optional
        Event loop to be assigned to instances.
    weak_default : bool, optional
        Default value for weak connections. Defaults to True.

    Returns
    -------
    class
        Decorated class with emitter/listener support.

    Notes
    -----
    - Assigns event loop and thread affinity to instances
    - Enables automatic threading support for emitters/listeners
    - weak_default can be overridden per connection

    See Also
    --------
    nx_emitter : Emitter decorator
    nx_listener : Listener decorator
    """

    def wrap(cls):
        """Wrap class with emitters"""

        original_init = cls.__init__

        def __init__(self, *args, **kwargs):
            current_loop = loop

            if current_loop is None:
                try:
                    current_loop = asyncio.get_running_loop()
                except RuntimeError:
                    nx_log_and_raise_error(
                        logger,
                        RuntimeError,
                        "No running event loop found.",
                    )

            # Set thread and event loop
            self._nx_thread = threading.current_thread()
            self._nx_affinity = self._nx_thread
            self._nx_loop = current_loop
            self._nx_weak_default = weak_default

            # Call the original __init__
            original_init(self, *args, **kwargs)

        def move_to_thread(self, target_thread):
            """Change thread affinity of the instance to targetThread"""

            target_thread._copy_affinity(self)

        cls.__init__ = __init__
        cls.move_to_thread = move_to_thread

        return cls

    if cls is None:
        return wrap

    return wrap(cls)


async def nx_graceful_shutdown():
    """
    Waits for all pending tasks to complete.
    This repeatedly checks for tasks until none are left except the current one.
    """
    while True:
        await asyncio.sleep(0)  # Let the event loop process pending callbacks

        tasks = asyncio.all_tasks()
        tasks.discard(asyncio.current_task())

        if not tasks:
            break

        # Wait for all pending tasks to complete (or fail) before checking again
        await asyncio.gather(*tasks, return_exceptions=True)
