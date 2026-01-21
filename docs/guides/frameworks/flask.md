# Flask Support

Rejig provides specialized tools for refactoring Flask applications: managing routes, blueprints, error handlers, and middleware.

## Installation

```bash
pip install rejig[flask]
```

## FlaskProject

The `FlaskProject` class provides Flask-specific operations.

```python
from rejig.frameworks.flask import FlaskProject

flask = FlaskProject("src/")

# Find Flask app instance
print(f"App file: {flask.app_file}")
print(f"App name: {flask.app_name}")
```

## Route Management

### Add Routes

```python
flask = FlaskProject("src/")

# Add a simple route
flask.add_route("/users", "get_users")

# Add with HTTP methods
flask.add_route("/users", "list_users", methods=["GET"])
flask.add_route("/users", "create_user", methods=["POST"])

# Add with all parameters
flask.add_route(
    path="/users/<int:user_id>",
    function_name="get_user",
    methods=["GET"],
    endpoint="user_detail",
)
```

### Remove Routes

```python
# Remove by path
flask.remove_route("/deprecated/endpoint")

# Remove by function name
flask.remove_route_by_function("old_handler")

# Remove by endpoint
flask.remove_route_by_endpoint("deprecated_endpoint")
```

### Modify Routes

```python
# Change route path
flask.update_route_path("get_user", "/api/v2/users/<int:id>")

# Add methods to existing route
flask.add_route_methods("user_handler", ["PUT", "PATCH"])

# Remove methods from route
flask.remove_route_methods("user_handler", ["DELETE"])
```

### List Routes

```python
# Get all routes
routes = flask.list_routes()

for route in routes:
    print(f"{route.path} -> {route.function}")
    print(f"  Methods: {route.methods}")
    print(f"  Blueprint: {route.blueprint or 'main'}")
```

## Blueprint Management

### Create Blueprint

```python
# Add a new blueprint
flask.add_blueprint(
    name="api",
    import_name="myapp.api",
    url_prefix="/api"
)

# This creates:
# api_bp = Blueprint('api', 'myapp.api', url_prefix='/api')
```

### Register Blueprint

```python
# Register existing blueprint with app
flask.register_blueprint("api_bp", url_prefix="/api/v1")

# This adds to app file:
# app.register_blueprint(api_bp, url_prefix='/api/v1')
```

### Add Route to Blueprint

```python
# Add route to specific blueprint
flask.add_route(
    path="/items",
    function_name="list_items",
    blueprint="api"  # Add to api blueprint
)
```

### List Blueprints

```python
blueprints = flask.list_blueprints()

for bp in blueprints:
    print(f"Blueprint: {bp.name}")
    print(f"  URL prefix: {bp.url_prefix}")
    print(f"  Routes: {len(bp.routes)}")
```

## Error Handlers

### Add Error Handler

```python
# Add 404 handler
flask.add_error_handler(404, "handle_not_found")

# This generates:
# @app.errorhandler(404)
# def handle_not_found(error):
#     return {'error': 'Not found'}, 404

# Add with custom body
flask.add_error_handler(
    error_code=500,
    function_name="handle_server_error",
    body="""
    logger.exception(error)
    return {'error': 'Internal server error'}, 500
    """
)
```

### Add Exception Handler

```python
# Handle specific exception type
flask.add_error_handler(
    "ValidationError",
    "handle_validation_error",
    body="""
    return {'error': str(error)}, 400
    """
)
```

### Remove Error Handler

```python
flask.remove_error_handler(404)
flask.remove_error_handler("ValidationError")
```

## Middleware / Before/After Request

### Add Before Request

```python
flask.add_before_request("check_authentication")

# Generates:
# @app.before_request
# def check_authentication():
#     pass  # TODO: implement

# With body
flask.add_before_request(
    "log_request",
    body="""
    logger.info(f"Request: {request.method} {request.path}")
    """
)
```

### Add After Request

```python
flask.add_after_request("add_cors_headers")

# With body
flask.add_after_request(
    "add_security_headers",
    body="""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    return response
    """
)
```

### Add Teardown

```python
flask.add_teardown_request("cleanup_db_session")
flask.add_teardown_appcontext("close_resources")
```

### Remove Handlers

```python
flask.remove_before_request("deprecated_check")
flask.remove_after_request("old_handler")
```

## Context Processors

