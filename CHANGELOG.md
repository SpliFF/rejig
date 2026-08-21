# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.6]

### Fixed

- **Removing a dependency no longer orphans its comment**: `DependenciesTarget.remove()`
  deleted only the key/value pair, so the comment documenting an entry survived it
  and was left stranded above whatever followed. The attached comment block now goes
  with the entry, along with one separator blank line so nothing is doubled up or
  left against the table header. A comment separated from the key by a blank line
  introduces the section rather than the entry, and is still preserved.
- **`remove()` no longer reports success without removing anything**: the Poetry
  branch looked the key up with the caller's raw spelling while `has()` compared
  PEP 503 normalised names, so `remove("foo_bar")` against a `foo-bar` key passed
  the guard, matched nothing, and still returned success. The key is now resolved
  by the same normalised comparison as `has()`.
- `__version__` was left at `0.1.4` by the 0.1.5 release; it now tracks
  `pyproject.toml` again.

### Added

- `_tomlkit_io.remove_key(table, key, comments=True)`: removes a key from a tomlkit
  table together with its attached comment block. Pass `comments=False` for the
  plain key-only removal.


## [0.1.5]

### Added

- Keep code structure and comments when editing TOML files


## [0.1.4]

### Added

- **Config key paths accept lists and a `KeyPath` builder**: `get()`, `set()`
  and `delete()` on `TomlTarget`, `YamlTarget` and `JsonTarget` now accept, in
  addition to a dotted string, a list/tuple of literal segments or a new
  `KeyPath` object (a `pathlib`-style builder: `KeyPath("a") / "b"`). A
  `pathlib.PurePath` is also accepted. This makes it possible to address a key
  that itself contains a literal `.` (e.g. `KeyPath("security") / "ignore" /
  "CVE-2026.0001"`), which the dotted-string form splits and cannot reach.
  `KeyPath` is exported at the top level (`from rejig import KeyPath`).

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
