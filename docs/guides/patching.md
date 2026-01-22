# Patching

Rejig provides comprehensive support for working with unified diffs and git patches. You can parse patches, apply them, generate them from rejig operations, convert them to rejig code, and reverse them for undo operations.

## Quick Start

```python
from rejig import Rejig

rj = Rejig("src/")

# Load and apply a patch
patch = rj.patch_from_file("changes.patch")
print(f"Files: {patch.file_count}, +{patch.total_additions}/-{patch.total_deletions}")
result = patch.apply()

# Generate a patch from rejig operations
result = rj.find_class("Foo").rename("Bar")
patch = rj.generate_patch(result)
patch.save("rename.patch")

# Reverse a patch (undo)
undo = patch.reverse()
undo.apply()
```

## Parsing Patches

### From a String

```python
diff_text = """
--- a/models.py
+++ b/models.py
@@ -10,3 +10,4 @@ class User:
     def __init__(self):
         self.name = ""
+        self.email = ""
"""

patch = rj.patch(diff_text)
print(f"Files affected: {patch.file_count}")
print(f"Lines added: {patch.total_additions}")
print(f"Lines removed: {patch.total_deletions}")
```

### From a File

```python
# Load from patch file
patch = rj.patch_from_file("bugfix.patch")

# Returns empty patch if file doesn't exist (no exception)
patch = rj.patch_from_file("missing.patch")
print(patch.file_count)  # 0
```

### Supported Formats

Rejig supports both unified diff and git diff formats:

**Unified Diff** (from `diff -u`):
```diff
--- a/file.py
+++ b/file.py
@@ -1,3 +1,4 @@
 line1
+inserted
 line2
 line3
```

**Git Diff** (from `git diff`):
```diff
diff --git a/file.py b/file.py
index abc1234..def5678 100644
--- a/file.py
+++ b/file.py
@@ -1,3 +1,4 @@
 line1
+inserted
 line2
 line3
```

Git extended format features are fully supported:
- New file mode (`new file mode 100644`)
- Deleted file mode (`deleted file mode 100644`)
- Renames (`rename from`, `rename to`, `similarity index`)
- Mode changes (`old mode`, `new mode`)
- Binary file detection

## Inspecting Patches

### Patch Properties

```python
patch = rj.patch_from_file("changes.patch")

# Basic stats
print(f"Total files: {patch.file_count}")
print(f"Additions: {patch.total_additions}")
print(f"Deletions: {patch.total_deletions}")

# File paths affected
for path in patch.paths:
    print(f"  {path}")
```

### Filtering by File Type

```python
# New files being added
for fp in patch.new_files:
    print(f"New: {fp.path}")

# Files being deleted
for fp in patch.deleted_files:
    print(f"Deleted: {fp.old_path}")

# Files being renamed
for fp in patch.renamed_files:
    print(f"Renamed: {fp.old_path} -> {fp.new_path}")

# Files being modified (content only)
for fp in patch.modified_files:
    print(f"Modified: {fp.path}")
```

### Navigating to Files and Hunks

```python
patch = rj.patch_from_file("changes.patch")

# Iterate over file targets
for file_target in patch.files():
    print(f"\n{file_target.path}:")
    print(f"  +{file_target.additions_count}/-{file_target.deletions_count}")

    # Iterate over hunks
    for hunk in file_target.hunks():
        print(f"  @@ {hunk.old_start},{hunk.old_count} -> {hunk.new_start},{hunk.new_count}")

# Look up specific file
file_target = patch.file("src/models.py")
if file_target:
    print(f"Found changes to models.py")

    # Look up specific hunk
    first_hunk = file_target.hunk(0)
    if first_hunk:
        print(f"First hunk starts at line {first_hunk.old_start}")
```

### Getting Content

```python
# Get hunk content
hunk = patch.file("src/models.py").hunk(0)

# Original content (what was removed + context)
old_content = hunk.get_old_content()

# New content (what was added + context)
new_content = hunk.get_new_content()

# Full patch as unified diff
diff_text = patch.to_unified_diff()
```

