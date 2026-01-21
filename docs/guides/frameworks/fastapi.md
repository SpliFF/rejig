# FastAPI Support

Rejig provides specialized tools for refactoring FastAPI applications: managing endpoints, dependencies, middleware, and routers.

## Installation

```bash
pip install rejig[fastapi]
```

## FastAPIProject

The `FastAPIProject` class provides FastAPI-specific operations.

```python
from rejig.frameworks.fastapi import FastAPIProject

api = FastAPIProject("src/")

# Find FastAPI app instance
print(f"App file: {api.app_file}")
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
    summary="Get user by ID",
    description="Retrieve a single user by their unique identifier.",
)

# Add POST endpoint
api.add_endpoint(
    path="/users",
    function_name="create_user",
    method="POST",
    response_model="User",
    status_code=201,
    body_model="UserCreate",
)
```

### Add Multiple Methods

```python
# Add CRUD endpoints for a resource
api.add_crud_endpoints(
    resource="users",
    model="User",
    create_model="UserCreate",
    update_model="UserUpdate",
)

# Generates:
# GET /users -> list_users
# POST /users -> create_user
# GET /users/{id} -> get_user
# PUT /users/{id} -> update_user
# DELETE /users/{id} -> delete_user
```

### Remove Endpoints

```python
# Remove by path and method
api.remove_endpoint("/deprecated", method="GET")

# Remove by function name
api.remove_endpoint_by_function("old_handler")

# Remove all methods for a path
api.remove_endpoint("/deprecated")  # Removes all methods
```

### Modify Endpoints

```python
# Change path
api.update_endpoint_path("get_user", "/api/v2/users/{user_id}")

# Add response model
api.set_endpoint_response_model("get_users", "list[User]")

# Add tags
api.add_endpoint_tags("get_user", ["users", "api"])

# Change status code
api.set_endpoint_status_code("create_user", 201)
```

### List Endpoints

```python
endpoints = api.list_endpoints()

for ep in endpoints:
    print(f"{ep.method} {ep.path}")
    print(f"  Function: {ep.function}")
    print(f"  Response model: {ep.response_model}")
    print(f"  Tags: {ep.tags}")
```

## Router Management

### Create Router

```python
# Add a new router
api.add_router(
    name="users_router",
    prefix="/users",
    tags=["users"],
)

# Creates:
# users_router = APIRouter(prefix="/users", tags=["users"])
```

### Include Router

```python
# Include router in main app
api.include_router("users_router", prefix="/api/v1")

# This adds:
# app.include_router(users_router, prefix="/api/v1")
```

### Add Endpoint to Router

```python
# Add endpoint to specific router
api.add_endpoint(
    path="/{user_id}",
    function_name="get_user",
    method="GET",
    router="users_router",
)
```

### List Routers

```python
routers = api.list_routers()

for router in routers:
    print(f"Router: {router.name}")
    print(f"  Prefix: {router.prefix}")
    print(f"  Endpoints: {len(router.endpoints)}")
```

## Dependency Injection

### Add Dependency

```python
# Add a simple dependency
api.add_dependency("get_db", "Depends(get_database)")

# Add dependency function
api.add_dependency_function(
    name="get_current_user",
    body="""
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    user = await verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user
    """,
)
```

### Add Dependency to Endpoint

```python
# Add dependency parameter to endpoint
api.add_endpoint_dependency(
    function_name="get_users",
    param_name="db",
    dependency="Depends(get_db)",
)

# Add current user dependency
api.add_endpoint_dependency(
    function_name="get_users",
    param_name="current_user",
    dependency="Depends(get_current_user)",
    type_hint="User",
)
```

### Add Router-Level Dependencies

```python
# Add dependency to all endpoints in router
api.add_router_dependency(
    router="users_router",
    dependency="Depends(verify_api_key)",
)
```

### Common Dependencies

```python
# Add database session dependency
api.add_dependency_function(
    "get_db",
    body="""
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
    """,
)

# Add authentication dependency
api.add_dependency_function(
    "get_current_user",
    body="""
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    user = await db.get(User, payload["sub"])
    if not user:
        raise HTTPException(status_code=401)
    return user
    """,
)
```

## Middleware

### Add Middleware

