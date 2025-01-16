<!-- docs/logging.md -->

# Logging Guidelines

## Requirements
PynneX requires **Python 3.10** or higher, plus a running `asyncio` event loop for any async usage. 

## Logging Structure
PynneX uses Python's standard logging module with the following hierarchy:

- `pynnex`: Root logger for all PynneX logs
  - `pynnex.emitter`: Emitter-related events
    - `pynnex.emitter.trace`: Detailed emitter debugging information
  - `pynnex.listener`: Listener-related events
    - `pynnex.listener.trace`: Detailed listener debugging information

Regardless of which alias (signal-slot, publisher-subscriber, etc.) you use, all logs appear under `pynnex.emitter` or `pynnex.listener`. This is the internal naming convention for PynneX’s logging system.

## Logging Levels
Each logger uses the following levels:

- `DEBUG`: Detailed information about emitter-listener connections and emissions
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
# Enable detailed emitter tracing
logging.getLogger('pynnex.emitter.trace').setLevel(logging.DEBUG)

# Enable detailed listener tracing
logging.getLogger('pynnex.listener.trace').setLevel(logging.DEBUG)
```

Trace loggers provide additional information such as:
- Detailed emitter emission state
- Connection details and receiver status
- Listener invocation timing and queue information
- Method binding and weak reference status

Note: By default, logging levels are determined by your application's logging configuration.
