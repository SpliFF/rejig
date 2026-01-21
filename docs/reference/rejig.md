# Rejig Class Reference

The main entry point for all operations.

## Overview

`Rejig` is the primary class you'll interact with. Create an instance pointed at your codebase, then use its factory methods to get targets.

```python
from rejig import Rejig

rj = Rejig("src/")
```

## Constructor

```python
Rejig(path: str | Path, dry_run: bool = False)
```

Create a Rejig instance.

**Parameters:**

- `path` — Directory, file, or glob pattern to work with
- `dry_run` — If True, preview changes without modifying files

**Example:**

```python
# Work with a directory
rj = Rejig("src/")

# Work with a single file
rj = Rejig("src/module.py")

# Work with glob pattern
rj = Rejig("src/**/*_test.py")

# Dry-run mode
rj = Rejig("src/", dry_run=True)

# Context manager (required for move operations)
with Rejig("src/") as rj:
    rj.find_class("X").move_to("other_module")
```

## Properties

| Property | Type | Description |
|----------|------|-------------|
| `path` | `Path` | Original path/pattern provided |
| `root` / `root_path` | `Path` | Resolved root directory |
| `files` | `list[Path]` | List of Python files (lazy-loaded) |
| `dry_run` | `bool` | Whether in dry-run mode |
| `in_transaction` | `bool` | Whether in a transaction |
| `current_transaction` | `Transaction \| None` | Active transaction |

## Target Factory Methods

### file

```python
rj.file(path: str | Path) -> FileTarget
```

Get a target for a specific Python file.

**Parameters:**

- `path` — File path, relative to root or absolute

**Example:**

```python
file = rj.file("models.py")
file = rj.file("subdir/utils.py")
```

### module

```python
rj.module(dotted_path: str) -> ModuleTarget
```

Get a target for a Python module by dotted path.

**Parameters:**

- `dotted_path` — Module path like `"myapp.models"`

**Example:**

```python
module = rj.module("myapp.models")
module = rj.module("myapp.utils.helpers")
```

### package

```python
rj.package(path: str | Path) -> PackageTarget
```

Get a target for a Python package directory.

**Parameters:**

- `path` — Package directory path

**Example:**

```python
pkg = rj.package("myapp/")
```

### text_file

```python
rj.text_file(path: str | Path) -> TextFileTarget
```

Get a target for any text file (non-Python).

**Example:**

```python
readme = rj.text_file("README.md")
```

### toml

```python
rj.toml(path: str | Path) -> TomlTarget
```

Get a target for a TOML file.

**Example:**

```python
config = rj.toml("pyproject.toml")
config.set("tool.black.line-length", 110)
```

### yaml

```python
rj.yaml(path: str | Path) -> YamlTarget
```

Get a target for a YAML file.

**Example:**

```python
config = rj.yaml("config.yml")
config.set("database.host", "localhost")
```

### json

```python
rj.json(path: str | Path) -> JsonTarget
```

Get a target for a JSON file.

**Example:**

```python
pkg = rj.json("package.json")
pkg.set("version", "2.0.0")
```

### ini

```python
rj.ini(path: str | Path) -> IniTarget
```

Get a target for an INI/CFG file.

**Example:**

```python
ini = rj.ini("setup.cfg")
ini.set("metadata", "version", "1.0.0")
```

## Find Methods (Single Target)

### find_class

```python
rj.find_class(name: str) -> ClassTarget | ErrorTarget
```

Find a class by exact name.

**Example:**

```python
cls = rj.find_class("MyClass")
if cls.exists():
    cls.rename("NewClass")
```

### find_function

```python
rj.find_function(name: str) -> FunctionTarget | ErrorTarget
```

Find a module-level function by exact name.

**Example:**

```python
func = rj.find_function("process_data")
func.add_decorator("cache")
```

## Find Methods (Multiple Targets)

### find_files

```python
rj.find_files(pattern: str = "**/*.py") -> TargetList[FileTarget]
```

Find files matching a glob pattern.

**Example:**

```python
all_py = rj.find_files()
tests = rj.find_files("tests/**/*.py")
```

### find_classes

```python
rj.find_classes(pattern: str | None = None) -> TargetList[ClassTarget]
```

Find all classes in the project.

**Parameters:**

- `pattern` — Optional regex pattern to filter by name

**Example:**

