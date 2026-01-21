# Import Management

Rejig provides comprehensive tools for managing Python imports: organizing, detecting unused imports, finding circular dependencies, and converting between relative and absolute imports.

## Adding and Removing Imports

### Add Imports

```python
from rejig import Rejig

rj = Rejig("src/")
file = rj.file("module.py")

# Add a simple import
file.add_import("import os")

# Add a from import
file.add_import("from typing import Optional, List")

# Add with alias
file.add_import("import numpy as np")

# Add to TYPE_CHECKING block
file.add_import("from myapp.models import User", type_checking=True)
```

### Remove Imports

```python
# Remove by exact match
file.remove_import("import os")

# Remove by pattern (regex)
file.remove_import(r"from deprecated import.*")

# Remove specific names from a from import
file.remove_import_name("typing", "Optional")  # Keeps List if imported
```

## Finding Imports

### Find All Imports

```python
imports = file.find_imports()

for imp in imports:
    print(f"{imp.line_number}: {imp.import_statement}")
    print(f"  Module: {imp.module}")
    print(f"  Names: {imp.get_imported_names()}")
    print(f"  Is from import: {imp.is_from_import}")
    print(f"  Is relative: {imp.is_relative}")
```

### Find Specific Imports

```python
# Find imports of a specific module
typing_imports = file.find_imports("typing")

# Find imports matching a pattern
test_imports = file.find_imports(pattern=r"^test_")

# Find relative imports
relative = file.find_imports().filter(lambda i: i.is_relative)

# Find TYPE_CHECKING imports
type_checking = file.find_imports().filter(lambda i: i.is_type_checking)
```

## Import Analysis

### ImportInfo Properties

Each import has detailed information:

```python
imp = file.find_imports("typing").first()

# Basic info
imp.module           # "typing"
imp.names            # ["Optional", "List"]
imp.aliases          # {"List": "L"} if aliased
imp.line_number      # 5
imp.import_statement # "from typing import Optional, List"

# Type info
imp.is_from_import   # True
imp.is_relative      # False
imp.relative_level   # 0 (1 for ".", 2 for "..", etc.)
imp.is_future        # True for __future__ imports
imp.is_type_checking # True if inside TYPE_CHECKING block

# Methods
imp.get_imported_names()    # ["Optional", "List"]
imp.get_original_name("L")  # "List" (resolve alias)
```

### Detect Unused Imports

```python
from rejig import ImportAnalyzer

analyzer = ImportAnalyzer(rj)

# Find unused imports in a file
unused = analyzer.find_unused_imports(file.path)
for imp in unused:
    print(f"Unused: {imp.import_statement} at line {imp.line_number}")

# Remove all unused imports
for imp in unused:
    file.remove_import(imp.import_statement)

# Or use the batch operation
file.find_unused_imports().delete_all()
```

### Detect Missing Imports

```python
# Find names used but not imported
missing = analyzer.find_missing_imports(file.path)
for name in missing:
    print(f"Missing import for: {name}")

# Suggest imports for missing names
suggestions = analyzer.suggest_imports(file.path)
for name, possible_imports in suggestions.items():
    print(f"{name} could be imported from: {possible_imports}")
```

## Import Organization

Rejig can organize imports similar to isort:

```python
from rejig import ImportOrganizer

organizer = ImportOrganizer(rj)

# Organize imports in a single file
organizer.organize(file.path)

# Organize all files in the project
organizer.organize_all()

# Preview changes (dry run)
rj_dry = Rejig("src/", dry_run=True)
organizer = ImportOrganizer(rj_dry)
result = organizer.organize_all()
print(result.diff)
```

### Organization Options

```python
organizer = ImportOrganizer(rj)

# Set grouping order
organizer.configure(
    sections=[
        "FUTURE",      # __future__ imports
        "STDLIB",      # Standard library
        "THIRDPARTY",  # Third-party packages
        "FIRSTPARTY",  # Your project's packages
        "LOCALFOLDER", # Relative imports
    ],
    lines_between_sections=2,
    lines_between_types=1,  # Between import and from import
    force_sort_within_sections=True,
    combine_as_imports=True,
)

organizer.organize_all()
```

## Circular Import Detection

