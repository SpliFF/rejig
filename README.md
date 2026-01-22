# Rejig

A comprehensive Python library for programmatic code refactoring, analysis, and transformation. The goal of this library is to help you automate common editing, refactoring and optimisations within a python codebase. Rejig is not an AI/LLM, it is an API for making targeted changes to code.

## Use-cases

I built this library primarily to automate codebase changes that were too complex for basic tools like sed or patch - however it has been fleshed out to perform a wide variety of tasks I consider useful for python code development. I wanted the power of a library like libCST without the complexity. While it doesn't always make sense to automate changes, sometimes it does - this library is for those times.

Where this library really shines is when you want to automate changes to a codebase but you don't know what other changes have been made. This may be the case where you have multiple projects based on the same/similar template but diverged enough that you can't just use git or patch to ship a set of changes. That was exactly the scenario that led me to write this - dealing with 20+ repos based on the same original code but with no common git history. Git didn't want to know about it because it needs a common parent commit and regular patch would fail due to line number or whitespace changes. One of the things Rejig does well is let you accurately target the thing you want to change even when you don't know exactly where it is.

Here are some other usage suggestions:

- **As an IDE or AI Backend** — This framework supports a lot of features you get in an IDE like PyCharm, except it's headless. You could wrap this in a UI or build an MCP server.
- **Improve Code** — Use it to find and modernize legacy programming patterns in a older codebase. Find errors and dead code. Add documentation, directives and type hints. Break up long files.
- **Migrate Frameworks** — ie, Move your Flask project to Django. Switch from Poetry to UV, etc
- **As an LLM alternative** - You want to automate some things with CoPilot/Claude but perhaps you're not allowed due to contract restrictions. This library provides a compromise between AI automation and tedious manual edits. It also means you get deterministic output instead of whatever an LLM thinks is right at the time.

## Features

- **Fluent Target API** — Chain operations naturally: `rj.file("app.py").find_class("User").find_method("save")`
- **Batch Operations** — Apply changes to multiple targets at once with `TargetList`
- **Atomic Transactions** — Collect changes and apply them atomically with rollback support
- **Dry-run Mode** — Preview all changes before applying them
- **Code Analysis** — Detect complexity issues, dead code, and patterns
- **Security Scanning** — Find hardcoded secrets and vulnerability patterns
- **Optimization Detection** — Identify duplicate code and loop improvements
- **Import Management** — Organize, detect unused, and fix circular imports
- **Type Hint Operations** — Infer, modernize, and generate type hints
- **Docstring Generation** — Create and update docstrings in multiple styles
- **Config File Support** — Manipulate TOML, YAML, JSON, and INI files
- **Project Management** — Manage pyproject.toml, dependencies, and tool configs
- **Framework Support** — Django, Flask, FastAPI, and SQLAlchemy integrations
- **Patch to Script** - Convert a patch file into a python script and vice-versa.

## Installation

```bash
pip install rejig

# For framework support
pip install rejig[django]    # Django projects
pip install rejig[flask]     # Flask projects
pip install rejig[fastapi]   # FastAPI projects

# For all features
pip install rejig[all]
```

## Quick Start

```python
from rejig import Rejig

# Initialize with a directory, file, or glob pattern
rj = Rejig("src/")

# Find and modify code
rj.find_class("MyClass").add_attribute("count", "int", "0")
rj.find_class("MyClass").find_method("process").insert_statement("self.validate()")

# Preview changes without modifying files
rj = Rejig("src/", dry_run=True)
result = rj.find_class("MyClass").add_attribute("x", "int", "0")
print(result.message)  # [DRY RUN] Would add attribute...
print(result.diff)     # Shows unified diff
```

## Core API

### Finding Code Elements