```python
# Add context processor
flask.add_context_processor("inject_user")

# With body
flask.add_context_processor(
    "inject_common_data",
    body="""
    return {
        'app_name': 'My Flask App',
        'current_user': get_current_user(),
    }
    """
)
```

## Configuration

### Add Config Class

```python
flask.add_config_class(
    name="ProductionConfig",
    parent="Config",
    settings={
        "DEBUG": "False",
        "SQLALCHEMY_DATABASE_URI": 'os.environ.get("DATABASE_URL")',
    }
)
```

### Modify Config

```python
# Add setting to existing config class
flask.add_config_setting("Config", "MAX_CONTENT_LENGTH", "16 * 1024 * 1024")

# Update setting
flask.update_config_setting("Config", "DEBUG", "False")
```

## Extension Management

### Add Extension

```python
# Add Flask-SQLAlchemy
flask.add_extension("Flask-SQLAlchemy", "db", "SQLAlchemy()")

# This adds:
# from flask_sqlalchemy import SQLAlchemy
# db = SQLAlchemy()

# In create_app or app initialization:
# db.init_app(app)
```

### Common Extensions

```python
# Add Flask-Migrate
flask.add_extension("Flask-Migrate", "migrate", "Migrate()")

# Add Flask-Login
flask.add_extension("Flask-Login", "login_manager", "LoginManager()")

# Add Flask-CORS
flask.add_extension("Flask-Cors", "cors", "CORS()")
```

## Common Patterns

### Convert to Application Factory

```python
flask = FlaskProject("src/")

# Convert from single app instance to factory pattern
flask.convert_to_factory()

# Before:
# app = Flask(__name__)
# app.config.from_object(Config)

# After:
# def create_app(config_class=Config):
#     app = Flask(__name__)
#     app.config.from_object(config_class)
#     return app
```

### Add API Versioning

```python
flask = FlaskProject("src/")

# Create versioned blueprints
flask.add_blueprint("api_v1", "myapp.api.v1", url_prefix="/api/v1")
flask.add_blueprint("api_v2", "myapp.api.v2", url_prefix="/api/v2")

# Move existing routes to v1
for route in flask.list_routes():
    if route.path.startswith("/api/"):
        flask.move_route_to_blueprint(route.function, "api_v1")
```

### Add Authentication

```python
flask = FlaskProject("src/")

# Add Flask-Login
flask.add_extension("Flask-Login", "login_manager", "LoginManager()")

# Add login required decorator usage
flask.add_before_request(
    "require_login",
    blueprint="api",  # Only for API blueprint
    body="""
    if not current_user.is_authenticated:
        return {'error': 'Unauthorized'}, 401
    """
)

# Add login/logout routes
flask.add_route("/auth/login", "login", methods=["POST"])
flask.add_route("/auth/logout", "logout", methods=["POST"])
```

### Add Logging

```python
flask = FlaskProject("src/")

# Add request logging
flask.add_before_request(
    "log_request_start",
    body="""
    g.request_start = time.time()
    logger.info(f"Request started: {request.method} {request.path}")
    """
)

flask.add_after_request(
    "log_request_end",
    body="""
    duration = time.time() - g.request_start
    logger.info(f"Request completed: {response.status_code} ({duration:.3f}s)")
    return response
    """
)
```

## Integration with Core Rejig

FlaskProject extends core Rejig functionality:

```python
flask = FlaskProject("src/")

# Core Rejig operations work
flask.find_function("helper").rename("utility")
flask.find_class("UserService").add_method(...)

# Plus Flask-specific operations
flask.add_route("/new", "new_handler")
flask.add_blueprint("admin", ...)
```

## Route Function Generation

```python
# Generate route function with common patterns
flask.generate_route_function(
    name="get_users",
    path="/users",
    methods=["GET"],
    template="api",  # Use API template (returns JSON)
)

# Template options:
# - "api": Returns JSON, includes error handling
# - "view": Renders template
# - "redirect": Returns redirect
# - "minimal": Just pass

# Generated API template:
# @app.route('/users', methods=['GET'])
# def get_users():
#     try:
#         # TODO: implement
#         return jsonify({'data': []})
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500
```

## Blueprint Discovery

```python
flask = FlaskProject("src/")

# Find all blueprints in the project
blueprints = flask.discover_blueprints()

for bp in blueprints:
    print(f"Found blueprint: {bp.name}")
    print(f"  File: {bp.file_path}")
    print(f"  Registered: {bp.is_registered}")
```
