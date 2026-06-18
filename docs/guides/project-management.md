# Project Management

Rejig provides high-level tools for managing Python projects: pyproject.toml configuration, dependencies, scripts, and tool settings.

## PythonProject

The `PythonProject` class provides a convenient facade for managing project configuration.

```python
from rejig import PythonProject

project = PythonProject(".")  # or path to project root

# Check if pyproject.toml exists
if project.exists:
    print(f"Project: {project.project().name}")
    print(f"Version: {project.project().version}")
```

## Project Metadata

### Access Project Section

```python
project = PythonProject(".")

# Get the [project] section target
proj = project.project()

# Read metadata (properties, not methods)
name = proj.name
version = proj.version
description = proj.description
license_ = proj.license
python_requires = proj.python_requires
```

### Modify Metadata

```python
proj = project.project()

# Set values
proj.set_name("my-package")
proj.set_version("2.0.0")
proj.set_description("A fantastic Python package")
proj.set_license("MIT")
proj.set_python_requires(">=3.10")
```

### Version Bumping

```python
proj = project.project()

# Current version: 1.2.3
# bump_version(part="patch") accepts "major", "minor", or "patch".
proj.bump_version("patch")   # -> 1.2.4
proj.bump_version("minor")   # -> 1.3.0
proj.bump_version("major")   # -> 2.0.0
```

### Authors

```python
# Get authors
authors = proj.authors
for author in authors:
    print(f"{author['name']} <{author['email']}>")

# Add author
proj.add_author("Jane Doe", "jane@example.com")

# Set all authors
proj.set_authors([
    {"name": "Jane Doe", "email": "jane@example.com"},
    {"name": "John Smith", "email": "john@example.com"},
])
```

### Keywords and Classifiers

```python
# Keywords
keywords = proj.keywords
proj.add_keyword("automation")
proj.add_keyword("refactoring")

# Classifiers
classifiers = proj.classifiers
proj.add_classifier("Development Status :: 4 - Beta")
proj.add_classifier("Programming Language :: Python :: 3.11")
```

### Project URLs

```python
# Get URLs
urls = proj.urls
# {"Homepage": "https://...", "Repository": "https://..."}

# Set URLs
proj.set_url("Homepage", "https://myproject.dev")
proj.set_url("Repository", "https://github.com/me/myproject")
proj.set_url("Documentation", "https://docs.myproject.dev")
```

## Dependencies

### Access Dependencies

```python
project = PythonProject(".")

# Main dependencies
deps = project.dependencies()

# Dev dependencies
dev_deps = project.dev_dependencies()

# Optional dependency group (via the pyproject target)
test_deps = project.pyproject.optional_dependencies("test")
```

### List Dependencies

```python
deps = project.dependencies()

# List all (returns a list of requirement strings)
for spec in deps.list():
    print(spec)  # e.g. "requests>=2.28.0"

# Check if dependency exists
if deps.has("requests"):
    print(f"requests version: {deps.get_version('requests')}")
```

### Add Dependencies

```python
deps = project.dependencies()

# Add with version specifier
deps.add("requests", "^2.28.0")
deps.add("django", ">=4.0,<5.0")

# Add without version (latest)
deps.add("black")

# Add with extras
deps.add("uvicorn", ">=0.20.0", extras=["standard"])
```

### Update Dependencies

```python
# Update version
deps.update("requests", "^2.31.0")

# Update to latest (remove version constraint)
deps.update("black", "*")
```

### Remove Dependencies

```python
deps.remove("deprecated-package")
```

### Dev Dependencies

```python
dev = project.dev_dependencies()

# Add dev dependencies
dev.add("pytest", "^7.0.0")
dev.add("mypy", "^1.0.0")
dev.add("black", "^23.0.0")
dev.add("ruff", "^0.1.0")
```

### Optional Dependency Groups

```python
# Access an optional-dependency group (created on first add)
docs = project.pyproject.optional_dependencies("docs")
docs.add("sphinx", "^6.0.0")
docs.add("sphinx-rtd-theme", "^1.0.0")
docs.add("myst-parser", "^1.0.0")
```

## Entry Points / Scripts

### Manage Scripts

```python
scripts = project.scripts()

# List scripts
for name, command in scripts.list().items():
    print(f"{name} = {command}")

# Add script
scripts.add("mycli", "mypackage.cli:main")
scripts.add("myserver", "mypackage.server:run")

# Update script
scripts.update("mycli", "mypackage.cli:new_main")

# Remove script
scripts.remove("old-command")

# Check if script exists
if scripts.has("mycli"):
    print(f"mycli command: {scripts.get_entry_point('mycli')}")
```

## Tool Configuration

### Black

```python
black = project.black()

# Configure
black.set_line_length(110)
black.set_target_version(["py310", "py311"])
black.set_extend_exclude(r"/(\.git|\.venv|migrations)/")

# Results in pyproject.toml:
# [tool.black]
# line-length = 110
# target-version = ["py310", "py311"]
# extend-exclude = '/(\.git|\.venv|migrations)/'
```

### Ruff

```python
ruff = project.ruff()

# Basic settings
ruff.set_line_length(110)
ruff.set_target_version("py310")

# Select rules
ruff.select(["E", "F", "W", "I", "UP"])

# Ignore specific rules
ruff.ignore(["E501", "F401"])

# isort settings (via ruff)
ruff.configure_isort(known_first_party=["mypackage"])
```

