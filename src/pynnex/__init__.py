"""
Pynnex - Python Signal/Slot Implementation
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

# Alias for core functions
from pynnex.core import (
    nx_with_signals as with_signals,
    nx_signal as signal,
    nx_slot as slot
)
from .contrib.patterns.worker.decorators import nx_with_worker as with_worker


__version__ = "0.5.0"

__all__ = [
    "nx_with_signals",
    "nx_signal",
    "nx_slot",
    "nx_with_worker",
    "nx_property",
    "nx_log_and_raise_error",
    "nx_graceful_shutdown",
    "NxConnectionType",
    "NxSignalConstants",    
    "with_signals",
    "signal",
    "slot",
    "with_worker",
]
