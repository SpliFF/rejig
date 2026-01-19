# Codemod Recipes

Ready-to-use scripts for common code migrations.

## Django Migrations

### Rename Model

```python
from rejig import Rejig

def rename_django_model(rj: Rejig, old_name: str, new_name: str):
    """Rename a Django model and update references."""

    # Rename the model class
    model = rj.find_classes(old_name).first()
    if not model:
        print(f"Model {old_name} not found")
        return

    model.rename(new_name)

    # Update Meta.db_table if it exists
    meta = model.find_class("Meta")
    if meta.exists():
        # Keep the old table name to avoid migration
        content = meta.get_content()
        if "db_table" not in str(content.data):
            meta.add_attribute("db_table", type_hint="str",
                             default=f'"{old_name.lower()}"')

    # Update ForeignKey references in other models
    for cls in rj.find_classes():
        content = cls.get_content()
        if content and old_name in str(content.data):
            # This is simplified - real impl would use CST
            pass

    print(f"Renamed {old_name} to {new_name}")


rj = Rejig("myapp/")
rename_django_model(rj, "UserProfile", "Profile")
```

### Add Created/Updated Timestamps

```python
def add_timestamps_to_models(rj: Rejig):
    """Add created_at and updated_at to all models."""

    for cls in rj.find_classes():
        # Check if it's a Django model
        content = cls.get_content()
        if not content or "models.Model" not in str(content.data):
            continue

        # Skip if already has timestamps
        if "created_at" in str(content.data):
            continue

        # Add the fields
        cls.add_attribute(
            "created_at",
            type_hint="models.DateTimeField",
            default="models.DateTimeField(auto_now_add=True)"
        )
        cls.add_attribute(
            "updated_at",
            type_hint="models.DateTimeField",
            default="models.DateTimeField(auto_now=True)"
        )

        print(f"Added timestamps to {cls.name}")


rj = Rejig("myapp/models/")
add_timestamps_to_models(rj)
```

## Testing Migrations

### Convert unittest to pytest

```python
def convert_unittest_to_pytest(rj: Rejig):
    """Convert unittest test classes to pytest functions."""

    for cls in rj.find_classes(pattern="^Test"):
        # Skip if not a unittest class
        content = cls.get_content()
        if not content or "unittest.TestCase" not in str(content.data):
            continue

        # Remove the base class
        cls.remove_base_class("unittest.TestCase")

        # Convert setUp to fixture
        setup = cls.find_method("setUp")
        if setup.exists():
            setup.rename("setup_method")
            setup.add_decorator("pytest.fixture(autouse=True)")

        # Convert assertion methods
        for method in cls.find_methods(pattern="^test_"):
            # This would need more sophisticated replacement
            # assertEqual → assert x == y
            # assertTrue → assert x
            pass

        print(f"Converted {cls.name}")


rj = Rejig("tests/")
convert_unittest_to_pytest(rj)
```

### Add pytest Markers

```python
def add_integration_markers(rj: Rejig):
    """Mark tests that use database or network as integration tests."""

    integration_indicators = ["database", "db", "requests", "httpx", "aiohttp"]

    for cls in rj.find_classes(pattern="^Test"):
        content = cls.get_content()
        if not content:
            continue

        content_str = str(content.data).lower()

        # Check for integration test indicators
        is_integration = any(ind in content_str for ind in integration_indicators)

        if is_integration:
            cls.add_decorator("pytest.mark.integration")
            print(f"Marked {cls.name} as integration")


rj = Rejig("tests/")
add_integration_markers(rj)
```

## Type Hint Migrations

### Add Type Hints from Defaults

```python
def add_type_hints_from_defaults(rj: Rejig):
    """Infer type hints from default parameter values."""

    type_map = {
        "None": "None",
        "True": "bool",
        "False": "bool",
        "[]": "list",
        "{}": "dict",
        '""': "str",
        "''": "str",
        "0": "int",
        "0.0": "float",
    }

    for func in rj.find_functions():
        if func.has_type_hints():
            continue

        # This would need actual parameter inspection
        # Simplified example
        func.infer_type_hints()
        print(f"Added hints to {func.name}")


rj = Rejig("src/")
add_type_hints_from_defaults(rj)
```

### Modernize Type Hints

```python
def modernize_all_type_hints(rj: Rejig):
    """Update to Python 3.10+ type hint syntax."""

    for file in rj.find_files():
        result = file.modernize_type_hints()
        if result.files_changed:
            print(f"Modernized {file.path}")


rj = Rejig("src/")
modernize_all_type_hints(rj)
```

## API Migrations

### Rename Function Across Codebase

```python
def rename_api_function(rj: Rejig, old_name: str, new_name: str):
    """Rename a function and update all call sites."""

    # Find and rename the function definition
    func = rj.find_functions(old_name).first()
    if func:
        func.rename(new_name)
        print(f"Renamed definition: {old_name} → {new_name}")

    # Update imports
    for file in rj.find_files():
        content = file.get_content()
        if not content:
            continue

        if f"from .* import.*{old_name}" in str(content.data):
            # Update import statement
            file.replace_pattern(
                rf"(from .* import.*)(\b{old_name}\b)",
                rf"\1{new_name}"
            )

        # Update call sites
        file.replace_pattern(rf"\b{old_name}\s*\(", f"{new_name}(")


rj = Rejig("src/")
rename_api_function(rj, "process_data", "transform_data")
```

