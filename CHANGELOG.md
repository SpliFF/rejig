# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-01-22

### Added

- **Core API**: Main `Rejig` class entry point with fluent API for code refactoring
- **Result System**: `Result`, `ErrorResult`, and `BatchResult` classes for operation outcomes
- **Target System**: Unified target architecture replacing legacy scope system
  - **Python Targets**: `PackageTarget`, `ModuleTarget`, `FileTarget`, `ClassTarget`, `FunctionTarget`, `MethodTarget`, `LineTarget`, `LineBlockTarget`, `CodeBlockTarget`, `CommentTarget`, `StringLiteralTarget`, `TodoTarget`
  - **Config Targets**: `TomlTarget`, `YamlTarget`, `JsonTarget`, `IniTarget`
  - **Text Targets**: `TextFileTarget`, `TextBlockTarget`
- **Transformers**: LibCST-based code transformers
  - `AddClassAttribute`, `AddFirstParameter`, `AddMethodDecorator`
  - `InsertAtMatch`, `InsertAtMethodStart`
  - `RemoveClassAttribute`, `RemoveDecorator`, `RemoveMethodDecorator`, `RemoveModuleLevelAssignment`
  - `RenameClass`, `RenameMethod`, `ReplaceIdentifier`
  - `StaticToClassMethod`
- **Import Management**: Import organization, unused detection/removal, missing detection/addition, relative/absolute conversion
- **Type Hints**: Type inference, stub generation, type comment conversion, syntax modernization
- **Docstrings**: Generation from signatures, updating, Google/NumPy/Sphinx style support
- **TODO Management**: Parser and finder for TODO/FIXME/XXX/HACK comments with reporting
- **Code Generation**: Dunder methods, test stubs, property generation
- **Code Modernization**: F-strings, walrus operator, modern typing syntax, deprecated API replacement
- **Code Analysis**: Cyclomatic complexity, import graphs, dead code detection, metrics
- **Module Operations**: Split, merge, rename with import updates, `__all__` management
- **Security Analysis**: Hardcoded secrets detection, vulnerability pattern detection
- **Directive Management**: Support for mypy, noqa, pylint, black, and coverage directives
- **Project Management**: `PythonProject` facade with pyproject.toml manipulation
  - Tool configuration targets for Black, Ruff, mypy, pytest, isort, coverage
  - Dependency management and entry point configuration
- **Packaging**: Support for multiple package formats
  - requirements.txt, PEP 621 pyproject.toml, Poetry, UV configurations
  - Format detection and conversion between formats
- **Framework Support**:
  - **Django**: Project detection, settings management, URL configuration
  - **Flask**: Route and blueprint support
  - **FastAPI**: Endpoint and dependency support
  - **SQLAlchemy**: Model and relationship support
- **Patching Module**: Runtime code patching capabilities
- **Transaction Support**: Atomic edit operations with rollback
- **Diff Previews**: Preview changes before applying with dry-run support
- **Comprehensive Test Suite**: Full test coverage for all modules

### Changed

- Merged `Match` and `FindResult` into unified Target API
- Updated transformers to prefer LibCST operations over string manipulation
- Reorganized deprecated scopes to new targets system
- Moved `Result` classes into `rejig.core.results`
- Introduced base classes for similar target types

### Fixed

- Various code quality improvements across all modules

[Unreleased]: https://github.com/SpliFF/rejig/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/SpliFF/rejig/releases/tag/v0.1.0