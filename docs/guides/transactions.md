# Transactions

Rejig supports atomic transactions for batch operations. Changes are collected and applied together, with automatic rollback on failure.

## Basic Usage

```python
from rejig import Rejig

rj = Rejig("src/")

# Use the context manager to collect changes, then commit explicitly
with rj.transaction() as tx:
    rj.find_class("OldClass").rename("NewClass")
    rj.find_function("old_func").rename("new_func")
    rj.find_class("Job").find_method("process").add_parameter("timeout", "int", "30")

    # Apply all changes atomically
    tx.commit()
```

## How Transactions Work

1. **Collection Phase**: All modifications are collected but not written
2. **Commit Phase**: Calling `tx.commit()` writes all changes atomically
3. **Rollback Phase**: If the context exits without committing (e.g. on an
   exception, or if you simply never call `commit()`), the transaction is
   automatically rolled back and no changes are written

```python
rj = Rejig("src/")

with rj.transaction() as tx:
    # These changes are collected, not immediately written
    rj.find_class("A").rename("B")
    rj.find_class("C").rename("D")

    # If an exception occurs here, nothing is written
    if some_condition:
        raise ValueError("Abort!")

    # More changes...
    rj.find_function("x").rename("y")

    # Write all changes together
    tx.commit()
```

## Manual Transaction Control

For more control, decide whether to commit or roll back inside the context:

```python
with rj.transaction() as tx:
    rj.find_class("A").rename("B")
    rj.find_class("C").rename("D")

    # Validate changes before committing
    if validation_passes():
        tx.commit()
    else:
        tx.rollback()

# If neither commit() nor rollback() is called (e.g. an exception
# propagates), the transaction is auto-rolled back on exit.
```

## Preview Changes

See what would be modified before committing:

```python
with rj.transaction() as tx:
    rj.find_class("OldName").rename("NewName")
    rj.find_function("helper").add_decorator("cache")

    # preview() returns a combined unified diff string
    print(f"Files to modify: {tx.pending_files}")
    print(f"Diff:\n{tx.preview()}")

    # Optionally abort
    if not confirm("Apply changes?"):
        tx.rollback()
        return

    tx.commit()
```

## Transaction Status

Check the current transaction state:

```python
rj = Rejig("src/")

# Check if in transaction
print(rj.in_transaction)  # False

with rj.transaction() as tx:
    print(rj.in_transaction)  # True

    # Access current transaction
    current = rj.current_transaction
    print(current is tx)  # True

    # Transaction has pending changes
    rj.find_class("A").rename("B")
    print(tx.pending_count)        # 1 (files with pending changes)
    print(tx.pending_files)        # [Path("models.py")]
```

## Nested Transactions

Transactions cannot be nested. Starting a new transaction inside an existing one will raise an error:

```python
with rj.transaction():
    # This raises RuntimeError: Nested transactions are not supported
    with rj.transaction():
        pass
```

## Batch Result from Transaction

`tx.commit()` returns a `BatchResult` covering every applied change:

```python
with rj.transaction() as tx:
    rj.find_class("A").rename("B")
    rj.find_function("x").rename("y")
    rj.find_class("Worker").find_method("run").add_decorator("cache")

    # commit() returns the combined result
    batch_result = tx.commit()

print(f"Success: {batch_result.success}")
print(f"Files changed: {batch_result.files_changed}")
print(f"Operations: {len(batch_result)}")

# Access individual results
for result in batch_result:
    print(f"  {result.message}")
```

## Error Handling

### Automatic Rollback

```python
try:
    with rj.transaction():
        rj.find_class("A").rename("B")
        raise ValueError("Something went wrong")
        rj.find_class("C").rename("D")  # Never reached
except ValueError:
    # Transaction was automatically rolled back
    # No files were modified
    pass
```

### Handling Partial Failures

Operations that fail return ErrorResult but don't abort the transaction:

```python
with rj.transaction() as tx:
    # This succeeds
    result1 = rj.find_class("Existing").rename("NewName")

    # This fails (class doesn't exist) but doesn't abort
    result2 = rj.find_class("NonExistent").rename("Something")

    # This still runs
    result3 = rj.find_function("helper").rename("utility")

    # Commit applies only the successful operations
    tx.commit()
```

To abort on any failure:

```python
with rj.transaction() as tx:
    results = []

    results.append(rj.find_class("A").rename("B"))
    results.append(rj.find_class("C").rename("D"))
    results.append(rj.find_function("x").rename("y"))

    # Check all succeeded
    if not all(results):
        failed = [r for r in results if not r.success]
        for r in failed:
            print(f"Failed: {r.message}")
        tx.rollback()
    else:
        tx.commit()
```

## Use Cases

### Coordinated Renames

```python
with rj.transaction() as tx:
    # Rename class and update all method references
    cls = rj.find_class("UserManager")
    cls.rename("UserService")

    # Update factory function
    rj.find_function("get_user_manager").rename("get_user_service")

    # Update remaining textual references (e.g. type hints) across files
    for file in rj.find_files():
        file.replace_pattern(r"\bUserManager\b", "UserService")

    tx.commit()
```

### Safe Migration

```python
def migrate_api_version():
    rj = Rejig("src/")

    with rj.transaction() as tx:
        # Update version constant
        rj.file("myapp/version.py").replace_pattern(
            r"API_VERSION = '1\.0'", "API_VERSION = '2.0'"
        )

        # Update the api_version argument wherever it appears
        for file in rj.find_files():
            file.replace_pattern(r"api_version='1\.0'", "api_version='2.0'")

        # Preview and confirm (preview() returns a unified diff string)
        print(tx.preview())
        if not confirm("Apply migration?"):
            tx.rollback()
            return False

        tx.commit()

    return True
```

### Batch Refactoring

```python
with rj.transaction() as tx:
    # Add logging to all API endpoints
    for cls in rj.find_classes(pattern=".*View$"):
        for method in cls.find_methods():
            if method.name in ["get", "post", "put", "delete"]:
                method.insert_statement("logger.info(f'API call: {request.path}')")

    # Add timing decorator to functions under src/api/
    api_funcs = rj.find_functions().filter(
        lambda f: "src/api/" in str(f.file_path)
    )
    for func in api_funcs:
        func.add_decorator("timing")

    tx.commit()
```

### Conditional Commit

```python
with rj.transaction() as tx:
    # Collect all changes
    rj.find_classes().add_decorator("dataclass")

    # Inspect the combined diff before deciding
    diff = tx.preview()  # unified diff string
    if not changes_look_safe(diff):  # your validation function
        print("Changes failed validation, rolling back")
        tx.rollback()
    else:
        tx.commit()
```

## Dry Run with Transactions

Combine dry run mode with transactions:

```python
rj = Rejig("src/", dry_run=True)

with rj.transaction() as tx:
    rj.find_class("A").rename("B")
    rj.find_function("x").rename("y")

    # Even in dry run, preview shows what would happen
    print(tx.preview())

# Nothing is written (dry run mode)
# But you can see the complete diff of all changes
```

## Best Practices

1. **Keep transactions focused**: Don't mix unrelated changes
2. **Preview before commit**: Use `tx.preview()` for complex changes
3. **Handle errors**: Decide whether to abort or continue on failures
4. **Use dry run for testing**: Test your refactoring logic safely
5. **Avoid side effects**: Don't perform I/O during collection phase
