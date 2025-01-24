# src/pynnex/__init__.py

"""
PynneX - a Python library that offers a modern emitter-listener mechanism with seamless thread safety.
"""

from .core import (
    nx_with_emitters,
    nx_emitter,
    nx_listener,
    nx_graceful_shutdown,
    NxConnectionType,
    NxConnection,
    NxEmitterConstants,
    NxEmitter,
    NxEmitterObserver,
    _determine_connection_type,
)
from .utils import nx_log_and_raise_error
from .contrib.patterns.worker.decorators import nx_with_worker, NxWorkerConstants
from .contrib.extensions.property import nx_property

# Convenience aliases (without nx_ prefix)
with_emitters = nx_with_emitters
emitter = nx_emitter
listener = nx_listener
with_worker = nx_with_worker

with_signals = nx_with_emitters
signal = nx_emitter
slot = nx_listener

with_publishers = nx_with_emitters
publisher = nx_emitter
subscriber = nx_listener

__all__ = [
    "nx_with_emitters",
    "nx_emitter",
    "nx_listener",
    "with_emitters",
    "emitter",
    "listener",
    "with_signals",
    "signal",
    "slot",
    "with_publishers",
    "publisher",
    "subscriber",
    "nx_with_worker",
    "NxWorkerConstants",
    "with_worker",
    "nx_property",
    "nx_log_and_raise_error",
    "nx_graceful_shutdown",
    "NxConnectionType",
    "NxConnection",
    "NxEmitterConstants",
    "NxEmitter",
    "NxEmitterObserver",
    "_determine_connection_type",
]
