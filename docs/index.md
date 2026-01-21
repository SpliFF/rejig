# Rejig

**Comprehensive Python code refactoring, analysis, and transformation.**

Rejig provides a fluent API for finding and modifying Python code elements. Whether you're building codemods, automating refactoring, analyzing code quality, or managing large-scale migrations, Rejig gives you precise control over your codebase.

## Features

### Code Manipulation
- **Target-based API** — Everything is a target: files, modules, classes, functions, methods, lines
- **Fluent chaining** — `rj.file("app.py").find_class("User").find_method("save")`
- **Batch operations** — Apply changes to multiple targets with `TargetList`
- **Atomic transactions** — Collect changes and apply atomically with rollback
- **Safe by default** — Operations return `Result` objects, never raise exceptions
- **Dry-run mode** — Preview all changes before applying

### Code Analysis
- **Complexity analysis** — Cyclomatic complexity, nesting depth, function length
- **Dead code detection** — Unused functions, classes, variables, imports
- **Pattern detection** — Missing type hints, bare excepts, magic numbers
- **Security scanning** — Hardcoded secrets, injection vulnerabilities, unsafe operations
- **Optimization detection** — Duplicate code, loop improvements

### Code Transformation
- **Import management** — Organize, detect unused, fix circular imports
- **Type hints** — Infer, modernize, and generate type annotations
- **Docstrings** — Generate and update in Google, NumPy, or Sphinx style
- **Code generation** — Dunder methods, properties, test stubs
- **Modernization** — f-strings, Python 3.10+ syntax, deprecated API replacement

### Project Management
- **pyproject.toml** — Manage metadata, dependencies, scripts
- **Tool configuration** — Black, Ruff, mypy, pytest, isort, coverage
- **Package format conversion** — requirements.txt, Poetry, PEP 621, UV

### Framework Support
- **Django** — Settings, URLs, app discovery
- **Flask** — Routes, blueprints, error handlers
- **FastAPI** — Endpoints, dependencies, middleware
- **SQLAlchemy** — Models, relationships

## Quick Example

```python
from rejig import Rejig

rj = Rejig("src/")

# Find all test classes and add a decorator
rj.find_classes(pattern="^Test").add_decorator("pytest.mark.slow")

# Rename a method and update all references
rj.file("models.py").find_class("User").find_method("get_name").rename("get_full_name")

# Add type hints to all functions
rj.find_functions().infer_type_hints()

# Generate docstrings for functions without them
rj.find_functions().without_docstrings().generate_docstrings(style="google")

# Find security issues
security_issues = rj.find_security_issues()
print(f"Found {len(security_issues)} security issues")

# Modify pyproject.toml
rj.toml("pyproject.toml").set("tool.black.line-length", 110)
```

## Why Rejig?

| Task | Without Rejig | With Rejig |
|------|---------------|------------|
| Rename a method | Find/replace (breaks things) | `target.rename("new_name")` |
| Add decorator to many classes | Manual editing | `targets.add_decorator("@cached")` |
| Find security vulnerabilities | External tools, CI setup | `rj.find_security_issues()` |
| Add type hints to legacy code | Manual annotation | `rj.find_functions().infer_type_hints()` |
| Generate docstrings | Write each one | `targets.generate_docstrings()` |
| Update pyproject.toml | Parse, modify, serialize | `rj.toml(path).set(key, value)` |
| Find duplicate code | Manual review | `rj.find_optimization_opportunities()` |

## Installation

```bash
pip install rejig

# With framework support
pip install rejig[django]
pip install rejig[all]
```

## Documentation

### Getting Started
- [Installation](getting-started/installation.md) — Install and verify
- [Quickstart](getting-started/quickstart.md) — Get up and running in 5 minutes
- [Core Concepts](getting-started/concepts.md) — Understand targets, results, and the API design

### Guides

#### Finding & Modifying Code
- [Finding Code](guides/finding-code.md) — Locate classes, functions, methods, and more
- [Modifying Code](guides/modifying-code.md) — Rename, add, remove, and transform code
- [Batch Operations](guides/batch-operations.md) — Work with multiple targets
- [Line Operations](guides/line-operations.md) — Work with individual lines and ranges

#### Code Quality
- [Code Analysis](guides/code-analysis.md) — Complexity, dead code, patterns
- [Security Analysis](guides/security-analysis.md) — Find vulnerabilities and secrets
- [Code Optimization](guides/code-optimization.md) — Detect duplicates and improvements

#### Code Transformation
- [Import Management](guides/imports.md) — Organize and manage imports
- [Type Hints](guides/type-hints.md) — Infer, modernize, and add type annotations
- [Docstrings](guides/docstrings.md) — Generate and update documentation
- [Code Generation](guides/code-generation.md) — Generate boilerplate code

#### Configuration
- [Config Files](guides/config-files.md) — TOML, YAML, JSON, INI manipulation
- [Project Management](guides/project-management.md) — pyproject.toml and dependencies
- [Transactions](guides/transactions.md) — Atomic operations with rollback

#### Framework-Specific
- [Django](guides/frameworks/django.md) — Django project operations
- [Flask](guides/frameworks/flask.md) — Flask application refactoring
- [FastAPI](guides/frameworks/fastapi.md) — FastAPI endpoint management

#### Error Handling
- [Error Handling](guides/error-handling.md) — Result-based error handling patterns

### Examples & Recipes
- [Refactoring Patterns](examples/refactoring-patterns.md) — Common refactoring scenarios
- [Codemod Recipes](examples/codemod-recipes.md) — Ready-to-use migration scripts
- [Optimization Recipes](examples/optimization-recipes.md) — Code quality improvements
- [Analysis Recipes](examples/analysis-recipes.md) — Code analysis scripts
- [Security Recipes](examples/security-recipes.md) — Security scanning scripts

### API Reference
- [Rejig Class](reference/rejig.md) — Main entry point
- [Targets](reference/targets.md) — All target classes
- [Results](reference/results.md) — Result classes
- [Analysis](reference/analysis.md) — Analysis types and findings
- [Security](reference/security.md) — Security types and findings
- [Transformers](reference/transformers.md) — LibCST transformers

### Sample Projects
- [Sample Projects](sample-projects/README.md) — Test projects for trying recipes