### Deprecate and Redirect

```python
def deprecate_function(rj: Rejig, old_name: str, new_name: str):
    """Add deprecation wrapper that redirects to new function."""

    func = rj.find_functions(old_name).first()
    if not func:
        print(f"Function {old_name} not found")
        return

    # Get the file
    file = rj.file(func.file_path)

    # Add deprecation wrapper
    wrapper = f'''
def {old_name}(*args, **kwargs):
    """Deprecated: Use {new_name} instead."""
    import warnings
    warnings.warn(
        "{old_name} is deprecated, use {new_name}",
        DeprecationWarning,
        stacklevel=2
    )
    return {new_name}(*args, **kwargs)
'''

    # Rename original
    func.rename(new_name)

    # Add wrapper after the renamed function
    # (This would need proper positioning logic)
    print(f"Deprecated {old_name} → {new_name}")


rj = Rejig("src/")
deprecate_function(rj, "old_api", "new_api")
```

## Cleanup Codemods

### Remove Debug Statements

```python
def remove_debug_statements(rj: Rejig):
    """Remove print statements and debugger calls."""

    debug_patterns = [
        r"^\s*print\s*\(",
        r"^\s*import pdb",
        r"^\s*pdb\.set_trace\(\)",
        r"^\s*breakpoint\(\)",
        r"^\s*import ipdb",
        r"^\s*ipdb\.set_trace\(\)",
    ]

    for file in rj.find_files():
        for pattern in debug_patterns:
            file.replace_pattern(pattern, "")

        print(f"Cleaned {file.path}")


rj = Rejig("src/")
remove_debug_statements(rj)
```

### Remove Unused Type Ignores

```python
def cleanup_type_ignores(rj: Rejig):
    """Remove type: ignore comments that are no longer needed."""

    result = rj.remove_unused_type_ignores()

    if result.files_changed:
        print(f"Cleaned {len(result.files_changed)} files")
        for f in result.files_changed:
            print(f"  - {f}")


rj = Rejig("src/")
cleanup_type_ignores(rj)
```

### Standardize String Quotes

```python
def standardize_quotes(rj: Rejig):
    """Convert all strings to double quotes (let Black handle it)."""

    # This is better handled by Black, but as an example:
    for file in rj.find_files():
        file.replace_pattern(r"'([^']*)'", r'"\1"')


# Better approach: just run Black
import subprocess
subprocess.run(["black", "src/"])
```

## Project Setup Codemods

### Initialize pyproject.toml

```python
def init_pyproject(rj: Rejig, project_name: str):
    """Create a modern pyproject.toml."""

    toml = rj.toml("pyproject.toml")

    # Project metadata
    toml.set("project.name", project_name)
    toml.set("project.version", "0.1.0")
    toml.set("project.requires-python", ">=3.10")
    toml.set("project.dependencies", [])
    toml.set("project.optional-dependencies.dev", [
        "pytest>=7.0",
        "black>=23.0",
        "ruff>=0.1.0",
        "mypy>=1.0",
    ])

    # Tool configuration
    toml.set("tool.black.line-length", 110)
    toml.set("tool.ruff.select", ["E", "F", "W", "I"])
    toml.set("tool.ruff.line-length", 110)
    toml.set("tool.mypy.python_version", "3.10")
    toml.set("tool.mypy.strict", True)
    toml.set("tool.pytest.ini_options.testpaths", ["tests"])

    print(f"Created pyproject.toml for {project_name}")


rj = Rejig(".")
init_pyproject(rj, "my-project")
```

## Running Codemods

### As a Script

```python
#!/usr/bin/env python3
"""Codemod: Add type hints to all functions."""

from rejig import Rejig
import sys

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "src/"
    rj = Rejig(path)

    results = (
        rj.find_functions()
        .filter(lambda f: not f.has_type_hints())
        .infer_type_hints()
    )

    print(f"Updated {len(results.succeeded)} functions")
    if results.failed:
        print(f"Failed: {len(results.failed)}")

if __name__ == "__main__":
    main()
```

### With Dry Run

```python
def run_codemod(rj: Rejig, dry_run: bool = True):
    """Run codemod with optional dry run."""

    if dry_run:
        rj = Rejig(rj.root, dry_run=True)
        print("DRY RUN - no files will be modified")

    # Your codemod logic here
    result = rj.find_classes("^Test").add_decorator("@slow")

    if dry_run:
        print(f"Would modify {len(result)} classes")
    else:
        print(f"Modified {len(result.files_changed)} files")


rj = Rejig("src/")
run_codemod(rj, dry_run=True)   # Preview
run_codemod(rj, dry_run=False)  # Apply
```
