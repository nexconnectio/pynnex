# tests/unit/test_property.py

# pylint: disable=no-member
# pylint: disable=unnecessary-lambda
# pylint: disable=useless-with-lock

"""
Test cases for the property pattern.
"""

import asyncio
import threading
import logging
import pytest
from pynnex.contrib.extensions.property import nx_property
from pynnex import nx_signal, nx_with_signals


logger = logging.getLogger(__name__)


@nx_with_signals
class Temperature:
    """Temperature class for testing"""

    def __init__(self):
        super().__init__()
        self._celsius = -273

    @nx_signal
    def celsius_changed(self):
        """Signal for celsius change"""

    @nx_property(notify=celsius_changed)
    def celsius(self) -> float:
        """Getter for celsius"""
        return self._celsius

    @celsius.setter
    def celsius(self, value: float):
        """Setter for celsius"""
        self._celsius = value


@nx_with_signals
class ReadOnlyTemperature:
    """ReadOnlyTemperature class for testing"""

    def __init__(self):
        super().__init__()
        self._celsius = 0

    @nx_signal
    def celsius_changed(self):
        """Signal for celsius change"""

    @nx_property(notify=celsius_changed)
    def celsius(self) -> float:
        """Getter for celsius"""
        return self._celsius


@pytest.mark.asyncio
async def test_property_basic():
    """Test basic property get/set operations"""

    temp = Temperature()
    assert temp.celsius == -273

    # Test setter
    temp.celsius = 25
    assert temp.celsius == 25


@pytest.mark.asyncio
async def test_property_notification():
    """Test property change notifications"""

    temp = Temperature()
    received_values = []

    # Connect signal
    temp.celsius_changed.connect(lambda x: received_values.append(x))

    # Test initial value
    temp.celsius = 25
    assert temp.celsius == 25
    assert received_values == [25]

    # Clear received values
    received_values.clear()

    # Test no notification on same value
    temp.celsius = 25
    assert not received_values

    # Test notification on value change
    temp.celsius = 30
    assert received_values == [30]

    # Test multiple changes
    temp.celsius = 15
    temp.celsius = 45
    assert received_values == [30, 15, 45]


@pytest.mark.asyncio
async def test_property_read_only():
    """Test read-only property behavior"""

    temp = ReadOnlyTemperature()

    with pytest.raises(AttributeError, match="can't set attribute"):
        temp.celsius = 25


@pytest.mark.asyncio
async def test_property_thread_safety():
    """Test property thread safety and notifications across threads"""

    temp = Temperature()
    received_values = []
    task_completed = asyncio.Event()
    main_loop = asyncio.get_running_loop()

    def background_task():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def set_temp():
            temp.celsius = 15
            await asyncio.sleep(0.1)

        try:
            loop.run_until_complete(set_temp())
        finally:
            loop.close()
            main_loop.call_soon_threadsafe(task_completed.set)

    # Connect signal
    temp.celsius_changed.connect(lambda x: received_values.append(x))

    # Start background thread
    thread = threading.Thread(target=background_task)
    thread.start()

    await task_completed.wait()

    thread.join()

    assert temp.celsius == 15
    assert 15 in received_values


@pytest.mark.asyncio
async def test_property_multiple_threads():
    """Test property behavior with multiple threads"""

    temp = Temperature()
    received_values = []
    values_lock = threading.Lock()
    threads_lock = threading.Lock()
    num_threads = 5
    task_completed = asyncio.Event()
    threads_done = 0
    main_loop = asyncio.get_running_loop()

    def on_celsius_changed(value):
        """Handler for celsius change"""

        with values_lock:
            received_values.append(value)

    temp.celsius_changed.connect(on_celsius_changed)

    def background_task(value):
        """Background task for thread safety testing"""

        nonlocal threads_done
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            with threads_lock:
                temp.celsius = value
                loop.run_until_complete(asyncio.sleep(0.1))
        finally:
            loop.close()

            with threading.Lock():
                nonlocal threads_done
                threads_done += 1
                if threads_done == num_threads:
                    main_loop.call_soon_threadsafe(task_completed.set)

    threads = [
        threading.Thread(target=background_task, args=(i * 10,))
        for i in range(num_threads)
    ]

    # Start threads
    for thread in threads:
        thread.start()

    # Wait for task completion
    try:
        await asyncio.wait_for(task_completed.wait(), timeout=2.0)
    except asyncio.TimeoutError:
        logger.warning("Timeout waiting for threads")

    # Join threads
    for thread in threads:
        thread.join()

    await asyncio.sleep(0.2)

    expected_values = set(i * 10 for i in range(num_threads))
    received_set = set(received_values)

    assert (
        expected_values == received_set
    ), f"Expected {expected_values}, got {received_set}"

    # DEBUG: Connect debug handler to monitor value changes
    # temp.celsius_changed.connect(
    #     lambda x: logger.debug(f"Temperature value after change: {temp.celsius}")
    # )


@pytest.mark.asyncio
async def test_property_exception_handling():
    """Test property behavior with exceptions in signal handlers"""

    temp = Temperature()
    received_values = []

    def handler_with_exception(value):
        """Handler with exception"""
        received_values.append(value)
        raise ValueError("Test exception")

    def normal_handler(value):
        """Normal handler"""
        received_values.append(value * 2)

    # Connect multiple handlers
    temp.celsius_changed.connect(handler_with_exception)
    temp.celsius_changed.connect(normal_handler)

    # Exception in handler shouldn't prevent property update
    temp.celsius = 25

    assert temp.celsius == 25
    assert 25 in received_values  # First handler executed
    assert 50 in received_values  # Second handler executed
