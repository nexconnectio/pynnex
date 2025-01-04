# tests/integration/test_thread_safety.py

# pylint: disable=unused-argument

"""
Test cases for thread safety of PynneX.
"""

import unittest
import threading
import gc
from pynnex import with_signals, signal


@with_signals
class SafeSender:
    """
    A class that sends events.
    """

    @signal
    def event(self, value):
        """
        Event signal.
        """


class SafeReceiver:
    """
    A class that receives events.
    """

    def __init__(self, name=None):
        self.called = 0
        self.name = name

    def on_event(self, value):
        """
        Event handler.
        """

        self.called += 1


class TestThreadSafe(unittest.IsolatedAsyncioTestCase):
    """
    Test cases for thread safety of PynneX.
    """

    async def test_thread_safety(self):
        """
        Test thread safety of PynneX.
        """

        sender = SafeSender()
        receiver = SafeReceiver("strong_ref")

        # regular connection
        sender.event.connect(receiver, receiver.on_event, weak=False)

        # weak reference connection
        weak_receiver = SafeReceiver("weak_ref")
        sender.event.connect(weak_receiver, weak_receiver.on_event, weak=True)

        # additional receivers
        extra_receivers = [SafeReceiver(f"extra_{i}") for i in range(10)]
        for r in extra_receivers:
            sender.event.connect(r, r.on_event, weak=False)

        # background thread to emit events
        def emit_task():
            """
            Background thread to emit events.
            """

            for i in range(1000):
                sender.event.emit(i)

        # thread to connect/disconnect repeatedly
        def connect_disconnect_task():
            """
            Thread to connect/disconnect repeatedly.
            """

            # randomly connect/disconnect one of extra_receivers
            for i in range(500):
                idx = i % len(extra_receivers)
                r = extra_receivers[idx]

                if i % 2 == 0:
                    sender.event.connect(r, r.on_event, weak=False)
                else:
                    sender.event.disconnect(r, r.on_event)

        # thread to try to GC weak_receiver
        def gc_task():
            """
            Thread to try to GC weak_receiver.
            """

            nonlocal weak_receiver
            for i in range(100):
                if i == 50:
                    # release weak_receiver reference and try to GC
                    del weak_receiver
                    gc.collect()
                else:
                    # randomly emit events
                    sender.event.emit(i)

        threads = []
        # multiple threads to perform various tasks
        threads.append(threading.Thread(target=emit_task))
        threads.append(threading.Thread(target=connect_disconnect_task))
        threads.append(threading.Thread(target=gc_task))

        # start threads
        for t in threads:
            t.start()

        # wait for all threads to finish
        for t in threads:
            t.join()

        # check: strong_ref receiver should have been called
        self.assertTrue(
            receiver.called > 0,
            f"Strong ref receiver should have been called. Called={receiver.called}",
        )

        # some extra_receivers may have been connected/disconnected repeatedly
        # if at least one of them has been called, it's normal
        called_counts = [r.called for r in extra_receivers]
        self.assertTrue(
            any(c > 0 for c in called_counts),
            "At least one extra receiver should have been called.",
        )

        # weak_receiver can be GCed. If it is GCed, the receiver will not be called anymore.
        # weak_receiver itself is GCed, so it is not accessible. In this case, it is simply checked that it works without errors.
        # Here, it is simply checked that the code does not raise an exception and terminates normally.
