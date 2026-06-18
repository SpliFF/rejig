# FastAPI Support

Rejig provides specialized tools for refactoring FastAPI applications: managing endpoints, dependencies, middleware, routers, and Pydantic models.

## Installation

```bash
pip install rejig[fastapi]
```

## FastAPIProject

The `FastAPIProject` class provides FastAPI-specific operations.

```python
from rejig.frameworks.fastapi import FastAPIProject

# project_root, app_module (default "app"), dry_run (default False)
api = FastAPIProject("src/", app_module="app")

# Find the FastAPI app variable name (e.g. 'app' from `app = FastAPI()`)
print(f"App variable: {api.find_fastapi_app_variable()}")
print(f"Main app file: {api.main_app_file}")
```

`FastAPIProject` also supports the context manager protocol for cleanup:

```python
with FastAPIProject("src/") as api:
    api.add_endpoint("/users", "get_users", method="GET")
```

## Endpoint Management

### Add Endpoints

```python
api = FastAPIProject("src/")

# Add GET endpoint
api.add_endpoint("/users", "get_users", method="GET")

# Add with all options
api.add_endpoint(
    path="/users/{user_id}",
    function_name="get_user",
    method="GET",
    response_model="User",
    status_code=200,
    tags=["users"],
    router="users_router",   # Optional: add to a router
    body="return await get_user_by_id(user_id)",
    parameters=[{"name": "user_id", "type": "int"}],
)

# Add POST endpoint
api.add_endpoint(
    path="/users",
    function_name="create_user",
    method="POST",
    response_model="User",
    status_code=201,
)
```

### Remove Endpoints

```python
# Remove by endpoint function name
api.remove_endpoint("old_handler")
```

### List Endpoints

`find_endpoints()` returns a list of dicts with `path`, `function`, `method`,
`router`, and `file` keys:

```python
endpoints = api.find_endpoints()

for ep in endpoints:
    print(f"{ep['method']} {ep['path']}")
    print(f"  Function: {ep['function']}")
    print(f"  Router: {ep['router'] or 'app'}")

# Only endpoints for a specific router
user_endpoints = api.find_endpoints(router="users_router")
```

## Router Management

### Create Router

```python
# Add a new router (creates a file by default)
api.add_router(
    name="users_router",
    prefix="/users",
    tags=["users"],
)

# Creates:
# users_router = APIRouter(prefix="/users", tags=["users"])
```

### Add Endpoint to Router

```python
# Add endpoint to a specific router
api.add_endpoint(
    path="/{user_id}",
    function_name="get_user",
    method="GET",
    router="users_router",
)
```

### List Routers

`find_routers()` returns a list of dicts with `variable`, `prefix`, and `file`
keys:

```python
routers = api.find_routers()

for router in routers:
    print(f"Router: {router['variable']}")
    print(f"  Prefix: {router['prefix']}")
    print(f"  File: {router['file']}")
```

## Dependency Injection

### Add Dependency Function

`add_dependency()` creates a dependency function from a body:

```python
# Add a dependency function
api.add_dependency(
    name="get_current_user",
    is_async=True,
    body="""user = await verify_token(token)
if not user:
    raise HTTPException(status_code=401, detail="Invalid token")
return user""",
)

# Add a database session dependency
api.add_dependency(
    name="get_db",
    is_async=True,
    body="""async with async_session() as session:
    yield session""",
)
```

### Add Depends Parameter to Endpoint

```python
# Add a Depends(...) parameter to an existing endpoint
api.add_depends_parameter(
    endpoint_name="get_users",
    param_name="db",
    dependency="Depends(get_db)",
)

api.add_depends_parameter(
    endpoint_name="get_users",
    param_name="current_user",
    dependency="Depends(get_current_user)",
)
```

## Middleware

### Add Middleware

`add_middleware()` takes the middleware class name plus keyword arguments for
the middleware constructor:

```python
# Add CORS middleware (import path auto-detected for common ones)
api.add_middleware(
    "CORSMiddleware",
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware with an explicit import path
api.add_middleware(
    "CustomMiddleware",
    import_path="myapp.middleware",
    custom_param="value",
)
```

### Remove Middleware

```python
api.remove_middleware("DeprecatedMiddleware")
```

## Pydantic Models

### Generate a Model

```python
# Add a Pydantic model with explicit fields
api.generate_pydantic_model(
    name="UserResponse",
    fields={
        "id": "int",
        "email": "str",
        "name": "str",
        "created_at": "datetime",
    },
)
```

### Generate Models From a JSON Schema

```python
from pathlib import Path

# Generate Pydantic models from a JSON schema file
api.generate_pydantic_models_from_schema(
    schema_file=Path("schemas/user.json"),
    output_file=Path("src/app/models/generated.py"),
)
```

## Common Patterns

### Add API Versioning

```python
api = FastAPIProject("src/")

# Create versioned routers
api.add_router("v1_router", prefix="/api/v1", tags=["v1"])
api.add_router("v2_router", prefix="/api/v2", tags=["v2"])

# Add endpoints to a versioned router
api.add_endpoint("/users", "list_users_v1", method="GET", router="v1_router")
```

### Add Authentication

```python
api = FastAPIProject("src/")

# Add an authentication dependency
api.add_dependency(
    name="get_current_user",
    is_async=True,
    body="""credentials_exception = HTTPException(
    status_code=401,
    detail="Could not validate credentials",
)
payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
user_id = payload.get("sub")
if user_id is None:
    raise credentials_exception
return await get_user(user_id)""",
)

# Add a login endpoint
api.add_endpoint(
    path="/token",
    function_name="login",
    method="POST",
    response_model="Token",
)
```

## Integration with Core Rejig

For CST-level edits (renaming, editing classes/functions), use a `Rejig`
instance scoped at the project root alongside the FastAPI-specific operations:

```python
from rejig import Rejig
from rejig.frameworks.fastapi import FastAPIProject

api = FastAPIProject("src/")

# FastAPI-specific operations
api.add_endpoint("/new", "new_handler", method="GET")
api.add_middleware("CORSMiddleware", allow_origins=["*"])

# Core Rejig operations on the same tree
rj = Rejig("src/")
rj.find_function("helper").rename("utility")
```