```python
all_classes = rj.find_classes()
test_classes = rj.find_classes(pattern="^Test")
```

### find_functions

```python
rj.find_functions(pattern: str | None = None) -> TargetList[FunctionTarget]
```

Find all module-level functions in the project.

**Parameters:**

- `pattern` — Optional regex pattern to filter by name

**Example:**

```python
all_funcs = rj.find_functions()
handlers = rj.find_functions(pattern=".*_handler$")
```

### find_methods

```python
rj.find_methods(pattern: str | None = None) -> TargetList[MethodTarget]
```

Find all methods across all classes.

**Example:**

```python
getters = rj.find_methods(pattern="^get_")
```

### find_imports

```python
rj.find_imports(module: str | None = None) -> TargetList[ImportTarget]
```

Find import statements.

**Example:**

```python
typing_imports = rj.find_imports("typing")
```

### find_comments

```python
rj.find_comments(pattern: str | None = None) -> TargetList[CommentTarget]
```

Find comments matching a pattern.

**Example:**

```python
todos = rj.find_comments(pattern="TODO")
```

### find_strings

```python
rj.find_strings() -> TargetList[StringLiteralTarget]
```

Find all string literals.

**Example:**

```python
strings = rj.find_strings()
```

### find_todos

```python
rj.find_todos() -> TodoTargetList
```

Find all TODO/FIXME/XXX/HACK comments.

**Example:**

```python
todos = rj.find_todos()
fixmes = todos.by_type("FIXME")
```

## Analysis Methods

### find_analysis_issues

```python
rj.find_analysis_issues(config: AnalysisConfig | None = None) -> AnalysisTargetList
```

Run code analysis and return issues.

**Example:**

```python
issues = rj.find_analysis_issues()
high_complexity = issues.by_type("HIGH_CYCLOMATIC_COMPLEXITY")
print(issues.summary())
```

### find_security_issues

```python
rj.find_security_issues(config: SecurityConfig | None = None) -> SecurityTargetList
```

Run security scanning and return issues.

**Example:**

```python
security = rj.find_security_issues()
critical = security.critical()
```

### find_optimization_opportunities

```python
rj.find_optimization_opportunities() -> OptimizeTargetList
```

Find optimization opportunities (duplicate code, loop improvements).

**Example:**

```python
opts = rj.find_optimization_opportunities()
duplicates = opts.by_type("DUPLICATE_CODE")
```

## Directive Methods

### find_type_ignores

```python
rj.find_type_ignores() -> DirectiveTargetList
```

Find `# type: ignore` comments.

**Example:**

```python
ignores = rj.find_type_ignores()
bare = ignores.filter(lambda t: t.is_bare)
```

### find_noqa_comments

```python
rj.find_noqa_comments() -> DirectiveTargetList
```

Find `# noqa` comments.

**Example:**

```python
noqas = rj.find_noqa_comments()
```

## Transaction Methods

### transaction

```python
rj.transaction() -> Transaction
```

Start an atomic transaction. Changes are collected and applied together.

**Example:**

```python
with rj.transaction() as tx:
    rj.find_class("A").rename("B")
    rj.find_class("C").rename("D")
    # Preview before commit
    print(tx.preview())
# All changes applied atomically
```

## Import Management

### add_import

```python
rj.add_import(path: Path, import_statement: str) -> Result
```

Add an import to a file.

**Example:**

```python
rj.add_import(Path("src/module.py"), "from typing import Optional")
```

### remove_import

```python
rj.remove_import(path: Path, pattern: str) -> Result
```

Remove imports matching a pattern.

**Example:**

```python
rj.remove_import(Path("src/module.py"), r"from deprecated import.*")
```

## Low-Level Methods

### transform_file

```python
rj.transform_file(path: Path, transformer: CSTTransformer) -> Result
```

Apply a LibCST transformer to a file.

**Example:**

```python
from rejig.transformers import RenameClass

result = rj.transform_file(
    Path("src/module.py"),
    RenameClass("OldName", "NewName")
)
```

## Context Manager

Use context manager for move operations (uses Rope internally):

```python
# Required for move operations
with Rejig("src/") as rj:
    rj.find_class("X").move_to("other_module")
    rj.find_function("helper").move_to("utils")
# Cleanup happens automatically

# Without context manager, call close() manually
rj = Rejig("src/")
rj.find_class("X").move_to("other_module")
rj.close()
```
