# src/pynnex/core.py

# pylint: disable=unnecessary-dunder-call
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
# pylint: disable=too-many-branches
# pylint: disable=too-many-positional-arguments

"""
Implementation of the Signal class for pynnex.

Provides signal-slot communication pattern for event handling, supporting both
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
logger_signal = logging.getLogger("pynnex.signal")
logger_slot   = logging.getLogger("pynnex.slot")
logger_signal_trace = logging.getLogger("pynnex.signal.trace")
logger_slot_trace = logging.getLogger("pynnex.slot.trace")

class NxSignalConstants:
    """Constants for signal-slot communication."""

    FROM_EMIT = "_nx_from_emit"
    THREAD = "_nx_thread"
    LOOP = "_nx_loop"
    AFFINITY = "_nx_affinity"
    WEAK_DEFAULT = "_nx_weak_default"


_nx_from_emit = contextvars.ContextVar(NxSignalConstants.FROM_EMIT, default=False)

def _get_func_name(func):
    """Get a clean function name for logging"""
    if hasattr(func, '__name__'):
        return func.__name__
    return str(func)

class NxConnectionType(Enum):
    """Connection type for signal-slot connections."""

    DIRECT_CONNECTION = 1
    QUEUED_CONNECTION = 2
    AUTO_CONNECTION = 3


@dataclass
class NxConnection:
    """Connection class for signal-slot connections."""

    receiver_ref: Optional[object]
    slot_func: Callable
    conn_type: NxConnectionType
    is_coro_slot: bool
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

    def get_slot_to_call(self):
        """
        Return the slot to call at emit time.
        For weakref bound method connections, reconstruct the bound method after recovering the receiver.
        For strong reference, it's already a bound method, so return it directly.
        For standalone functions, return them directly.
        """

        if self.is_weak and isinstance(self.slot_func, WeakMethod):
            real_method = self.slot_func()
            return real_method

        if not self.is_bound:
            return self.slot_func

        receiver = self.get_receiver()
        if receiver is None:
            return None

        # bound + weak=False or bound + weak=True (already not a WeakMethod) case
        return self.slot_func

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
                        "A running loop is required for coroutine slots."
                    ),
                )

        return func(*args, **kwargs)

    return wrap


def _determine_connection_type(conn_type, receiver, owner, is_coro_slot):
    """
    Determine the actual connection type based on the given parameters.
    This logic was originally inside emit, but is now extracted for easier testing.
    """
    actual_conn_type = conn_type

    if conn_type == NxConnectionType.AUTO_CONNECTION:
        if is_coro_slot:
            actual_conn_type = NxConnectionType.QUEUED_CONNECTION
            logger.debug(
                "Connection determined: type=%s, reason=is_coro_slot_and_has_receiver",
                actual_conn_type,
            )
        else:
            receiver = receiver() if isinstance(receiver, weakref.ref) else receiver

            is_receiver_valid = receiver is not None
            has_thread = hasattr(receiver, NxSignalConstants.THREAD)
            has_affinity = hasattr(receiver, NxSignalConstants.AFFINITY)
            has_owner_thread = hasattr(owner, NxSignalConstants.THREAD)
            has_owner_affinity = hasattr(owner, NxSignalConstants.AFFINITY)

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
    If the slot is a bound method, return the unbound function (__func__), otherwise return the slot as is.
    """

    return getattr(callable_obj, "__func__", callable_obj)