### Summary

```python
# Get a human-readable summary
print(patch.summary())

# Output:
# Patch: 3 file(s)
#   +42/-15 lines
#   New: 1
#   Modified: 2
# Files:
#   src/new_module.py (new): +30/-0
#   src/models.py: +10/-5
#   src/utils.py: +2/-10
```

## Applying Patches

### Basic Apply

```python
rj = Rejig("src/")
patch = rj.patch_from_file("changes.patch")

# Apply all changes
result = patch.apply()

if result.success:
    print(f"Applied to {len(result.files_changed)} files")
else:
    print(f"Failed: {result.message}")
```

### Dry Run Mode

```python
rj = Rejig("src/", dry_run=True)
patch = rj.patch_from_file("changes.patch")

# Preview what would happen
result = patch.apply()
print(result.diff)  # Shows diff without writing files
```

### Apply Individual Files or Hunks

```python
patch = rj.patch_from_file("changes.patch")

# Apply only changes to a specific file
file_target = patch.file("src/models.py")
if file_target:
    result = file_target.apply()

# Apply a specific hunk (use with caution - line numbers may shift)
hunk = file_target.hunk(0)
result = hunk.apply()
```

## Generating Patches

### From a Single Result

```python
rj = Rejig("src/", dry_run=True)

# Perform an operation
result = rj.find_class("OldName").rename("NewName")

# Generate a patch from the result
patch = rj.generate_patch(result)
patch.save("rename.patch")
```

### From a BatchResult

```python
rj = Rejig("src/", dry_run=True)

# Perform batch operations
batch = rj.find_classes(pattern="^Test").add_decorator("pytest.mark.slow")

# Generate patch from all changes
patch = rj.generate_patch(batch)
print(patch.summary())
```

### From a Transaction

```python
rj = Rejig("src/", dry_run=True)

with rj.transaction() as tx:
    rj.find_class("Foo").rename("Bar")
    rj.find_function("helper").add_decorator("cache")
    rj.find_method("process").add_parameter("timeout", "int", "30")

    # Generate patch from transaction (before commit)
    patch = rj.generate_patch(tx)
    patch.save("refactoring.patch")
```

### Saving Patches

```python
patch = rj.generate_patch(result)

# Save to file
result = patch.save("output.patch")
if result.success:
    print(f"Saved to {result.files_changed[0]}")

# Overwrite existing file
result = patch.save("output.patch", overwrite=True)

# Get as string instead of saving
diff_text = patch.to_unified_diff()
```

## Reversing Patches

Create a reversed patch to undo changes:

```python
# Load original patch
patch = rj.patch_from_file("changes.patch")

# Create reversed version
undo_patch = patch.reverse()

# Apply to undo the original changes
result = undo_patch.apply()

# Or save for later
undo_patch.save("undo-changes.patch")
```

Reversal works at all levels:

```python
# Reverse entire patch
undo_patch = patch.reverse()

# Reverse a specific file's changes
undo_file = patch.file("models.py").reverse()

# Reverse a specific hunk
undo_hunk = patch.file("models.py").hunk(0).reverse()
```

## Converting to Rejig Code

Convert a patch to equivalent rejig Python code:

```python
patch = rj.patch_from_file("changes.patch")

# Generate rejig code
code = patch.to_rejig_code()
print(code)

# Output might be:
# rj.file("src/models.py").find_class("OldName").rename("NewName")
# rj.file("src/utils.py").lines(10, 15).rewrite("...")
```

### Smart Mode vs Line Mode

```python
# Smart mode (default): Detects high-level operations
code = patch.to_rejig_code(smart_mode=True)
# Output: rj.file("src/models.py").find_class("Foo").rename("Bar")

# Line mode: Always uses line-based operations (more reliable)
code = patch.to_rejig_code(smart_mode=False)
# Output: rj.file("src/models.py").lines(10, 15).rewrite("...")
```

### Custom Variable Name

