"""
Tests for rejig.frameworks.flask module.

This module tests Flask project management:
- FlaskProject class
- RouteManager class
- BlueprintManager class
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig.frameworks.flask import FlaskProject


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def flask_app_file(tmp_path: Path) -> Path:
    """Create a minimal Flask app file."""
    app_file = tmp_path / "app.py"
    app_file.write_text(textwrap.dedent('''\
        from flask import Flask

        app = Flask(__name__)

        @app.route('/')
        def index():
            return "Hello, World!"
    '''))
    return app_file


@pytest.fixture
def flask_package(tmp_path: Path) -> Path:
    """Create a Flask app as a package."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    # __init__.py
    init_file = app_dir / "__init__.py"
    init_file.write_text(textwrap.dedent('''\
        from flask import Flask

        app = Flask(__name__)

        from . import routes
    '''))

    # routes.py
    routes_file = app_dir / "routes.py"
    routes_file.write_text(textwrap.dedent('''\
        from . import app

        @app.route('/')
        def index():
            return "Hello, World!"

        @app.route('/api/users', methods=['GET', 'POST'])
        def users():
            return {"users": []}
    '''))

    return tmp_path


# =============================================================================
# FlaskProject Tests
# =============================================================================

class TestFlaskProject:
    """Tests for FlaskProject class."""

    def test_init_with_single_file(self, flask_app_file: Path):
        """FlaskProject should work with single file apps."""
        project = FlaskProject(flask_app_file.parent)

        assert project.project_root == flask_app_file.parent
        assert project.app_path == flask_app_file

    def test_init_with_package(self, flask_package: Path):
        """FlaskProject should work with package apps."""
        project = FlaskProject(flask_package)

        assert project.project_root == flask_package
        assert project.app_path == flask_package / "app"

    def test_init_raises_for_missing_directory(self, tmp_path: Path):
        """FlaskProject should raise ValueError for missing directory."""
        with pytest.raises(ValueError, match="not found"):
            FlaskProject(tmp_path / "nonexistent")

    def test_dry_run_mode(self, flask_app_file: Path):
        """FlaskProject should support dry-run mode."""
        project = FlaskProject(flask_app_file.parent, dry_run=True)

        assert project.dry_run is True

    def test_context_manager(self, flask_app_file: Path):
        """FlaskProject should work as context manager."""
        with FlaskProject(flask_app_file.parent) as project:
            assert project.project_root == flask_app_file.parent

    def test_main_app_file_property(self, flask_package: Path):
        """main_app_file should return the correct file."""
        project = FlaskProject(flask_package)

        assert project.main_app_file == flask_package / "app" / "__init__.py"

    def test_routes_file_property_with_routes_py(self, flask_package: Path):
        """routes_file should return routes.py if it exists."""
        project = FlaskProject(flask_package)

        assert project.routes_file == flask_package / "app" / "routes.py"

    def test_find_flask_app_variable(self, flask_app_file: Path):
        """find_flask_app_variable should find the app variable."""
        project = FlaskProject(flask_app_file.parent)

        app_var = project.find_flask_app_variable()

        assert app_var == "app"

    def test_find_flask_app_variable_with_custom_name(self, tmp_path: Path):
        """find_flask_app_variable should find custom variable names."""
        app_file = tmp_path / "app.py"
        app_file.write_text(textwrap.dedent('''\
            from flask import Flask
            application = Flask(__name__)
        '''))

        project = FlaskProject(tmp_path)
        app_var = project.find_flask_app_variable()

        assert app_var == "application"


# =============================================================================
# Route Management Tests
# =============================================================================

