# tests/performance/test_memory.py

# pylint: disable=no-member
# pylint: disable=redefined-outer-name
# pylint: disable=unused-variable


"""
Test cases for memory usage.
"""

import pytest
from pynnex import with_emitters, emitter, listener


def create_complex_emitter_chain():
    """Create a complex emitter chain"""

    @with_emitters
    class Sender:
        """Sender class"""

        @emitter
        def emitter(self):
            """Emitter method"""

    @with_emitters
    class Receiver:
        """Receiver class"""

        @listener
        def listener(self, value):
            """Listener method"""

    sender = Sender()
    receivers = [Receiver() for _ in range(100)]
    for r in receivers:
        sender.emitter.connect(r, r.listener)
    return sender


@pytest.mark.performance
@pytest.mark.asyncio
async def test_memory_usage():
    """Test memory usage"""
    # Create and delete emitter/listener pairs repeatedly
    for _ in range(1000):
        sender = create_complex_emitter_chain()
        sender.emitter.disconnect()