```python
# Add CORS middleware
api.add_middleware(
    "CORSMiddleware",
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
api.add_middleware(
    "CustomMiddleware",
    custom_param="value",
)
```

### Add Custom Middleware Class

```python
api.add_middleware_class(
    name="TimingMiddleware",
    body="""
class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        response.headers["X-Process-Time"] = str(duration)
        return response
    """,
)

# Register it
api.add_middleware("TimingMiddleware")
```

### Remove Middleware

```python
api.remove_middleware("DeprecatedMiddleware")
```

## Exception Handlers

### Add Exception Handler

```python
# Add handler for specific exception
api.add_exception_handler(
    exception_class="ValidationError",
    handler_name="validation_error_handler",
    body="""
async def validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )
    """,
)

# Add HTTP exception handler
api.add_exception_handler(
    exception_class="HTTPException",
    handler_name="http_exception_handler",
)
```

### Add Generic Error Handler

```python
api.add_exception_handler(
    exception_class="Exception",
    handler_name="generic_error_handler",
    body="""
async def generic_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
    """,
)
```

## Background Tasks

```python
# Add background task to endpoint
api.add_background_task(
    endpoint="create_user",
    task_function="send_welcome_email",
    task_args=["user.email"],
)

# Modifies create_user to include:
# background_tasks.add_task(send_welcome_email, user.email)
```

## Response Models

### Create Response Model

```python
# Add Pydantic model for responses
api.add_response_model(
    name="UserResponse",
    fields={
        "id": "int",
        "email": "str",
        "name": "str",
        "created_at": "datetime",
    },
)

# Create from existing model
api.create_response_model_from("User", "UserResponse", exclude=["password"])
```

## Common Patterns

### Add API Versioning

```python
api = FastAPIProject("src/")

# Create versioned routers
api.add_router("v1_router", prefix="/api/v1", tags=["v1"])
api.add_router("v2_router", prefix="/api/v2", tags=["v2"])

# Move endpoints to v1
for ep in api.list_endpoints():
    if not ep.router:
        api.move_endpoint_to_router(ep.function, "v1_router")
```

### Add Authentication

```python
api = FastAPIProject("src/")

# Add OAuth2 scheme
api.add_code("""
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
""")

# Add authentication dependency
api.add_dependency_function(
    "get_current_user",
    body="""
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return await get_user(user_id)
    """,
)

# Add login endpoint
api.add_endpoint(
    path="/token",
    function_name="login",
    method="POST",
    response_model="Token",
)
```

### Add Rate Limiting

```python
api = FastAPIProject("src/")

# Add slowapi for rate limiting
api.add_dependency("limiter", "Limiter(key_func=get_remote_address)")

# Add to specific endpoint
api.add_endpoint_decorator(
    "get_users",
    '@limiter.limit("10/minute")',
)
```

### Convert to Async

```python
api = FastAPIProject("src/")

# Convert sync endpoints to async
for func in api.find_functions(pattern="^(get|create|update|delete)_"):
    if not func.is_async:
        func.convert_to_async()
```

## Integration with Core Rejig

FastAPIProject extends core Rejig functionality:

```python
api = FastAPIProject("src/")

# Core Rejig operations work
api.find_function("helper").rename("utility")
api.find_class("UserService").add_method(...)

# Plus FastAPI-specific operations
api.add_endpoint("/new", "new_handler", method="GET")
api.add_middleware("CORSMiddleware", ...)
```

## OpenAPI Customization

```python
api = FastAPIProject("src/")

# Update OpenAPI metadata
api.set_openapi_info(
    title="My API",
    version="1.0.0",
    description="A fantastic API",
)

# Add OpenAPI tags
api.add_openapi_tag(
    name="users",
    description="User management endpoints",
)

# Set contact info
api.set_openapi_contact(
    name="API Support",
    email="support@example.com",
    url="https://support.example.com",
)
```

## Testing Helpers

```python
# Generate test client setup
api.generate_test_client("tests/conftest.py")

# Generates:
# import pytest
# from httpx import AsyncClient
# from main import app
#
# @pytest.fixture
# async def client():
#     async with AsyncClient(app=app, base_url="http://test") as client:
#         yield client

# Generate endpoint tests
api.generate_endpoint_tests("tests/test_users.py", router="users_router")
```