Circular imports can cause runtime errors. Rejig can detect them:

```python
from rejig import ImportGraph

graph = ImportGraph(rj)

# Build the import graph
graph.build()

# Find all circular imports
cycles = graph.find_circular_imports()
for cycle in cycles:
    print(f"Circular import chain:")
    print(f"  {' -> '.join(cycle.modules)}")

# Check if a specific import would create a cycle
would_cycle = graph.would_create_cycle("module_a", "module_b")
```

### Import Graph Analysis

```python
# Get all modules that import a specific module
importers = graph.get_importers("myapp.models")
print(f"Modules importing myapp.models: {importers}")

# Get all modules imported by a specific module
imports = graph.get_imports("myapp.views")
print(f"Modules imported by myapp.views: {imports}")

# Find the shortest import path between two modules
path = graph.find_path("module_a", "module_z")
if path:
    print(f"Import path: {' -> '.join(path)}")

# Get dependency depth (how many levels deep)
depth = graph.get_depth("myapp.views")
print(f"Import depth: {depth}")
```

## Relative/Absolute Conversion

### Convert to Relative Imports

```python
# Convert absolute imports to relative within the same package
file.convert_imports_to_relative()

# Example:
# Before: from myapp.models import User
# After:  from .models import User
```

### Convert to Absolute Imports

```python
# Convert relative imports to absolute
file.convert_imports_to_absolute(package_name="myapp")

# Example:
# Before: from .models import User
# After:  from myapp.models import User
```

## Import Targets

Work with imports as targets for batch operations:

```python
# Get import targets
imports = file.find_imports()

# Filter imports
stdlib = imports.filter(lambda i: i.is_stdlib)
third_party = imports.filter(lambda i: not i.is_stdlib and not i.is_first_party)

# Batch operations
imports.matching(r"deprecated").delete_all()

# Add names to existing imports
typing_import = imports.matching("typing").first()
if typing_import:
    typing_import.add_name("Any")
    typing_import.add_name("Dict")
```

## Common Patterns

### Clean Up Imports After Refactoring

```python
rj = Rejig("src/")

# After removing code, clean up unused imports
for file in rj.find_files():
    unused = file.find_unused_imports()
    if unused:
        unused.delete_all()
        print(f"Removed {len(unused)} unused imports from {file.path}")
```

### Migrate Import Style

```python
# Convert all typing imports to Python 3.10+ style
for file in rj.find_files():
    # Remove typing imports that are now builtins
    file.remove_import_name("typing", "List")
    file.remove_import_name("typing", "Dict")
    file.remove_import_name("typing", "Set")
    file.remove_import_name("typing", "Tuple")
    file.remove_import_name("typing", "Optional")

    # Clean up empty typing imports
    typing_import = file.find_imports("typing").first()
    if typing_import and not typing_import.names:
        typing_import.delete()
```

### Consolidate Imports

```python
# Combine multiple imports from the same module
from rejig import ImportOrganizer

organizer = ImportOrganizer(rj)
organizer.configure(
    combine_star_imports=False,
    combine_as_imports=True,
    force_single_line=False,
)
organizer.organize_all()

# Before:
# from typing import Optional
# from typing import List
# from typing import Dict

# After:
# from typing import Dict, List, Optional
```

### Add TYPE_CHECKING Imports

```python
# Move runtime-only type imports to TYPE_CHECKING block
file = rj.file("module.py")

# Add the TYPE_CHECKING import if needed
file.add_import("from typing import TYPE_CHECKING")

# Move heavy imports to TYPE_CHECKING
file.move_import_to_type_checking("from myapp.heavy_module import HeavyClass")
```

## Integration with Other Features

### With Code Analysis

```python
# Find files with circular imports
issues = rj.find_analysis_issues()
circular = issues.by_type("CIRCULAR_IMPORT")
for issue in circular:
    print(f"Circular import in {issue.file_path}: {issue.message}")
```

### With Modernization

```python
# Modernize imports as part of code modernization
from rejig import Rejig

rj = Rejig("src/")

# Modernize type hints (which may affect imports)
rj.find_functions().modernize_type_hints()

# Then clean up now-unused typing imports
for file in rj.find_files():
    file.find_unused_imports().delete_all()
```
