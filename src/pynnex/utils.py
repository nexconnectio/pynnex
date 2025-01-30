# src/pynnex/utils.py

"""
Utility functions for PynneX
"""

import logging

def nx_log_and_raise_error(
    logger: logging.Logger, exception_class, message, known_test_exception=False
):
    """
    Log the provided message and raise the specified exception.
    If known_test_exception is True, logs as WARNING without a full stack trace.
    Otherwise logs as ERROR with stack trace.
    """
    if not issubclass(exception_class, Exception):
        raise TypeError("exception_class must be a subclass of Exception")

    if known_test_exception:
        # intentional test exception -> warning level, no full stack trace
        logger.warning(f"{message} (Known test scenario, no full stack trace)")
    else:
        # regular exception -> error level, stack trace included
        logger.error(message, exc_info=True)

    raise exception_class(message)
