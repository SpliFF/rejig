# Modifying Code

Once you've found code elements, you can transform them.

## Class Operations

### Renaming

```python
cls = rj.find_classes("OldName").first()
result = cls.rename("NewName")
```

### Adding Methods

```python
cls = rj.file("models.py").find_class("User")

# Simple method
cls.add_method("validate", body="return True")

# With parameters and return type
cls.add_method(
    "get_display_name",
    parameters="self, include_title: bool = False",
    return_type="str",
    body="return f'{self.first_name} {self.last_name}'"
)

# With decorator
cls.add_method(
    "cached_value",
    body="return self._compute()",
    decorators=["@cached_property"]
)
```

### Adding Attributes

```python
cls.add_attribute("created_at", type_hint="datetime", default="None")
cls.add_attribute("MAX_RETRIES", type_hint="int", default="3")
```

### Adding Decorators

```python
cls.add_decorator("dataclass")
cls.add_decorator("dataclass(frozen=True)")
```

### Removing Decorators

```python
cls.remove_decorator("dataclass")
```

### Inheritance

```python
cls.add_base_class("BaseModel")
cls.remove_base_class("OldBase")
cls.add_mixin("LoggingMixin")
```

### Deleting

```python
cls.delete()
```

### Duplicating

```python
cls.duplicate("UserCopy")
```

## Method Operations

### Renaming

```python
method = cls.find_method("old_name")
method.rename("new_name")
```

### Adding Decorators

```python
method.add_decorator("staticmethod")
method.add_decorator("lru_cache(maxsize=100)")
```

### Removing Decorators

```python
method.remove_decorator("staticmethod")
```

### Inserting Statements

```python
# At the start of the method body
method.insert_statement("self.validate()", position="start")

# At the end of the method body
method.insert_statement("self.log_action()", position="end")
```

### Parameters

```python
# Add a parameter
method.add_parameter("timeout", type="int", default="30")

# Remove a parameter
method.remove_parameter("deprecated_arg")

# Rename a parameter
method.rename_parameter("old_name", "new_name")
```

### Type Hints

```python
method.set_return_type("list[str]")
method.set_parameter_type("data", "dict[str, Any]")
method.remove_type_hints()  # Strip all type annotations
```

### Deleting

```python
method.delete()
```

### Extracting to Function

```python
# Extract method to a module-level function
method.extract_to_function("helper_process")
```

## Function Operations

Functions support the same operations as methods:

```python
func = rj.file("utils.py").find_function("process")

func.rename("process_data")
func.add_decorator("lru_cache")
func.insert_statement("logger.debug('Starting')", position="start")
func.add_parameter("verbose", type="bool", default="False")
func.set_return_type("ProcessResult")
func.delete()
```

## File Operations

### Adding Imports

```python
file = rj.file("mymodule.py")

file.add_import("from typing import Optional")
file.add_import("import json")
file.add_import("from myapp.utils import helper")
```

### Organizing Imports

```python
file.organize_imports()           # Sort and group imports
file.remove_unused_imports()      # Remove imports not used in file
file.add_missing_imports()        # Add imports for undefined names
```

### Converting Import Styles

```python
file.convert_relative_to_absolute()   # from .utils → from mypackage.utils
file.convert_absolute_to_relative()   # from mypackage.utils → from .utils
```

### Adding Functions/Classes

```python
file.add_function("main", body="print('Hello')")
file.add_class("Config", body="DEBUG = True")
```

## Async Conversions

```python
func = rj.find_functions("fetch_data").first()

# Convert sync to async
func.convert_to_async()

# Convert async to sync
func.convert_to_sync()
```

## Docstrings

### Generating

```python
func.generate_docstring(style="google")  # or "numpy", "sphinx"
cls.generate_docstrings()  # Generate for all methods
```

### Updating

```python
method.update_docstring_param("timeout", "Maximum wait time in seconds")
method.add_docstring_raises("ValueError", "If input is negative")
method.add_docstring_example(">>> process(5)\\n10")
method.add_docstring_returns("The processed result")
```

### Converting Styles

```python
file.convert_docstring_style("google", "numpy")
```

## Type Hint Modernization

```python
# Modernize type hints (Python 3.10+ style)
file.modernize_type_hints()  # List[str] → list[str], Optional[X] → X | None

# Convert type comments to annotations
file.convert_type_comments_to_annotations()  # # type: str → : str
```

## Class Conversions

```python
cls = rj.find_classes("Config").first()

# Convert to dataclass
cls.convert_to_dataclass()

# Convert from dataclass
cls.convert_from_dataclass()

# Other conversions
cls.convert_to_pydantic_model()
cls.convert_to_typed_dict()
cls.convert_to_named_tuple()
```

## Generating Dunder Methods

```python
cls.generate_init_from_attributes()
cls.generate_repr()
cls.generate_eq()
cls.generate_hash()
cls.generate_all_dunders()  # All of the above
```

## Properties

```python
# Convert attribute to property
cls.convert_attribute_to_property("_name", getter=True, setter=True)

# Add a computed property
cls.add_property("full_name", getter="return f'{self.first} {self.last}'")
```

## Comment Operations

### Rewriting Comments

```python
# Find and rewrite a comment
comments = file.find_comments(pattern="TODO")
for comment in comments:
    comment.rewrite(f"DONE: {comment.text}")
```

### Deleting Comments

```python
# Remove all TODO comments
for comment in file.find_comments(pattern="TODO"):
    comment.delete()

# Remove a specific comment
comment = file.find_comments(pattern="temporary hack").first()
comment.delete()
```

### Converting to Docstrings

```python
# Convert a comment preceding a function to a docstring
# Before: # Processes the input data
#         def process(): ...
# After:  def process():
#             """Processes the input data."""
comment = file.find_comments(pattern="Processes the").first()
comment.convert_to_docstring()
```

## String Literal Operations

### Rewriting String Content

```python
# Replace string content (preserves quote style)
strings = file.find_strings(pattern="old_value")
for s in strings:
    s.rewrite("new_value")
```

### Converting to F-Strings

```python
# Convert .format() calls to f-strings
# Before: "Hello {}".format(name)
# After:  f"Hello {name}"
for s in file.find_strings(pattern="\\.format\\("):
    s.convert_to_fstring()
```

### Converting to Raw Strings

```python
# Add r prefix for regex patterns
for s in file.find_strings(pattern="\\\\d\\+"):
    s.convert_to_raw()
# Before: "\\d+"
# After:  r"\d+"
```

### Converting to Multiline

```python
# Convert long strings to triple-quoted
for s in file.find_strings():
    if len(s.value) > 80:
        s.convert_to_multiline()
```

### Changing Quote Style

```python
# Standardize to double quotes
for s in file.find_strings():
    if s.quote_style == "single":
        s.change_quote_style("double")

# Quote style options: "single", "double", "triple_single", "triple_double"
```

### Deleting Strings

```python
# Remove debug strings
for s in file.find_strings(pattern="DEBUG:"):
    s.delete()
```

## Result Handling

All operations return a `Result`:

```python
result = cls.rename("NewName")

if result:
    print(f"Modified: {result.files_changed}")
else:
    print(f"Failed: {result.message}")
    if result.exception:
        result.raise_if_error()  # Re-raise if you want
```

## Next Steps

- [Line Operations](line-operations.md) — Work with specific lines
- [Batch Operations](batch-operations.md) — Apply changes to multiple targets
- [Error Handling](error-handling.md) — Handle failures gracefully
