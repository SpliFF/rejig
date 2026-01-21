# Type Hints

Rejig provides comprehensive tools for working with Python type hints: inferring types from code, modernizing syntax to Python 3.10+, generating stub files, and managing type annotations.

## Inferring Type Hints

Rejig can infer type hints from default values, parameter names, and usage patterns.

### From Default Values

```python
from rejig import Rejig

rj = Rejig("src/")

# Infer types for a specific function
func = rj.find_function("process")
func.infer_type_hints()

# Before:
# def process(count=0, name="", items=[], enabled=True):

# After:
# def process(count: int = 0, name: str = "", items: list = [], enabled: bool = True):
```

### From Parameter Names

Rejig uses common naming conventions to infer types:

```python
# Parameter name patterns:
# count, num, total, index, size  ->  int
# is_*, has_*, should_*, can_*    ->  bool
# *_list, *_items                 ->  list
# *_dict, *_map                   ->  dict
# *_set                           ->  set
# *_str, *_name, *_text           ->  str
# *_path, *_file, *_dir           ->  Path
# *_date                          ->  date
# *_time                          ->  time
# *_datetime                      ->  datetime

func = rj.find_function("get_user")
func.infer_type_hints()

# Before:
# def get_user(user_id, is_active, user_name):

# After:
# def get_user(user_id: int, is_active: bool, user_name: str):
```

### Batch Inference

```python
# Infer types for all functions
rj.find_functions().infer_type_hints()

# Infer types for all methods in a class
rj.find_class("MyClass").find_methods().infer_type_hints()

# Infer types for functions without any type hints
rj.find_functions().filter(lambda f: not f.has_type_hints).infer_type_hints()
```

### Inference Options

```python
func.infer_type_hints(
    infer_return=True,           # Infer return type
    infer_parameters=True,       # Infer parameter types
    use_names=True,              # Use parameter name heuristics
    use_defaults=True,           # Use default value types
    use_docstring=True,          # Parse docstring for types
    preserve_existing=True,      # Don't overwrite existing hints
)
```

## Modernizing Type Hints

Convert older typing syntax to Python 3.10+ style:

### Basic Modernization

```python
# Modernize a single function
func = rj.find_function("process")
func.modernize_type_hints()

# Modernize all functions
rj.find_functions().modernize_type_hints()

# Modernize all methods
rj.find_methods().modernize_type_hints()
```

### What Gets Modernized

```python
# Before -> After

# Generic types (Python 3.9+)
List[str]           ->  list[str]
Dict[str, int]      ->  dict[str, int]
Set[int]            ->  set[int]
Tuple[int, str]     ->  tuple[int, str]
FrozenSet[str]      ->  frozenset[str]
Type[MyClass]       ->  type[MyClass]

# Optional and Union (Python 3.10+)
Optional[str]       ->  str | None
Union[str, int]     ->  str | int
Union[A, B, C]      ->  A | B | C
Optional[List[str]] ->  list[str] | None

# Callable
Callable[[int], str]  ->  Callable[[int], str]  # No change needed

# Nested types
Dict[str, List[int]]  ->  dict[str, list[int]]
Optional[Dict[str, List[int]]]  ->  dict[str, list[int]] | None
```

### Import Cleanup After Modernization

```python
# After modernization, clean up unused typing imports
rj.find_functions().modernize_type_hints()

for file in rj.find_files():
    file.find_unused_imports().delete_all()

# This removes: from typing import List, Dict, Optional, Union
# if they're no longer needed
```

## Setting Type Hints Manually

### Parameter Types

```python
func = rj.find_function("process")

# Set a single parameter type
func.set_parameter_type("data", "dict[str, Any]")

# Set multiple parameter types
func.set_parameter_type("items", "list[Item]")
func.set_parameter_type("callback", "Callable[[str], bool]")

# Set with import (automatically adds the import)
func.set_parameter_type("user", "User", import_from="myapp.models")
```

### Return Types

```python
# Set return type
func.set_return_type("list[str]")

# Set return type with import
func.set_return_type("Response", import_from="myapp.types")

# Remove return type
func.remove_return_type()
```

### Class Attributes

```python
cls = rj.find_class("MyClass")

# Add typed attribute
cls.add_attribute("items", "list[Item]", "[]")

# The type hint is included in the class body:
# class MyClass:
#     items: list[Item] = []
```

## Removing Type Hints

Sometimes you need to strip type hints (e.g., for compatibility):

```python
# Remove all type hints from a function
func = rj.find_function("process")
func.remove_type_hints()

# Remove from all functions
rj.find_functions().remove_type_hints()

# Remove only parameter hints (keep return type)
func.remove_parameter_types()

# Remove only return type (keep parameter hints)
func.remove_return_type()
```

## Converting Type Comments

Convert Python 2 style type comments to annotations:

