# Results

All operations return Result objects instead of raising exceptions.

## Result

The base result class for successful operations.

```python
@dataclass
class Result:
    success: bool
    message: str
    files_changed: list[Path]
    data: Any = None
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `success` | `bool` | Whether the operation succeeded |
| `message` | `str` | Human-readable description |
| `files_changed` | `list[Path]` | Files that were modified |
| `data` | `Any` | Optional payload for queries |

### Methods

#### \_\_bool\_\_

Results are truthy when successful:

```python
result = cls.rename("NewName")
if result:
    print("Success!")
```

#### is_error

Check if this is an error result:

```python
if result.is_error():
    print(f"Failed: {result.message}")
```

### Example

```python
result = cls.rename("NewName")

print(result.success)        # True
print(result.message)        # "Renamed User to NewName"
print(result.files_changed)  # [Path("models.py")]
```

## ErrorResult

Returned when an operation fails.

```python
@dataclass
class ErrorResult(Result):
    success: bool = False  # Always False
    exception: Exception | None = None
    operation: str = ""
    target_repr: str = ""
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `success` | `bool` | Always `False` |
| `message` | `str` | Error description |
| `exception` | `Exception \| None` | Original exception if any |
| `operation` | `str` | Name of the failed operation |
| `target_repr` | `str` | String representation of the target |

### Methods

#### raise_if_error

Convert the result to an exception:

```python
result = cls.rename("NewName")
if result.is_error():
    result.raise_if_error()  # Raises RuntimeError or original exception
```

### Example

```python
result = cls.rename("NewName")

if result.is_error():
    print(result.message)       # "Class 'User' not found"
    print(result.operation)     # "rename"
    print(result.target_repr)   # "ClassTarget(name='User')"

    if result.exception:
        print(type(result.exception))  # Original exception type
```

## BatchResult

Returned when operating on multiple targets.

```python
@dataclass
class BatchResult:
    results: list[Result]
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `results` | `list[Result]` | All individual results |
| `success` | `bool` | `True` if ALL succeeded |
| `partial_success` | `bool` | `True` if ANY succeeded |
| `all_failed` | `bool` | `True` if ALL failed |
| `succeeded` | `list[Result]` | Successful results |
| `failed` | `list[Result]` | Failed results |
| `files_changed` | `list[Path]` | All modified files |

### Methods

#### \_\_bool\_\_

Truthy only when ALL operations succeeded:

```python
results = classes.add_decorator("@slow")
if results:
    print("All succeeded!")
```

#### \_\_len\_\_

Number of operations:

```python
print(f"Processed {len(results)} targets")
```

#### \_\_iter\_\_

Iterate over all results:

```python
for result in results:
    print(result.message)
```

### Example

```python
results = rj.find_classes("^Test").add_decorator("@slow")

# Check status
if results.success:
    print(f"Added to all {len(results)} classes")
elif results.partial_success:
    print(f"Succeeded: {len(results.succeeded)}")
    print(f"Failed: {len(results.failed)}")
else:
    print("All failed")

# Handle failures
for r in results.failed:
    print(f"Failed: {r.message}")

# Get modified files
print(f"Files changed: {results.files_changed}")
```

## Common Patterns

### Simple Success Check

```python
result = cls.rename("NewName")
if result:
    print("Done!")
```

### Detailed Error Handling

```python
result = cls.rename("NewName")
if result.is_error():
    print(f"Operation: {result.operation}")
    print(f"Target: {result.target_repr}")
    print(f"Error: {result.message}")
```

### Convert to Exception

```python
result = cls.rename("NewName")
if not result:
    result.raise_if_error()
```

### Batch with Partial Failure Handling

```python
results = classes.add_decorator("@slow")

if not results.success:
    print("Some operations failed:")
    for r in results.failed:
        print(f"  - {r.message}")
```

### Collect All Errors

```python
errors = []
for cls in classes:
    result = cls.add_decorator("@slow")
    if not result:
        errors.append(result)

if errors:
    for e in errors:
        print(f"{e.target_repr}: {e.message}")
```

---

::: rejig.result
    options:
      show_source: false
      members:
        - Result
        - ErrorResult
        - BatchResult
