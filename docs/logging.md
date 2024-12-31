# Logging Guidelines

## Requirements
`PynneX` requires Python 3.10 or higher.

PynneX uses Python's standard logging module with the following levels:

- `DEBUG`: Detailed information about signal-slot connections and emissions
- `INFO`: Important state changes and major events
- `WARNING`: Potential issues that don't affect functionality
- `ERROR`: Exceptions and failures

To enable debug logging in tests:
```bash
PYNNEX_DEBUG=1 pytest
```

Configure logging in your application:
```python
import logging
logging.getLogger('pynnex').setLevel(logging.INFO)
```
