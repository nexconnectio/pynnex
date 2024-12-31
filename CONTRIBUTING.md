Thank you for your interest in contributing to `PynneX`! This document provides guidelines and instructions for contributing to the project.

## Important Notice
Please note that while we greatly appreciate and welcome contributions, this project does not provide financial compensation for contributions. Any donations or sponsorships received are used solely for project maintenance and improvement, and are not distributed to individual contributors.

By contributing to this project, you agree that:
- Your contributions are voluntary
- You are granting your contributions under the project's MIT License
- You are not entitled to financial compensation for your contributions
- You understand that any project donations/sponsorships are used for project maintenance only

## Development Setup

1. Fork and clone the repository:
```bash
git clone https://github.com/nexconnectio/pynnex.git
cd pynnex
```

2. Create a virtual environment and install development dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

## Code Style

We follow these coding conventions:
- PEP 8 style guide
- Maximum line length of 88 characters (Black default)
- Type hints for function arguments and return values
- Docstrings for all public modules, functions, classes, and methods

## Testing

Run the test suite before submitting changes:
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=pynnex

# Run specific test file
pytest tests/unit/test_signal.py

# Enable debug logging during tests
PYNNEX_DEBUG=1 pytest
```

## Pull Request Process

1. Create a new branch for your feature or bugfix:
```bash
git checkout -b feature-name
```

2. Make your changes and commit them:
```bash
git add .
git commit -m "Description of changes"
```

3. Ensure your changes include:
   - Tests for any new functionality
   - Documentation updates if needed
   - No unnecessary debug prints or commented code
   - Type hints for new functions/methods

4. Push your changes and create a pull request:
```bash
git push origin feature-name
```

5. In your pull request description:
   - Describe what the changes do
   - Reference any related issues
   - Note any breaking changes
   - Include examples if applicable

## Development Guidelines

### Adding New Features

1. Start with tests
2. Implement the feature
3. Update documentation
4. Add examples if applicable

### Debug Logging

Use appropriate log levels:
```python
import logging

logger = logging.getLogger(__name__)

# Debug information
logger.debug("Detailed connection info")

# Important state changes
logger.info("Signal connected successfully")

# Warning conditions
logger.warning("Multiple connections detected")

# Errors
logger.error("Failed to emit signal", exc_info=True)
```

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Focus on constructive criticism
- Accept feedback gracefully
- Put the project's best interests first

### Enforcement

Violations of the code of conduct may result in:
1. Warning
2. Temporary ban
3. Permanent ban

Report issues to project maintainers via email.

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).
