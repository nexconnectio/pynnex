# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-12-28

### Added
- Initial release of Pynnex (rebranded from tsignal)
- Comprehensive signal-slot mechanism with Python 3.10+ features
- Core Features:
  - Robust signal-slot communication pattern
  - Thread-safe operations with automatic thread affinity
  - Full async/await support
  - Weak reference support for automatic cleanup
  - One-shot connections
  - Worker thread pattern
  - Simplified decorator aliases (@signal, @slot, @with_signals, @with_worker)
- Comprehensive test suite with 100% coverage
- Full documentation and examples

### Requirements
- Python 3.10 or higher (for stable asyncio operations)