```python
rj = Rejig("src/")

# Find by name
cls = rj.find_class("MyClass")
func = rj.find_function("process_data")
method = rj.find_class("MyClass").find_method("save")

# Find multiple with patterns
classes = rj.find_classes(pattern="^Test")      # All test classes
methods = rj.find_methods(pattern="^get_")      # All getter methods
funcs = rj.find_functions(pattern=".*_handler$") # All handlers

# Find in specific files
file_target = rj.file("models.py")
module_target = rj.module("myapp.models")

# Find other elements
todos = rj.find_todos()
imports = rj.find_imports("typing")
strings = rj.find_strings()
comments = rj.find_comments(pattern="TODO")
```

### Class Operations

```python
cls = rj.find_class("MyClass")

# Attributes
cls.add_attribute("cache", "dict[str, Any] | None", "None")
cls.remove_attribute("old_attr")

# Methods
cls.add_method("validate", "def validate(self):\n    pass")
cls.find_method("process").rename("handle")

# Decorators
cls.add_decorator("dataclass")
cls.remove_decorator("deprecated")

# Structure
cls.rename("NewClassName")
cls.add_base_class("BaseModel")
cls.convert_to_dataclass()
cls.delete()
```

### Method & Function Operations

```python
method = rj.find_class("MyClass").find_method("process")

# Statements
method.insert_statement("self.validate()", position="start")
method.insert_before_match(r"return\s+", "self.log_result(result)")
method.insert_after_match(r"result\s*=", "self.validate_result(result)")

# Parameters
method.add_parameter("timeout", "int", "30")
method.remove_parameter("old_param")
method.rename_parameter("data", "payload")
method.set_parameter_type("value", "str | None")

# Decorators
method.add_decorator("cached_property")
method.remove_decorator("staticmethod")
method.convert_to_classmethod()

# Type hints and docstrings
method.set_return_type("list[str]")
method.infer_type_hints()
method.generate_docstring(style="google")

# Conversions
method.convert_to_async()
method.wrap_with_try_except("ValueError", "logger.error(e)")
```

### Batch Operations

```python
# Apply operations to multiple targets
classes = rj.find_classes(pattern="^Test")
classes.add_decorator("pytest.mark.slow")

# Filter and operate
rj.find_functions().in_file("utils.py").add_decorator("timer")
rj.find_methods(pattern="^test_").first(10).add_decorator("skip")

# Type hints for all functions
rj.find_functions().infer_type_hints()
rj.find_methods().modernize_type_hints()

# Generate docstrings
rj.find_functions().without_docstrings().generate_docstrings(style="google")
```

### Line Operations

```python
file = rj.file("config.py")

# Single lines
line = file.find_line(42)
line.insert_before("# Important:")
line.insert_after("logger.info('done')")
line.rewrite("new_content = True")

# Line ranges
block = file.line_range(10, 20)
block.indent(4)
block.delete()

# Code blocks
for_block = file.find_code_block("for")
for_block.insert_statement("total += 1")
```

### Import Management

```python
from rejig import Rejig, ImportOrganizer, ImportGraph

rj = Rejig("src/")

# Add/remove imports
file = rj.file("module.py")
file.add_import("from typing import Optional, List")
file.remove_import(r"from deprecated import.*")

# Organize imports (isort-like)
organizer = ImportOrganizer(rj)
organizer.organize_all()

# Find unused imports
unused = file.find_unused_imports()
unused.delete_all()

# Detect circular imports
graph = ImportGraph(rj)
cycles = graph.find_circular_imports()
for cycle in cycles:
    print(f"Circular: {' -> '.join(cycle.modules)}")
```

### Type Hints

```python
rj = Rejig("src/")

# Infer from defaults and names
func = rj.find_function("process")
func.infer_type_hints()  # count: int, is_valid: bool, items: list

# Modernize syntax (Python 3.10+)
rj.find_functions().modernize_type_hints()
# List[str] -> list[str]
# Optional[int] -> int | None
# Union[str, int] -> str | int

# Add specific type hints
func.set_parameter_type("data", "dict[str, Any]")
func.set_return_type("list[str]")

# Generate stub files
from rejig import StubGenerator
StubGenerator(rj).generate_stubs("src/", "stubs/")
```

### Docstrings

