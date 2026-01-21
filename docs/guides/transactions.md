# Transactions

Rejig supports atomic transactions for batch operations. Changes are collected and applied together, with automatic rollback on failure.

## Basic Usage

```python
from rejig import Rejig

rj = Rejig("src/")

# Use context manager for automatic commit/rollback
with rj.transaction() as tx:
    rj.find_class("OldClass").rename("NewClass")
    rj.find_function("old_func").rename("new_func")
    rj.find_method("process").add_parameter("timeout", "int", "30")

# All changes applied atomically when exiting the context
```

## How Transactions Work

1. **Collection Phase**: All modifications are collected but not written
2. **Commit Phase**: On successful exit, all changes are written atomically
3. **Rollback Phase**: On exception, no changes are written

```python
rj = Rejig("src/")

with rj.transaction():
    # These changes are collected, not immediately written
    rj.find_class("A").rename("B")
    rj.find_class("C").rename("D")

    # If an exception occurs here, nothing is written
    if some_condition:
        raise ValueError("Abort!")

    # More changes...
    rj.find_function("x").rename("y")

# Only here are all changes written together
```

## Manual Transaction Control

For more control, use explicit commit/rollback:

```python
tx = rj.transaction()
tx.begin()

try:
    rj.find_class("A").rename("B")
    rj.find_class("C").rename("D")

    # Validate changes before committing
    if validation_passes():
        tx.commit()
    else:
        tx.rollback()
except Exception:
    tx.rollback()
    raise
```

## Preview Changes

See what would be modified before committing:

```python
with rj.transaction() as tx:
    rj.find_class("OldName").rename("NewName")
    rj.find_function("helper").add_decorator("cache")

    # Preview changes
    preview = tx.preview()

    print(f"Files to modify: {preview.files_changed}")
    print(f"Diff:\n{preview.diff}")

    # Optionally abort
    if not confirm("Apply changes?"):
        tx.rollback()
        return

# Changes applied on exit (if not rolled back)
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
    print(tx.has_changes)  # True
    print(len(tx.pending_changes))  # 1
```

## Nested Transactions

Transactions cannot be nested. Starting a new transaction inside an existing one will raise an error:

```python
with rj.transaction():
    # This will raise an error
    with rj.transaction():  # Error: Already in transaction
        pass
```

If you need nested behavior, use savepoints (manual approach):

```python
with rj.transaction() as tx:
    rj.find_class("A").rename("B")

    # Save current state
    savepoint = tx.create_savepoint()

    try:
        rj.find_class("C").rename("D")
        rj.find_class("E").rename("F")
    except Exception:
        # Rollback to savepoint, keeping earlier changes
        tx.rollback_to_savepoint(savepoint)
```

## Batch Result from Transaction

Get a combined result for all operations:

```python
with rj.transaction() as tx:
    result1 = rj.find_class("A").rename("B")
    result2 = rj.find_function("x").rename("y")
    result3 = rj.find_method("m").add_decorator("cache")

# Get combined result
batch_result = tx.result

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

# Transaction commits with partial success
# Only successful operations are applied
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
```

## Use Cases

### Coordinated Renames

```python
with rj.transaction():
    # Rename class and update all method references
    cls = rj.find_class("UserManager")
    cls.rename("UserService")

    # Update factory function
    rj.find_function("get_user_manager").rename("get_user_service")

    # Update type hints referencing the old name
    for func in rj.find_functions():
        if "UserManager" in func.get_type_hints():
            func.replace_type_hint("UserManager", "UserService")
```

### Safe Migration

```python
def migrate_api_version():
    rj = Rejig("src/")

    with rj.transaction() as tx:
        # Update version constant
        rj.find_module("myapp.version").find_assignment("API_VERSION").rewrite("API_VERSION = '2.0'")

        # Update all endpoint decorators
        for method in rj.find_methods(pattern="^(get|post|put|delete)_"):
            method.replace_decorator_arg("api_version", "'1.0'", "'2.0'")

        # Preview and confirm
        print(tx.preview().diff)
        if not confirm("Apply migration?"):
            tx.rollback()
            return False

    return True
```

### Batch Refactoring

```python
with rj.transaction():
    # Add logging to all API endpoints
    for cls in rj.find_classes(pattern=".*View$"):
        for method in cls.find_methods():
            if method.name in ["get", "post", "put", "delete"]:
                method.insert_statement("logger.info(f'API call: {request.path}')")

    # Add timing decorator
    for func in rj.find_functions().in_directory("src/api/"):
        func.add_decorator("timing")
```

### Conditional Commit

```python
with rj.transaction() as tx:
    # Collect all changes
    rj.find_classes().add_decorator("dataclass")

    # Run tests to verify changes work
    preview = tx.preview()
    preview.write_to_temp()  # Write to temp files

    test_result = run_tests_on_temp()

    if not test_result.passed:
        print("Tests failed, rolling back")
        tx.rollback()
    # else: auto-commit on exit
```

## Dry Run with Transactions

Combine dry run mode with transactions:

```python
rj = Rejig("src/", dry_run=True)

with rj.transaction() as tx:
    rj.find_class("A").rename("B")
    rj.find_function("x").rename("y")

    # Even in dry run, preview shows what would happen
    print(tx.preview().diff)

# Nothing is written (dry run mode)
# But you can see the complete diff of all changes
```

## Best Practices

1. **Keep transactions focused**: Don't mix unrelated changes
2. **Preview before commit**: Use `tx.preview()` for complex changes
3. **Handle errors**: Decide whether to abort or continue on failures
4. **Use dry run for testing**: Test your refactoring logic safely
5. **Avoid side effects**: Don't perform I/O during collection phase
