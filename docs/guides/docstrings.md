# Docstrings

Rejig provides tools for generating, updating, and converting docstrings. Supports Google, NumPy, and Sphinx/reStructuredText styles.

## Generating Docstrings

### For a Single Function

```python
from rejig import Rejig

rj = Rejig("src/")

func = rj.find_function("process_data")
func.generate_docstring()

# Before:
# def process_data(items: list[str], limit: int = 10) -> dict[str, int]:
#     result = {}
#     for item in items[:limit]:
#         result[item] = len(item)
#     return result

# After (Google style by default):
# def process_data(items: list[str], limit: int = 10) -> dict[str, int]:
#     """Process data items and return length mapping.
#
#     Args:
#         items: List of items to process.
#         limit: Maximum number of items to process. Defaults to 10.
#
#     Returns:
#         Dictionary mapping items to their lengths.
#     """
#     result = {}
#     ...
```

### Specify Style

```python
# Google style (default)
func.generate_docstring(style="google")

# NumPy style
func.generate_docstring(style="numpy")

# Sphinx/reStructuredText style
func.generate_docstring(style="sphinx")
```

### Style Examples

**Google Style:**
```python
def process(items: list[str], limit: int = 10) -> dict[str, int]:
    """Process items and return counts.

    Args:
        items: List of items to process.
        limit: Maximum items. Defaults to 10.

    Returns:
        Dictionary of item counts.

    Raises:
        ValueError: If items is empty.
    """
```

**NumPy Style:**
```python
def process(items: list[str], limit: int = 10) -> dict[str, int]:
    """Process items and return counts.

    Parameters
    ----------
    items : list[str]
        List of items to process.
    limit : int, optional
        Maximum items. Default is 10.

    Returns
    -------
    dict[str, int]
        Dictionary of item counts.

    Raises
    ------
    ValueError
        If items is empty.
    """
```

**Sphinx Style:**
```python
def process(items: list[str], limit: int = 10) -> dict[str, int]:
    """Process items and return counts.

    :param items: List of items to process.
    :type items: list[str]
    :param limit: Maximum items. Default is 10.
    :type limit: int
    :returns: Dictionary of item counts.
    :rtype: dict[str, int]
    :raises ValueError: If items is empty.
    """
```

### Batch Generation

```python
# Generate for all functions without docstrings
rj.find_functions().without_docstrings().generate_docstrings()

# Generate for all methods in a class
rj.find_class("MyClass").find_methods().without_docstrings().generate_docstrings()

# Generate for all public functions
rj.find_functions().filter(lambda f: not f.name.startswith("_")).generate_docstrings()

# Generate for entire codebase (all functions/methods in every file)
rj.find_files().generate_all_docstrings()
```

### Generation Options

```python
func.generate_docstring(
    style="google",   # "google", "numpy", or "sphinx"
    summary="",       # Custom summary line; auto-generated from the name if empty
    overwrite=False,  # Replace an existing docstring when True
)
```

## Updating Docstrings

When a parameter changes, update or add its description in the docstring:

```python
# Update or add a single parameter's description
func.update_docstring_param("timeout", "Maximum wait time in seconds")
```

## Converting Docstring Styles

Convert between docstring formats. `convert_docstring_style` operates on files
and takes a `from_style` (or `None` to auto-detect) and a required `to_style`.

```python
# Convert all docstrings in a file to Google style (auto-detect source)
rj.file("module.py").convert_docstring_style(None, "google")

# Convert from a known style to another
rj.file("module.py").convert_docstring_style("sphinx", "google")

# Convert across the whole codebase
rj.find_files().convert_docstring_style(None, "google")
```

### Style Detection

```python
# Detect current docstring style
from rejig.docstrings import DocstringParser

parser = DocstringParser()
docstring = func.get_docstring().data
style = parser.detect_style(docstring)
print(f"Current style: {style}")  # DocstringStyle enum value
```

## Parsing Docstrings

Extract structured information from docstrings:

```python
from rejig.docstrings import DocstringParser

parser = DocstringParser()
doc = parser.parse(func.get_docstring().data)

# Access components
print(doc.summary)           # Short description
print(doc.description)       # Extended description
print(doc.params)            # List of parameters
print(doc.returns)           # Return documentation
print(doc.raises)            # List of exceptions
print(doc.examples)          # Example code blocks

# Parameter details
for param in doc.params:
    print(f"  {param.name}: {param.type_hint}")
    print(f"    {param.description}")
```

## Filtering by Docstrings

### Find Functions Without Docstrings

```python
# Functions without any docstring
no_docs = rj.find_functions().without_docstrings()

# Functions with docstrings
has_docs = rj.find_functions().with_docstrings()

# Public functions without docstrings
public_no_docs = (
    rj.find_functions()
    .filter(lambda f: not f.name.startswith("_"))
    .without_docstrings()
)
```

### Find Incomplete Docstrings

```python
# Functions whose docstring has no documented parameters
from rejig.docstrings import DocstringParser

parser = DocstringParser()

def has_undocumented_params(func):
    if not func.has_docstring:
        return False
    doc = parser.parse(func.get_docstring().data)
    return len(doc.params) == 0

incomplete = rj.find_functions().with_docstrings().filter(has_undocumented_params)
```

## Class Docstrings

`ClassTarget.generate_docstrings()` generates docstrings for every method in the
class (it does not synthesize the class-level docstring).

```python
cls = rj.find_class("MyClass")

# Generate docstrings for all methods in the class
cls.generate_docstrings()

# Choose a style, and overwrite existing docstrings if desired
cls.generate_docstrings(style="numpy", overwrite=False)

# Inspect the class's own docstring
if cls.has_docstring:
    print(cls.get_docstring().data)
```

## Common Patterns

### Document All Public API

```python
rj = Rejig("src/")

# Generate docstrings for public API only
for func in rj.find_functions():
    if not func.name.startswith("_") and not func.has_docstring:
        func.generate_docstring(style="google")

for cls in rj.find_classes():
    if not cls.name.startswith("_"):
        for method in cls.find_methods():
            if not method.name.startswith("_") and not method.has_docstring:
                method.generate_docstring(style="google")
```

### Migrate Docstring Style

```python
# Convert entire codebase from Sphinx to Google style
rj = Rejig("src/")

# Conversion operates on files (auto-detect the source style with None)
rj.find_files().convert_docstring_style(None, "google")
```

### Validate Docstring Coverage

```python
# Check docstring coverage for CI
rj = Rejig("src/")

public_functions = rj.find_functions().filter(lambda f: not f.name.startswith("_"))
missing_funcs = public_functions.without_docstrings()

# Methods are checked per class
missing_methods = []
for cls in rj.find_classes():
    for method in cls.find_methods_without_docstrings():
        if not method.name.startswith("_"):
            missing_methods.append(method)

if missing_funcs or missing_methods:
    print("Missing docstrings:")
    for func in missing_funcs:
        print(f"  Function: {func.file_path}:{func.name}")
    for method in missing_methods:
        print(f"  Method: {method.file_path}:{method.class_name}.{method.name}")
    exit(1)
```

### Generate Docstrings from Signatures

```python
# generate_docstring builds the docstring from the function signature,
# including parameters, return type, and raised exceptions.
func.generate_docstring(style="google")

# For a function like:
# def process(data: dict[str, Any], limit: int = 10) -> list[str]:
# it produces:
#     """Process data.
#
#     Args:
#         data: ...
#         limit: ... Defaults to 10.
#
#     Returns:
#         ...
#     """
```

## Integration with Analysis

### Find Missing Docstrings

```python
rj = Rejig("src/")

# Functions and methods lacking docstrings
missing = rj.find_functions_without_docstrings()
for issue in missing:
    print(f"{issue.location} - {issue.name}")

# Classes lacking docstrings
for issue in rj.find_classes_without_docstrings():
    print(f"{issue.location} - {issue.name}")
```