```python
rj = Rejig("src/")

# Generate docstrings from signatures
func = rj.find_function("process")
func.generate_docstring(style="google")  # or "numpy", "sphinx"

# Generate for all functions without docstrings
rj.find_functions().without_docstrings().generate_docstrings()

# Convert between styles
rj.find_functions().convert_docstring_style("google", "numpy")

# Update existing docstrings when signatures change
func.update_docstring()
```

### Code Analysis

```python
from rejig import Rejig

rj = Rejig("src/")

# Find complexity issues
issues = rj.find_analysis_issues()
high_complexity = issues.by_type("HIGH_CYCLOMATIC_COMPLEXITY")
long_functions = issues.by_type("LONG_FUNCTION")

# Group by file
by_file = issues.group_by_file()
for file_path, file_issues in by_file.items():
    print(f"{file_path}: {len(file_issues)} issues")

# Find dead code
dead = issues.by_types(["UNUSED_FUNCTION", "UNUSED_CLASS", "UNUSED_VARIABLE"])

# Get summary
print(issues.summary())
# Total: 42 issues (3 high, 15 medium, 24 low)
```

### Security Scanning

```python
from rejig import Rejig

rj = Rejig("src/")

# Find security issues
security = rj.find_security_issues()

# Filter by severity
critical = security.critical()
high = security.high()

# Filter by type
secrets = security.by_types([
    "HARDCODED_SECRET",
    "HARDCODED_API_KEY",
    "HARDCODED_PASSWORD"
])
injection = security.by_types([
    "SQL_INJECTION",
    "COMMAND_INJECTION"
])

# Get detailed report
for issue in security:
    print(f"{issue.severity}: {issue.message}")
    print(f"  {issue.file_path}:{issue.line_number}")
```

### Optimization Detection

```python
from rejig import Rejig

rj = Rejig("src/")

# Find optimization opportunities
opts = rj.find_optimization_opportunities()

# Duplicate code detection
duplicates = opts.by_type("DUPLICATE_CODE")
for dup in duplicates:
    print(f"Duplicate code at {dup.locations}")

# Loop optimization suggestions
loops = opts.by_types([
    "LOOP_TO_COMPREHENSION",
    "LOOP_TO_BUILTIN"
])
for loop in loops:
    print(f"{loop.message}")
    print(f"Suggestion: {loop.suggestion}")

# Quick wins (low-risk optimizations)
quick = opts.quick_wins()
```

### Config Files

```python
rj = Rejig(".")

# TOML files (pyproject.toml, etc.)
toml = rj.toml("pyproject.toml")
toml.set("tool.black.line-length", 110)
toml.get("project.version")
toml.delete("tool.deprecated")

# YAML files
yaml = rj.yaml("config.yaml")
yaml.set("database.host", "localhost")
yaml.get_section("logging")

# JSON files
json_file = rj.json("package.json")
json_file.set("version", "2.0.0")

# INI files
ini = rj.ini("setup.cfg")
ini.set("metadata", "version", "1.0.0")
```

### Project Management

```python
from rejig import PythonProject

# High-level project management
project = PythonProject(".")

# Metadata
project.project().set_version("2.0.0")
project.project().bump_version("minor")
project.project().add_author("Jane Doe", "jane@example.com")

# Dependencies
project.dependencies().add("requests", "^2.28.0")
project.dependencies().update("django", "^4.2.0")
project.dependencies().remove("deprecated-package")
project.dev_dependencies().add("pytest", "^7.0.0")

# Entry points / scripts
project.scripts().add("mycli", "myapp.cli:main")

# Tool configuration
project.black().set_line_length(110)
project.ruff().select_rules(["E", "F", "W"])
project.mypy().set_strict(True)
project.pytest().set_test_paths(["tests/"])
```

### Transactions

```python
rj = Rejig("src/")

# Atomic batch operations
with rj.transaction() as tx:
    rj.find_class("OldName").rename("NewName")
    rj.find_function("old_func").rename("new_func")
    rj.find_methods(pattern="^_old").rename(lambda m: m.name.replace("_old", "_new"))

    # Preview before commit
    print(tx.preview())

# Changes applied atomically, or rolled back on error
```

