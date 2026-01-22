# Patching Reference

Complete API reference for the patching module.

## Data Models

### Patch

A complete patch containing changes to one or more files.

```python
from rejig.patching import Patch

patch = Patch(files=[...], format=PatchFormat.UNIFIED)
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `files` | `list[FilePatch]` | List of file patches |
| `format` | `PatchFormat` | Patch format (UNIFIED or GIT) |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `file_count` | `int` | Number of files in the patch |
| `total_additions` | `int` | Total added lines across all files |
| `total_deletions` | `int` | Total deleted lines across all files |
| `paths` | `list[Path]` | All file paths affected |
| `new_files` | `list[FilePatch]` | Files being created |
| `deleted_files` | `list[FilePatch]` | Files being deleted |
| `renamed_files` | `list[FilePatch]` | Files being renamed |
| `modified_files` | `list[FilePatch]` | Files with content changes only |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `get_file(path)` | `FilePatch \| None` | Get file patch by path |
| `reverse()` | `Patch` | Create reversed patch (undo) |
| `to_unified_diff()` | `str` | Convert to unified diff string |
| `summary()` | `str` | Human-readable summary |

---

### FilePatch

All changes to a single file.

```python
from rejig.patching import FilePatch

fp = FilePatch(
    old_path=Path("old.py"),
    new_path=Path("new.py"),
    hunks=[...],
    is_renamed=True,
)
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `old_path` | `Path \| None` | Path in original version |
| `new_path` | `Path \| None` | Path in new version |
| `hunks` | `list[Hunk]` | List of change hunks |
| `is_new` | `bool` | Whether file is new |
| `is_deleted` | `bool` | Whether file is deleted |
| `is_renamed` | `bool` | Whether file is renamed |
| `is_binary` | `bool` | Whether file is binary |
| `old_mode` | `str \| None` | Original file mode |
| `new_mode` | `str \| None` | New file mode |
| `similarity_index` | `int \| None` | Similarity % for renames |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `path` | `Path \| None` | Primary path (new_path or old_path) |
| `additions_count` | `int` | Total added lines |
| `deletions_count` | `int` | Total deleted lines |
| `has_changes` | `bool` | Whether file has any changes |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `to_header_lines()` | `list[str]` | Generate diff header lines |
| `to_unified_diff()` | `str` | Convert to unified diff |
| `reverse()` | `FilePatch` | Create reversed file patch |

---

### Hunk

A contiguous block of changes in a file.

```python
from rejig.patching import Hunk

hunk = Hunk(
    old_start=10,
    old_count=3,
    new_start=10,
    new_count=5,
    changes=[...],
    function_context="def my_func():",
)
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `old_start` | `int` | Starting line in original file |
| `old_count` | `int` | Line count in original file |
| `new_start` | `int` | Starting line in new file |
| `new_count` | `int` | Line count in new file |
| `changes` | `list[Change]` | List of changes |
| `function_context` | `str \| None` | Function context from @@ line |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `additions` | `list[Change]` | Added lines only |
| `deletions` | `list[Change]` | Deleted lines only |
| `additions_count` | `int` | Count of added lines |
| `deletions_count` | `int` | Count of deleted lines |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `to_header()` | `str` | Generate @@ header line |
| `to_diff_lines()` | `list[str]` | Get diff lines including header |
| `reverse()` | `Hunk` | Create reversed hunk |
| `get_old_content()` | `str` | Original content (deletions + context) |
| `get_new_content()` | `str` | New content (additions + context) |

---

### Change

A single line change in a hunk.

```python
from rejig.patching import Change, ChangeType

change = Change(
    type=ChangeType.ADD,
    content="new line",
    old_line=None,
    new_line=10,
)
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `type` | `ChangeType` | Type of change |
| `content` | `str` | Line content (without +/- prefix) |
| `old_line` | `int \| None` | Line number in original file |
| `new_line` | `int \| None` | Line number in new file |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `is_addition` | `bool` | True if added line |
| `is_deletion` | `bool` | True if deleted line |
| `is_context` | `bool` | True if context line |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `to_diff_line()` | `str` | Convert to diff line with prefix |

---

### Enums

#### PatchFormat

```python
from rejig.patching import PatchFormat

PatchFormat.UNIFIED  # Standard unified diff
PatchFormat.GIT      # Git extended format
```

#### ChangeType

```python
from rejig.patching import ChangeType

ChangeType.ADD      # Added line (+)
ChangeType.DELETE   # Deleted line (-)
ChangeType.CONTEXT  # Context line ( )
```

#### OperationType

