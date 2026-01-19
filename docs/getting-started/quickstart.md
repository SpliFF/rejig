# Quickstart

This guide walks you through the basics of using Rejig to find and modify Python code.

## Create a Rejig Instance

Every operation starts with a `Rejig` instance pointed at your codebase:

```python
from rejig import Rejig

# Point at your source directory
rj = Rejig("src/")

# Or use the current directory
rj = Rejig(".")

# Enable dry-run mode to preview changes without modifying files
rj = Rejig("src/", dry_run=True)
```

The path you provide becomes the **root** for all relative path operations.

## Find Code Elements

Use factory methods to get **targets** — objects representing code elements:

```python
# Get a specific file
file = rj.file("mymodule.py")

# Get a module by dotted path
module = rj.module("myapp.models")

# Find a class (searches all files)
cls = rj.find_classes("UserModel").first()

# Find all functions matching a pattern
funcs = rj.find_functions(pattern="^process_")
```

## Navigate Through Code

Targets can navigate to nested elements:

```python
# File → Class → Method
method = rj.file("models.py").find_class("User").find_method("save")

# Module → Function
func = rj.module("myapp.utils").find_function("calculate")

# Class → All methods
methods = rj.find_classes("Handler").first().find_methods()
```

## Modify Code

Call methods on targets to make changes:

```python
# Rename a class
rj.find_classes("OldName").first().rename("NewName")

# Add a decorator
cls = rj.file("views.py").find_class("MyView")
cls.add_decorator("login_required")

# Add a method to a class
cls.add_method("validate", body="return self.is_valid()")

# Insert a statement at the start of a method
method = cls.find_method("save")
method.insert_statement("self.updated_at = now()")

# Add a class attribute
cls.add_attribute("created_at", type_hint="datetime", default="None")
```

## Check Results

All operations return a `Result` object:

```python
result = cls.rename("NewName")

if result.success:
    print(f"Changed files: {result.files_changed}")
else:
    print(f"Failed: {result.message}")

# Results are truthy when successful
if result:
    print("It worked!")
```

## Batch Operations

Find methods return a `TargetList` for batch operations:

```python
# Find all test classes
test_classes = rj.find_classes(pattern="^Test")

# Add a decorator to all of them
results = test_classes.add_decorator("pytest.mark.integration")

# Check the batch result
print(f"Modified {len(results.succeeded)} classes")
print(f"Failed: {len(results.failed)}")
```

## Work with Lines

Access specific lines for directive management:

```python
file = rj.file("mymodule.py")

# Add a type: ignore comment
file.line(42).add_type_ignore("arg-type")

# Work with a range of lines
file.lines(10, 20).indent()

# Find the code block containing a line
block = file.block_at_line(15)
print(f"Line 15 is inside a {block.kind}: {block.name}")
```

## Dry Run Mode

Preview changes without modifying files:

```python
rj = Rejig("src/", dry_run=True)

# Operations return what would happen
result = rj.find_classes("User").first().rename("UserModel")

# In dry-run mode, success=True but no files are modified
print(result.message)  # "Would rename User to UserModel"
```

## Next Steps

- [Core Concepts](concepts.md) — Understand targets, results, and error handling
- [Finding Code](../guides/finding-code.md) — Learn all the ways to locate code
- [Modifying Code](../guides/modifying-code.md) — Deep dive into transformations
