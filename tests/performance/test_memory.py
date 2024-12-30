# tests/performance/test_memory.py

# pylint: disable=no-member
# pylint: disable=redefined-outer-name
# pylint: disable=unused-variable


"""
Test cases for memory usage.
"""

import pytest
from pynnex import nx_with_signals, nx_signal, nx_slot


def create_complex_signal_chain():
    """Create a complex signal chain"""

    @nx_with_signals
    class Sender:
        """Sender class"""

        @nx_signal
        def signal(self):
            """Signal method"""

    @nx_with_signals
    class Receiver:
        """Receiver class"""

        @nx_slot
        def slot(self, value):
            """Slot method"""

    sender = Sender()
    receivers = [Receiver() for _ in range(100)]
    for r in receivers:
        sender.signal.connect(r, r.slot)
    return sender


@pytest.mark.performance
@pytest.mark.asyncio
async def test_memory_usage():
    """Test memory usage"""
    # Create and delete signal/slot pairs repeatedly
    for _ in range(1000):
        sender = create_complex_signal_chain()
        sender.signal.disconnect()
