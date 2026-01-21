"""
Tests for rejig.frameworks.fastapi module.

This module tests FastAPI project management:
- FastAPIProject class
- EndpointManager class
- DependencyManager class
- MiddlewareManager class
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from rejig.frameworks.fastapi import FastAPIProject


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def fastapi_app_file(tmp_path: Path) -> Path:
    """Create a minimal FastAPI app file."""
    app_file = tmp_path / "main.py"
    app_file.write_text(textwrap.dedent('''\
        from fastapi import FastAPI

        app = FastAPI()

        @app.get('/')
        async def root():
            return {"message": "Hello, World!"}
    '''))
    return app_file


@pytest.fixture
def fastapi_package(tmp_path: Path) -> Path:
    """Create a FastAPI app as a package."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    # main.py
    main_file = app_dir / "main.py"
    main_file.write_text(textwrap.dedent('''\
        from fastapi import FastAPI

        app = FastAPI()

        @app.get('/')
        async def root():
            return {"message": "Hello, World!"}

        @app.get('/items/{item_id}')
        async def get_item(item_id: str):
            return {"item_id": item_id}

        @app.post('/items', status_code=201)
        async def create_item():
            return {"created": True}
    '''))

    # __init__.py
    init_file = app_dir / "__init__.py"
    init_file.write_text('"""FastAPI app package."""\n')

    return tmp_path


# =============================================================================
# FastAPIProject Tests
# =============================================================================

class TestFastAPIProject:
    """Tests for FastAPIProject class."""

    def test_init_with_single_file(self, fastapi_app_file: Path):
        """FastAPIProject should work with single file apps."""
        project = FastAPIProject(fastapi_app_file.parent)

        assert project.project_root == fastapi_app_file.parent
        assert project.app_path == fastapi_app_file

    def test_init_with_package(self, fastapi_package: Path):
        """FastAPIProject should work with package apps."""
        project = FastAPIProject(fastapi_package)

        assert project.project_root == fastapi_package
        assert project.app_path == fastapi_package / "app"

    def test_init_raises_for_missing_directory(self, tmp_path: Path):
        """FastAPIProject should raise ValueError for missing directory."""
        with pytest.raises(ValueError, match="not found"):
            FastAPIProject(tmp_path / "nonexistent")

    def test_dry_run_mode(self, fastapi_app_file: Path):
        """FastAPIProject should support dry-run mode."""
        project = FastAPIProject(fastapi_app_file.parent, dry_run=True)

        assert project.dry_run is True

    def test_context_manager(self, fastapi_app_file: Path):
        """FastAPIProject should work as context manager."""
        with FastAPIProject(fastapi_app_file.parent) as project:
            assert project.project_root == fastapi_app_file.parent

    def test_main_app_file_property(self, fastapi_package: Path):
        """main_app_file should return the correct file."""
        project = FastAPIProject(fastapi_package)

        assert project.main_app_file == fastapi_package / "app" / "main.py"

    def test_find_fastapi_app_variable(self, fastapi_app_file: Path):
        """find_fastapi_app_variable should find the app variable."""
        project = FastAPIProject(fastapi_app_file.parent)

        app_var = project.find_fastapi_app_variable()

        assert app_var == "app"

    def test_find_fastapi_app_variable_with_custom_name(self, tmp_path: Path):
        """find_fastapi_app_variable should find custom variable names."""
        app_file = tmp_path / "main.py"
        app_file.write_text(textwrap.dedent('''\
            from fastapi import FastAPI
            application = FastAPI()
        '''))

        project = FastAPIProject(tmp_path)
        app_var = project.find_fastapi_app_variable()

        assert app_var == "application"


# =============================================================================
# Endpoint Management Tests
# =============================================================================

