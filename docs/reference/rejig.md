# Rejig

The main entry point for all operations.

## Overview

`Rejig` is the primary class you'll interact with. Create an instance pointed at your codebase, then use its factory methods to get targets.

```python
from rejig import Rejig

rj = Rejig("src/")
```

## Constructor

### Rejig

```python
Rejig(root: str | Path, dry_run: bool = False)
```

Create a Rejig instance.

**Parameters:**

- `root` — Base directory for all relative path operations
- `dry_run` — If True, preview changes without modifying files

**Example:**

```python
# Normal mode
rj = Rejig("src/")

# Dry-run mode
rj = Rejig("src/", dry_run=True)
```

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
```

### yaml

```python
rj.yaml(path: str | Path) -> YamlTarget
```

Get a target for a YAML file.

**Example:**

```python
config = rj.yaml("config.yml")
```

### json

```python
rj.json(path: str | Path) -> JsonTarget
```

Get a target for a JSON file.

**Example:**

```python
pkg = rj.json("package.json")
```

## Find Methods

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
process_funcs = rj.find_functions(pattern="^process_")
```

### find_files

```python
rj.find_files(glob: str = "**/*.py") -> TargetList[FileTarget]
```

Find all files matching the glob pattern.

**Parameters:**

- `glob` — Glob pattern (default: all Python files)

**Example:**

```python
all_py = rj.find_files()
tests = rj.find_files("tests/**/*.py")
```

### find_todos

```python
rj.find_todos() -> TodoTargetList
```

Find all TODO comments in the project.

**Example:**

```python
todos = rj.find_todos()
fixmes = rj.find_todos().by_type("FIXME")
```

## Properties

### root

```python
rj.root -> Path
```

The root directory for path resolution.

### dry_run

```python
rj.dry_run -> bool
```

Whether dry-run mode is enabled.

---

::: rejig.Rejig
    options:
      show_source: false
      members:
        - __init__
        - file
        - module
        - package
        - text_file
        - toml
        - yaml
        - json
        - find_classes
        - find_functions
        - find_files
        - find_todos