```python
from rejig.patching import OperationType

# Class operations
OperationType.CLASS_ADD
OperationType.CLASS_DELETE
OperationType.CLASS_RENAME

# Function operations
OperationType.FUNCTION_ADD
OperationType.FUNCTION_DELETE
OperationType.FUNCTION_RENAME

# Method operations
OperationType.METHOD_ADD
OperationType.METHOD_DELETE
OperationType.METHOD_RENAME

# Decorator operations
OperationType.DECORATOR_ADD
OperationType.DECORATOR_REMOVE

# Import operations
OperationType.IMPORT_ADD
OperationType.IMPORT_REMOVE

# Line operations
OperationType.LINE_REWRITE
OperationType.LINE_INSERT
OperationType.LINE_DELETE

# File operations
OperationType.FILE_CREATE
OperationType.FILE_DELETE
OperationType.FILE_RENAME
```

---

## Target Classes

### PatchTarget

Target for a complete patch. Provides fluent API for patch operations.

```python
from rejig import Rejig

rj = Rejig("src/")
patch = rj.patch_from_file("changes.patch")
```

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `patch` | `Patch` | Underlying Patch object |
| `file_count` | `int` | Number of files |
| `total_additions` | `int` | Total added lines |
| `total_deletions` | `int` | Total deleted lines |
| `paths` | `list[Path]` | All affected paths |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `exists()` | `bool` | True if patch has files |
| `files()` | `TargetList[PatchFileTarget]` | Get all file targets |
| `file(path)` | `PatchFileTarget \| None` | Get specific file target |
| `apply()` | `Result` | Apply the patch |
| `reverse()` | `PatchTarget` | Create reversed patch target |
| `to_rejig_code(var, smart)` | `str` | Convert to rejig code |
| `to_script(**kwargs)` | `str` | Generate complete Python script |
| `save_script(path, **kwargs)` | `Result` | Save Python script to file |
| `to_unified_diff()` | `str` | Get as unified diff string |
| `save(path, overwrite)` | `Result` | Save to file |
| `analyze()` | `list[DetectedOperation]` | Detect operations |
| `summary()` | `str` | Human-readable summary |
| `get_content()` | `Result` | Get diff in result.data |

**to_script() Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `variable_name` | `str` | `"rj"` | Variable name for Rejig instance |
| `root_path` | `str` | `"."` | Root path for Rejig instance |
| `description` | `str \| None` | `None` | Script docstring description |
| `dry_run` | `bool` | `False` | Generate dry-run mode script |
| `smart_mode` | `bool` | `True` | Use smart operation detection |
| `include_error_handling` | `bool` | `True` | Include result checking code |
| `include_summary` | `bool` | `True` | Include patch summary comments |

---

### PatchFileTarget

Target for a single file within a patch.

```python
file_target = patch.file("src/models.py")
```

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `file_patch` | `FilePatch` | Underlying FilePatch |
| `path` | `Path \| None` | Primary path |
| `old_path` | `Path \| None` | Original path |
| `new_path` | `Path \| None` | New path |
| `is_new` | `bool` | Whether new file |
| `is_deleted` | `bool` | Whether deleted |
| `is_renamed` | `bool` | Whether renamed |
| `additions_count` | `int` | Added lines |
| `deletions_count` | `int` | Deleted lines |
| `hunk_count` | `int` | Number of hunks |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `exists()` | `bool` | True if has changes |
| `hunks()` | `TargetList[PatchHunkTarget]` | Get all hunk targets |
| `hunk(index)` | `PatchHunkTarget \| None` | Get hunk by index |
| `apply()` | `Result` | Apply this file's changes |
| `reverse()` | `PatchFileTarget` | Create reversed target |
| `to_unified_diff()` | `str` | Get as unified diff |
| `get_content()` | `Result` | Get diff in result.data |

---

### PatchHunkTarget

Target for a single hunk within a file patch.

```python
hunk_target = file_target.hunk(0)
```

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `hunk` | `Hunk` | Underlying Hunk |
| `index` | `int` | Index in parent file |
| `old_start` | `int` | Start line in original |
| `old_count` | `int` | Line count in original |
| `new_start` | `int` | Start line in new |
| `new_count` | `int` | Line count in new |
| `function_context` | `str \| None` | Function context |
| `additions_count` | `int` | Added lines |
| `deletions_count` | `int` | Deleted lines |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `exists()` | `bool` | True if has changes |
| `apply()` | `Result` | Apply this hunk |
| `reverse()` | `PatchHunkTarget` | Create reversed target |
| `get_old_content()` | `str` | Original content |
| `get_new_content()` | `str` | New content |
| `to_header()` | `str` | Get @@ header |
| `to_diff_lines()` | `list[str]` | Get diff lines |
| `get_content()` | `Result` | Get diff in result.data |

---

## Parser

### PatchParser

Parser for unified diff and git diff formats.