class TestFastAPIEndpoints:
    """Tests for FastAPI endpoint management."""

    def test_find_endpoints(self, fastapi_package: Path):
        """find_endpoints should find all endpoints in the project."""
        project = FastAPIProject(fastapi_package)

        endpoints = project.find_endpoints()

        assert len(endpoints) >= 3
        paths = [e["path"] for e in endpoints]
        assert "/" in paths
        assert "/items/{item_id}" in paths
        assert "/items" in paths

    def test_find_endpoints_detects_methods(self, fastapi_package: Path):
        """find_endpoints should detect HTTP methods."""
        project = FastAPIProject(fastapi_package)

        endpoints = project.find_endpoints()

        methods = {e["path"]: e["method"] for e in endpoints}
        assert methods["/"] == "GET"
        assert methods["/items/{item_id}"] == "GET"
        assert methods["/items"] == "POST"

    def test_add_endpoint(self, fastapi_app_file: Path):
        """add_endpoint should add a new endpoint."""
        project = FastAPIProject(fastapi_app_file.parent)

        result = project.add_endpoint(
            "/users",
            "get_users",
            method="GET",
        )

        assert result.success is True

        content = fastapi_app_file.read_text()
        assert "@app.get('/users')" in content
        assert "async def get_users()" in content

    def test_add_endpoint_with_response_model(self, fastapi_app_file: Path):
        """add_endpoint should add endpoint with response model."""
        project = FastAPIProject(fastapi_app_file.parent)

        result = project.add_endpoint(
            "/items",
            "list_items",
            method="GET",
            response_model="ItemList",
        )

        assert result.success is True

        content = fastapi_app_file.read_text()
        assert "response_model=ItemList" in content

    def test_add_endpoint_with_status_code(self, fastapi_app_file: Path):
        """add_endpoint should add endpoint with status code."""
        project = FastAPIProject(fastapi_app_file.parent)

        result = project.add_endpoint(
            "/items",
            "create_item",
            method="POST",
            status_code=201,
        )

        assert result.success is True

        content = fastapi_app_file.read_text()
        assert "status_code=201" in content

    def test_add_endpoint_with_tags(self, fastapi_app_file: Path):
        """add_endpoint should add endpoint with OpenAPI tags."""
        project = FastAPIProject(fastapi_app_file.parent)

        result = project.add_endpoint(
            "/admin/users",
            "admin_users",
            tags=["admin", "users"],
        )

        assert result.success is True

        content = fastapi_app_file.read_text()
        assert "tags=" in content

    def test_add_endpoint_with_path_parameters(self, fastapi_app_file: Path):
        """add_endpoint should handle path parameters."""
        project = FastAPIProject(fastapi_app_file.parent)

        result = project.add_endpoint(
            "/items/{item_id}",
            "get_item",
            method="GET",
        )

        assert result.success is True

        content = fastapi_app_file.read_text()
        assert "item_id: str" in content

    def test_add_endpoint_dry_run(self, fastapi_app_file: Path):
        """add_endpoint should not modify files in dry-run mode."""
        original_content = fastapi_app_file.read_text()
        project = FastAPIProject(fastapi_app_file.parent, dry_run=True)

        result = project.add_endpoint("/test", "test_endpoint")

        assert result.success is True
        assert "[DRY RUN]" in result.message
        assert fastapi_app_file.read_text() == original_content

    def test_add_endpoint_fails_if_exists(self, fastapi_app_file: Path):
        """add_endpoint should fail if function already exists."""
        project = FastAPIProject(fastapi_app_file.parent)

        result = project.add_endpoint("/other", "root")  # 'root' already exists

        assert result.success is False
        assert "already exists" in result.message

    def test_remove_endpoint(self, fastapi_app_file: Path):
        """remove_endpoint should remove an endpoint."""
        project = FastAPIProject(fastapi_app_file.parent)

        result = project.remove_endpoint("root")

        assert result.success is True

        content = fastapi_app_file.read_text()
        assert "async def root()" not in content

    def test_remove_endpoint_dry_run(self, fastapi_app_file: Path):
        """remove_endpoint should not modify files in dry-run mode."""
        original_content = fastapi_app_file.read_text()
        project = FastAPIProject(fastapi_app_file.parent, dry_run=True)

        result = project.remove_endpoint("root")

        assert result.success is True
        assert "[DRY RUN]" in result.message
        assert fastapi_app_file.read_text() == original_content

    def test_remove_endpoint_fails_if_not_found(self, fastapi_app_file: Path):
        """remove_endpoint should fail if function doesn't exist."""
        project = FastAPIProject(fastapi_app_file.parent)

        result = project.remove_endpoint("nonexistent_endpoint")

        assert result.success is False
        assert "not found" in result.message


# =============================================================================
# Router Management Tests
# =============================================================================

class TestFastAPIRouters:
    """Tests for FastAPI router management."""

    def test_find_routers(self, tmp_path: Path):
        """find_routers should find all routers."""
        app_file = tmp_path / "main.py"
        app_file.write_text(textwrap.dedent('''\
            from fastapi import FastAPI, APIRouter

            app = FastAPI()
            items_router = APIRouter(prefix='/items', tags=['items'])

            app.include_router(items_router)
        '''))

        project = FastAPIProject(tmp_path)
        routers = project.find_routers()

        assert len(routers) >= 1
        router_vars = [r["variable"] for r in routers]
        assert "items_router" in router_vars

    def test_add_router_creates_file(self, fastapi_package: Path):
        """add_router should create a router file."""
        project = FastAPIProject(fastapi_package)

        result = project.add_router("users", "/users", tags=["users"])

        assert result.success is True

        # Check router file was created
        routers_dir = fastapi_package / "app" / "routers"
        assert routers_dir.exists()
        assert (routers_dir / "users.py").exists()

    def test_add_router_dry_run(self, fastapi_package: Path):
        """add_router should not create files in dry-run mode."""
        project = FastAPIProject(fastapi_package, dry_run=True)

        result = project.add_router("users", "/users")

        assert result.success is True
        assert "[DRY RUN]" in result.message

        routers_dir = fastapi_package / "app" / "routers"
        assert not routers_dir.exists()