```python
# Convert type comments to annotations
func.convert_type_comments()

# Before:
# def process(data):
#     # type: (dict) -> list
#     pass

# After:
# def process(data: dict) -> list:
#     pass

# Batch conversion
rj.find_functions().convert_type_comments()
```

## Generating Stub Files

Create .pyi stub files for type checking:

```python
from rejig import StubGenerator

generator = StubGenerator(rj)

# Generate stubs for a single file
generator.generate_stub("src/mymodule.py", "stubs/mymodule.pyi")

# Generate stubs for entire package
generator.generate_stubs("src/", "stubs/")

# Options
generator.generate_stubs(
    "src/",
    "stubs/",
    include_private=False,       # Exclude _private functions
    include_docstrings=False,    # Don't include docstrings
    infer_types=True,            # Infer missing types
)
```

### Stub Content Example

```python
# Generated stub for mymodule.pyi

from typing import Any

class MyClass:
    items: list[str]
    count: int

    def __init__(self, items: list[str] | None = None) -> None: ...
    def process(self, data: dict[str, Any]) -> list[str]: ...
    def _private_method(self) -> None: ...  # Excluded if include_private=False

def helper(value: str) -> int: ...
```

## Type Hint Analysis

### Check for Missing Type Hints

```python
# Find functions without type hints
issues = rj.find_analysis_issues()
missing_hints = issues.by_type("MISSING_TYPE_HINT")

for issue in missing_hints:
    print(f"{issue.file_path}:{issue.line_number} - {issue.name} missing type hints")
```

### Type Hint Coverage

```python
from rejig import TypeHintAnalyzer

analyzer = TypeHintAnalyzer(rj)

# Get coverage statistics
stats = analyzer.coverage_stats()
print(f"Functions with type hints: {stats.typed_functions}/{stats.total_functions}")
print(f"Methods with type hints: {stats.typed_methods}/{stats.total_methods}")
print(f"Coverage: {stats.coverage_percent:.1f}%")

# Get details by file
for file_path, file_stats in stats.by_file.items():
    print(f"{file_path}: {file_stats.coverage_percent:.1f}%")
```

### Find Inconsistent Types

```python
# Find places where the same parameter name has different types
inconsistencies = analyzer.find_inconsistent_types()

for name, types in inconsistencies.items():
    print(f"Parameter '{name}' has multiple types:")
    for type_hint, locations in types.items():
        print(f"  {type_hint}: {locations}")
```

## Common Patterns

### Add Type Hints to Legacy Code

```python
rj = Rejig("src/")

# Step 1: Infer what we can
rj.find_functions().infer_type_hints()
rj.find_methods().infer_type_hints()

# Step 2: Check coverage
from rejig import TypeHintAnalyzer
analyzer = TypeHintAnalyzer(rj)
print(analyzer.coverage_stats())

# Step 3: Find remaining untyped functions for manual review
untyped = rj.find_functions().filter(lambda f: not f.has_type_hints)
for func in untyped:
    print(f"Needs manual types: {func.file_path}:{func.name}")
```

### Modernize an Entire Codebase

```python
rj = Rejig("src/")

# Modernize type hints
rj.find_functions().modernize_type_hints()
rj.find_methods().modernize_type_hints()

# Clean up imports
for file in rj.find_files():
    file.find_unused_imports().delete_all()

# Add future annotations for forward references
for file in rj.find_files():
    file.add_import("from __future__ import annotations")
```

### Enforce Type Hint Standards

```python
# In CI/pre-commit, check that new code has type hints
rj = Rejig("src/")

# Find functions added since last commit
# (you'd filter by changed files in practice)
issues = rj.find_analysis_issues()
missing = issues.by_type("MISSING_TYPE_HINT")

if missing:
    print("Functions missing type hints:")
    for issue in missing:
        print(f"  {issue.file_path}:{issue.line_number} - {issue.name}")
    exit(1)
```

### Generate Types for Third-Party Libraries

```python
from rejig import StubGenerator

# Generate stubs for a vendored library
generator = StubGenerator(Rejig("vendor/"))
generator.generate_stubs(
    "vendor/external_lib/",
    "stubs/external_lib/",
    infer_types=True,
)
```

## Integration with mypy

### Add Type Ignore Comments

```python
# Add type: ignore to a specific line
line = rj.file("module.py").find_line(42)
line.add_type_ignore(["arg-type"])  # Specific error code

# Find and fix bare type: ignore comments
type_ignores = rj.find_type_ignores()
bare = type_ignores.filter(lambda t: t.is_bare)
for ignore in bare:
    # Make them specific
    ignore.update_codes(["type-arg"])
```

### Remove Unnecessary Type Ignores

```python
# After fixing type issues, remove unnecessary ignores
# (This requires running mypy and parsing output)

# Manually remove specific ignores
type_ignores = rj.find_type_ignores()
type_ignores.by_codes(["import"]).delete_all()  # Remove import ignores
```
