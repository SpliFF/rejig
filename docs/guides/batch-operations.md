# Batch Operations

Apply changes to multiple targets at once.

## TargetList

When you find multiple items, you get a `TargetList`:

```python
classes = rj.find_classes(pattern="^Test")  # TargetList[ClassTarget]
funcs = rj.find_functions()                  # TargetList[FunctionTarget]
```

## Iteration

```python
for cls in classes:
    print(f"{cls.name} in {cls.file_path}")
```

## Accessing Items

```python
classes.first()    # First target or None
classes.last()     # Last target or None
classes[0]         # First target (raises IndexError if empty)
classes[2:5]       # Slice (returns list)
len(classes)       # Number of targets
bool(classes)      # True if not empty
classes.to_list()  # Convert to plain list
```

## Filtering

### By Predicate

```python
# Keep only classes with docstrings
classes.filter(lambda c: c.has_docstring())

# Keep only functions with type hints
funcs.filter(lambda f: f.has_type_hints())

# Keep only targets that exist
targets.filter(lambda t: t.exists())
```

### By File

```python
classes.in_file(Path("models.py"))
classes.in_file("models.py")  # String also works
```

### By Name Pattern

```python
classes.matching("User")       # Name contains "User"
classes.matching("^Base")      # Name starts with "Base"
classes.matching("Handler$")   # Name ends with "Handler"
```

### Chaining Filters

```python
targets = (
    rj.find_classes()
    .filter(lambda c: not c.has_docstring())
    .in_file("models.py")
    .matching("^User")
)
```

## Batch Operations

Operations on `TargetList` apply to all targets and return a `BatchResult`:

### Decorators

```python
results = classes.add_decorator("dataclass")
results = classes.remove_decorator("deprecated")
```

### Renaming

```python
# Rename using regex substitution
results = classes.rename(r"^Old", "New")  # OldUser → NewUser
results = funcs.rename(r"_v1$", "_v2")    # process_v1 → process_v2
```

### Deleting

```python
results = classes.delete()
results = funcs.delete()
```

### Inserting Statements

```python
methods = cls.find_methods()
results = methods.insert_statement("self.log_call()", position="start")
```

### Aliases

Some batch methods have `_all` aliases for clarity:

```python
classes.delete_all()           # Same as delete()
classes.add_decorator_all()    # Same as add_decorator()
classes.rename_all()           # Same as rename()
```

## BatchResult

Batch operations return a `BatchResult`:

```python
results = classes.add_decorator("@slow")

# Check overall status
results.success          # True if ALL operations succeeded
results.partial_success  # True if ANY operation succeeded
results.all_failed       # True if ALL operations failed

# Access individual results
results.succeeded        # list[Result] - successful operations
results.failed           # list[Result] - failed operations

# Aggregate information
results.files_changed    # list[Path] - all files modified
len(results)             # Total number of operations

# Iterate
for result in results:
    print(result.message)
```

### Handling Partial Failures

```python
results = classes.add_decorator("@pytest.mark.slow")

if results.success:
    print(f"Added decorator to all {len(results)} classes")
elif results.partial_success:
    print(f"Succeeded: {len(results.succeeded)}, Failed: {len(results.failed)}")
    for r in results.failed:
        print(f"  Failed: {r.message}")
else:
    print("All operations failed")
```

## Common Patterns

### Add Decorator to All Test Classes

```python
results = rj.find_classes(pattern="^Test").add_decorator("pytest.mark.integration")
```

### Generate Docstrings for Functions Without Them

```python
results = (
    rj.find_functions()
    .filter(lambda f: not f.has_docstring())
    .generate_docstrings(style="google")
)
```

### Add Type Hints to All Public Functions

```python
results = (
    rj.find_functions()
    .filter(lambda f: not f.name.startswith("_"))
    .filter(lambda f: not f.has_type_hints())
    .infer_type_hints()
)
```

### Rename Methods Across Multiple Classes

```python
for cls in rj.find_classes(pattern=".*Repository"):
    cls.find_method("get_all").rename("list_all")
```

### Delete All Deprecated Methods

```python
results = (
    rj.find_classes()
    .find_methods(pattern=".*")
    .filter(lambda m: "@deprecated" in str(m.get_content().data or ""))
    .delete()
)
```

### Bulk Add Type Ignore

```python
# Find all lines with mypy errors and add ignores
for file in rj.find_files():
    for line_num in get_mypy_error_lines(file.path):  # Your function
        file.line(line_num).add_type_ignore()
```

## Performance Considerations

Batch operations are generally more efficient than looping:

```python
# Preferred - single batch operation
rj.find_classes("^Test").add_decorator("@slow")

# Less efficient - individual operations
for cls in rj.find_classes("^Test"):
    cls.add_decorator("@slow")
```

The batch approach:
- Parses each file once
- Applies all changes in a single pass
- Writes each file once

## Next Steps

- [Config Files](config-files.md) — Work with TOML, YAML, and JSON
- [Error Handling](error-handling.md) — Handle failures gracefully
