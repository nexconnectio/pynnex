"""
Pynnex - A lightweight, pure-Python signal/slot library.
"""

from .core import (
    nx_with_signals,
    nx_signal,
    nx_slot,
    nx_graceful_shutdown,
    NxConnectionType,
    NxSignalConstants
)
from .utils import nx_log_and_raise_error
from .contrib.patterns.worker.decorators import nx_with_worker
from .contrib.extensions.property import nx_property

# Convenience aliases (without nx_ prefix)
with_signals = nx_with_signals
signal = nx_signal
slot = nx_slot
with_worker = nx_with_worker

__all__ = [
    'nx_with_signals', 'with_signals',
    'nx_signal', 'signal',
    'nx_slot', 'slot',
    'nx_with_worker', 'with_worker',
    'nx_property',
    'nx_log_and_raise_error',
    'nx_graceful_shutdown',
    'NxConnectionType',
    'NxSignalConstants'
]