class NxSignal:
    """Signal class for pynnex."""

    def __init__(self):
        self.connections = []
        self.owner = None
        self.connections_lock = threading.RLock()

    def connect(
        self,
        receiver_or_slot,
        slot=None,
        conn_type=NxConnectionType.AUTO_CONNECTION,
        weak=None,
        one_shot=False,
    ):
        """
        Connect this signal to a slot (callable). The connected slot will be invoked
        on each `emit()` call.

        Parameters
        ----------
        receiver_or_slot : object or callable
            If `slot` is omitted, this can be a standalone callable (function or lambda),
            or a bound method. Otherwise, this is treated as the receiver object.
        slot : callable, optional
            When `receiver_or_slot` is a receiver object, `slot` should be the method
            to connect. If both `receiver_or_slot` and `slot` are given, this effectively
            connects the signal to the method `slot` of the given `receiver`.
        conn_type : NxConnectionType, optional
            Specifies how the slot is invoked relative to the signal emitter. Defaults to
            `NxConnectionType.AUTO_CONNECTION`, which automatically determines direct or queued
            invocation based on thread affinity and slot type (sync/async).
        weak : bool, optional
            If `True`, a weak reference to the receiver is stored so the connection
            is automatically removed once the receiver is garbage-collected.
            If omitted (`None`), the default is determined by the decorator `@nx_with_signals`
            (i.e., `weak_default`).
        one_shot : bool, optional
            If `True`, this connection is automatically disconnected right after the
            first successful emission. Defaults to `False`.

        Raises
        ------
        TypeError
            If the provided slot is not callable or if `receiver_or_slot` is not callable
            when `slot` is `None`.
        AttributeError
            If `receiver_or_slot` is `None` while `slot` is provided.
        ValueError
            If `conn_type` is invalid (not one of AUTO_CONNECTION, DIRECT_CONNECTION, QUEUED_CONNECTION).

        Examples
        --------
        # Connect a bound method
        signal.connect(receiver, receiver.some_method)

        # Connect a standalone function
        def standalone_func(value):
            print("Received:", value)
        signal.connect(standalone_func)

        # One-shot connection
        signal.connect(receiver, receiver.one_time_handler, one_shot=True)

        # Weak reference connection
        signal.connect(receiver, receiver.on_event, weak=True)
        """

        logger.debug("Signal connection: class=%s, receiver=%s, slot=%s",
            self.__class__.__name__,
            getattr(receiver_or_slot, '__name__', str(receiver_or_slot)),
            getattr(slot, '__name__', str(slot))
        )

        if weak is None and self.owner is not None:
            weak = getattr(self.owner, NxSignalConstants.WEAK_DEFAULT, False)

        if slot is None:
            if not callable(receiver_or_slot):
                nx_log_and_raise_error(
                    logger,
                    TypeError,
                    "receiver_or_slot must be callable.",
                )

            receiver = None
            is_bound_method = hasattr(receiver_or_slot, "__self__")
            maybe_slot = (
                receiver_or_slot.__func__ if is_bound_method else receiver_or_slot
            )
            is_coro_slot = asyncio.iscoroutinefunction(maybe_slot)

            if is_bound_method:
                obj = receiver_or_slot.__self__

                if hasattr(obj, NxSignalConstants.THREAD) and hasattr(
                    obj, NxSignalConstants.LOOP
                ):
                    receiver = obj
                    slot = receiver_or_slot
                else:
                    slot = _wrap_standalone_function(receiver_or_slot, is_coro_slot)
            else:
                slot = _wrap_standalone_function(receiver_or_slot, is_coro_slot)
        else:
            # when both receiver and slot are provided
            if receiver_or_slot is None:
                nx_log_and_raise_error(
                    logger,
                    AttributeError,
                    "Receiver cannot be None.",
                )

            if not callable(slot):
                nx_log_and_raise_error(
                    logger, TypeError, "Slot must be callable."
                )

            receiver = receiver_or_slot
            is_coro_slot = asyncio.iscoroutinefunction(slot)

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
        bound_self = getattr(slot, "__self__", None)

        if bound_self is not None:
            is_bound = True

            if weak and receiver is not None:
                wm = WeakMethod(slot)
                receiver_ref = weakref.ref(bound_self, self._cleanup_on_ref_dead)
                conn = NxConnection(
                    receiver_ref,
                    wm,
                    conn_type,
                    is_coro_slot,
                    is_bound=True,
                    is_weak=True,
                    is_one_shot=one_shot,
                )
            else:
                # strong ref
                conn = NxConnection(
                    bound_self,
                    slot,
                    conn_type,
                    is_coro_slot,
                    is_bound,
                    False,
                    one_shot,
                )
        else:
            # standalone function or lambda
            # weak not applied to function itself, since no receiver
            conn = NxConnection(
                None,
                slot,
                conn_type,
                is_coro_slot,
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
                after_count
            )

    def disconnect(self, receiver: object = None, slot: Callable = None) -> int:
        """
        Disconnects one or more slots from the signal. This method attempts to find and remove
        connections that match the given `receiver` and/or `slot`.

        Parameters
        ----------
        receiver : object, optional
            The receiver object initially connected to the signal. If omitted, matches any receiver.
        slot : Callable, optional
            The slot (callable) that was connected to the signal. If omitted, matches any slot.

        Returns
        -------
        int
            The number of connections successfully disconnected.

        Notes
        -----
        - If neither `receiver` nor `slot` is specified, all connections are removed.
        - If only `receiver` is given (and `slot=None`), all connections involving that receiver will be removed.
        - If only `slot` is given (and `receiver=None`), all connections involving that slot are removed.
        - If both `receiver` and `slot` are given, only the connections that match both will be removed.

        Example
        -------
        Consider a signal connected to multiple slots of a given receiver:

        >>> signal.disconnect(receiver=my_receiver)
        # All connections associated with `my_receiver` are removed.

        Or if a specific slot was connected:

        >>> signal.disconnect(slot=my_specific_slot)
        # All connections to `my_specific_slot` are removed.

        Passing both `receiver` and `slot`:

        >>> signal.disconnect(receiver=my_receiver, slot=my_specific_slot)
        # Only the connections that match both `my_receiver` and `my_specific_slot` are removed.
        """

        with self.connections_lock:
            if receiver is None and slot is None:
                count = len(self.connections)
                self.connections.clear()
                return count

            original_count = len(self.connections)
            new_connections = []

            # When disconnecting, if the slot_func is a WeakMethod, it must also be processed,
            # so real_method is obtained and compared.
            slot_unbound = _extract_unbound_function(slot) if slot else None

            for conn in self.connections:
                conn_receiver = conn.get_receiver()

                # If receiver is None, accept unconditionally, otherwise compare conn_receiver == receiver
                receiver_match = (receiver is None or conn_receiver == receiver)

                # If slot is None, accept unconditionally, otherwise compare unboundfunc
                if slot_unbound is None:
                    slot_match = True
                else:
                    if isinstance(conn.slot_func, WeakMethod):
                        # Get the actual method from WeakMethod
                        real_method = conn.slot_func()

                        if real_method is None:
                            # The method has already disappeared -> consider it as slot_match (can be disconnected)
                            slot_match = True
                        else:
                            slot_match = (
                                _extract_unbound_function(real_method) == slot_unbound
                                or getattr(real_method, "__wrapped__", None) == slot_unbound
                            )
                    else:
                        # General function or bound method
                        slot_match = (
                            _extract_unbound_function(conn.slot_func) == slot_unbound
                            or getattr(conn.slot_func, "__wrapped__", None) == slot_unbound
                        )

                # Both True means this conn is a target for disconnection, otherwise keep
                if receiver_match and slot_match:
                    continue

                new_connections.append(conn)

            self.connections = new_connections
            disconnected = original_count - len(self.connections)
            return disconnected

    def emit(self, *args, **kwargs):
        """
        Emit the signal with the specified arguments. All connected slots will be
        invoked, either directly or via their respective event loops, depending on
        the connection type and thread affinity.

        Parameters
        ----------
        *args : Any
            Positional arguments passed on to each connected slot.
        **kwargs : Any
            Keyword arguments passed on to each connected slot.

        Notes
        -----
        - When a connected slot is marked with `is_one_shot=True`, it is automatically
        disconnected immediately after being invoked for the first time.
        - If a slot was connected with a weak reference (`weak=True`) and its receiver
        has been garbage-collected, that connection is skipped and removed from the
        internal list of connections.
        - If the slot is asynchronous and `conn_type` is `AUTO_CONNECTION`, it typically
        uses a queued connection (queued to the slot’s event loop).
        - If an exception occurs in a slot, the exception is logged, but does not halt
        the emission to other slots.

        Examples
        --------
        signal.emit(42, message="Hello")
        """

        if logger.isEnabledFor(logging.DEBUG):
            # Signal meta info
            signal_name = getattr(self, "signal_name", "<anonymous>")
            owner_class = type(self.owner).__name__ if self.owner else "<no_owner>"
            thread_name = threading.current_thread().name
            payload_repr = f"args={args}, kwargs={kwargs}"

            logger.debug(
                'Signal emit started: name=%s, owner=%s, thread=%s, payload=%s',
                signal_name,
                owner_class,
                thread_name,
                payload_repr
            )

            start_ts = time.monotonic()

        if logger_signal_trace.isEnabledFor(logging.DEBUG):
            connections_info = []
            if hasattr(self, 'connections'):
                for i, conn in enumerate(self.connections):
                    connections_info.append(
                        f"    #{i}: type={type(conn.receiver_ref)}, "
                        f"alive={conn.get_receiver() is not None}, "
                        f"slot={conn.slot_func}"
                    )

            trace_msg = (
                "Signal Trace:\n"
                f"  name: {getattr(self, 'signal_name', '<anonymous>')}\n"
                f"  owner: {self.owner}\n"
                f"  connections ({len(self.connections)}):\n"
                "{}".format(
                    '\n'.join(
                        f"    #{i}: type={type(conn.receiver_ref)}, "
                        f"alive={conn.get_receiver() is not None}, "
                        f"slot={_get_func_name(conn.slot_func)}"
                        for i, conn in enumerate(self.connections)
                    ) if self.connections else '    none'
                )
            )

            logger_signal_trace.debug(trace_msg)

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

                slot_to_call = conn.get_slot_to_call()

                if slot_to_call is None:
                    # Unable to call bound method due to receiver GC or other reasons
                    continue

                actual_conn_type = _determine_connection_type(
                    conn.conn_type, conn.get_receiver(), self.owner, conn.is_coro_slot
                )

                self._invoke_slot(conn, slot_to_call, actual_conn_type, *args, **kwargs)

                if conn.is_one_shot:
                    with self.connections_lock:
                        if conn in self.connections:
                            self.connections.remove(conn)

        finally:
            _nx_from_emit.reset(token)

            if logger_signal.isEnabledFor(logging.DEBUG):
                signal_name = getattr(self, "signal_name", "<anonymous>")
                # pylint: disable=possibly-used-before-assignment
                elapsed_ms = (time.monotonic() - start_ts) * 1000
                # pylint: enable=possibly-used-before-assignment

                if elapsed_ms > 0:
                    logger.debug('Signal emit completed: name="%s", elapsed=%.2fms',
                        signal_name, elapsed_ms)
                else:
                    logger.debug('Signal emit completed: name="%s"', signal_name)

    def _invoke_slot(self, conn, slot_to_call, actual_conn_type, *args, **kwargs):
        """Invoke the slot once."""

        if logger_slot.isEnabledFor(logging.DEBUG):
            signal_name = getattr(self, "signal_name", "<anonymous>")
            slot_name = getattr(slot_to_call, "__name__", "<anonymous_slot>")
            receiver_obj = conn.get_receiver()
            receiver_class = type(receiver_obj).__name__ if receiver_obj else "<no_receiver>"

        if logger_slot_trace.isEnabledFor(logging.DEBUG):
            trace_msg = (
                f"Slot Invoke Trace:\n"
                f"  signal: {getattr(self, 'signal_name', '<anonymous>')}\n"
                f"  connection details:\n"
                f"    receiver_ref type: {type(conn.receiver_ref)}\n"
                f"    receiver alive: {conn.get_receiver() is not None}\n"
                f"    slot_func: {_get_func_name(conn.slot_func)}\n"
                f"    is_weak: {conn.is_weak}\n"
                f"  slot to call:\n"
                f"    type: {type(slot_to_call)}\n"
                f"    name: {_get_func_name(slot_to_call)}\n"
                f"    qualname: {getattr(slot_to_call, '__qualname__', '<unknown>')}\n"
                f"    module: {getattr(slot_to_call, '__module__', '<unknown>')}"
            )

            logger_slot_trace.debug(trace_msg)

        try:
            if actual_conn_type == NxConnectionType.DIRECT_CONNECTION:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Calling slot directly")

                if logger_slot.isEnabledFor(logging.DEBUG):
                    start_ts = time.monotonic()
                    logger.debug(
                        'Slot invoke started: "%s" -> %s.%s, connection=direct',
                        signal_name,
                        receiver_class,
                        slot_name
                    )

                result = slot_to_call(*args, **kwargs)

                if logger_slot.isEnabledFor(logging.DEBUG):
                    exec_ms = (time.monotonic() - start_ts) * 1000
                    logger.debug(
                        'Slot invoke completed: "%s" -> %s.%s, connection=direct, exec_time=%.2fms, result=%s',
                        signal_name,
                        receiver_class,
                        slot_name,
                        exec_ms,
                        result
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
                    logger.debug('Scheduling slot: name=%s, receiver=%s, connection=%s, is_coro=%s',
                        slot_to_call.__name__, getattr(slot_to_call, '__self__', '<no_receiver>'),
                        actual_conn_type, conn.is_coro_slot)


                if receiver is not None:
                    receiver_loop = getattr(receiver, NxSignalConstants.LOOP, None)
                    receiver_thread = getattr(receiver, NxSignalConstants.THREAD, None)

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
                        "receiver loop not running. Signals may not be delivered. receiver=%s",
                        receiver.__class__.__name__,
                    )
                    return

                if receiver_thread and not receiver_thread.is_alive():
                    logger.warning(
                        "The receiver's thread is not alive. Signals may not be delivered. receiver=%s",
                        receiver.__class__.__name__,
                    )

                def dispatch(
                    is_coro_slot=conn.is_coro_slot,
                    slot_to_call=slot_to_call,
                ):
                    if is_coro_slot:
                        returned = asyncio.create_task(
                            slot_to_call(*args, **kwargs)
                        )
                    else:
                        returned = slot_to_call(*args, **kwargs)

                    if logger_slot.isEnabledFor(logging.DEBUG):
                        wait_ms = (time.monotonic() - queued_at) * 1000
                        logger.debug(
                            'Slot invoke started: "%s" -> %s.%s, connection=queued, queue_wait=%.2fms',
                            signal_name,
                            receiver_class,
                            slot_name,
                            wait_ms
                        )

                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Task created: id=%s, slot="%s" -> %s.%s',
                            returned.get_name(), signal_name, receiver_class, slot_name)

                    return returned

                receiver_loop.call_soon_threadsafe(dispatch)

        except Exception as e:
            logger.error(
                "error in emission: %s", e, exc_info=True
            )


