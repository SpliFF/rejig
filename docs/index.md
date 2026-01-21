# Rejig

**Programmatic Python refactoring with LibCST.**

Rejig provides a fluent API for finding and modifying Python code elements. Whether you're building codemods, automating refactoring, or managing large-scale code migrations, Rejig gives you precise control over your codebase.

## Features

- **Target-based API** — Everything is a target: files, modules, classes, functions, methods, even individual lines
- **Fluent chaining** — Chain operations naturally: `rj.file("app.py").find_class("User").find_method("save")`
- **Batch operations** — Apply changes to multiple targets at once with `TargetList`
- **Safe by default** — Operations return `Result` objects instead of raising exceptions
- **Dry-run support** — Preview changes before applying them
- **Config file support** — Manipulate TOML, YAML, and JSON files with the same API

## Quick Example

```python
from rejig import Rejig

rj = Rejig("src/")

# Find all test classes and add a decorator
rj.find_classes(pattern="^Test").add_decorator("pytest.mark.slow")

# Rename a method across a class
rj.file("models.py").find_class("User").find_method("get_name").rename("get_full_name")

# Add type hints to a function
func = rj.module("myapp.utils").find_function("process")
func.set_return_type("list[str]")
func.set_parameter_type("data", "dict[str, Any]")

# Modify pyproject.toml
rj.toml("pyproject.toml").set("tool.black.line-length", 110)
```

## Why Rejig?

| Task | Without Rejig | With Rejig |
|------|---------------|------------|
| Rename a method | Find/replace (breaks things) | `target.rename("new_name")` |
| Add decorator to many classes | Manual editing | `targets.add_decorator("@cached")` |
| Update config files | Parse, modify, serialize | `rj.toml(path).set(key, value)` |
| Migrate code patterns | Write custom AST visitors | Chain target operations |

## Installation

```bash
pip install rejig
```

## Next Steps

- [Quickstart](getting-started/quickstart.md) — Get up and running in 5 minutes
- [Core Concepts](getting-started/concepts.md) — Understand targets, results, and the API design
- [Guides](guides/finding-code.md) — Learn common workflows
- [Code Optimization](guides/code-optimization.md) — Find and fix inefficient code
- [Optimization Recipes](examples/optimization-recipes.md) — Ready-to-use optimization scripts