# =============================================================================
# Dependency Management Tests
# =============================================================================

class TestFastAPIDependencies:
    """Tests for FastAPI dependency management."""

    def test_add_dependency(self, fastapi_app_file: Path):
        """add_dependency should add a dependency function."""
        project = FastAPIProject(fastapi_app_file.parent)

        result = project.add_dependency(
            "get_db",
            "yield Session()",
            is_async=False,
        )

        assert result.success is True
        assert result.files_changed

        # add_dependency creates a separate deps.py file by default
        deps_file = result.files_changed[0]
        content = deps_file.read_text()
        assert "def get_db()" in content
        assert "yield Session()" in content


# =============================================================================
# Pydantic Model Generation Tests
# =============================================================================

class TestFastAPIPydanticModels:
    """Tests for Pydantic model generation."""

    def test_generate_pydantic_model(self, fastapi_package: Path):
        """generate_pydantic_model should generate a model."""
        project = FastAPIProject(fastapi_package)

        result = project.generate_pydantic_model(
            "Item",
            {"name": "str", "price": "float", "description": "str | None = None"},
        )

        assert result.success is True
        assert result.files_changed

        # Check model file
        model_file = result.files_changed[0]
        content = model_file.read_text()
        assert "class Item(BaseModel)" in content
        assert "name: str" in content
        assert "price: float" in content

    def test_generate_pydantic_model_dry_run(self, fastapi_package: Path):
        """generate_pydantic_model should not create files in dry-run mode."""
        project = FastAPIProject(fastapi_package, dry_run=True)

        result = project.generate_pydantic_model(
            "TestModel",
            {"field": "str"},
        )

        assert result.success is True
        assert "[DRY RUN]" in result.message

    def test_generate_pydantic_models_from_schema(self, fastapi_package: Path, tmp_path: Path):
        """generate_pydantic_models_from_schema should generate from JSON schema."""
        schema_file = tmp_path / "schema.json"
        schema = {
            "title": "Person",
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["name"],
        }
        schema_file.write_text(json.dumps(schema))

        project = FastAPIProject(fastapi_package)
        result = project.generate_pydantic_models_from_schema(schema_file)

        assert result.success is True
        assert "Person" in result.data["models"]

    def test_generate_pydantic_models_from_invalid_schema(self, fastapi_package: Path, tmp_path: Path):
        """generate_pydantic_models_from_schema should fail for invalid JSON."""
        schema_file = tmp_path / "invalid.json"
        schema_file.write_text("not valid json")

        project = FastAPIProject(fastapi_package)
        result = project.generate_pydantic_models_from_schema(schema_file)

        assert result.success is False
        assert "Invalid JSON" in result.message


# =============================================================================
# Middleware Management Tests
# =============================================================================

class TestFastAPIMiddleware:
    """Tests for FastAPI middleware management."""

    def test_add_middleware(self, fastapi_app_file: Path):
        """add_middleware should add middleware."""
        project = FastAPIProject(fastapi_app_file.parent)

        result = project.add_middleware(
            "CORSMiddleware",
            allow_origins=["*"],
            allow_methods=["*"],
        )

        assert result.success is True

        content = fastapi_app_file.read_text()
        assert "add_middleware" in content
        assert "CORSMiddleware" in content


# =============================================================================
# Integration Tests
# =============================================================================

class TestFastAPIIntegration:
    """Integration tests for FastAPI project management."""

    def test_full_workflow(self, tmp_path: Path):
        """Test complete FastAPI project workflow."""
        # Create basic app
        app_file = tmp_path / "main.py"
        app_file.write_text(textwrap.dedent('''\
            from fastapi import FastAPI
            app = FastAPI()
        '''))

        project = FastAPIProject(tmp_path)

        # Add endpoints
        result = project.add_endpoint("/", "root", body='return {"message": "Hello"}')
        assert result.success is True

        result = project.add_endpoint("/users", "list_users", method="GET")
        assert result.success is True

        result = project.add_endpoint("/users", "create_user", method="POST", status_code=201)
        assert result.success is True

        # Find endpoints
        endpoints = project.find_endpoints()
        assert len(endpoints) >= 3

        methods = [e["method"] for e in endpoints]
        assert "GET" in methods
        assert "POST" in methods
