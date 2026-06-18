# Sample Projects

This directory contains sample Python projects for testing Rejig recipes and exploring the library's capabilities.

## Projects

### 1. legacy-flask-app
A deliberately outdated Flask application with:
- Old-style type comments instead of annotations
- Missing docstrings
- Hardcoded configuration values
- No type hints
- Deprecated patterns

**Use for testing:**
- Type hint inference and modernization
- Docstring generation
- Security scanning (hardcoded secrets)
- Flask framework refactoring

### 2. modern-fastapi
A FastAPI application with some issues:
- Inconsistent async/sync patterns
- Missing response models
- Some security issues (SQL injection patterns)
- Incomplete documentation

**Use for testing:**
- FastAPI refactoring
- Async conversion
- Security analysis
- API documentation generation

### 3. django-blog
A Django blog application with:
- Basic models, views, and URLs
- Some code duplication
- Missing migrations patterns
- Configuration in settings.py

**Use for testing:**
- Django framework operations
- Settings management
- URL configuration
- Model operations

### 4. cli-tool
A command-line tool using Click with:
- Multiple commands
- Configuration handling
- Some complexity issues
- Testing gaps

**Use for testing:**
- Code analysis (complexity)
- Test generation
- Docstring generation
- Dead code detection

### 5. data-processor
A data processing library with:
- Heavy use of pandas patterns
- Missing type hints
- Magic numbers and hardcoded strings
- Optimization opportunities

**Use for testing:**
- DRY analysis (duplicate code)
- Loop optimization
- Type hint inference
- Code modernization

## Usage

Each project can be used standalone with Rejig:

```python
from rejig import Rejig

# Work with a specific sample project
rj = Rejig("docs/sample-projects/legacy-flask-app/")

# Run analysis
report = rj.analyze_code()
print(report)

# Try transformations
rj.find_functions().infer_type_hints()
```

## Testing Recipes

Work through the recipe guides in `docs/examples/` against these projects:

- [`analysis-recipes.md`](../examples/analysis-recipes.md) — try against `cli-tool/`
- [`security-recipes.md`](../examples/security-recipes.md) — try against `legacy-flask-app/`
- [`optimization-recipes.md`](../examples/optimization-recipes.md) — try against `data-processor/`
