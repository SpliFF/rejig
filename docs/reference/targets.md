# Targets

Targets are objects representing code elements you can inspect or modify.

## Base Classes

### Target

The abstract base class for all targets.

```python
class Target(ABC):
    def exists(self) -> bool: ...
    def get_content(self) -> Result: ...
```

### ErrorTarget

Returned when navigation fails. Allows safe chaining.

```python
# Navigation returns ErrorTarget instead of raising
method = rj.file("x.py").find_class("Missing").find_method("foo")
print(type(method))  # ErrorTarget

# Operations return ErrorResult
result = method.rename("bar")
print(result.success)  # False
```

### TargetList

A list of targets supporting batch operations.

```python
classes = rj.find_classes(pattern="^Test")  # TargetList[ClassTarget]

# Filtering
classes.filter(lambda c: c.has_docstring())
classes.in_file("models.py")
classes.matching("User")

# Batch operations
classes.add_decorator("@slow")  # Returns BatchResult
classes.delete()
```

## Python Targets

### FileTarget

A Python file.

```python
file = rj.file("models.py")

# Properties
file.path           # Path object
file.exists()       # True if file exists

# Navigation
file.find_class("User")       # ClassTarget
file.find_function("main")    # FunctionTarget
file.find_classes()           # TargetList[ClassTarget]
file.find_functions()         # TargetList[FunctionTarget]
file.line(42)                 # LineTarget
file.lines(10, 20)            # LineBlockTarget
file.block_at_line(15)        # CodeBlockTarget

# Operations
file.add_import("from typing import Optional")
file.add_function("main", body="pass")
file.add_class("Config", body="DEBUG = True")
file.organize_imports()
file.remove_unused_imports()
```

### ModuleTarget

A Python module by dotted path.

```python
module = rj.module("myapp.models")

# Properties
module.module_path   # "myapp.models"
module.file_path     # Resolved Path or None

# Navigation
module.find_class("User")
module.find_function("helper")

# Operations
module.add_function("new_func")
module.add_class("NewClass")
```

### PackageTarget

A Python package directory.

```python
pkg = rj.package("myapp/")

# Properties
pkg.path         # Path to directory
pkg.exists()     # True if __init__.py exists

# Navigation
pkg.find_modules()             # TargetList[ModuleTarget]
pkg.find_classes()             # TargetList[ClassTarget]
pkg.find_functions()           # TargetList[FunctionTarget]

# Operations
pkg.generate_stubs("stubs/")   # Generate .pyi files
pkg.merge_modules(["a.py", "b.py"], into="combined.py")
```

### ClassTarget

A class definition.

```python
cls = file.find_class("User")

# Properties
cls.name                      # "User"
cls.file_path                 # Path to containing file
cls.exists()                  # True if found
cls.has_docstring()           # True if has docstring
cls.get_lines()               # (start, end) line numbers
cls.get_content()             # Result with source code

# Navigation
cls.find_method("save")       # MethodTarget
cls.find_methods()            # TargetList[MethodTarget]

# Operations
cls.rename("NewName")
cls.add_method("validate", body="return True")
cls.add_attribute("name", type_hint="str", default="''")
cls.add_decorator("dataclass")
cls.remove_decorator("old_decorator")
cls.add_base_class("BaseModel")
cls.remove_base_class("OldBase")
cls.delete()
cls.duplicate("UserCopy")

# Conversions
cls.convert_to_dataclass()
cls.convert_to_pydantic_model()
cls.generate_all_dunders()
```

### FunctionTarget

A module-level function.

```python
func = file.find_function("process")

# Properties
func.name                     # "process"
func.file_path                # Path to file
func.exists()                 # True if found
func.has_docstring()          # True if has docstring
func.has_type_hints()         # True if has annotations
cls.get_lines()               # (start, end) line numbers

# Operations
func.rename("process_data")
func.add_decorator("lru_cache")
func.remove_decorator("deprecated")
func.insert_statement("log('start')", position="start")
func.add_parameter("timeout", type="int", default="30")
func.remove_parameter("old_param")
func.set_return_type("list[str]")
func.set_parameter_type("data", "dict[str, Any]")
func.generate_docstring(style="google")
func.delete()

# Conversions
func.convert_to_async()
func.convert_to_sync()
```

### MethodTarget

A method within a class.

```python
method = cls.find_method("save")

# Properties (same as FunctionTarget)
method.name
method.class_name             # Name of containing class
method.file_path
method.exists()
method.has_docstring()
method.has_type_hints()

# Operations (same as FunctionTarget)
method.rename("save_data")
method.add_decorator("transaction")
method.insert_statement("self.validate()")
method.set_return_type("bool")
method.delete()

# Additional
method.extract_to_function("save_helper")
```

### LineTarget

A single line in a file.