# property is used for lazy initialization of the signal.
# The signal object is created only when first accessed, and a cached object is returned thereafter.
class NxSignalProperty(property):
    """Signal property class for pynnex."""

    def __init__(self, fget, signal_name):
        super().__init__(fget)
        self.signal_name = signal_name

    def __get__(self, obj, objtype=None):
        signal = super().__get__(obj, objtype)

        if obj is not None:
            signal.owner = obj

        return signal


def nx_signal(func):
    """
    Decorator that defines a signal attribute within a class decorated by @nx_with_signals.
    The decorated function name is used as the signal name, and it provides a lazy-initialized
    NxSignal instance.

    Parameters
    ----------
    func : function
        A placeholder function that helps to define the signal's name and docstring. The
        function body is ignored at runtime, as the signal object is created and stored
        dynamically.

    Returns
    -------
    NxSignalProperty
        A property-like descriptor that, when accessed, returns the underlying NxSignal object.

    Notes
    -----
    - A typical usage looks like:
      
python
      @nx_with_signals
      class MyClass:
          @nx_signal
          def some_event(self):
              # The body here is never called at runtime.
              pass

    - You can then emit the signal via self.some_event.emit(...).
    - The actual signal object is created and cached when first accessed.

    See Also
    --------
    nx_with_signals : Decorates a class to enable signal/slot features.
    NxSignal : The class representing an actual signal (internal usage).
    """

    sig_name = func.__name__

    def wrap(self):
        """Wrap signal"""

        if not hasattr(self, f"_{sig_name}"):
            setattr(self, f"_{sig_name}", NxSignal())

        return getattr(self, f"_{sig_name}")

    return NxSignalProperty(wrap, sig_name)


