# Error Handling

Rejig uses result objects instead of exceptions for predictable error handling.

## Design Philosophy

Rejig follows a **result-oriented** approach:

- Operations return `Result` objects, not values
- Failed operations return `ErrorResult`, not exceptions
- Navigation to non-existent targets returns `ErrorTarget`
- Batch operations return `BatchResult` with per-target results

This design enables:

- **Safe chaining** — No need for try/except around every call
- **Graceful degradation** — Handle failures where it makes sense
- **Batch error handling** — Know exactly which operations failed

## Result Types

### Result

Successful operations return `Result`:

```python
result = cls.rename("NewName")

result.success        # True
result.message        # "Renamed User to NewName"
result.files_changed  # [Path("models.py")]
result.data           # Optional payload
```

Results are truthy when successful:

```python
if result:
    print("Success!")
```

### ErrorResult

Failed operations return `ErrorResult`:

```python
result = cls.rename("NewName")

if result.is_error():
    result.success        # False
    result.message        # "Class 'User' not found in models.py"
    result.operation      # "rename"
    result.target_repr    # "ClassTarget(name='User')"
    result.exception      # Original exception (if any)
```

### BatchResult

Batch operations return `BatchResult`:

```python
results = classes.add_decorator("@slow")

results.success          # True only if ALL succeeded
results.partial_success  # True if ANY succeeded
results.all_failed       # True if ALL failed
results.succeeded        # list[Result]
results.failed           # list[Result]
```

## Checking Results

### Simple Check

```python
result = cls.rename("NewName")

if result:
    print("Renamed successfully")
else:
    print(f"Failed: {result.message}")
```

### Detailed Check

```python
result = cls.rename("NewName")

if result.success:
    print(f"Changed: {result.files_changed}")
elif result.is_error():
    print(f"Operation '{result.operation}' failed")
    print(f"Target: {result.target_repr}")
    print(f"Message: {result.message}")
```

### Re-raising Exceptions

If you want exception behavior:

```python
result = cls.rename("NewName")

if result.is_error():
    result.raise_if_error()  # Raises RuntimeError or original exception
```

## ErrorTarget

When navigation fails, you get an `ErrorTarget`:

```python
# This doesn't raise, even if the class doesn't exist
method = rj.file("models.py").find_class("Missing").find_method("save")

print(type(method))     # ErrorTarget
print(method.exists())  # False
```

### Safe Chaining

ErrorTarget allows chaining without defensive checks:

```python
# This entire chain is safe
result = (
    rj.file("models.py")
    .find_class("User")        # Returns ClassTarget or ErrorTarget
    .find_method("save")       # Returns MethodTarget or ErrorTarget
    .insert_statement("x = 1") # Returns Result or ErrorResult
)

# Just check the final result
if not result:
    print(f"Something failed: {result.message}")
```

### Navigation Methods Return ErrorTarget

```python
cls = rj.file("models.py").find_class("Missing")

# These return ErrorTarget, not exceptions
cls.find_method("foo")      # ErrorTarget
cls.find_methods()          # Empty TargetList
```

### Operations Return ErrorResult

```python
cls = rj.file("models.py").find_class("Missing")

# These return ErrorResult, not exceptions
result = cls.rename("NewName")
print(result.success)   # False
print(result.message)   # "Class 'Missing' not found"
```

## Batch Error Handling

### Check Overall Status

```python
results = classes.add_decorator("@slow")

if results.success:
    print("All operations succeeded")
elif results.partial_success:
    print(f"{len(results.succeeded)} succeeded, {len(results.failed)} failed")
else:
    print("All operations failed")
```

### Handle Individual Failures

```python
results = classes.add_decorator("@slow")

for result in results.failed:
    print(f"Failed: {result.message}")
    # Optionally re-raise
    # result.raise_if_error()
```

### Collect Modified Files

```python
results = classes.add_decorator("@slow")

if results.partial_success:
    print(f"Modified files: {results.files_changed}")
```

## Common Patterns

### Try Operation, Fall Back

```python
# Try to find in one location, fall back to another
cls = rj.file("models.py").find_class("User")
if not cls.exists():
    cls = rj.file("base/models.py").find_class("User")

if cls.exists():
    cls.add_method("validate")
```

### Collect All Errors

```python
errors = []

for cls in rj.find_classes(pattern="^Test"):
    result = cls.add_decorator("@pytest.mark.slow")
    if not result:
        errors.append((cls.name, result.message))

if errors:
    print("Failures:")
    for name, msg in errors:
        print(f"  {name}: {msg}")
```

### Validate Before Bulk Operation

```python
classes = rj.find_classes(pattern="^Test")

# Check all targets exist before modifying
missing = [c for c in classes if not c.exists()]
if missing:
    print(f"Missing classes: {[c.name for c in missing]}")
else:
    classes.add_decorator("@slow")
```

### Dry Run First

```python
# Preview changes
rj_dry = Rejig("src/", dry_run=True)
result = rj_dry.find_classes("User").first().rename("UserModel")
print(f"Would do: {result.message}")

# If happy, do it for real
rj = Rejig("src/")
result = rj.find_classes("User").first().rename("UserModel")
```

## When to Use Exceptions

While Rejig prefers results, you might want exceptions for:

- **Script termination** — Stop on first error
- **Integration with exception-based code** — Match existing patterns
- **Critical operations** — Fail fast

```python
result = cls.rename("NewName")
if not result:
    result.raise_if_error()  # Convert to exception
```

Or wrap operations:

```python
def rename_or_raise(target, new_name):
    result = target.rename(new_name)
    if not result:
        result.raise_if_error()
    return result
```

## Next Steps

- [Examples](../examples/refactoring-patterns.md) — Real-world patterns
- [API Reference](../reference/results.md) — Complete Result API