```python
code = patch.to_rejig_code(variable_name="refactor")
# Output: refactor.file("src/models.py").find_class("Foo").rename("Bar")
```

## Generating Python Scripts

Convert a patch to a complete, executable Python script that applies the changes using rejig operations:

```python
patch = rj.patch_from_file("changes.patch")

# Generate a complete Python script
script = patch.to_script()
print(script)
```

The generated script includes:
- Shebang line (`#!/usr/bin/env python3`)
- Module docstring with patch metadata
- Imports
- Patch summary as comments
- Main function with error handling
- Standard `if __name__ == "__main__"` block

### Saving Scripts

```python
# Save the script directly to a file
result = patch.save_script("apply_changes.py")
if result.success:
    print(f"Script saved to {result.files_changed[0]}")

# Overwrite existing file
result = patch.save_script("apply_changes.py", overwrite=True)
```

The saved script is automatically made executable.

### Script Options

```python
# Full control over script generation
script = patch.to_script(
    variable_name="refactor",       # Name for Rejig instance
    root_path="src/",               # Root path in the script
    description="Apply bugfix",     # Custom docstring description
    dry_run=True,                   # Generate dry-run mode script
    smart_mode=False,               # Use line-based operations
    include_error_handling=True,    # Include result checking
    include_summary=True,           # Include patch summary comments
)
```

### Example Generated Script

For a simple rename patch, the generated script looks like:

```python
#!/usr/bin/env python3
"""
Apply bugfix

Generated from patch: +5/-3 lines
"""

from pathlib import Path

from rejig import Rejig


# Patch Summary
# Files: 1
# Additions: +5
# Deletions: -3
#   src/models.py: +5/-3


def main() -> None:
    """Apply the patch changes."""
    rj = Rejig("src/")

    # Apply changes
    results = []

    result = rj.file("src/models.py").find_class("OldName").rename("NewName")
    results.append(result)
    if not result.success:
        print(f"Warning: {result.message}")

    # Report results
    success_count = sum(1 for r in results if r.success)
    total_count = len(results)
    print(f"Completed: {success_count}/{total_count} operations succeeded")

    if success_count < total_count:
        failed = [r for r in results if not r.success]
        for r in failed:
            print(f"  Failed: {r.message}")


if __name__ == "__main__":
    main()
```

### Use Cases

**Share refactoring as executable script:**
```python
# Generate a script that teammates can run
patch = rj.patch_from_file("migration.patch")
patch.save_script("run_migration.py", description="Database model migration")
```

**Create dry-run preview scripts:**
```python
# Generate a script that previews changes without applying
patch.save_script(
    "preview_changes.py",
    dry_run=True,
    description="Preview the refactoring changes",
)
```

**Generate scripts for CI/CD:**
```python
# Generate a script for automated pipelines
patch.save_script(
    "apply_in_ci.py",
    root_path="${PROJECT_ROOT}",
    include_error_handling=True,
)
```

## Analyzing Patches

Detect what operations a patch represents:

```python
from rejig.patching import OperationType

patch = rj.patch_from_file("changes.patch")

# Get detected operations
operations = patch.analyze()

for op in operations:
    print(f"{op.type.name}: {op.details}")
    print(f"  File: {op.file_path}")
    print(f"  Confidence: {op.confidence}")
```

### Detected Operation Types

The analyzer can detect:

| Operation | Description |
|-----------|-------------|
| `CLASS_ADD` | New class definition added |
| `CLASS_DELETE` | Class definition removed |
| `CLASS_RENAME` | Class renamed (detected from paired add/delete) |
| `FUNCTION_ADD` | New module-level function added |
| `FUNCTION_DELETE` | Module-level function removed |
| `FUNCTION_RENAME` | Function renamed |
| `METHOD_ADD` | New method added to a class |
| `METHOD_DELETE` | Method removed from a class |
| `METHOD_RENAME` | Method renamed |
| `DECORATOR_ADD` | Decorator added |
| `DECORATOR_REMOVE` | Decorator removed |
| `IMPORT_ADD` | Import statement added |
| `IMPORT_REMOVE` | Import statement removed |
| `LINE_REWRITE` | Lines replaced with new content |
| `LINE_INSERT` | Lines inserted |
| `LINE_DELETE` | Lines deleted |
| `FILE_CREATE` | New file created |
| `FILE_DELETE` | File deleted |
| `FILE_RENAME` | File renamed |