### TODO Management

```python
rj = Rejig("src/")

# Find all TODOs
todos = rj.find_todos()

# Filter
fixmes = todos.by_type("FIXME")
high_priority = todos.by_priority(1)
my_todos = todos.by_author("john")
with_issues = todos.with_issue_refs()

# Operations
for todo in todos.without_issue_refs():
    todo.link_to_issue("GH-123")

# Report
print(todos.summary())
```

### Linting Directives

```python
rj = Rejig("src/")

# Find type: ignore comments
type_ignores = rj.find_type_ignores()
bare_ignores = type_ignores.filter(lambda t: t.is_bare)
for ignore in bare_ignores:
    ignore.update_codes(["type-arg"])  # Make specific

# Find noqa comments
noqas = rj.find_noqa_comments()
noqas.by_codes(["E501"]).remove_all()  # Remove line-length ignores

# Find all directives
from rejig import DirectiveFinder
directives = DirectiveFinder(rj).find_all()
print(directives.summary())
```

### Framework Support

#### Django

```python
from rejig.frameworks.django import DjangoProject

with DjangoProject("/path/to/project") as project:
    # Settings
    project.add_installed_app("myapp", after="django.contrib.auth")
    project.add_middleware("myapp.middleware.Custom", position="first")
    project.add_setting("MY_SETTING", '"value"')
    project.update_setting("DEBUG", "False")

    # URLs
    project.add_url_include("myapp.urls", path_prefix="api/")
    project.add_url_pattern("health/", "HealthView.as_view()", name="health")

    # App discovery
    app = project.find_app_containing_class("MyView")
```

#### Flask

```python
from rejig.frameworks.flask import FlaskProject

flask = FlaskProject("src/")
flask.add_route("/users", "get_users", methods=["GET"])
flask.add_blueprint("admin", url_prefix="/admin")
flask.add_error_handler(404, "handle_not_found")
```

#### FastAPI

```python
from rejig.frameworks.fastapi import FastAPIProject

api = FastAPIProject("src/")
api.add_endpoint("/items/{id}", "get_item", method="GET")
api.add_dependency("get_db", "Depends(get_database)")
api.add_middleware("CORSMiddleware", allow_origins=["*"])
```

## Result Handling

All operations return a `Result` object:

```python
result = cls.add_attribute("count", "int", "0")

if result.success:
    print(f"Success: {result.message}")
    print(f"Files changed: {result.files_changed}")
    print(f"Diff:\n{result.diff}")
else:
    print(f"Failed: {result.message}")
    if result.exception:
        print(f"Exception: {result.exception}")

# Results are truthy/falsy
if result:
    print("Operation succeeded!")
```

## Error Handling

Rejig never raises exceptions for missing targets. Instead, `ErrorTarget` allows safe chaining:

```python
# This won't raise even if class doesn't exist
result = rj.find_class("NonExistent").find_method("foo").rename("bar")

if not result:
    print(result.message)  # "Class 'NonExistent' not found"
```

## Dry Run Mode

Preview all changes without modifying files:

```python
rj = Rejig("src/", dry_run=True)
result = rj.find_class("MyClass").rename("NewClass")
print(result.message)  # [DRY RUN] Would rename class MyClass to NewClass
print(result.diff)     # Shows what would change
```

## Requirements

- Python 3.10+
- libcst >= 1.0.0
- rope >= 1.0.0 (for move operations)

## Documentation

Full documentation: [docs/](docs/)

- [Getting Started](docs/getting-started/quickstart.md)
- [Core Concepts](docs/getting-started/concepts.md)
- [API Reference](docs/reference/)
- [Examples & Recipes](docs/examples/)

## License

MIT

## Contributing

A significant portion of this library was generated using Claude Code. That doesn't mean humans aren't welcome to contribute. Contact the author via Github Repository (https://github.com/SpliFF/rejig) or email (spliff@warriorhut.org) if you have feature requests or contributions you think should be included.
