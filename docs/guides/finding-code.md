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
    print(f"Found User class at line {cls.get_lines()[0]}")
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
cls.get_lines()           # (start_line, end_line)
cls.get_content()         # Result with source code
```

### Function/Method Information

```python
func = rj.find_functions("process").first()

func.name                 # "process"
func.file_path            # Path to the file
func.exists()             # True if found
func.has_docstring()      # True if has docstring
func.has_type_hints()     # True if has type annotations
func.get_lines()          # (start_line, end_line)
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

## Finding Comments

### All Comments

```python
file = rj.file("mymodule.py")

# All comments in a file
comments = file.find_comments()

# Filter by content
todos = file.find_comments(pattern="TODO|FIXME")
```

### Across the Project

```python
# All comments
comments = rj.find_comments()

# TODO/FIXME comments
todos = rj.find_comments(pattern="TODO|FIXME|XXX|HACK")

# Comments mentioning a specific topic
auth_comments = rj.find_comments(pattern="(?i)auth|login|password")
```

### Comment Properties

```python
for comment in comments:
    print(comment.text)         # Comment text (without #)
    print(comment.line_number)  # Line number
    print(comment.is_inline)    # True if code precedes comment
    print(comment.is_todo())    # True if TODO/FIXME/etc.
```

## Finding Strings

### All Strings

```python
file = rj.file("mymodule.py")

# All string literals
strings = file.find_strings()

# By content pattern
urls = file.find_strings(pattern="https?://")
sql = file.find_strings(pattern="SELECT.*FROM")
```

### Specific String Types

```python
# Multiline/triple-quoted strings
multiline = file.find_multiline_strings()

# F-strings
fstrings = file.find_fstrings()

# Docstrings only
docstrings = file.find_docstrings()
```

### Across the Project

```python
# Find all SQL queries
sql_strings = rj.find_sql_strings()

# Find hardcoded user-facing strings (for i18n)
hardcoded = rj.find_hardcoded_strings(min_length=10)

# Find all multiline strings
multiline = rj.find_multiline_strings()

# Find all docstrings
docstrings = rj.find_docstrings()
```

### String Properties

```python
for s in strings:
    print(s.value)              # Content (unquoted)
    print(s.kind)               # "simple", "fstring", "raw", etc.
    print(s.quote_style)        # "single", "double", "triple_*"
    print(s.is_multiline)       # True for triple-quoted
    print(s.is_docstring)       # True if it's a docstring

    # Analysis helpers
    print(s.contains_sql())     # Looks like SQL?
    print(s.contains_url())     # Contains URL?
    print(s.contains_path())    # Looks like file path?
```

## Next Steps

- [Modifying Code](modifying-code.md) — Transform the code you've found
- [Batch Operations](batch-operations.md) — Work with multiple targets
