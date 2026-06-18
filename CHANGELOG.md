# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.3] - 2026-06-18

### Added

- **Literal file replacement**: `FileTarget.replace(pattern, replacement, count=0)`
  performs an in-place literal text replacement (plain `str.replace`), so regex
  metacharacters match themselves. It is the literal counterpart to the existing
  regex `replace_pattern()`, and — because `TargetList.replace_all()` dispatches
  to it — enables one-line whole-tree find-and-replace:
  `rj.find_files("app/*/api.py").replace_all("foo(", "bar(")`.

## [0.1.2] - 2026-06-18

### Added

- **Import sorting via isort**: `FileTarget.sort_imports()` sorts and groups a
  file's imports using isort, configured from the project's own
  `pyproject.toml` / `setup.cfg` / `.isort.cfg` (discovered by searching upward
  from the file). Output matches what the project's own isort / pre-commit / CI
  run produces, honoring options like `profile`, `force_single_line`,
  `known_third_party`, and `src_paths`. `add_import()` and
  `remove_unused_imports()` now re-sort imports automatically, controlled by the
  new `Rejig(auto_sort_imports=True)` flag (default on) and a per-call `sort`
  argument. isort is now a runtime dependency.

### Changed

- **YAML editing preserves formatting**: `YamlTarget` now uses `ruamel.yaml` in
  round-trip mode instead of PyYAML. Comments, quote styles, key order, and
  scalar wrapping in untouched parts of a file are preserved, so a
  load → mutate → dump cycle only rewrites the keys actually changed and keeps
  diffs minimal. Requires the `rejig[yaml]` extra (`ruamel.yaml`).

### Fixed

- **`add_import` no longer skips imports that are substrings of an existing
  line**: the "already present" check used substring containment, so
  `add_import("import time")` was silently skipped when the file merely contained
  `from calendar import timegm`. It now matches whole import lines.

## [0.1.1] - 2026-06-18

### Fixed

- **Packaging**: Include `rejig.security.secrets` in distributions. A `.gitignore`
  `SECRET*` rule matched `src/rejig/security/secrets.py` (case-insensitively on
  macOS), so the file was never committed and the 0.1.0 wheel/sdist shipped without
  it, breaking `import rejig`. 0.1.0 is broken; use 0.1.1.

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

[Unreleased]: https://github.com/SpliFF/rejig/compare/v0.1.3...HEAD
[0.1.3]: https://github.com/SpliFF/rejig/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/SpliFF/rejig/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/SpliFF/rejig/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/SpliFF/rejig/releases/tag/v0.1.0