def nx_slot(func):
    """
    Decorator that marks a method as a 'slot' for PynneX. Slots can be either synchronous
    or asynchronous, and PynneX automatically handles cross-thread invocation.

    If this decorated method is called directly (i.e., not via a signal’s emit())
    from a different thread than the slot’s home thread/event loop, PynneX also ensures
    that the call is dispatched (queued) correctly to the slot's thread. This guarantees
    consistent and thread-safe execution whether the slot is triggered by a signal emit
    or by a direct method call.

    Parameters
    ----------
    func : function or coroutine
        The method to be decorated as a slot. If it's a coroutine (async def), PynneX
        treats it as an async slot.

    Returns
    -------
    function or coroutine
        A wrapped version of the original slot, with added thread/loop handling for
        cross-thread invocation.

    Notes
    -----
    - If the slot is synchronous and the emitter (or caller) is in another thread,
      PynneX queues a function call to the slot’s thread/event loop.
    - If the slot is asynchronous (async def), PynneX ensures that the coroutine
      is scheduled on the correct event loop.
    - The threading affinity and event loop references are automatically assigned
      by @nx_with_signals or @nx_with_worker when the class instance is created.

    Examples
    --------
    @nx_with_signals
    class Receiver:
        @nx_slot
        def on_data_received(self, data):
            print("Synchronous slot called in a thread-safe manner.")

        @nx_slot
        async def on_data_received_async(self, data):
            await asyncio.sleep(1)
            print("Asynchronous slot called in a thread-safe manner.")
    """

    is_coroutine = asyncio.iscoroutinefunction(func)

    if is_coroutine:

        @functools.wraps(func)
        async def wrap(self, *args, **kwargs):
            """Wrap coroutine slots"""

            try:
                asyncio.get_running_loop()
            except RuntimeError:
                nx_log_and_raise_error(
                    logger,
                    RuntimeError,
                    "No running loop in coroutine.",
                )

            if not hasattr(self, NxSignalConstants.THREAD):
                self._nx_thread = threading.current_thread()

            if not hasattr(self, NxSignalConstants.LOOP):
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
            """Wrap regular slots"""

            if not hasattr(self, NxSignalConstants.THREAD):
                self._nx_thread = threading.current_thread()

            if not hasattr(self, NxSignalConstants.LOOP):
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


