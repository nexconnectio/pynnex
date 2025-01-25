<!-- CHANGELOG.md -->

# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.2] - 2025-01-24
- Improved worker pattern task cancellation
  - Simplify task result handling by moving it to try block
  - Remove redundant cancelled flag

### Changed

 [1.1.1] - 2025-01-24

### Changed
- Improved worker pattern implementation:
  - Added state machine (CREATED, STARTING, STARTED, STOPPING, STOPPED)
  - Added thread-safe task queue with pre-loop buffering
  - Replaced run() method with started signal listener pattern
  - Enhanced worker lifecycle management and cleanup
  - Added detailed debug logging for worker operations
- Updated documentation and examples:
  - Added complete runnable worker examples
  - Updated API documentation to reflect new worker pattern
  - Improved README examples with async context

## [1.1.0] - 2025-01-16

### Changed
- Renamed signal/slot terminology to emitter/listener across the API:
  - @signal → @emitter (aliases: @signal, @publisher)
  - @slot → @listener (aliases: @slot, @subscriber)
  - @with_signals → @with_emitters (aliases: @with_signals, @with_publishers)
  - Updated all documentation and examples
  - Kept old terms as aliases for backward compatibility
  - Updated logging namespaces from signal/slot to emitter/listener

## [1.0.4] - 2025-01-15

### Changed
- Handle task name safely

## [1.0.3] - 2025-01-15

### Changed
- Enhanced logging structure with hierarchical loggers:
  - Improved log message clarity and structure 
  - Added trace-level loggers (emitter.trace, listener.trace) for detailed debugging
- Improved weak reference handling:
  - Replaced manual bound method reconstruction with WeakMethod
  - Enhanced cleanup for weak method references

## [1.0.2] - 2025-01-04

### Changed
- Removed nx_ prefix from public API imports for better consistency:
  - Updated imports in examples and tests to use unprefixed versions (emitter, with_emitters, etc.)
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
- Initial release of PynneX (rebranded from temitter)
- Comprehensive emitter-listener mechanism with Python 3.10+ features
- Core Features:
  - Robust emitter-listener communication pattern
  - Thread-safe operations with automatic thread affinity
  - Full async/await support
  - Weak reference support for automatic cleanup
  - One-shot connections
  - Worker thread pattern
  - Simplified decorator aliases (@emitter, @listener, @with_emitters, @with_worker)
- Comprehensive test suite with 100% coverage
- Full documentation and examples

### Requirements
- Python 3.10 or higher (for stable asyncio operations)
