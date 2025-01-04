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
import threading
from typing import Callable, Optional
from pynnex.utils import nx_log_and_raise_error

logger = logging.getLogger(__name__)


class NxSignalConstants:
    """Constants for signal-slot communication."""

    FROM_EMIT = "_nx_from_emit"
    THREAD = "_nx_thread"
    LOOP = "_nx_loop"
    AFFINITY = "_nx_affinity"
    WEAK_DEFAULT = "_nx_weak_default"


_nx_from_emit = contextvars.ContextVar(NxSignalConstants.FROM_EMIT, default=False)


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

        if not self.is_bound:
            # standalone function
            return self.slot_func

        receiver = self.get_receiver()

        if receiver is None:
            # weak ref is dead
            return None

        # Restore bound method
        if self.is_weak:
            # slot_func is an unbound function, so reconstruct the bound method using __get__
            return self.slot_func.__get__(receiver, type(receiver))

        # For instance of strong reference, slot_func may be already bound method,
        # or it may be bound method at connect time.
        # In either case, it can be returned directly.
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
                        "[NxSignal][_wrap_standalone_function] No running event loop found. "
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

    logger.debug(
        "[NxSignal][_determine_connection_type] conn_type=%s receiver=%s owner=%s is_coro_slot=%s",
        conn_type,
        receiver,
        owner,
        is_coro_slot,
    )

    if conn_type == NxConnectionType.AUTO_CONNECTION:
        if is_coro_slot:
            actual_conn_type = NxConnectionType.QUEUED_CONNECTION
            logger.debug(
                "[NxSignal][_determine_connection_type] actual_conn_type=%s reason=is_coro_slot",
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
                        "[NxSignal][_determine_connection_type] actual_conn_type=%s reason=same_thread",
                        actual_conn_type,
                    )
                else:
                    actual_conn_type = NxConnectionType.QUEUED_CONNECTION
                    logger.debug(
                        "[NxSignal][_determine_connection_type] actual_conn_type=%s reason=different_thread",
                        actual_conn_type,
                    )
            else:
                actual_conn_type = NxConnectionType.DIRECT_CONNECTION
                logger.debug(
                    "[NxSignal][_determine_connection_type] actual_conn_type=%s reason=no_receiver or invalid thread or affinity "
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

        logger.debug(
            "[NxSignal][connect][START] class=%s receiver_or_slot=%s slot=%s",
            self.__class__.__name__,
            receiver_or_slot,
            slot,
        )

        if weak is None and self.owner is not None:
            weak = getattr(self.owner, NxSignalConstants.WEAK_DEFAULT, False)

        if slot is None:
            if not callable(receiver_or_slot):
                nx_log_and_raise_error(
                    logger,
                    TypeError,
                    "[NxSignal][connect] receiver_or_slot must be callable.",
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
                    "[NxSignal][connect] Receiver cannot be None.",
                )

            if not callable(slot):
                nx_log_and_raise_error(
                    logger, TypeError, "[NxSignal][connect] Slot must be callable."
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

        if hasattr(slot, "__self__") and slot.__self__ is not None:
            # It's a bound method
            slot_instance = slot.__self__
            slot_func = slot.__func__
            is_bound = True

            if weak and receiver is not None:
                receiver_ref = weakref.ref(slot_instance, self._cleanup_on_ref_dead)
                conn = NxConnection(
                    receiver_ref,
                    slot_func,
                    conn_type,
                    is_coro_slot,
                    is_bound,
                    True,
                    one_shot,
                )
            else:
                # strong ref
                conn = NxConnection(
                    slot_instance,
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
            is_bound = False
            conn = NxConnection(
                None, slot, conn_type, is_coro_slot, is_bound, False, one_shot
            )

        logger.debug("[NxSignal][connect][END] conn=%s", conn)

        with self.connections_lock:
            self.connections.append(conn)

    def _cleanup_on_ref_dead(self, ref):
        """Cleanup connections on weak reference death."""

        # ref is a weak reference to the receiver
        # Remove connections associated with the dead receiver
        with self.connections_lock:
            self.connections = [
                conn for conn in self.connections if conn.receiver_ref is not ref
            ]

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
                # No receiver or slot specified, remove all connections.
                count = len(self.connections)
                self.connections.clear()

                return count

            original_count = len(self.connections)
            new_connections = []

            logger.debug(
                "[NxSignal][disconnect][START] receiver: %s slot: %s original_count: %s",
                receiver,
                slot,
                original_count,
            )

            # In case slot is a bound method, convert it to an unbound function.
            slot_unbound = _extract_unbound_function(slot)

            for conn in self.connections:
                # If the connection does not reference a receiver (standalone function)
                # and a slot is specified, check if the connected func_or_slot matches the given slot.
                receiver_match = receiver is None or conn.get_receiver() == receiver
                slot_match = (
                    slot is None
                    or conn.slot_func == slot_unbound
                    or getattr(conn.slot_func, "__wrapped__", None) == slot_unbound
                )

                if receiver_match and slot_match:
                    # remove this connection
                    logger.debug(
                        "[NxSignal][disconnect][MATCHED] func: %s receiver_match: %s slot_match: %s",
                        conn.slot_func,
                        receiver_match,
                        slot_match,
                    )
                    continue

                # If the connection was not matched by the given criteria, keep it.
                logger.debug(
                    "[NxSignal][disconnect][NOT MATCHED] func: %s", conn.slot_func
                )
                new_connections.append((conn))

            self.connections = new_connections
            disconnected = original_count - len(self.connections)

            logger.debug(
                "[NxSignal][disconnect][END] disconnected: %s",
                disconnected,
            )

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

        logger.debug("[NxSignal][emit][START]")

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

                logger.debug(
                    "[NxSignal][emit] slot=%s receiver=%s conn_type=%s",
                    getattr(slot_to_call, "__name__", slot_to_call),
                    conn.get_receiver(),
                    actual_conn_type,
                )

                try:
                    if actual_conn_type == NxConnectionType.DIRECT_CONNECTION:
                        logger.debug("[NxSignal][emit][DIRECT] calling slot directly")
                        result = slot_to_call(*args, **kwargs)
                        logger.debug(
                            "[NxSignal][emit][DIRECT] result=%s result_type=%s",
                            result,
                            type(result),
                        )
                    else:
                        # Handle QUEUED CONNECTION
                        receiver = conn.get_receiver()

                        if receiver is not None:
                            receiver_loop = getattr(
                                receiver, NxSignalConstants.LOOP, None
                            )
                            receiver_thread = getattr(
                                receiver, NxSignalConstants.THREAD, None
                            )

                            if not receiver_loop:
                                logger.error(
                                    "[NxSignal][emit][QUEUED] No event loop found for receiver. receiver=%s",
                                    receiver,
                                    stack_info=True,
                                )
                                continue
                        else:
                            try:
                                receiver_loop = asyncio.get_running_loop()
                            except RuntimeError:
                                nx_log_and_raise_error(
                                    logger,
                                    RuntimeError,
                                    "[NxSignal][emit][QUEUED] No running event loop found for queued connection.",
                                )

                            receiver_thread = None

                        if not receiver_loop.is_running():
                            logger.warning(
                                "[NxSignal][emit][QUEUED] receiver loop not running. Signals may not be delivered. receiver=%s",
                                receiver.__class__.__name__,
                            )
                            continue

                        if receiver_thread and not receiver_thread.is_alive():
                            logger.warning(
                                "[NxSignal][emit][QUEUED] The receiver's thread is not alive. Signals may not be delivered. receiver=%s",
                                receiver.__class__.__name__,
                            )

                        logger.debug(
                            "[NxSignal][emit][QUEUED] slot=%s is_coroutine=%s",
                            getattr(slot_to_call, "__name__", slot_to_call),
                            conn.is_coro_slot,
                        )

                        def dispatch(
                            is_coro_slot=conn.is_coro_slot,
                            slot_to_call=slot_to_call,
                        ):
                            logger.debug(
                                "[NxSignal][emit][QUEUED][dispatch] calling slot=%s",
                                getattr(slot_to_call, "__name__", slot_to_call),
                            )

                            if is_coro_slot:
                                returned = asyncio.create_task(
                                    slot_to_call(*args, **kwargs)
                                )
                            else:
                                returned = slot_to_call(*args, **kwargs)

                            logger.debug(
                                "[NxSignal][emit][QUEUED][dispatch] returned=%s type=%s",
                                returned,
                                type(returned),
                            )

                            return returned

                        receiver_loop.call_soon_threadsafe(dispatch)

                except Exception as e:
                    logger.error(
                        "[NxSignal][emit] error in emission: %s", e, exc_info=True
                    )

                if conn.is_one_shot:
                    with self.connections_lock:
                        if conn in self.connections:
                            self.connections.remove(conn)

        finally:
            _nx_from_emit.reset(token)

        logger.debug("[NxSignal][emit][END]")


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
    Decorator that defines a signal attribute within a class decorated by `@nx_with_signals`.
    The decorated function name is used as the signal name, and it provides a lazy-initialized
    `NxSignal` instance.

    Parameters
    ----------
    func : function
        A placeholder function that helps to define the signal's name and docstring. The
        function body is ignored at runtime, as the signal object is created and stored
        dynamically.

    Returns
    -------
    NxSignalProperty
        A property-like descriptor that, when accessed, returns the underlying `NxSignal` object.

    Notes
    -----
    - A typical usage looks like:
      ```python
      @nx_with_signals
      class MyClass:
          @nx_signal
          def some_event(self):
              # The body here is never called at runtime.
              pass
      ```
    - You can then emit the signal via `self.some_event.emit(...)`.
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

    If this decorated method is called directly (i.e., not via a signal’s `emit()`)
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
    - If the slot is asynchronous (`async def`), PynneX ensures that the coroutine
      is scheduled on the correct event loop.
    - The threading affinity and event loop references are automatically assigned
      by `@nx_with_signals` or `@nx_with_worker` when the class instance is created.

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
                    "[NxSignal][nx_slot][wrap] No running loop in coroutine.",
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
                        "[NxSignal][nx_slot][wrap] No running event loop found.",
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
                        "[nx_slot][wrap] No running event loop found.",
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
        Determines the default value for `weak` connections on signals from instances of
        this class. If `True`, any signal `connect` call without a specified `weak` argument
        will store a weak reference to the receiver. Defaults to `True`.

    Returns
    -------
    class
        The decorated class, now enabled with signal/slot features.

    Notes
    -----
    - This decorator modifies the class’s `__init__` method to automatically assign
      `_nx_thread`, `_nx_loop`, `_nx_affinity`, and `_nx_weak_default`.
    - Typically, you’ll write:
      ```python
      @nx_with_signals
      class MyClass:
          @nx_signal
          def some_event(self):
              pass
      ```
      Then create an instance: `obj = MyClass()`, and connect signals as needed.
    - The `weak_default` argument can be overridden on a per-connection basis
      by specifying `weak=True` or `weak=False` in `connect`.

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
                        "[nx_with_signals][wrap][__init__] No running event loop found.",
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
