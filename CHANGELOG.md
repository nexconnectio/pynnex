<!-- CHANGELOG.md -->

# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2025-01-04

### Changed
- Removed nx_ prefix from public API imports for better consistency:
  - Updated imports in examples and tests to use unprefixed versions (signal, with_signals, etc.)
  - Maintained nx_ prefix in internal implementation files
  - Improved API documentation with detailed method descriptions

## [1.0.1] - 2025-01-02

### Changed
- Improved documentation structure and readability:
  - Improved usage guide structure and navigation
  - Updated example descriptions and use cases
- Enhanced decorator alias usage clarity

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
