# Refactoring Patterns

Common refactoring scenarios with Rejig.

## Renaming

### Rename a Class

```python
from rejig import Rejig

rj = Rejig("src/")

# Find and rename
cls = rj.find_classes("OldClassName").first()
if cls:
    result = cls.rename("NewClassName")
    print(f"Changed: {result.files_changed}")
```

### Rename a Method Across Classes

```python
# Rename in a specific class
cls = rj.file("models.py").find_class("User")
cls.find_method("get_name").rename("get_full_name")

# Rename in all classes that have it
for cls in rj.find_classes():
    method = cls.find_method("old_method")
    if method.exists():
        method.rename("new_method")
```

### Rename with Pattern

```python
# Rename all classes matching a pattern
results = rj.find_classes(pattern="^Old").rename(r"^Old", "New")
# OldUser → NewUser, OldOrder → NewOrder
```

## Adding Code

### Add Method to All Classes

```python
# Add a `validate` method to all model classes
for cls in rj.find_classes(pattern=".*Model$"):
    if not cls.find_method("validate").exists():
        cls.add_method("validate", body="return True", return_type="bool")
```

### Add Decorator to Test Classes

```python
rj.find_classes(pattern="^Test").add_decorator("pytest.mark.integration")
```

### Add Type Hints

```python
# Add return type to all public functions
for func in rj.find_functions():
    if not func.name.startswith("_") and not func.has_type_hints():
        func.set_return_type("None")  # Or infer: func.infer_type_hints()
```

### Add Docstrings

```python
# Generate docstrings for undocumented functions
(
    rj.find_functions()
    .filter(lambda f: not f.has_docstring())
    .generate_docstrings(style="google")
)
```

## Removing Code

### Remove Deprecated Decorator

```python
rj.find_classes().remove_decorator("deprecated")
rj.find_functions().remove_decorator("deprecated")
```

### Remove Unused Imports

```python
for file in rj.find_files():
    file.remove_unused_imports()
```

### Delete Methods

```python
# Delete all methods named `_old_helper`
for cls in rj.find_classes():
    method = cls.find_method("_old_helper")
    if method.exists():
        method.delete()
```

## Moving Code

### Extract Method to Function

```python
cls = rj.file("views.py").find_class("UserView")
method = cls.find_method("_format_response")
method.extract_to_function("format_response")
```

### Move Lines

```python
file = rj.file("utils.py")

# Move a block of code to a different position
file.lines(50, 75).move_to(10)

# Move to another file
file.lines(100, 150).move_to_file("helpers.py", after_line=20)
```

## Converting Code

### Convert Classes to Dataclasses

```python
# Find classes that look like data containers
for cls in rj.find_classes():
    methods = cls.find_methods()
    # If only __init__ and simple methods, convert
    if len(methods) <= 3:
        cls.convert_to_dataclass()
```

### Convert Sync to Async

```python
# Convert all functions in an async module
for func in rj.file("async_utils.py").find_functions():
    func.convert_to_async()
```

### Modernize Type Hints

```python
# Update to Python 3.10+ style
for file in rj.find_files():
    file.modernize_type_hints()  # List[str] → list[str]
```

## Bulk Updates

### Add Logging to All Methods

```python
for cls in rj.find_classes(pattern=".*Service$"):
    for method in cls.find_methods():
        if not method.name.startswith("_"):
            method.insert_statement(
                f"logger.debug('Entering {method.name}')",
                position="start"
            )
```

### Add Validation to Setters

```python
for cls in rj.find_classes(pattern=".*Model$"):
    for method in cls.find_methods(pattern="^set_"):
        method.insert_statement("self._validate()", position="start")
```

### Standardize Error Handling

```python
for func in rj.find_functions(pattern="^fetch_"):
    func.wrap_with_try_except(
        exceptions=["ConnectionError", "Timeout"],
        handler="logger.error(f'Fetch failed: {e}'); raise"
    )
```

## Configuration Updates

### Update pyproject.toml

```python
toml = rj.toml("pyproject.toml")

# Update version
toml.set("project.version", "2.0.0")

# Configure tools
toml.set("tool.black.line-length", 110)
toml.set("tool.ruff.select", ["E", "F", "W", "I"])
```

### Sync Versions Across Files

```python
version = "2.0.0"

rj.toml("pyproject.toml").set("project.version", version)
rj.json("package.json").set("version", version)

init = rj.file("src/mypackage/__init__.py")
init.replace_pattern(r'__version__ = "[^"]+"', f'__version__ = "{version}"')
```

## Safety Patterns

### Dry Run First

```python
# Preview changes
rj_dry = Rejig("src/", dry_run=True)
result = rj_dry.find_classes("User").first().rename("UserModel")
print(f"Would: {result.message}")

# Then apply
rj = Rejig("src/")
result = rj.find_classes("User").first().rename("UserModel")
```

### Validate Before Bulk Changes

```python
classes = rj.find_classes(pattern="^Test")

# Check what will be affected
print(f"Will modify {len(classes)} classes:")
for cls in classes:
    print(f"  - {cls.name} in {cls.file_path}")

# Confirm before proceeding
if input("Continue? [y/N] ").lower() == "y":
    classes.add_decorator("@slow")
```

### Handle Partial Failures

```python
results = rj.find_classes().add_decorator("@dataclass")

if results.partial_success:
    print(f"Succeeded: {len(results.succeeded)}")
    print(f"Failed: {len(results.failed)}")

    for r in results.failed:
        print(f"  - {r.message}")
```
