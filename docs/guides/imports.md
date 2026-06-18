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

file.add_import("from myapp.models import User")
```

### Remove Imports

Imports are removed through targets. Find them with `find_imports()` or
`find_unused_imports()`, then call `delete()` on a target (or the list).

```python
# Remove all unused imports in one step
file.remove_unused_imports()

# Or operate on targets
file.find_unused_imports().delete()

# Delete a single import target
imp = file.find_imports().filter_relative().to_list()[0]
imp.delete()
```

## Finding Imports

### Find All Imports

```python
imports = file.find_imports()

for imp in imports:
    print(f"{imp.line_number}: {imp.module}")
    print(f"  Names: {imp.names}")
    print(f"  Is relative: {imp.is_relative}")
    print(f"  Is unused: {imp.is_unused}")
```

### Filter Imports

`find_imports()` takes no arguments and returns an `ImportTargetList`. Narrow
results with the built-in filters:

```python
# Find relative imports
relative = file.find_imports().filter_relative()

# Find absolute imports
absolute = file.find_imports().filter_absolute()

# Find unused imports
unused = file.find_imports().filter_unused()

# Restrict to a specific file
in_file = file.find_imports().in_file("module.py")
```

## Import Analysis

### ImportTarget Properties

Each `ImportTarget` returned by `find_imports()` exposes:

```python
imp = file.find_imports().to_list()[0]

imp.line_number      # 5
imp.module           # "typing" (None for "import os" style)
imp.names            # ["Optional", "List"]
imp.is_relative      # False
imp.is_unused        # True if the import is never used
```

The full underlying `ImportInfo` (with extra detail) is available via
`imp.import_info`:

```python
info = imp.import_info

info.import_statement # "from typing import Optional, List"
info.aliases          # {"L": "List"} if aliased
info.is_from_import   # True
info.relative_level   # 0 (1 for ".", 2 for "..", etc.)
info.is_future        # True for __future__ imports
info.is_type_checking # True if inside TYPE_CHECKING block

info.get_imported_names()    # ["Optional", "List"]
info.get_original_name("L")  # "List" (resolve alias)
```

### Detect Unused Imports

```python
from rejig import ImportAnalyzer

analyzer = ImportAnalyzer(rj)

# Find unused imports in a file (returns ImportInfo objects)
unused = analyzer.find_unused_imports(file.path)
for info in unused:
    print(f"Unused: {info.import_statement} at line {info.line_number}")

# Remove all unused imports
file.remove_unused_imports()

# Or use the target-based batch operation
file.find_unused_imports().delete()
```

### Detect Potentially Missing Imports

```python
# Find names that are used but appear to have no definition or import
missing = analyzer.find_potentially_missing_imports(file.path)
for name in missing:
    print(f"Possibly missing import for: {name}")
```

## Import Organization

Rejig can organize imports similar to isort. The organizer sorts imports into
sections (future, standard library, third-party, first-party, local) and orders
them within each section.

```python
from rejig import ImportOrganizer

organizer = ImportOrganizer(rj)

# Organize imports in a single file (takes a Path)
organizer.organize(file.path)

# Organize every Python file in the project
for f in rj.find_files():
    organizer.organize(f.path)
```

### First-Party Packages

First-party packages are auto-detected, but you can specify them explicitly when
constructing the organizer:

```python
organizer = ImportOrganizer(rj, first_party_packages={"mypackage"})

for f in rj.find_files():
    organizer.organize(f.path)
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
    print(f"  {' -> '.join(cycle.cycle)}")
    # Or simply: print(str(cycle))
```

### Import Graph Analysis

```python
# Get all modules that import a specific module (direct dependents)
dependents = graph.get_dependents("myapp.models")
print(f"Modules importing myapp.models: {dependents}")

# Get all modules imported by a specific module (direct dependencies)
deps = graph.get_dependencies("myapp.views")
print(f"Modules imported by myapp.views: {deps}")

# Get all transitive dependencies of a module
all_deps = graph.get_all_dependencies("myapp.views")
print(f"All (transitive) dependencies: {all_deps}")
```

## Relative/Absolute Conversion

Conversion is done per import target.

### Convert to Relative Imports

```python
# Convert absolute imports to relative within the same package
for imp in file.find_imports().filter_absolute():
    imp.convert_to_relative()

# Example:
# Before: from myapp.models import User
# After:  from .models import User
```

### Convert to Absolute Imports

```python
# Convert relative imports to absolute
for imp in file.find_imports().filter_relative():
    imp.convert_to_absolute(package_name="myapp")

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
relative = imports.filter_relative()
absolute = imports.filter_absolute()
unused = imports.filter_unused()

# Batch delete (e.g. remove all unused imports)
imports.filter_unused().delete()

# Inspect individual targets
for imp in imports:
    print(imp.line_number, imp.module, imp.names)
```

## Common Patterns

### Clean Up Imports After Refactoring

```python
rj = Rejig("src/")

# After removing code, clean up unused imports
for file in rj.find_files():
    unused = file.find_unused_imports()
    if unused:
        print(f"Removing {len(unused)} unused imports from {file.path}")
        unused.delete()
```

### Modernize typing Imports

```python
# Modernize type hints to Python 3.10+ syntax, then drop now-unused imports
for file in rj.find_files():
    file.modernize_type_hints()

# Clean up imports that are no longer referenced
# (e.g. "from typing import List, Dict" once List/Dict are gone)
for file in rj.find_files():
    file.find_unused_imports().delete()
```

### Reorganize Imports

```python
# Sort and group imports across the project
from rejig import ImportOrganizer

organizer = ImportOrganizer(rj)
for file in rj.find_files():
    organizer.organize(file.path)

# Before:
# from typing import Optional
# import os
# from typing import List

# After:
# import os
#
# from typing import List, Optional
```

## Integration with Other Features

### With Circular Import Detection

```python
# Find circular imports across the project
from rejig import ImportGraph

graph = ImportGraph(rj)
graph.build()
for cycle in graph.find_circular_imports():
    print(f"Circular import: {cycle}")
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
    file.find_unused_imports().delete()
```