class TestFlaskRoutes:
    """Tests for Flask route management."""

    def test_find_routes(self, flask_package: Path):
        """find_routes should find all routes in the project."""
        project = FlaskProject(flask_package)

        routes = project.find_routes()

        assert len(routes) >= 2
        paths = [r["path"] for r in routes]
        assert "/" in paths
        assert "/api/users" in paths

    def test_find_routes_detects_methods(self, flask_package: Path):
        """find_routes should detect HTTP methods."""
        project = FlaskProject(flask_package)

        routes = project.find_routes()

        users_route = next((r for r in routes if r["path"] == "/api/users"), None)
        assert users_route is not None
        assert "GET" in users_route["methods"]
        assert "POST" in users_route["methods"]

    def test_add_route(self, flask_app_file: Path):
        """add_route should add a new route."""
        project = FlaskProject(flask_app_file.parent)

        result = project.add_route(
            "/api/items",
            "get_items",
            methods=["GET"],
        )

        assert result.success is True
        assert "get_items" in result.message or "/api/items" in result.message

        # Verify the route was added
        content = flask_app_file.read_text()
        assert "@app.route('/api/items')" in content
        assert "def get_items()" in content

    def test_add_route_with_methods(self, flask_app_file: Path):
        """add_route should add route with multiple methods."""
        project = FlaskProject(flask_app_file.parent)

        result = project.add_route(
            "/api/data",
            "handle_data",
            methods=["GET", "POST"],
        )

        assert result.success is True

        content = flask_app_file.read_text()
        assert "methods=" in content
        assert "GET" in content
        assert "POST" in content

    def test_add_route_dry_run(self, flask_app_file: Path):
        """add_route should not modify files in dry-run mode."""
        original_content = flask_app_file.read_text()
        project = FlaskProject(flask_app_file.parent, dry_run=True)

        result = project.add_route("/api/test", "test_route")

        assert result.success is True
        assert "[DRY RUN]" in result.message
        assert flask_app_file.read_text() == original_content

    def test_add_route_fails_if_exists(self, flask_app_file: Path):
        """add_route should fail if function already exists."""
        project = FlaskProject(flask_app_file.parent)

        result = project.add_route("/other", "index")  # 'index' already exists

        assert result.success is False
        assert "already exists" in result.message

    def test_remove_route(self, flask_app_file: Path):
        """remove_route should remove a route."""
        project = FlaskProject(flask_app_file.parent)

        result = project.remove_route("index")

        assert result.success is True

        content = flask_app_file.read_text()
        assert "def index()" not in content

    def test_remove_route_dry_run(self, flask_app_file: Path):
        """remove_route should not modify files in dry-run mode."""
        original_content = flask_app_file.read_text()
        project = FlaskProject(flask_app_file.parent, dry_run=True)

        result = project.remove_route("index")

        assert result.success is True
        assert "[DRY RUN]" in result.message
        assert flask_app_file.read_text() == original_content

    def test_remove_route_fails_if_not_found(self, flask_app_file: Path):
        """remove_route should fail if function doesn't exist."""
        project = FlaskProject(flask_app_file.parent)

        result = project.remove_route("nonexistent_route")

        assert result.success is False
        assert "not found" in result.message

    def test_add_error_handler(self, flask_app_file: Path):
        """add_error_handler should add an error handler."""
        project = FlaskProject(flask_app_file.parent)

        result = project.add_error_handler(404, "not_found")

        assert result.success is True

        content = flask_app_file.read_text()
        assert "@app.errorhandler(404)" in content
        assert "def not_found(error)" in content


# =============================================================================
# Blueprint Management Tests
# =============================================================================

