<!-- docs/logging.md -->

# Logging Guidelines

## Requirements
Pynnex requires Python 3.10 or higher.

## Logging Structure
Pynnex uses Python's standard logging module with the following hierarchy:

- `pynnex`: Root logger for all Pynnex logs
  - `pynnex.signal`: Signal-related events
    - `pynnex.signal.trace`: Detailed signal debugging information
  - `pynnex.slot`: Slot-related events
    - `pynnex.slot.trace`: Detailed slot debugging information

## Logging Levels
Each logger uses the following levels:

- `DEBUG`: Detailed information about signal-slot connections and emissions
- `INFO`: Important state changes and major events
- `WARNING`: Potential issues that don't affect functionality
- `ERROR`: Exceptions and failures

## Configuration

### Basic Configuration
To enable debug logging in tests:
```bash
PYNNEX_DEBUG=1 pytest
```

Configure logging in your application:
```python
import logging
logging.getLogger('pynnex').setLevel(logging.INFO)
```

### Trace Logging
For detailed debugging, you can selectively enable trace loggers:
```python
# Enable detailed signal tracing
logging.getLogger('pynnex.signal.trace').setLevel(logging.DEBUG)

# Enable detailed slot tracing
logging.getLogger('pynnex.slot.trace').setLevel(logging.DEBUG)
```

Trace loggers provide additional information such as:
- Detailed signal emission state
- Connection details and receiver status
- Slot invocation timing and queue information
- Method binding and weak reference status

Note: By default, logging levels are determined by your application's logging configuration.
