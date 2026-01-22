# Config Files

Manipulate TOML, YAML, JSON, and INI files with the same target-based API.

## TOML Files

Common for `pyproject.toml`:

```python
toml = rj.toml("pyproject.toml")

# Read values (dotted key path)
version = toml.get("project.version")
line_length = toml.get("tool.black.line-length", default=88)

# Set values
toml.set("project.version", "2.0.0")
toml.set("tool.black.line-length", 110)
toml.set("tool.ruff.select", ["E", "F", "W"])

# Delete keys
toml.delete_key("tool.deprecated-tool")

# Get entire sections
black_config = toml.get_section("tool.black")

# Replace entire file content (validates TOML syntax)
toml.rewrite(new_content)
```

### Common pyproject.toml Operations

```python
toml = rj.toml("pyproject.toml")

# Update version
toml.set("project.version", "1.2.0")

# Add a dependency
deps = toml.get("project.dependencies", default=[])
deps.append("requests>=2.28.0")
toml.set("project.dependencies", deps)

# Configure tools
toml.set("tool.black.line-length", 110)
toml.set("tool.black.target-version", ["py310", "py311"])
toml.set("tool.ruff.select", ["E", "F", "W", "I"])
toml.set("tool.mypy.strict", True)
```

## YAML Files

```python
yaml = rj.yaml("config.yml")

# Read values
debug = yaml.get("app.debug", default=False)
hosts = yaml.get("database.hosts")

# Set values
yaml.set("app.version", "2.0.0")
yaml.set("database.pool_size", 10)

# Delete keys
yaml.delete_key("deprecated_setting")
```

### Nested Structures

```python
yaml = rj.yaml("docker-compose.yml")

# Access nested values
image = yaml.get("services.web.image")
ports = yaml.get("services.web.ports")

# Set nested values
yaml.set("services.web.environment.DEBUG", "false")
```

## JSON Files

```python
json_file = rj.json("package.json")

# Read values
name = json_file.get("name")
version = json_file.get("version")
scripts = json_file.get("scripts", default={})

# Set values
json_file.set("version", "2.0.0")
json_file.set("scripts.test", "pytest")

# Delete keys
json_file.delete_key("devDependencies.old-package")
```

## INI Files

```python
ini = rj.ini("setup.cfg")

# Read values (section, key)
name = ini.get("metadata", "name")
version = ini.get("metadata", "version")

# Set values
ini.set("metadata", "version", "2.0.0")
ini.set("options", "python_requires", ">=3.10")

# Delete keys
ini.delete_key("options", "deprecated_option")

# Add sections
ini.add_section("tool:pytest")
ini.set("tool:pytest", "testpaths", "tests")

# Get entire file as nested dict
data = ini.get_data()
```

## Text Files

For files without structured format:

```python
text = rj.text_file("README.md")

# Read content
result = text.get_content()
if result:
    print(result.data)

# Line operations
text.line(1).get_content()  # First line

# Pattern operations
matches = text.find_pattern(r"## .*")  # Find markdown headers
text.replace_pattern(r"v\d+\.\d+\.\d+", "v2.0.0")  # Update version strings
```

## Checking Existence

```python
toml = rj.toml("pyproject.toml")

if toml.exists():
    version = toml.get("project.version")
else:
    print("pyproject.toml not found")
```

## Result Handling

Config operations return `Result`:

```python
result = toml.set("project.version", "2.0.0")

if result:
    print(f"Updated {result.files_changed}")
else:
    print(f"Failed: {result.message}")
```

## Common Patterns

### Update Version Everywhere

```python
new_version = "2.0.0"

# pyproject.toml
rj.toml("pyproject.toml").set("project.version", new_version)

# package.json (if exists)
pkg = rj.json("package.json")
if pkg.exists():
    pkg.set("version", new_version)

# __init__.py
init = rj.file("src/mypackage/__init__.py")
init.replace_pattern(r'__version__ = "[^"]+"', f'__version__ = "{new_version}"')
```

### Sync Tool Configuration

```python
# Ensure consistent settings across projects
toml = rj.toml("pyproject.toml")

toml.set("tool.black.line-length", 110)
toml.set("tool.isort.profile", "black")
toml.set("tool.isort.line_length", 110)
toml.set("tool.mypy.python_version", "3.10")
toml.set("tool.mypy.strict", True)
```

### Add GitHub Actions Workflow

```python
yaml = rj.yaml(".github/workflows/test.yml")

yaml.set("name", "Tests")
yaml.set("on.push.branches", ["main"])
yaml.set("on.pull_request.branches", ["main"])
yaml.set("jobs.test.runs-on", "ubuntu-latest")
yaml.set("jobs.test.steps", [
    {"uses": "actions/checkout@v4"},
    {"uses": "actions/setup-python@v5", "with": {"python-version": "3.10"}},
    {"run": "pip install -e .[dev]"},
    {"run": "pytest"},
])
```

## Next Steps

- [Error Handling](error-handling.md) — Handle failures gracefully
- [Examples](../examples/refactoring-patterns.md) — Real-world patterns