def nx_with_signals(cls=None, *, loop=None, weak_default=True):
    """
    Class decorator that enables the use of PynneX-based signals and slots.
    When applied, it assigns an event loop and a thread affinity to each instance,
    providing automatic threading support for signals and slots.

    Parameters
    ----------
    cls : class, optional
        The class to be decorated. If not provided, returns a decorator that can be
        applied to a class.
    loop : asyncio.AbstractEventLoop, optional
        An event loop to be assigned to the instances of the decorated class. If omitted,
        PynneX attempts to retrieve the current running loop. If none is found, it raises
        an error or creates a new event loop in some contexts.
    weak_default : bool, optional
        Determines the default value for weak connections on signals from instances of
        this class. If True, any signal connect call without a specified weak argument
        will store a weak reference to the receiver. Defaults to True.

    Returns
    -------
    class
        The decorated class, now enabled with signal/slot features.

    Notes
    -----
    - This decorator modifies the class’s __init__ method to automatically assign
      _nx_thread, _nx_loop, _nx_affinity, and _nx_weak_default.
    - Typically, you’ll write:
      
python
      @nx_with_signals
      class MyClass:
          @nx_signal
          def some_event(self):
              pass

      Then create an instance: obj = MyClass(), and connect signals as needed.
    - The weak_default argument can be overridden on a per-connection basis
      by specifying weak=True or weak=False in connect.

    Example
    -------
    @nx_with_signals(loop=some_asyncio_loop, weak_default=False)
    class MySender:
        @nx_signal
        def message_sent(self):
            pass
    """

    def wrap(cls):
        """Wrap class with signals"""

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
