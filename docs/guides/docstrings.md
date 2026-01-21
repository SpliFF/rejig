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

# Generate for entire codebase
rj.find_functions().generate_all_docstrings()
rj.find_methods().generate_all_docstrings()
```

### Generation Options

```python
func.generate_docstring(
    style="google",
    include_types=True,       # Include type info in docstring
    include_defaults=True,    # Document default values
    include_raises=True,      # Include Raises section
    include_examples=False,   # Don't add Example section
    summary_from_name=True,   # Generate summary from function name
)
```

## Updating Docstrings

When function signatures change, update docstrings to match:

```python
# Update docstring to match current signature
func.update_docstring()

# This will:
# - Add documentation for new parameters
# - Remove documentation for removed parameters
# - Update types if they changed
# - Preserve existing descriptions
```

### Batch Updates

```python
# Update all docstrings in a file
rj.file("module.py").find_functions().update_docstrings()

# Update after a refactoring
cls = rj.find_class("MyClass")
cls.add_parameter_to_all_methods("context", "Context")
cls.find_methods().update_docstrings()
```

## Converting Docstring Styles

Convert between docstring formats:

```python
# Convert a single function
func = rj.find_function("process")
func.convert_docstring_style("numpy")  # Convert to NumPy style

# Convert from one style to another
func.convert_docstring_style(from_style="sphinx", to_style="google")

# Batch conversion
rj.find_functions().convert_docstring_style("google")
rj.find_methods().convert_docstring_style("google")
```

### Style Detection

```python
# Detect current docstring style
from rejig import DocstringParser

parser = DocstringParser()
style = parser.detect_style(func.docstring)
print(f"Current style: {style}")  # "google", "numpy", "sphinx", or "unknown"
```

## Parsing Docstrings

Extract structured information from docstrings:

```python
from rejig import DocstringParser

parser = DocstringParser()
doc = parser.parse(func.docstring)

# Access components
print(doc.summary)           # Short description
print(doc.description)       # Extended description
print(doc.parameters)        # List of parameters
print(doc.returns)           # Return documentation
print(doc.raises)            # List of exceptions
print(doc.examples)          # Example code blocks

# Parameter details
for param in doc.parameters:
    print(f"  {param.name}: {param.type}")
    print(f"    {param.description}")
    print(f"    Default: {param.default}")
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
# Functions with docstrings missing parameter documentation
from rejig import DocstringParser

parser = DocstringParser()

def has_incomplete_docstring(func):
    if not func.docstring:
        return False
    doc = parser.parse(func.docstring)
    # Check if all parameters are documented
    param_names = {p.name for p in doc.parameters}
    func_params = {p.name for p in func.parameters if p.name not in ("self", "cls")}
    return func_params - param_names

incomplete = rj.find_functions().filter(has_incomplete_docstring)
```

## Class and Module Docstrings

### Class Docstrings

```python
cls = rj.find_class("MyClass")

# Generate class docstring
cls.generate_docstring()

# This documents:
# - Class purpose
# - Class attributes
# - Example usage (optional)

# Before:
# class MyClass:
#     name: str
#     count: int

# After:
# class MyClass:
#     """Container for named items with count tracking.
#
#     Attributes:
#         name: The name identifier.
#         count: Number of items.
#     """
#     name: str
#     count: int
```

### Module Docstrings

```python
file = rj.file("utils.py")

# Add module docstring
file.set_module_docstring("""
Utility functions for data processing.

This module provides helper functions for common data
manipulation tasks including validation, transformation,
and formatting.
""")

# Get existing module docstring
print(file.module_docstring)
```

## Common Patterns

### Document All Public API

```python
rj = Rejig("src/")

# Generate docstrings for public API only
for func in rj.find_functions():
    if not func.name.startswith("_") and not func.docstring:
        func.generate_docstring(style="google")

for cls in rj.find_classes():
    if not cls.name.startswith("_"):
        if not cls.docstring:
            cls.generate_docstring(style="google")
        for method in cls.find_methods():
            if not method.name.startswith("_") and not method.docstring:
                method.generate_docstring(style="google")
```

### Migrate Docstring Style

```python
# Convert entire codebase from Sphinx to Google style
rj = Rejig("src/")

rj.find_functions().with_docstrings().convert_docstring_style("google")
rj.find_methods().with_docstrings().convert_docstring_style("google")
rj.find_classes().with_docstrings().convert_docstring_style("google")
```

### Sync Docstrings After Refactoring

```python
# After changing function signatures, update all docstrings
rj = Rejig("src/")

# Update docstrings to match current signatures
rj.find_functions().with_docstrings().update_docstrings()
rj.find_methods().with_docstrings().update_docstrings()
```

### Validate Docstring Coverage

```python
# Check docstring coverage for CI
rj = Rejig("src/")

public_functions = rj.find_functions().filter(lambda f: not f.name.startswith("_"))
public_methods = rj.find_methods().filter(lambda m: not m.name.startswith("_"))

missing_funcs = public_functions.without_docstrings()
missing_methods = public_methods.without_docstrings()

if missing_funcs or missing_methods:
    print("Missing docstrings:")
    for func in missing_funcs:
        print(f"  Function: {func.file_path}:{func.name}")
    for method in missing_methods:
        print(f"  Method: {method.file_path}:{method.class_name}.{method.name}")
    exit(1)
```

### Generate Docstrings from Type Hints

```python
# If type hints exist, use them for docstring generation
func.generate_docstring(
    include_types=True,   # Include types from annotations
    style="google",
)

# This produces:
# def process(data: dict[str, Any], limit: int = 10) -> list[str]:
#     """Process data with limit.
#
#     Args:
#         data (dict[str, Any]): Input data to process.
#         limit (int): Maximum items. Defaults to 10.
#
#     Returns:
#         list[str]: Processed results.
#     """
```

## Integration with Analysis

### Find Documentation Issues

```python
issues = rj.find_analysis_issues()

# Find missing docstrings
missing = issues.by_type("MISSING_DOCSTRING")
for issue in missing:
    print(f"{issue.file_path}:{issue.line_number} - {issue.name}")

# Auto-fix by generating
for issue in missing:
    if issue.target_type == "function":
        rj.find_function(issue.name).generate_docstring()
    elif issue.target_type == "method":
        # Parse class.method format
        cls_name, method_name = issue.name.rsplit(".", 1)
        rj.find_class(cls_name).find_method(method_name).generate_docstring()
```

### Docstring Quality Report

```python
from rejig import DocstringAnalyzer

analyzer = DocstringAnalyzer(rj)
report = analyzer.analyze()

print(f"Total functions: {report.total_functions}")
print(f"With docstrings: {report.with_docstrings}")
print(f"Coverage: {report.coverage_percent:.1f}%")
print()
print(f"Style breakdown:")
for style, count in report.styles.items():
    print(f"  {style}: {count}")
print()
print(f"Quality issues:")
for issue in report.quality_issues:
    print(f"  {issue.file_path}:{issue.name}: {issue.message}")
```
