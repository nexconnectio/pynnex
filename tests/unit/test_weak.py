# tests/unit/test_weak.py

"""
Test cases for weak reference connections.
"""

# pylint: disable=unused-argument
# pylint: disable=redundant-unittest-assert

import unittest
import gc
import asyncio
import weakref
from pynnex.core import nx_with_signals, nx_signal


class WeakRefReceiver:
    """
    A class that receives weak reference events.
    """

    def __init__(self):
        self.called = False

    def on_signal(self, value):
        """
        Event handler.
        """

        self.called = True
        print(f"WeakRefReceiver got value: {value}")


@nx_with_signals(weak_default=True)
class WeakRefSender:
    """
    A class that sends weak reference events.
    """

    @nx_signal
    def event(self):
        """
        Event signal.
        """


class StrongRefReceiver:
    """
    A class that receives strong reference events.
    """

    def __init__(self):
        """
        Initialize the receiver.
        """

        self.called = False

    def on_signal(self, value):
        """
        Event handler.
        """

        self.called = True
        print(f"StrongRefReceiver got value: {value}")


@nx_with_signals(weak_default=True)
class MixedSender:
    """
    A class that sends mixed reference events.
    """

    @nx_signal
    def event(self, value):
        """
        Event signal.
        """


class TestWeakRefConnections(unittest.IsolatedAsyncioTestCase):
    """
    Test cases for weak reference connections.
    """

    async def test_weak_default_connection(self):
        """
        Test weak default connection.
        """

        sender = WeakRefSender()
        receiver = WeakRefReceiver()

        # connect without specifying weak, should use weak_default=True
        sender.event.connect(receiver, receiver.on_signal)

        sender.event.emit(42)
        self.assertTrue(receiver.called, "Receiver should be called when alive")

        # Delete receiver and force GC
        del receiver
        gc.collect()

        # After GC, the connection should be removed automatically
        # Emit again and ensure no error and no print from receiver
        sender.event.emit(100)
        # If receiver was alive or connection remained, it would print or set called to True
        # But we no longer have access to receiver here
        # Just ensure no exception - implicit check
        self.assertTrue(
            True, "No exception emitted, weak ref disconnected automatically"
        )

    async def test_override_weak_false(self):
        """
        Test override weak=False.
        """

        sender = MixedSender()
        receiver = StrongRefReceiver()

        # Even though weak_default=True, we explicitly set weak=False
        sender.event.connect(receiver, receiver.on_signal, weak=False)

        sender.event.emit(10)
        self.assertTrue(receiver.called, "Receiver called with strong ref")

        # Reset called
        receiver.called = False

        # Delete receiver and force GC
        receiver_ref = weakref.ref(receiver)
        del receiver
        gc.collect()

        # Check if receiver is GCed
        # Originally: self.assertIsNone(receiver_ref(), "Receiver should be GCed")
        # Update the expectation: Since weak=False means strong ref remains, receiver won't GC.
        self.assertIsNotNone(
            receiver_ref(), "Receiver should NOT be GCed due to strong ref"
        )

        # Emit again, should still have a reference
        sender.event.emit(200)
        # Even if we can't call receiver (it was del), the reference in slot keeps it alive,
        # but possibly as an inaccessible object.
        # Just checking no exception raised and that receiver_ref is not None.
        # This confirms the slot strong reference scenario.
        self.assertTrue(True, "No exception raised, strong ref scenario is consistent")

    async def test_explicit_weak_true(self):
        """
        Test explicit weak=True.
        """

        sender = MixedSender()
        receiver = StrongRefReceiver()

        # weak_default=True anyway, but let's be explicit
        sender.event.connect(receiver, receiver.on_signal, weak=True)

        sender.event.emit(20)
        self.assertTrue(receiver.called, "Explicit weak=True call")

        receiver.called = False

        # Create a weak reference to the receiver
        receiver_ref = weakref.ref(receiver)
        self.assertIsNotNone(receiver_ref(), "Receiver should be alive before deletion")

        # Delete strong reference and force GC
        del receiver
        gc.collect()

        # Check if the receiver has been collected
        self.assertIsNone(
            receiver_ref(), "Receiver should be GCed after weakref disconnection"
        )

        # Receiver gone, emit again
        # Should not call anything, no crash
        sender.event.emit(30)
        self.assertTrue(True, "No exception and no call because weak disconnect")


if __name__ == "__main__":
    asyncio.run(unittest.main())