### mypy

```python
mypy = project.mypy()

# Basic settings
mypy.set_python_version("3.10")
mypy.enable_strict()

# Import handling
mypy.enable_ignore_missing_imports()

# Warning settings
mypy.enable_warn_return_any()

# Per-module overrides
mypy.configure_module("mypackage.legacy", ignore_errors=True)
```

### pytest

```python
pytest_cfg = project.pytest()

# Basic settings
pytest_cfg.set_testpaths(["tests"])
pytest_cfg.set_python_files(["test_*.py", "*_test.py"])
pytest_cfg.set_python_classes(["Test*"])
pytest_cfg.set_python_functions(["test_*"])

# Add markers (one at a time: name, description)
pytest_cfg.add_marker("slow", "marks tests as slow")
pytest_cfg.add_marker("integration", "marks integration tests")

# Add options
pytest_cfg.set_addopts("-v --tb=short")
pytest_cfg.add_filterwarning("ignore::DeprecationWarning")
```

### isort

```python
isort = project.isort()

# Use Black-compatible profile
isort.set_profile("black")

# Custom settings
isort.set_line_length(110)
isort.set_known_first_party(["mypackage"])
isort.set_known_third_party(["django", "rest_framework"])
```

### coverage

```python
coverage = project.coverage()

# Source paths
coverage.set_source(["src/mypackage"])

# Omit patterns
coverage.set_omit([
    "*/tests/*",
    "*/__init__.py",
    "*/migrations/*",
])

# Minimum coverage
coverage.set_fail_under(80)

# Report settings
coverage.enable_show_missing()
```

## Direct pyproject.toml Access

For advanced use cases, access the pyproject.toml directly:

```python
pyproject = project.pyproject

# Get any value
build_backend = pyproject.get("build-system.build-backend")

# Set any value
pyproject.set("tool.custom.setting", "value")

# Get entire section
tool_settings = pyproject.get_section("tool")

# Delete a key
pyproject.delete("tool.deprecated")
```

## Common Patterns

### Initialize New Project

```python
from rejig import PythonProject

project = PythonProject("my-new-project")

# Set up project metadata
proj = project.project()
proj.set_name("my-new-project")
proj.set_version("0.1.0")
proj.set_description("A new Python project")
proj.set_python_requires(">=3.10")
proj.add_author("Your Name", "you@example.com")
proj.set_license("MIT")

# Add dependencies
deps = project.dependencies()
deps.add("requests", "^2.28.0")
deps.add("click", "^8.0.0")

# Add dev dependencies
dev = project.dev_dependencies()
dev.add("pytest", "^7.0.0")
dev.add("black", "^23.0.0")
dev.add("ruff", "^0.1.0")
dev.add("mypy", "^1.0.0")

# Add CLI entry point
project.scripts().add("mycli", "my_new_project.cli:main")

# Configure tools
project.black().set_line_length(110)
project.ruff().select(["E", "F", "W", "I", "UP"])
project.mypy().enable_strict()
project.pytest().set_testpaths(["tests"])
```

### Sync Tool Configurations

```python
# Ensure consistent line length across tools
LINE_LENGTH = 110

project = PythonProject(".")
project.black().set_line_length(LINE_LENGTH)
project.ruff().set_line_length(LINE_LENGTH)
project.isort().set_line_length(LINE_LENGTH)
```

### Migrate from setup.py

```python
# Read existing setup.py values and create pyproject.toml
import ast
from pathlib import Path

# Parse setup.py (simplified)
setup_py = Path("setup.py").read_text()
# ... extract values ...

project = PythonProject(".")
proj = project.project()
proj.set_name(name)
proj.set_version(version)
proj.set_description(description)
# etc.
```

### Add Standard Dev Dependencies

```python
def setup_dev_environment(project: PythonProject):
    """Add standard development dependencies."""
    dev = project.dev_dependencies()

    # Testing
    dev.add("pytest", "^7.0.0")
    dev.add("pytest-cov", "^4.0.0")
    dev.add("pytest-asyncio", "^0.21.0")

    # Linting and formatting
    dev.add("black", "^23.0.0")
    dev.add("ruff", "^0.1.0")
    dev.add("mypy", "^1.0.0")

    # Pre-commit
    dev.add("pre-commit", "^3.0.0")

    # Configure tools
    project.black().set_line_length(110)
    project.ruff().select(["E", "F", "W", "I", "UP", "B", "C4"])
    project.mypy().enable_strict()
    project.pytest().set_testpaths(["tests"])
    project.coverage().set_fail_under(80)
```

### Check Outdated Dependencies

```python
import subprocess
from rejig import PythonProject

project = PythonProject(".")
deps = project.dependencies()

# Get current requirement specs (deps.list() returns strings like "requests>=2.28.0")
current = deps.list()

# Check against PyPI (using pip)
result = subprocess.run(
    ["pip", "index", "versions", *current],
    capture_output=True, text=True
)
# ... parse output to find outdated packages ...
```

## Dry Run Mode

Preview changes without modifying files:

```python
project = PythonProject(".", dry_run=True)

# In dry-run mode each operation returns a Result with the proposed diff
# instead of writing to disk.
result = project.project().set_version("2.0.0")
print(result.diff)

result = project.dependencies().add("new-package", "^1.0.0")
print(result.diff)
```
