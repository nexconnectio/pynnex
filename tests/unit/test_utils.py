# tests/unit/test_utils.py

# pylint: disable=no-member
# pylint: disable=unused-argument
# pylint: disable=redefined-outer-name

"""Test utils"""

from unittest.mock import MagicMock
import logging
import pytest
from pynnex.utils import nx_log_and_raise_error


@pytest.fixture
def mock_logger():
    """Mock logger"""

    return MagicMock(spec=logging.Logger)


def test_valid_exception_class(mock_logger):
    """Test with valid exception class"""

    with pytest.raises(ValueError) as exc_info:
        nx_log_and_raise_error(mock_logger, ValueError, "test message")

    assert str(exc_info.value) == "test message"
    mock_logger.error.assert_called_once_with("test message", exc_info=True)
    mock_logger.warning.assert_not_called()


def test_invalid_exception_class(mock_logger):
    """Test with invalid exception class"""

    with pytest.raises(TypeError) as exc_info:
        nx_log_and_raise_error(mock_logger, str, "test message")

    assert str(exc_info.value) == "exception_class must be a subclass of Exception"
    mock_logger.error.assert_not_called()
    mock_logger.warning.assert_not_called()


def test_known_test_exception(mock_logger):
    """Test with known test exception"""

    with pytest.raises(ValueError) as exc_info:
        nx_log_and_raise_error(
            mock_logger, ValueError, "test message", known_test_exception=True
        )

    assert str(exc_info.value) == "test message"
    mock_logger.warning.assert_called_once_with(
        "test message (Known test scenario, no full stack trace)"
    )
    mock_logger.error.assert_not_called()


def test_custom_exception(mock_logger):
    """Test with custom exception class"""

    class CustomError(Exception):
        """Custom error"""

    with pytest.raises(CustomError) as exc_info:
        nx_log_and_raise_error(mock_logger, CustomError, "test message")

    assert str(exc_info.value) == "test message"
    mock_logger.error.assert_called_once_with("test message", exc_info=True)
    mock_logger.warning.assert_not_called()


def test_with_actual_logger(caplog):
    """Test with actual logger to verify log output"""

    logger = logging.getLogger("test")

    with pytest.raises(ValueError), caplog.at_level(logging.ERROR):
        nx_log_and_raise_error(logger, ValueError, "test actual logger")

    assert "test actual logger" in caplog.text
