# Core Concepts

Understanding these concepts will help you use Rejig effectively.

## Targets

A **target** is an object representing something in your codebase that you can inspect or modify. Everything in Rejig is a target.

### Python Targets

| Target | Represents | Example |
|--------|------------|---------|
| `FileTarget` | A Python file | `rj.file("app.py")` |
| `ModuleTarget` | A module by dotted path | `rj.module("myapp.models")` |
| `PackageTarget` | A package directory | `rj.package("myapp/")` |
| `ClassTarget` | A class definition | `file.find_class("User")` |
| `FunctionTarget` | A module-level function | `file.find_function("main")` |
| `MethodTarget` | A method in a class | `cls.find_method("save")` |
| `LineTarget` | A single line | `file.line(42)` |
| `LineBlockTarget` | A range of lines | `file.lines(10, 20)` |
| `CodeBlockTarget` | A code structure | `file.block_at_line(15)` |

### Config Targets

| Target | Represents | Example |
|--------|------------|---------|
| `TomlTarget` | A TOML file | `rj.toml("pyproject.toml")` |
| `YamlTarget` | A YAML file | `rj.yaml("config.yml")` |
| `JsonTarget` | A JSON file | `rj.json("package.json")` |
| `TextFileTarget` | Any text file | `rj.text_file("README.md")` |

### Navigation

Targets can navigate to other targets:

```python
# Start with a file, drill down to a method
rj.file("models.py")           # FileTarget
  .find_class("User")          # ClassTarget
  .find_method("save")         # MethodTarget
```

### Target Existence

Targets are created immediately, but the underlying code may not exist:

```python
cls = rj.file("models.py").find_class("NonExistent")

# The target exists, but the class doesn't
print(cls.exists())  # False

# Operations on non-existent targets return ErrorResult
result = cls.rename("NewName")
print(result.success)  # False
print(result.message)  # "Class 'NonExistent' not found"
```

## Results

Operations return **Result** objects instead of raising exceptions.

### Result

```python
result = cls.rename("NewName")

result.success        # bool - did it work?
result.message        # str - human-readable description
result.files_changed  # list[Path] - files that were modified
result.data           # Any - optional payload for queries
```

Results are truthy when successful:

```python
if result:
    print("Success!")
```

### ErrorResult

When an operation fails, you get an `ErrorResult`:

```python
result = cls.rename("NewName")

if result.is_error():
    print(result.message)      # What went wrong
    print(result.operation)    # Which operation failed
    print(result.target_repr)  # Which target

    # Optionally re-raise as an exception
    result.raise_if_error()
```

### BatchResult

When operating on multiple targets, you get a `BatchResult`:

```python
results = rj.find_classes("^Test").add_decorator("@slow")

results.success         # True if ALL succeeded
results.partial_success # True if ANY succeeded
results.all_failed      # True if ALL failed
results.succeeded       # list[Result] - successful operations
results.failed          # list[Result] - failed operations
results.files_changed   # list[Path] - all files modified
```

## TargetList

When you find multiple items, you get a `TargetList`:

```python
classes = rj.find_classes(pattern="^Test")  # TargetList[ClassTarget]
```

### Iteration

```python
for cls in classes:
    print(cls.name)
```

### Filtering

```python
# By predicate
classes.filter(lambda c: c.has_docstring())

# By file
classes.in_file(Path("tests/test_user.py"))

# By name pattern
classes.matching("User")
```

### Accessing Items

```python
classes.first()   # First target or None
classes.last()    # Last target or None
classes[0]        # First target (raises if empty)
len(classes)      # Number of targets
```

### Batch Operations

Operations on `TargetList` apply to all targets:

```python
# Returns BatchResult
results = classes.add_decorator("@pytest.mark.slow")
results = classes.delete()
results = classes.rename(r"^Test", "Integration")
```

## ErrorTarget

When navigation fails, you get an `ErrorTarget` instead of raising an exception:

```python
# This doesn't raise, even if the class doesn't exist
method = rj.file("x.py").find_class("Missing").find_method("foo")

# ErrorTarget allows chaining
print(type(method))  # ErrorTarget

# But operations return ErrorResult
result = method.rename("bar")
print(result.success)  # False
```

This design lets you write chains without defensive checks:

```python
# Safe - won't raise even if User or save don't exist
result = (
    rj.file("models.py")
    .find_class("User")
    .find_method("save")
    .insert_statement("self.validate()")
)

# Just check the result
if not result:
    print(f"Couldn't modify: {result.message}")
```

## Path Resolution

The path passed to `Rejig()` is the root for all relative operations:

```python
rj = Rejig("/home/user/project/src")

rj.file("utils.py")           # /home/user/project/src/utils.py
rj.file("sub/module.py")      # /home/user/project/src/sub/module.py
rj.file("/etc/config")        # /etc/config (absolute, unchanged)
rj.module("myapp.models")     # Searches under root for myapp/models.py
```

## Dry Run Mode

Enable dry-run mode to preview changes:

```python
rj = Rejig("src/", dry_run=True)

# Operations describe what would happen
result = rj.find_classes("User").first().rename("UserModel")
print(result.message)  # "Would rename User to UserModel in models.py"

# No files are modified
print(result.files_changed)  # []
```

## Next Steps

- [Finding Code](../guides/finding-code.md) — All the ways to locate code
- [Modifying Code](../guides/modifying-code.md) — Available transformations
- [Error Handling](../guides/error-handling.md) — Working with results