## Use Cases

### Review Patches Before Applying

```python
def review_and_apply(patch_path: str):
    rj = Rejig("src/")
    patch = rj.patch_from_file(patch_path)

    # Show summary
    print(patch.summary())
    print("\n" + "=" * 60 + "\n")

    # Show detected operations
    for op in patch.analyze():
        print(f"  {op.type.name}: {op.details}")

    # Show full diff
    print("\n" + patch.to_unified_diff())

    # Confirm
    if input("\nApply? [y/N] ").lower() == "y":
        result = patch.apply()
        print(f"Applied: {result.message}")
```

### Create Undo Patches for Safety

```python
def safe_refactor(rj: Rejig):
    with rj.transaction() as tx:
        # Perform changes
        rj.find_class("OldAPI").rename("NewAPI")
        rj.find_function("deprecated_helper").delete()

        # Generate both forward and reverse patches
        forward_patch = rj.generate_patch(tx)
        undo_patch = forward_patch.reverse()

        # Save undo patch BEFORE committing
        undo_patch.save("undo-refactor.patch")

        # Now commit
        tx.commit()
        forward_patch.save("refactor.patch")
```

### Migrate Code Changes to Another Branch

```python
# On feature branch: capture changes as patch
rj = Rejig("src/", dry_run=True)
result = rj.find_classes(pattern="^Legacy").rename("^Legacy", "Modern")
patch = rj.generate_patch(result)
patch.save("migration.patch")

# On target branch: apply the patch
rj = Rejig("src/")
patch = rj.patch_from_file("migration.patch")
result = patch.apply()
```

### Compare Patch to Current State

```python
def check_patch_applicability(patch_path: str):
    rj = Rejig("src/")
    patch = rj.patch_from_file(patch_path)

    issues = []
    for file_target in patch.files():
        path = rj._resolve_path(file_target.path)

        if file_target.is_new and path.exists():
            issues.append(f"Would create {path} but it already exists")
        elif file_target.is_deleted and not path.exists():
            issues.append(f"Would delete {path} but it doesn't exist")
        elif not file_target.is_new and not path.exists():
            issues.append(f"Would modify {path} but it doesn't exist")

    if issues:
        print("Potential issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("Patch appears applicable")
```

### Generate Patches for CI/CD

```python
def generate_migration_patch():
    """Generate a patch for code migration, suitable for CI review."""
    rj = Rejig("src/", dry_run=True)

    with rj.transaction() as tx:
        # Modernize type hints
        rj.find_files("**/*.py").modernize_type_hints()

        # Update deprecated APIs
        for func in rj.find_functions():
            if "oldapi" in func.name.lower():
                func.rename(func.name.replace("oldapi", "newapi"))

        # Generate patch
        patch = rj.generate_patch(tx)

        # Add metadata
        header = f"""# Auto-generated migration patch
# Generated: {datetime.now().isoformat()}
# Operations: {len(patch.analyze())}
# Files affected: {patch.file_count}

"""

        with open("migration.patch", "w") as f:
            f.write(header)
            f.write(patch.to_unified_diff())
```

## Best Practices

1. **Always use dry_run for patch generation**: This ensures you see what would change without modifying files.

2. **Save undo patches before applying**: In case something goes wrong, you have a way to revert.

3. **Review patches before applying**: Use `patch.summary()` and `patch.analyze()` to understand changes.

4. **Use transactions for complex changes**: Generate patches from transactions for atomic, reviewable changes.

5. **Prefer smart_mode=False for reliability**: Line-based operations are more predictable than detected operations.

6. **Check file existence before applying**: Patches may fail if expected files don't exist or have changed.
