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

# Infer types for functions that lack type hints
rj.find_functions_without_type_hints().infer_type_hints()
```

### Inference Options

By default, existing hints are preserved. Pass `overwrite=True` to replace them:

```python
# Keep existing hints (default)
func.infer_type_hints()

# Re-infer and overwrite existing hints
func.infer_type_hints(overwrite=True)
```

## Modernizing Type Hints

Convert older typing syntax to Python 3.10+ style:

### Basic Modernization

```python
# Modernize all functions (batch operation on a TargetList)
rj.find_functions().modernize_type_hints()

# Modernize all methods in a class
rj.find_class("MyClass").find_methods().modernize_type_hints()

# Modernize an entire file
rj.file("module.py").modernize_type_hints()
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

# For types from another module, add the import separately
func.set_parameter_type("user", "User")
rj.file(func.file_path).add_import("from myapp.models import User")
```

### Return Types

```python
# Set return type
func.set_return_type("list[str]")
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
# Remove all type hints from a function (parameters and return type)
func = rj.find_function("process")
func.remove_type_hints()

# Remove from all functions
rj.find_functions().remove_type_hints()
```

## Converting Type Comments

Convert Python 2 style type comments to annotations:

```python
# Convert type comments to annotations across all functions
rj.find_functions().convert_type_comments()

# Before:
# def process(data):
#     # type: (dict) -> list
#     pass

# After:
# def process(data: dict) -> list:
#     pass

# Methods in a class
rj.find_class("MyClass").find_methods().convert_type_comments()
```

## Generating Stub Files

Create .pyi stub files for type checking:

```python
from pathlib import Path
from rejig.typehints import StubGenerator

generator = StubGenerator(rj)

# Generate the stub text for a single file (returns a string)
stub_text = generator.generate_stub(Path("src/mymodule.py"))

# Write a .pyi stub for a single file (output_dir defaults to a 'stubs/' dir)
generator.generate_for_file(Path("src/mymodule.py"), Path("stubs/"))

# Generate stubs for an entire package
generator.generate_for_package(Path("src/mypackage/"), Path("stubs/"))
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
# Find functions and methods that lack type hints
missing_hints = rj.find_functions_without_type_hints()

for issue in missing_hints:
    print(f"{issue.location} - {issue.name} missing type hints")
```

The result is an `AnalysisTargetList`. Each item exposes `.location`, `.name`,
`.message`, and `.line_number`, and can navigate back to the function:

```python
for issue in rj.find_functions_without_type_hints():
    func = issue.to_function_target()
    func.infer_type_hints()
```

## Common Patterns

### Add Type Hints to Legacy Code

```python
rj = Rejig("src/")

# Step 1: Infer what we can
rj.find_functions().infer_type_hints()

# Step 2: Find remaining untyped functions for manual review
for issue in rj.find_functions_without_type_hints():
    print(f"Needs manual types: {issue.location} - {issue.name}")
```

### Modernize an Entire Codebase

```python
rj = Rejig("src/")

# Modernize type hints
rj.find_functions().modernize_type_hints()

# Clean up imports
for file in rj.find_files():
    file.find_unused_imports().delete()

# Add future annotations for forward references
for file in rj.find_files():
    file.add_import("from __future__ import annotations")
```

### Enforce Type Hint Standards

```python
# In CI/pre-commit, check that new code has type hints
rj = Rejig("src/")

missing = rj.find_functions_without_type_hints()

if missing:
    print("Functions missing type hints:")
    for issue in missing:
        print(f"  {issue.location} - {issue.name}")
    exit(1)
```

### Generate Types for Third-Party Libraries

```python
from pathlib import Path
from rejig.typehints import StubGenerator

# Generate stubs for a vendored library
generator = StubGenerator(Rejig("vendor/"))
generator.generate_for_package(
    Path("vendor/external_lib/"),
    Path("stubs/external_lib/"),
)
```

## Integration with mypy

### Add Type Ignore Comments

```python
# Add type: ignore to a specific line
line = rj.file("module.py").line(42)
line.add_type_ignore("arg-type")  # Specific error code

# Find and fix bare type: ignore comments
type_ignores = rj.find_type_ignores()
for ignore in type_ignores.bare():
    # Make them specific by adding a code
    ignore.add_code("type-arg")
```

### Remove Unnecessary Type Ignores

```python
# After fixing type issues, remove unnecessary ignores
# (This requires running mypy and parsing output)

# Manually remove ignores carrying a specific code
type_ignores = rj.find_type_ignores()
type_ignores.with_code("import").delete()  # Remove import ignores
```
