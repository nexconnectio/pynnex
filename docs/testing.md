<!-- docs/testing.md -->

# Testing Guide

## Overview
Pynnex requires Python 3.10 or higher and uses pytest for testing. Our test suite includes unit tests, integration tests, performance tests, and supports async testing.

## Test Structure
```
tests/
├── __init__.py
├── conftest.py          # Shared fixtures and configurations
├── unit/               # Unit tests
│   ├── __init__.py
│   ├── test_property.py
│   ├── test_signal.py
│   ├── test_slot.py
│   ├── test_utils.py
│   └── test_weak.py
├── integration/        # Integration tests
│   ├── __init__.py
│   ├── test_async.py
│   ├── test_threading.py
│   ├── test_with_signals.py
│   ├── test_worker_signal.py
│   ├── test_worker_queue.py
│   └── test_worker.py
└── performance/        # Performance and stress tests
    ├── __init__.py
    ├── test_stress.py
    └── test_memory.py
```

## Running Tests

### Basic Test Commands
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with very verbose output
pytest -vv

# Run with print statements visible
pytest -s

# Run specific test file
pytest tests/unit/test_signal.py

# Run specific test case
pytest tests/unit/test_signal.py -k "test_signal_disconnect_all"

# Run tests by marker
pytest -v -m asyncio
pytest -v -m performance  # Run performance tests only
```

### Performance Tests
Performance tests include stress testing and memory usage analysis. These tests are marked with the `@pytest.mark.performance` decorator.

```bash
# Run only performance tests
pytest -v -m performance

# Run specific performance test
pytest tests/performance/test_stress.py
pytest tests/performance/test_memory.py
```

Note: Performance tests might take longer to run and consume more resources than regular tests.

### Debug Mode
To enable debug logging during tests:
```bash
# Windows
set PYNNEX_DEBUG=1
pytest tests/unit/test_signal.py -v

# Linux/Mac
PYNNEX_DEBUG=1 pytest tests/unit/test_signal.py -v
```

### Test Coverage
To run tests with coverage report:
```bash
# Run tests with coverage
pytest --cov=pynnex

# Generate HTML coverage report
pytest --cov=pynnex --cov-report=html
```

## Async Testing Configuration

The project uses `pytest-asyncio` with `asyncio_mode = "auto"` to handle async fixtures and tests. This configuration allows for more flexible handling of async/sync code interactions, especially in worker-related tests where we need to manage both synchronous and asynchronous operations.

Key points:
- Async fixtures can yield values directly
- Both sync and async tests can use the same fixtures
- Worker thread initialization and cleanup are handled automatically