```python
line = file.line(42)

# Properties
line.line_number              # 42
line.file_path                # Path to file
line.exists()                 # True if line exists
line.get_content()            # Result with line content

# Directive operations
line.add_type_ignore("arg-type")
line.remove_type_ignore()
line.add_noqa("E501")
line.remove_noqa()
line.add_pylint_disable("line-too-long")
line.add_fmt_skip()
line.add_no_cover()

# TODO operations
line.add_todo("Fix this")
line.remove_todo()
line.link_to_issue("#123")
```

### LineBlockTarget

A range of lines.

```python
block = file.lines(10, 20)

# Properties
block.start_line              # 10
block.end_line                # 20
block.file_path               # Path to file
block.get_content()           # Result with content

# Operations
block.move_to(100)            # Move to line 100
block.move_to_file("other.py", after_line=5)
block.rewrite("new content")
block.prepend("# Start\n")
block.append("# End\n")
block.delete()
block.indent(2)
block.dedent()

# Wrapping
block.wrap_with_fmt_off()
block.wrap_with_pylint_disable(["C0114"])
block.wrap_with_no_cover()
```

### CodeBlockTarget

A detected code structure (class, function, if, for, etc.).

```python
block = file.block_at_line(42)

# Properties
block.kind                    # "class", "function", "if", "for", etc.
block.name                    # Name if applicable
block.start_line              # First line
block.end_line                # Last line
block.file_path               # Path to file

# Operations
block.delete()
block.to_line_block()         # Convert to LineBlockTarget
```

### CommentTarget

A Python comment (standalone or inline).

```python
# Find comments
comments = file.find_comments()
todos = file.find_comments(pattern="TODO|FIXME")

# Access comment properties
for comment in comments:
    comment.line_number           # Line number
    comment.text                  # Comment text (without #)
    comment.is_inline             # True if code precedes comment
    comment.file_path             # Path to file

# Operations
comment.rewrite("New comment text")
comment.delete()
comment.convert_to_docstring()    # If preceding a function/class

# Check type
comment.is_todo()                 # True for TODO/FIXME/XXX/HACK
comment.to_line_target()          # Get LineTarget for this line
```

### StringLiteralTarget

A string literal in Python code.

```python
# Find strings
strings = file.find_strings()
sql_strings = file.find_strings(pattern="SELECT.*FROM")
multiline = file.find_multiline_strings()
fstrings = file.find_fstrings()
docstrings = file.find_docstrings()

# Access string properties
for s in strings:
    s.value                       # String content (unquoted)
    s.kind                        # "simple", "multiline", "fstring", "raw", "bytes"
    s.quote_style                 # "single", "double", "triple_single", "triple_double"
    s.line_number                 # Start line
    s.end_line_number             # End line (for multiline)
    s.is_multiline                # True for triple-quoted
    s.is_docstring                # True if it's a docstring

# Operations
s.rewrite("new content")          # Replace content (keeps quotes)
s.convert_to_fstring()            # Convert .format() to f-string
s.convert_to_raw()                # Add r prefix
s.convert_to_multiline()          # Convert to triple-quoted
s.change_quote_style("double")    # Change quote type
s.delete()

# Analysis helpers
s.contains_sql()                  # True if looks like SQL
s.contains_url()                  # True if contains URL
s.contains_path()                 # True if looks like file path
s.to_line_block()                 # Get LineBlockTarget
```

## Config Targets

### TomlTarget

A TOML file.

```python
toml = rj.toml("pyproject.toml")

toml.exists()                 # True if file exists
toml.get("tool.black.line-length")
toml.get("missing.key", default=None)
toml.set("project.version", "2.0.0")
toml.delete_key("tool.old-tool")
toml.get_section("tool.black")
```

### YamlTarget

A YAML file.

```python
yaml = rj.yaml("config.yml")

yaml.exists()
yaml.get("database.host")
yaml.set("database.port", 5432)
yaml.delete_key("deprecated")
```

### JsonTarget

A JSON file.

```python
json = rj.json("package.json")

json.exists()
json.get("version")
json.set("scripts.test", "pytest")
json.delete_key("devDependencies.old")
```

### IniTarget

An INI/CFG file.

```python
ini = rj.ini("setup.cfg")

ini.exists()
ini.get("metadata", "name")
ini.set("metadata", "version", "2.0.0")
ini.delete_key("options", "old_option")
ini.add_section("tool:pytest")
```

### TextFileTarget

Any text file.

```python
text = rj.text_file("README.md")

text.exists()
text.get_content()
text.line(1)                  # First line
text.lines(1, 10)             # First 10 lines
text.find_pattern(r"## .*")   # Find headers
text.replace_pattern(r"v\d+", "v2")
```

---

::: rejig.targets
    options:
      show_source: false
