# Finding Code

Rejig provides multiple ways to locate code elements in your codebase.

## Starting Points

### Files

Get a target for a specific file:

```python
# By relative path (relative to Rejig root)
file = rj.file("mymodule.py")
file = rj.file("subdir/utils.py")

# By absolute path
file = rj.file("/absolute/path/to/file.py")
```

### Modules

Get a target by Python module path:

```python
# Dotted module path
module = rj.module("myapp.models")
module = rj.module("myapp.utils.helpers")

# The module is resolved relative to the Rejig root
```

### Packages

Get a target for a package directory:

```python
pkg = rj.package("myapp/")
pkg = rj.package("myapp/subpackage/")
```

## Finding Classes

### In a Specific File

```python
file = rj.file("models.py")

# Find by exact name
cls = file.find_class("User")

# Find all classes
classes = file.find_classes()

# Find by pattern
classes = file.find_classes(pattern="^Base")  # Classes starting with "Base"
```

### Across the Project

```python
# All classes in the project
classes = rj.find_classes()

# By exact name (first match)
cls = rj.find_classes("UserModel").first()

# By pattern
classes = rj.find_classes(pattern="^Test")      # Test classes
classes = rj.find_classes(pattern="Handler$")   # Handler classes
classes = rj.find_classes(pattern=".*Mixin.*")  # Mixin classes
```

## Finding Functions

### Module-Level Functions

```python
file = rj.file("utils.py")

# Find by exact name
func = file.find_function("calculate")

# Find all functions
funcs = file.find_functions()

# Find by pattern
funcs = file.find_functions(pattern="^process_")
```

### Across the Project

```python
# All module-level functions
funcs = rj.find_functions()

# By pattern
funcs = rj.find_functions(pattern="^get_")
funcs = rj.find_functions(pattern="_helper$")
```

## Finding Methods

Methods belong to classes:

```python
cls = rj.file("models.py").find_class("User")

# Find by exact name
method = cls.find_method("save")

# Find all methods
methods = cls.find_methods()

# Find by pattern
methods = cls.find_methods(pattern="^_")        # Private methods
methods = cls.find_methods(pattern="^test_")    # Test methods
methods = cls.find_methods(pattern="^get_|^set_")  # Getters/setters
```

## Filtering Results

`TargetList` provides filtering methods:

```python
classes = rj.find_classes()

# Filter by predicate
classes.filter(lambda c: c.has_docstring())
classes.filter(lambda c: c.exists())

# Filter by file
classes.in_file(Path("models.py"))

# Filter by name pattern (additional filtering)
classes.matching("User")
```

### Chaining Filters

```python
# Find test classes without docstrings in the tests directory
targets = (
    rj.find_classes(pattern="^Test")
    .filter(lambda c: not c.has_docstring())
    .filter(lambda c: "tests/" in str(c.file_path))
)
```

## Checking Existence

```python
cls = rj.file("models.py").find_class("User")

if cls.exists():
    print(f"Found User class at line {cls.start_line}")
else:
    print("User class not found")
```

## Getting Information

### Class Information

```python
cls = rj.find_classes("User").first()

cls.name                  # "User"
cls.file_path             # Path to the file
cls.exists()              # True if found
cls.has_docstring()       # True if has docstring
cls.start_line            # First line of the class definition
cls.end_line              # Last line of the class definition
cls.get_content()         # Result with source code
```

### Function/Method Information

```python
func = rj.find_functions("process").first()

func.name                 # "process"
func.file_path            # Path to the file
func.exists()             # True if found
func.has_docstring()      # True if has docstring
func.start_line           # First line of the function definition
func.end_line             # Last line of the function definition
func.get_content()        # Result with source code
```

## Finding by Line

### Single Line

```python
file = rj.file("mymodule.py")
line = file.line(42)

# Check what's on this line
content = line.get_content()
```

### Line Range

```python
block = file.lines(10, 20)
content = block.get_content()
```

### Code Block at Line

Find the enclosing code structure:

```python
block = file.block_at_line(42)

print(block.kind)   # "class", "function", "method", "if", "for", etc.
print(block.name)   # Name if applicable
print(block.start_line)
print(block.end_line)
```

## Pattern Syntax

Patterns use Python regular expressions:

```python
# Starts with
rj.find_classes(pattern="^Test")

# Ends with
rj.find_classes(pattern="Handler$")

# Contains
rj.find_classes(pattern=".*User.*")

# Multiple options
rj.find_functions(pattern="^(get|set|delete)_")

# Case insensitive (use (?i) flag)
rj.find_classes(pattern="(?i)^test")
```

## Finding TODO Comments

TODO/FIXME/XXX/HACK/NOTE/BUG comments are found project-wide:

```python
# All TODO-style comments across the working set
todos = rj.find_todos()

print(f"Found {len(todos)} TODOs")

# Filter by type
fixmes = todos.by_type("FIXME")

# Filter to high priority
urgent = todos.high_priority()

# Find TODOs not linked to an issue
unlinked = todos.without_issues()

for todo in todos:
    print(f"{todo.todo_type}: {todo.todo_text}")
    print(f"  {todo.location}")
```

## Finding Hardcoded Strings

Find hardcoded string literals that might need externalization (for example,
for i18n):

```python
# Strings at least `min_length` characters long
hardcoded = rj.find_hardcoded_strings(min_length=10)

for match in hardcoded:
    print(f"{match.file_path}:{match.line_number}: {match.message}")
```

This returns an `AnalysisTargetList`. See [Code Analysis](code-analysis.md) for
the full set of pattern finders and how to work with findings.

## Next Steps

- [Modifying Code](modifying-code.md) — Transform the code you've found
- [Batch Operations](batch-operations.md) — Work with multiple targets
