# src/pynnex/contrib/extensions/property.py

# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments
# pylint: disable=no-else-return
# pylint: disable=unnecessary-dunder-call

"""
This module provides a property decorator that allows for thread-safe access to properties.
"""

import asyncio
import threading
import logging
from pynnex.core import NxEmitterConstants
from pynnex.utils import nx_log_and_raise_error

logger = logging.getLogger(__name__)


class NxProperty(property):
    """
    Thread-safe property decorator for emitter-enabled classes.

    Parameters
    ----------
    fget : callable, optional
        Getter function.
    fset : callable, optional
        Setter function.
    fdel : callable, optional
        Deleter function.
    doc : str, optional
        Property docstring.
    notify : NxEmitter, optional
        Emitter to emit on value change.

    Notes
    -----
    - Ensures thread-safe access via event loop
    - Automatically queues operations across threads
    - Emits notify emitter on value changes
    - Uses '_private_name' for storage

    See Also
    --------
    nx_with_emitters : Class decorator for emitter/listener features
    nx_property : Property decorator factory
    """

    def __init__(self, fget=None, fset=None, fdel=None, doc=None, notify=None):
        super().__init__(fget, fset, fdel, doc)
        self.notify = notify
        self._private_name = None

    def __set_name__(self, owner, name):
        self._private_name = f"_{name}"

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        if self.fget is None:
            raise AttributeError("unreadable attribute")

        if (
            hasattr(obj, NxEmitterConstants.THREAD)
            and threading.current_thread() != obj._nx_thread
        ):
            # Dispatch to event loop when accessed from a different thread
            future = asyncio.run_coroutine_threadsafe(
                self._get_value(obj), obj._nx_loop
            )

            return future.result()
        else:
            return self._get_value_sync(obj)

    def __set__(self, obj, value):
        if self.fset is None:
            raise AttributeError("can't set attribute")

        # DEBUG: Thread safety verification logs
        # logger.debug(f"thread: {obj._nx_thread} current thread: {threading.current_thread()} loop: {obj._nx_loop}")

        if (
            hasattr(obj, NxEmitterConstants.THREAD)
            and threading.current_thread() != obj._nx_thread
        ):
            # Queue the setter call in the object's event loop
            future = asyncio.run_coroutine_threadsafe(
                self._set_value(obj, value), obj._nx_loop
            )

            # Wait for completion like listener direct calls
            return future.result()
        else:
            return self._set_value_sync(obj, value)

    def _set_value_sync(self, obj, value):
        old_value = self.__get__(obj, type(obj))
        result = self.fset(obj, value)

        if self.notify is not None and old_value != value:
            try:
                emitter_name = getattr(self.notify, "emitter_name", None)

                if emitter_name:
                    emitter = getattr(obj, emitter_name)
                    emitter.emit(value)
                else:
                    nx_log_and_raise_error(
                        logger,
                        AttributeError,
                        f"No emitter_name found in {self.notify}",
                    )

            except AttributeError as e:
                logger.warning(
                    "Property %s notify attribute not found. Error: %s",
                    self._private_name,
                    str(e),
                )

        return result

    async def _set_value(self, obj, value):
        return self._set_value_sync(obj, value)

    def _get_value_sync(self, obj):
        return self.fget(obj)

    async def _get_value(self, obj):
        return self._get_value_sync(obj)

    def setter(self, fset):
        """
        Set the setter for the property.
        """
        return type(self)(self.fget, fset, self.fdel, self.__doc__, self.notify)


def nx_property(func=None, *, notify=None):
    """
    Decorator to create a thread-safe property.

    Parameters
    ----------
    notify : NxEmitter, optional
        Emitter to emit on value change.

    Returns
    -------
    NxProperty
        Thread-safe property descriptor.

    Notes
    -----
    - Ensures thread-safe access via event loop
    - Emits notify emitter when value changes
    - Must be used within @nx_with_emitters class

    See Also
    --------
    NxProperty : Base property implementation
    nx_with_emitters : Required class decorator
    """

    if func is not None:
        return NxProperty(fget=func, notify=notify)

    def decorator(func):
        return NxProperty(fget=func, notify=notify)

    return decorator
