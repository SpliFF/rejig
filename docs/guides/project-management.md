# Project Management

Rejig provides high-level tools for managing Python projects: pyproject.toml configuration, dependencies, scripts, and tool settings.

## PythonProject

The `PythonProject` class provides a convenient facade for managing project configuration.

```python
from rejig import PythonProject

project = PythonProject(".")  # or path to project root

# Check if pyproject.toml exists
if project.exists:
    print(f"Project: {project.project().get_name()}")
    print(f"Version: {project.project().get_version()}")
```

## Project Metadata

### Access Project Section

```python
project = PythonProject(".")

# Get the [project] section target
proj = project.project()

# Read metadata
name = proj.get_name()
version = proj.get_version()
description = proj.get_description()
license_ = proj.get_license()
python_requires = proj.get_requires_python()
```

### Modify Metadata

```python
proj = project.project()

# Set values
proj.set_name("my-package")
proj.set_version("2.0.0")
proj.set_description("A fantastic Python package")
proj.set_license("MIT")
proj.set_requires_python(">=3.10")
```

### Version Bumping

```python
proj = project.project()

# Current version: 1.2.3
proj.bump_version("patch")   # -> 1.2.4
proj.bump_version("minor")   # -> 1.3.0
proj.bump_version("major")   # -> 2.0.0

# With pre-release
proj.bump_version("minor", prerelease="alpha")  # -> 1.3.0a1
proj.bump_version("prerelease")                 # -> 1.3.0a2
```

### Authors

```python
# Get authors
authors = proj.get_authors()
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
keywords = proj.get_keywords()
proj.add_keyword("automation")
proj.add_keyword("refactoring")

# Classifiers
classifiers = proj.get_classifiers()
proj.add_classifier("Development Status :: 4 - Beta")
proj.add_classifier("Programming Language :: Python :: 3.11")
```

### Project URLs

```python
# Get URLs
urls = proj.get_urls()
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

# Optional dependency group
test_deps = project.optional_dependencies("test")
```

### List Dependencies

```python
deps = project.dependencies()

# List all
for dep in deps.list():
    print(f"{dep.name}: {dep.version_spec}")

# Check if dependency exists
if deps.has("requests"):
    print(f"requests version: {deps.get('requests')}")
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
# Create a new group
project.dependencies().add_group("docs")

# Add to specific group
docs = project.optional_dependencies("docs")
docs.add("sphinx", "^6.0.0")
docs.add("sphinx-rtd-theme", "^1.0.0")

# Or add directly
project.dependencies().add_to_group("docs", "myst-parser", "^1.0.0")
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
    print(f"mycli command: {scripts.get('mycli')}")
```

## Tool Configuration

### Black

```python
black = project.black()

# Configure
black.set_line_length(110)
black.set_target_versions(["py310", "py311"])
black.set_include_pattern(r"\.pyi?$")
black.set_exclude_pattern(r"/(\.git|\.venv|migrations)/")

# Results in pyproject.toml:
# [tool.black]
# line-length = 110
# target-version = ["py310", "py311"]
# include = '\.pyi?$'
# exclude = '/(\.git|\.venv|migrations)/'
```

### Ruff

```python
ruff = project.ruff()

# Basic settings
ruff.set_line_length(110)
ruff.set_target_version("py310")

# Select rules
ruff.select_rules(["E", "F", "W", "I", "UP"])

# Ignore specific rules
ruff.ignore_rules(["E501", "F401"])

# Per-file ignores
ruff.add_per_file_ignores("tests/*", ["S101", "PLR2004"])
ruff.add_per_file_ignores("__init__.py", ["F401"])

# isort settings (via ruff)
ruff.set_isort_section_order([
    "future", "standard-library", "third-party", "first-party", "local-folder"
])
ruff.set_isort_known_first_party(["mypackage"])
```

### mypy

```python
mypy = project.mypy()

# Basic settings
mypy.set_python_version("3.10")
mypy.set_strict(True)

# Import handling
mypy.set_ignore_missing_imports(True)

# Warning settings
mypy.set_warn_unused_ignores(True)
mypy.set_warn_return_any(True)

# Per-module overrides
mypy.add_module_override("mypackage.legacy", {
    "ignore_errors": True,
})
```

### pytest

```python
pytest_cfg = project.pytest()

# Basic settings
pytest_cfg.set_test_paths(["tests"])
pytest_cfg.set_python_files(["test_*.py", "*_test.py"])
pytest_cfg.set_python_classes(["Test*"])
pytest_cfg.set_python_functions(["test_*"])

# Add markers
pytest_cfg.set_markers([
    "slow: marks tests as slow",
    "integration: marks integration tests",
])

# Add options
pytest_cfg.add_ini_option("addopts", "-v --tb=short")
pytest_cfg.add_ini_option("filterwarnings", [
    "ignore::DeprecationWarning",
])
```

### isort

```python
isort = project.isort()

# Use Black-compatible profile
isort.set_profile("black")

# Custom settings
isort.set_line_length(110)
isort.set_multi_line_mode(3)
isort.set_known_first_party(["mypackage"])
isort.set_known_third_party(["django", "rest_framework"])
```

### coverage

```python
coverage = project.coverage()

# Source paths
coverage.set_source_paths(["src/mypackage"])

# Omit patterns
coverage.set_omit_patterns([
    "*/tests/*",
    "*/__init__.py",
    "*/migrations/*",
])

# Minimum coverage
coverage.set_min_percentage(80)
coverage.set_fail_under(80)

# Report settings
coverage.set_show_missing(True)
coverage.set_skip_covered(True)
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
proj.set_requires_python(">=3.10")
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
project.ruff().select_rules(["E", "F", "W", "I", "UP"])
project.mypy().set_strict(True)
project.pytest().set_test_paths(["tests"])
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
    project.ruff().select_rules(["E", "F", "W", "I", "UP", "B", "C4"])
    project.mypy().set_strict(True)
    project.pytest().set_test_paths(["tests"])
    project.coverage().set_fail_under(80)
```

### Check Outdated Dependencies

```python
import subprocess
from rejig import PythonProject

project = PythonProject(".")
deps = project.dependencies()

# Get current versions
current = {dep.name: dep.version_spec for dep in deps.list()}

# Check against PyPI (using pip)
result = subprocess.run(
    ["pip", "index", "versions", *current.keys()],
    capture_output=True, text=True
)
# ... parse output to find outdated packages ...
```

## Dry Run Mode

Preview changes without modifying files:

```python
project = PythonProject(".", dry_run=True)

# Make changes
project.project().set_version("2.0.0")
project.dependencies().add("new-package", "^1.0.0")

# See what would change
result = project.save()
print(result.diff)
```