class TestFlaskBlueprints:
    """Tests for Flask blueprint management."""

    def test_find_blueprints(self, tmp_path: Path):
        """find_blueprints should find all blueprints."""
        # Create app with blueprint
        app_file = tmp_path / "app.py"
        app_file.write_text(textwrap.dedent('''\
            from flask import Flask, Blueprint

            app = Flask(__name__)
            api_bp = Blueprint('api', __name__, url_prefix='/api')

            app.register_blueprint(api_bp)
        '''))

        project = FlaskProject(tmp_path)
        blueprints = project.find_blueprints()

        assert len(blueprints) >= 1
        bp_names = [bp["name"] for bp in blueprints]
        assert "api" in bp_names

    def test_add_blueprint_creates_package(self, flask_package: Path):
        """add_blueprint should create a blueprint package."""
        project = FlaskProject(flask_package)

        result = project.add_blueprint("admin", url_prefix="/admin")

        assert result.success is True

        # Check package was created
        admin_dir = flask_package / "app" / "admin"
        assert admin_dir.exists()
        assert (admin_dir / "__init__.py").exists()
        assert (admin_dir / "routes.py").exists()

    def test_add_blueprint_dry_run(self, flask_package: Path):
        """add_blueprint should not create files in dry-run mode."""
        project = FlaskProject(flask_package, dry_run=True)

        result = project.add_blueprint("admin", url_prefix="/admin")

        assert result.success is True
        assert "[DRY RUN]" in result.message

        # Check package was NOT created
        admin_dir = flask_package / "app" / "admin"
        assert not admin_dir.exists()

    def test_register_blueprint(self, tmp_path: Path):
        """register_blueprint should register a blueprint."""
        # Create app and blueprint in separate files
        app_file = tmp_path / "app.py"
        app_file.write_text(textwrap.dedent('''\
            from flask import Flask

            app = Flask(__name__)
        '''))

        admin_dir = tmp_path / "admin"
        admin_dir.mkdir()
        (admin_dir / "__init__.py").write_text(textwrap.dedent('''\
            from flask import Blueprint
            admin_bp = Blueprint('admin', __name__)
        '''))

        project = FlaskProject(tmp_path)
        result = project.register_blueprint("admin_bp", "admin", url_prefix="/admin")

        assert result.success is True

        content = app_file.read_text()
        assert "from admin import admin_bp" in content
        assert "register_blueprint(admin_bp" in content

    def test_remove_blueprint(self, tmp_path: Path):
        """remove_blueprint should remove a blueprint."""
        # Create app with blueprint
        app_file = tmp_path / "app.py"
        app_file.write_text(textwrap.dedent('''\
            from flask import Flask
            from admin import admin_bp

            app = Flask(__name__)
            app.register_blueprint(admin_bp, url_prefix='/admin')
        '''))

        project = FlaskProject(tmp_path)
        result = project.remove_blueprint("admin")

        assert result.success is True

        content = app_file.read_text()
        assert "admin_bp" not in content


# =============================================================================
# OpenAPI Generation Tests
# =============================================================================

class TestFlaskOpenAPI:
    """Tests for OpenAPI spec generation."""

    def test_generate_openapi_spec(self, flask_package: Path):
        """generate_openapi_spec should generate valid spec."""
        project = FlaskProject(flask_package)

        result = project.generate_openapi_spec(title="Test API")

        assert result.success is True
        assert result.data is not None
        assert result.data["openapi"] == "3.0.0"
        assert result.data["info"]["title"] == "Test API"
        assert "/" in result.data["paths"]

    def test_generate_openapi_spec_to_file(self, flask_package: Path, tmp_path: Path):
        """generate_openapi_spec should write to file."""
        output_file = tmp_path / "openapi.json"
        project = FlaskProject(flask_package)

        result = project.generate_openapi_spec(
            output_file=output_file,
            title="File API",
        )

        assert result.success is True
        assert output_file.exists()

        import json
        spec = json.loads(output_file.read_text())
        assert spec["info"]["title"] == "File API"

    def test_generate_openapi_spec_fails_with_no_routes(self, tmp_path: Path):
        """generate_openapi_spec should fail if no routes."""
        app_file = tmp_path / "app.py"
        app_file.write_text("from flask import Flask\napp = Flask(__name__)\n")

        project = FlaskProject(tmp_path)
        result = project.generate_openapi_spec()

        assert result.success is False
        assert "No routes found" in result.message


# =============================================================================
# Integration Tests
# =============================================================================

class TestFlaskIntegration:
    """Integration tests for Flask project management."""

    def test_full_workflow(self, tmp_path: Path):
        """Test complete Flask project workflow."""
        # Create basic app
        app_file = tmp_path / "app.py"
        app_file.write_text(textwrap.dedent('''\
            from flask import Flask
            app = Flask(__name__)
        '''))

        project = FlaskProject(tmp_path)

        # Add routes
        result = project.add_route("/", "index")
        assert result.success is True

        result = project.add_route("/api/users", "get_users", methods=["GET"])
        assert result.success is True

        result = project.add_route("/api/users", "create_user", methods=["POST"])
        assert result.success is True

        # Add error handler
        result = project.add_error_handler(404, "not_found")
        assert result.success is True

        # Find routes
        routes = project.find_routes()
        assert len(routes) >= 3

        # Generate OpenAPI spec
        result = project.generate_openapi_spec()
        assert result.success is True
        assert len(result.data["paths"]) >= 2
