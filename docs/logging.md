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
  - `pynnex.worker`: Worker-related events

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

### Using dictConfig
For more advanced configuration, you can use Python's `logging.config.dictConfig`:

```python
import logging.config

config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - [%(filename)s:%(funcName)s] - %(levelname)s - %(message)s",
            "datefmt": "%H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "pynnex": {"level": "DEBUG", "handlers": ["console"]},
        "pynnex.emitter": {"level": "DEBUG", "handlers": ["console"]},
        "pynnex.emitter.trace": {"level": "DEBUG", "handlers": ["console"]},
        "pynnex.listener": {"level": "DEBUG", "handlers": ["console"]},
        "pynnex.listener.trace": {"level": "DEBUG", "handlers": ["console"]},
        "pynnex.worker": {"level": "DEBUG", "handlers": ["console"]},
    },
    "root": {
        "level": "DEBUG",
        "handlers": ["console"],
    },
}

logging.config.dictConfig(config)
```

This configuration:
- Sets up a console handler with timestamp and context information
- Enables DEBUG level logging for all pynnex loggers
- Uses a consistent format across all log messages

You can adjust the log levels and add additional handlers (like file handlers) as needed for your application.
