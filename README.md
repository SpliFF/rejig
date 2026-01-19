# Manipylate

A Python library for programmatic code refactoring using LibCST.

## Installation

```bash
pip install rejig

# For Django project support (includes rope)
pip install rejig[django]
```

## Quick Start

```python
from rejig import Manipylate

# Initialize with a directory or glob pattern
pym = Manipylate("src/")

# Find and modify a class
pym.find_class("MyClass").add_attribute("count", "int", "0")

# Chain operations on methods
pym.find_class("MyClass").find_method("process").insert_statement("self.validate()")

# Preview changes without modifying files
pym = Manipylate("src/", dry_run=True)
result = pym.find_class("MyClass").add_attribute("x", "int", "0")
print(result.message)  # [DRY RUN] Would add attribute...
```

## Core API

### Manipylate

The main entry point for code refactoring operations.

```python
from rejig import Manipylate

# Work with all Python files in a directory
pym = Manipylate("src/myproject/")

# Work with specific files using glob patterns
pym = Manipylate("src/**/*_views.py")

# Work with a single file
pym = Manipylate("path/to/file.py")
```

### Finding Code Elements

```python
# Find a class
class_scope = pym.find_class("MyClass")

# Find a method within a class
method_scope = pym.find_class("MyClass").find_method("my_method")

# Find a module-level function
func_scope = pym.find_function("process_data")

# Search for patterns
results = pym.search(r"TODO:.*")
for match in results:
    print(f"{match.file_path}:{match.line_number} - {match.name}")
```

### Class Operations

```python
class_scope = pym.find_class("MyClass")

# Add a class attribute
class_scope.add_attribute("cache", "dict[str, Any] | None", "None")

# Remove a class attribute
class_scope.remove_attribute("old_attr")

# Rename the class
class_scope.rename("NewClassName")

# Add/remove decorators
class_scope.add_decorator("dataclass")
class_scope.remove_decorator("deprecated")
```

### Method Operations

```python
method_scope = pym.find_class("MyClass").find_method("process")

# Insert a statement at the start of the method
method_scope.insert_statement("self.validate()")

# Add a parameter
method_scope.add_parameter("timeout", "int", "30")

# Replace identifiers within the method
method_scope.replace_identifier("cache", "cls._cache")

# Convert staticmethod to classmethod
method_scope.convert_to_classmethod()

# Add/remove decorators
method_scope.add_decorator("cached_property")
method_scope.remove_decorator("staticmethod")

# Rename the method
method_scope.rename("new_method_name")

# Insert code before/after matching lines
method_scope.insert_before_match(r"return\s+", "self.log_result(result)")
method_scope.insert_after_match(r"result\s*=", "self.validate_result(result)")
```

### Function Operations

```python
func_scope = pym.find_function("process_data")

# Insert a statement
func_scope.insert_statement("validate_input(data)")

# Add a decorator
func_scope.add_decorator("lru_cache")

# Rename the function
func_scope.rename("handle_data")
```

## Move Operations (Rope-based)

Move classes and functions between modules with automatic import updates:

```python
from rejig import Manipylate

# Use context manager for automatic cleanup
with Manipylate("src/") as pym:
	# Move a class to a new module
	pym.move_class(Path("src/old.py"), "MyClass", "new_module")

	# Move a function
	pym.move_function(Path("src/utils.py"), "helper", "new_utils")

# Or use the fluent API
with Manipylate("src/") as pym:
	pym.find_class("MyClass").move_to("new_module.models")
	pym.find_function("helper").move_to("utils.common")

# Without context manager (manual cleanup)
pym = Manipylate("src/")
pym.find_class("MyClass").move_to("other_module")
pym.close()  # Always close after move operations
```

## Django Project Support

For Django-specific operations, use the `DjangoProject` class:

```python
from rejig.django import DjangoProject

with DjangoProject("/path/to/project") as project:
	# Settings management
	project.add_installed_app("myapp", after_app="django.contrib.auth")
	project.add_middleware("myapp.middleware.CustomMiddleware", position="first")
	project.add_setting("MY_SETTING", '"value"', comment="Custom setting")
	project.update_setting("DEBUG", "False")
	project.delete_setting("DEPRECATED_SETTING")

	# URL configuration
	project.add_url_include("myapp.urls", path_prefix="api/")
	project.add_url_pattern("healthcheck/", "HealthView.as_view()", name="healthcheck")
	project.remove_url_pattern_by_view("OldView")

	# Dependency management (pyproject.toml)
	project.add_dependency("requests", "^2.28.0")
	project.update_dependency("django", "^4.2.0")
	project.remove_dependency("deprecated-package")

	# App discovery
	app_name = project.find_app_containing_class("MyView", filename="views.py")
	file_path = project.find_file_containing_class("MyModel")

	# Code movement (same as core Manipylate)
	project.move_class(source_file, "MyClass", "newapp.models")
	project.move_function(source_file, "helper_func", "utils.helpers")
```

## Result Handling

All operations return a `RefactorResult`:

```python
result = class_scope.add_attribute("count", "int", "0")

if result.success:
    print(f"Success: {result.message}")
    for file in result.files_changed or []:
        print(f"  Modified: {file}")
else:
    print(f"Failed: {result.message}")

# Results are also truthy/falsy
if result:
    print("Operation succeeded!")
```

## Dry Run Mode

Preview changes without modifying files:

```python
pym = Manipylate("src/", dry_run=True)
result = pym.find_class("MyClass").add_attribute("x", "int", "0")
print(result.message)  # [DRY RUN] Would add attribute x to MyClass
print(result.files_changed)  # Shows files that would be modified
```

## Advanced Usage

### Custom Transformers

You can use LibCST transformers directly:

```python
import libcst as cst
from rejig import Manipylate


class MyTransformer(cst.CSTTransformer):
	# Your custom transformer logic
	pass


pym = Manipylate("src/")
for file_path in pym.files:
	result = pym.transform_file(file_path, MyTransformer())
```

### Import Management

```python
from pathlib import Path

pym = Manipylate("src/")

# Add an import
pym.add_import(Path("src/module.py"), "from typing import Optional")

# Remove an import
pym.remove_import(Path("src/module.py"), r"from deprecated import.*")
```

## Requirements

- Python 3.10+
- libcst >= 1.0.0
- rope >= 1.0.0

## License

MIT
