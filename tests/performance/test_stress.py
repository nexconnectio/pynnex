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
from pynnex import with_emitters, emitter, listener, nx_graceful_shutdown

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
async def test_heavy_emitter_load():
    """Test heavy emitter load"""

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
        async def listener(self):
            """Listener method"""
            await asyncio.sleep(0.001)

    sender = Sender()
    receivers = [Receiver() for _ in range(100)]
    for r in receivers:
        sender.emitter.connect(r, r.listener)

    for _ in range(1000):
        sender.emitter.emit()

    # Graceful shutdown: ensure all tasks triggered by emit are completed
    await nx_graceful_shutdown()
