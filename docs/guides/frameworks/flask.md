# Flask Support

Rejig provides specialized tools for refactoring Flask applications: managing routes, blueprints, and error handlers.

## Installation

```bash
pip install rejig[flask]
```

## FlaskProject

The `FlaskProject` class provides Flask-specific operations.

```python
from rejig.frameworks.flask import FlaskProject

# project_root, app_module (default "app"), dry_run (default False)
flask = FlaskProject("src/", app_module="app")

# Find the Flask app variable name (e.g. 'app' from `app = Flask(__name__)`)
print(f"App variable: {flask.find_flask_app_variable()}")
print(f"Main app file: {flask.main_app_file}")
print(f"Routes file: {flask.routes_file}")
```

`FlaskProject` also supports the context manager protocol for cleanup:

```python
with FlaskProject("src/") as flask:
    flask.add_route("/users", "get_users")
```

## Route Management

### Add Routes

```python
flask = FlaskProject("src/")

# Add a simple route (defaults to GET)
flask.add_route("/users", "get_users")

# Add with HTTP methods
flask.add_route("/users", "list_users", methods=["GET"])
flask.add_route("/users", "create_user", methods=["POST"])

# Add with all parameters
flask.add_route(
    path="/users/<int:user_id>",
    function_name="get_user",
    methods=["GET"],
    blueprint="api",        # Optional: add to a blueprint
    body="return jsonify({})",
)
```

### Remove Routes

```python
# Remove by view function name
flask.remove_route("old_handler")
```

### List Routes

`find_routes()` returns a list of dicts with `path`, `function`, `methods`, and
`blueprint` keys:

```python
# Get all routes
routes = flask.find_routes()

for route in routes:
    print(f"{route['path']} -> {route['function']}")
    print(f"  Methods: {route['methods']}")
    print(f"  Blueprint: {route['blueprint'] or 'main'}")

# Only routes for a specific blueprint
api_routes = flask.find_routes(blueprint="api")
```

## Blueprint Management

### Create Blueprint

```python
# Add a new blueprint (creates a package by default)
flask.add_blueprint(
    name="api",
    url_prefix="/api",
    import_name="myapp.api",
)

# This creates a Blueprint definition like:
# api = Blueprint('api', 'myapp.api', url_prefix='/api')
```

### Register Blueprint

```python
# Register an existing blueprint variable with the app
flask.register_blueprint(
    blueprint_var="api_bp",
    import_path="app.api",
    url_prefix="/api/v1",
)

# This adds to the app file:
# from app.api import api_bp
# app.register_blueprint(api_bp, url_prefix='/api/v1')
```

### Add Route to Blueprint

```python
# Add route to a specific blueprint
flask.add_route(
    path="/items",
    function_name="list_items",
    blueprint="api",  # Add to api blueprint
)
```

### Remove Blueprint

```python
# Remove the blueprint definition (and optionally its package directory)
flask.remove_blueprint("api")
flask.remove_blueprint("api", remove_package=True)
```

### List Blueprints

`find_blueprints()` returns a list of dicts with `name`, `variable`,
`url_prefix`, and `file` keys:

```python
blueprints = flask.find_blueprints()

for bp in blueprints:
    print(f"Blueprint: {bp['name']} (variable: {bp['variable']})")
    print(f"  URL prefix: {bp['url_prefix']}")
    print(f"  File: {bp['file']}")
```

## Error Handlers

### Add Error Handler

`add_error_handler()` takes an HTTP error code (an `int`) and a handler
function name:

```python
# Add 404 handler
flask.add_error_handler(404, "handle_not_found")

# Generates:
# @app.errorhandler(404)
# def handle_not_found(error):
#     return {'error': 'Not found'}, 404

# Add with a custom body
flask.add_error_handler(
    error_code=500,
    function_name="handle_server_error",
    body="""logger.exception(error)
return {'error': 'Internal server error'}, 500""",
)
```

## OpenAPI Generation

Generate an OpenAPI specification from the discovered routes:

```python
flask = FlaskProject("src/")

# Return the spec in result.data
result = flask.generate_openapi_spec(title="My API", version="1.0.0")
spec = result.data

# Or write it to a file (.json, .yaml, or .yml)
flask.generate_openapi_spec(
    output_file="openapi.json",
    title="My API",
    version="1.0.0",
    description="A Flask API",
)
```

## Common Patterns

### Add API Versioning

```python
flask = FlaskProject("src/")

# Create versioned blueprints
flask.add_blueprint("api_v1", url_prefix="/api/v1", import_name="myapp.api.v1")
flask.add_blueprint("api_v2", url_prefix="/api/v2", import_name="myapp.api.v2")

# Add routes to a versioned blueprint
flask.add_route("/users", "list_users_v1", methods=["GET"], blueprint="api_v1")
```

### Add Authentication Routes

```python
flask = FlaskProject("src/")

# Add login/logout routes
flask.add_route("/auth/login", "login", methods=["POST"])
flask.add_route("/auth/logout", "logout", methods=["POST"])
```

## Integration with Core Rejig

For CST-level edits (renaming, editing classes/functions), use a `Rejig`
instance scoped at the project root alongside the Flask-specific operations:

```python
from rejig import Rejig
from rejig.frameworks.flask import FlaskProject

flask = FlaskProject("src/")

# Flask-specific operations
flask.add_route("/new", "new_handler")
flask.add_blueprint("admin", url_prefix="/admin")

# Core Rejig operations on the same tree
rj = Rejig("src/")
rj.find_function("helper").rename("utility")
```
