# tests/unit/test_weak.py

"""
Test cases for weak reference connections.
"""

import gc
import logging
import weakref
import pytest

from pynnex import with_emitters, emitter

logger = logging.getLogger(__name__)


class WeakRefReceiver:
    """
    A class that receives weak reference events.
    """

    def __init__(self):
        self.called = False

    def on_emitter(self, value):
        """
        Event handler.
        """

        self.called = True
        print(f"WeakRefReceiver got value: {value}")


@with_emitters(weak_default=True)
class Sender:
    """
    A class that sends weak reference events.
    """

    @emitter
    def event(self):
        """
        Event emitter.
        """


class Receiver:
    """
    A class that receives strong reference events.
    """

    def __init__(self):
        """
        Initialize the receiver.
        """

        self.called = False

    def on_emitter(self, value):
        """
        Event handler.
        """

        self.called = True
        print(f"StrongRefReceiver got value: {value}")


@with_emitters(weak_default=True)
class MixedSender:
    """
    A class that sends mixed reference events.
    """

    @emitter
    def event(self, value):
        """
        Event emitter.
        """


@pytest.mark.asyncio
async def test_weak_default_connection():
    """
    Test weak default connection.
    """
    sender = Sender()
    receiver = Receiver()

    # connect without specifying weak, should use weak_default=True
    sender.event.connect(receiver, receiver.on_emitter)

    sender.event.emit(42)
    assert receiver.called, "Receiver should be called when alive"

    # Delete receiver and force GC
    del receiver
    gc.collect()

    # After GC, the connection should be removed automatically
    sender.event.emit(100)

    assert True, "No exception emitted, weak ref disconnected automatically"


@pytest.mark.asyncio
async def test_override_weak_false():
    """
    Test override weak=False.
    """
    sender = MixedSender()
    receiver = Receiver()

    sender.event.connect(receiver, receiver.on_emitter, weak=False)

    sender.event.emit(10)
    assert receiver.called, "Receiver called with strong ref"

    receiver.called = False

    receiver_ref = weakref.ref(receiver)
    del receiver
    gc.collect()

    assert receiver_ref() is not None, "Receiver should NOT be GCed due to strong ref"

    sender.event.emit(200)
    assert True, "No exception raised, strong ref scenario is consistent"