```python
from rejig.patching import PatchParser

parser = PatchParser()
patch = parser.parse(diff_text)
```

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `parse(text)` | `Patch` | Parse diff text |
| `parse_file(path)` | `Patch \| None` | Parse from file |
| `parse_to_result(text)` | `Result` | Parse with result wrapper |

### Convenience Functions

```python
from rejig.patching import parse_patch, parse_patch_file

# Parse from string
patch = parse_patch(diff_text)

# Parse from file
patch = parse_patch_file(Path("changes.patch"))
```

---

## Generator

### PatchGenerator

Generate patches from rejig operations.

```python
from rejig.patching import PatchGenerator

gen = PatchGenerator()
patch = gen.from_result(result)
```

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `from_result(result)` | `Patch` | From single Result |
| `from_batch_result(batch)` | `Patch` | From BatchResult |
| `from_transaction(tx)` | `Patch` | From Transaction |
| `from_files(original, modified)` | `Patch` | From file content dicts |
| `from_diff_string(text)` | `Patch` | From raw diff text |
| `to_file(patch, path, overwrite)` | `Result` | Save patch to file |

### Convenience Functions

```python
from rejig.patching import generate_patch_from_result, generate_patch_from_batch

patch = generate_patch_from_result(result)
patch = generate_patch_from_batch(batch_result)
```

---

## Converter

### PatchConverter

Convert patches to rejig operations and code.

```python
from rejig.patching import PatchConverter

converter = PatchConverter(rejig, smart_mode=True)
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `rejig` | `Rejig` | required | Rejig instance |
| `smart_mode` | `bool` | `True` | Detect high-level operations |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `to_rejig_code(patch, var)` | `str` | Convert to rejig code |
| `to_script(patch, **kwargs)` | `str` | Generate complete Python script |
| `save_script(patch, path, **kwargs)` | `Result` | Save script to file |
| `apply(patch)` | `Result` | Apply patch |

**to_script() Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `variable_name` | `str` | `"rj"` | Variable name for Rejig instance |
| `root_path` | `str` | `"."` | Root path for Rejig instance |
| `description` | `str \| None` | `None` | Script docstring description |
| `dry_run` | `bool` | `False` | Generate dry-run mode script |
| `include_error_handling` | `bool` | `True` | Include result checking code |
| `include_summary` | `bool` | `True` | Include patch summary comments |

### Convenience Functions

```python
from rejig.patching import (
    convert_patch_to_code,
    apply_patch,
    generate_script_from_patch,
    save_script_from_patch,
)

code = convert_patch_to_code(patch, rejig, smart_mode=True)
result = apply_patch(patch, rejig)

# Script generation
script = generate_script_from_patch(patch, rejig, description="My script")
result = save_script_from_patch(patch, rejig, "apply.py", overwrite=True)
```

---

## Analyzer

### PatchAnalyzer

Analyze patches to detect high-level operations.

```python
from rejig.patching import PatchAnalyzer

analyzer = PatchAnalyzer()
operations = analyzer.analyze(patch)
```

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `analyze(patch)` | `list[DetectedOperation]` | Detect all operations |
| `analyze_file_patch(fp)` | `list[DetectedOperation]` | Analyze single file |
| `analyze_hunk(hunk, path, idx)` | `list[DetectedOperation]` | Analyze single hunk |
| `get_optimal_operations(patch)` | `list[DetectedOperation]` | Get optimized operation set |

---

### DetectedOperation

A detected operation from patch analysis.

```python
from rejig.patching import DetectedOperation, OperationType

op = DetectedOperation(
    type=OperationType.CLASS_RENAME,
    file_path=Path("models.py"),
    details={"old_name": "Foo", "new_name": "Bar"},
    confidence=0.8,
)
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `type` | `OperationType` | Type of operation |
| `file_path` | `Path` | Affected file |
| `details` | `dict` | Operation-specific details |
| `hunk_index` | `int \| None` | Hunk index (if applicable) |
| `confidence` | `float` | Confidence score (0.0-1.0) |

---

## Rejig Methods

Methods added to the `Rejig` class for patching support.

### patch()

Create a PatchTarget from diff text.

```python
patch = rj.patch(diff_text)
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `patch_text` | `str` | Unified or git diff text |

**Returns:** `PatchTarget`

---

### patch_from_file()

Load a patch from a file.

```python
patch = rj.patch_from_file("changes.patch")
patch = rj.patch_from_file(Path("changes.patch"))
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | `str \| Path` | Path to patch file |

**Returns:** `PatchTarget` (empty if file doesn't exist)

---

### generate_patch()

Generate a patch from operation results.

```python
patch = rj.generate_patch(result)
patch = rj.generate_patch(batch_result)
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `result` | `Result \| BatchResult` | Operation result(s) |

**Returns:** `PatchTarget`
