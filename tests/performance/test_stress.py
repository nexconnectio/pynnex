# tests/performance/test_stress.py

# pylint: disable=no-member
# pylint: disable=redefined-outer-name
# pylint: disable=unused-variable

"""
Test cases for stress testing.
"""

import asyncio
import logging
import pytest
from pynnex import nx_with_signals, nx_signal, nx_slot, nx_graceful_shutdown

logger = logging.getLogger(__name__)


async def graceful_shutdown():
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


@pytest.mark.asyncio
async def test_heavy_signal_load():
    """Test heavy signal load"""

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
        async def slot(self):
            """Slot method"""
            await asyncio.sleep(0.001)

    sender = Sender()
    receivers = [Receiver() for _ in range(100)]
    for r in receivers:
        sender.signal.connect(r, r.slot)

    for _ in range(1000):
        sender.signal.emit()

    # Graceful shutdown: ensure all tasks triggered by emit are completed
    await nx_graceful_shutdown()
