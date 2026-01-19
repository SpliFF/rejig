# Line Operations

Work with specific lines for fine-grained control.

## Line Targets

### Single Line

```python
file = rj.file("mymodule.py")
line = file.line(42)
```

### Line Range

```python
block = file.lines(10, 20)  # Lines 10 through 20
```

### Code Block at Line

Find the enclosing structure:

```python
block = file.block_at_line(42)

print(block.kind)        # "class", "function", "method", "if", "for", "while", "try", "with"
print(block.name)        # Name if applicable (class/function name)
print(block.start_line)  # First line of the block
print(block.end_line)    # Last line of the block
```

## Linting Directives

### Type Ignore (mypy)

```python
line = file.line(42)

# Add type: ignore
line.add_type_ignore()                           # Generic
line.add_type_ignore("arg-type")                 # Specific code
line.add_type_ignore(["arg-type", "return-value"])  # Multiple codes
line.add_type_ignore("arg-type", reason="Legacy API")  # With reason

# Remove
line.remove_type_ignore()
```

### Noqa (flake8, ruff)

```python
line.add_noqa()              # Blanket noqa
line.add_noqa("E501")        # Specific code
line.add_noqa(["E501", "F401"])  # Multiple codes

line.remove_noqa()
```

### Pylint

```python
line.add_pylint_disable("line-too-long")
line.remove_pylint_disable()
```

### Formatter (Black)

```python
line.add_fmt_skip()  # # fmt: skip
```

### Coverage

```python
line.add_no_cover()     # pragma: no cover
line.remove_no_cover()
```

## TODO Comments

### Adding TODOs

```python
line.add_todo("Refactor this")
line.add_todo("Fix bug", type="FIXME")
line.add_todo("Needs review", type="TODO", author="jane")
```

### Removing TODOs

```python
line.remove_todo()
```

### Linking to Issues

```python
line.link_to_issue("#123")
```

## Line Block Operations

### Content Access

```python
block = file.lines(10, 20)

result = block.get_content()
if result:
    print(result.data)
```

### Moving Lines

```python
# Move to another position in the same file
block.move_to(100)

# Move to another file
block.move_to_file("other.py", after_line=10)
```

### Rewriting

```python
block.rewrite("""
def new_function():
    pass
""")
```

### Inserting

```python
block.prepend("# Section start\n")
block.append("# Section end\n")
```

### Deleting

```python
block.delete()
```

### Indentation

```python
block.indent()      # Indent by 1 level
block.indent(2)     # Indent by 2 levels
block.dedent()      # Dedent by 1 level
block.dedent(2)     # Dedent by 2 levels
```

## Directive Wrapping

Wrap a block of lines with directives:

```python
block = file.lines(10, 20)

# Wrap with fmt: off/on
block.wrap_with_fmt_off()

# Wrap with pylint disable/enable
block.wrap_with_pylint_disable(["C0114", "C0115"])

# Wrap with pragma: no cover
block.wrap_with_no_cover()
```

## Converting to Line Block

Code blocks can be converted to line blocks for raw operations:

```python
code_block = file.block_at_line(42)
line_block = code_block.to_line_block()

# Now you can use line block operations
line_block.indent()
line_block.move_to(100)
```

## Project-Wide Directive Operations

### Finding Directives

```python
# All type: ignore comments
rj.find_type_ignores()

# Bare ignores (without specific codes)
rj.find_bare_type_ignores()

# Other directive types
rj.find_noqa_comments()
rj.find_pylint_disables()
rj.find_fmt_off_regions()
rj.find_no_cover_comments()

# Everything
rj.find_all_directives()
```

### Cleaning Up

```python
# Remove directives that are no longer needed
rj.remove_unused_type_ignores()
rj.remove_unused_noqa()
rj.remove_unused_pylint_disables()

# Upgrade bare ignores to specific codes
rj.add_error_codes_to_type_ignores()

# Normalize formatting
rj.normalize_directive_style()
```

### Auditing

```python
# Get statistics
stats = rj.count_directives_by_type()

# Find potentially stale directives
rj.find_stale_directives()

# Full audit report
rj.audit_directives()
```

## Next Steps

- [Batch Operations](batch-operations.md) — Apply operations to multiple targets
- [Error Handling](error-handling.md) — Handle failures gracefully
