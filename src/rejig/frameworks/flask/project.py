"""Flask project class for refactoring operations.

This module provides the main FlaskProject class that combines all
Flask-specific refactoring capabilities.
"""
from __future__ import annotations

import re
from pathlib import Path

from rejig.core import Rejig
from rejig.core.results import Result

from .blueprints import BlueprintManager
from .routes import RouteManager


class FlaskProject:
    """
    Represents a Flask project for refactoring operations.

    This is the main entry point for Flask-specific refactoring operations.
    Initialize with the path to your Flask application directory.

    Parameters
    ----------
    project_root : Path | str
        Path to the project root directory containing the Flask app.
    app_module : str, optional
        Name of the main Flask application module/package. Defaults to "app".
    dry_run : bool, optional
        If True, all operations will report what they would do without making
        actual changes. Defaults to False.

    Attributes
    ----------
    project_root : Path
        Resolved absolute path to the project root directory.
    app_path : Path
        Path to the Flask application module.
    dry_run : bool
        Whether operations are in dry-run mode.

    Examples
    --------
    >>> flask = FlaskProject("/path/to/myproject")
    >>> flask.add_route("/api/users", "get_users", methods=["GET"])
    Result(success=True, ...)

    >>> # Preview changes without modifying files
    >>> flask = FlaskProject("/path/to/myproject", dry_run=True)
    >>> result = flask.add_blueprint("admin", url_prefix="/admin")
    >>> print(result.message)
    [DRY RUN] Would add blueprint 'admin' with prefix '/admin'
    """

    def __init__(
        self,
        project_root: Path | str,
        app_module: str = "app",
        dry_run: bool = False,
    ):
        self.project_root = Path(project_root).resolve()
        self.app_module = app_module
        self.dry_run = dry_run

        if not self.project_root.exists():
            raise ValueError(f"Project root directory not found: {self.project_root}")

        # Determine app path - could be a file or directory
        self.app_path = self._find_app_path()

        # Initialize sub-managers
        self._routes = RouteManager(self)
        self._blueprints = BlueprintManager(self)

        # Create internal Rejig instance for CST operations
        self._rejig = Rejig(self.project_root, dry_run=dry_run)

    def _find_app_path(self) -> Path:
        """Find the Flask application path (file or directory)."""
        # Try as a package directory
        pkg_path = self.project_root / self.app_module
        if pkg_path.is_dir() and (pkg_path / "__init__.py").exists():
            return pkg_path

        # Try as a single file
        file_path = self.project_root / f"{self.app_module}.py"
        if file_path.is_file():
            return file_path

        # Default to expecting a package
        return pkg_path

    @property
    def main_app_file(self) -> Path:
        """Path to the main Flask app file (where Flask() is instantiated)."""
        if self.app_path.is_file():
            return self.app_path
        return self.app_path / "__init__.py"

    @property
    def routes_file(self) -> Path:
        """Path to the routes file (routes.py or main app file)."""
        if self.app_path.is_file():
            return self.app_path
        routes_py = self.app_path / "routes.py"
        if routes_py.exists():
            return routes_py
        views_py = self.app_path / "views.py"
        if views_py.exists():
            return views_py
        return self.main_app_file

    def close(self) -> None:
        """Close the project and clean up resources."""
        self._rejig.close()

    def __enter__(self):
        """Context manager support."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up on context exit."""
        self.close()
        return False

    # -------------------------------------------------------------------------
    # App Discovery Methods
    # -------------------------------------------------------------------------

    def find_flask_app_variable(self, file_path: Path | None = None) -> str | None:
        """
        Find the Flask app variable name in a file.

        Parameters
        ----------
        file_path : Path | None
            File to search in. Defaults to main app file.

        Returns
        -------
        str | None
            Variable name (e.g., 'app', 'application') or None if not found.
        """
        target_file = file_path or self.main_app_file
        if not target_file.exists():
            return None

        content = target_file.read_text()
        # Match patterns like: app = Flask(__name__) or application = Flask(...)
        match = re.search(r"(\w+)\s*=\s*Flask\s*\(", content)
        return match.group(1) if match else None

    def find_blueprints(self) -> list[dict[str, str]]:
        """
        Find all registered blueprints in the project.

        Returns
        -------
        list[dict[str, str]]
            List of dicts with 'name', 'variable', and 'url_prefix' keys.
        """
        return self._blueprints.find_blueprints()

    def find_routes(self, blueprint: str | None = None) -> list[dict[str, str]]:
        """
        Find all routes in the project.

        Parameters
        ----------
        blueprint : str | None
            If provided, only return routes for this blueprint.

        Returns
        -------
        list[dict[str, str]]
            List of dicts with 'path', 'function', 'methods', and 'blueprint' keys.
        """
        return self._routes.find_routes(blueprint)

    # -------------------------------------------------------------------------
    # Route Management (delegated to RouteManager)
    # -------------------------------------------------------------------------

    def add_route(
        self,
        path: str,
        function_name: str,
        methods: list[str] | None = None,
        blueprint: str | None = None,
        file_path: Path | None = None,
        body: str = "pass",
    ) -> Result:
        """
        Add a new route to the Flask application.

        Parameters
        ----------
        path : str
            URL path for the route (e.g., '/api/users').
        function_name : str
            Name of the view function.
        methods : list[str] | None
            HTTP methods (e.g., ['GET', 'POST']). Defaults to ['GET'].
        blueprint : str | None
            Blueprint name if adding to a blueprint.
        file_path : Path | None
            File to add route to. Defaults to routes_file.
        body : str
            Function body. Defaults to "pass".

        Returns
        -------
        Result
            Result with success status.
        """
        return self._routes.add_route(path, function_name, methods, blueprint, file_path, body)

    def remove_route(
        self,
        function_name: str,
        file_path: Path | None = None,
    ) -> Result:
        """
        Remove a route from the Flask application.

        Parameters
        ----------
        function_name : str
            Name of the view function to remove.
        file_path : Path | None
            File containing the route.

        Returns
        -------
        Result
            Result with success status.
        """
        return self._routes.remove_route(function_name, file_path)

    def add_error_handler(
        self,
        error_code: int,
        function_name: str,
        file_path: Path | None = None,
        body: str | None = None,
    ) -> Result:
        """
        Add an error handler to the Flask application.

        Parameters
        ----------
        error_code : int
            HTTP error code to handle (e.g., 404, 500).
        function_name : str
            Name of the handler function.
        file_path : Path | None
            File to add handler to.
        body : str | None
            Function body. Defaults to returning JSON error.

        Returns
        -------
        Result
            Result with success status.
        """
        return self._routes.add_error_handler(error_code, function_name, file_path, body)

    # -------------------------------------------------------------------------
    # Blueprint Management (delegated to BlueprintManager)
    # -------------------------------------------------------------------------

    def add_blueprint(
        self,
        name: str,
        url_prefix: str | None = None,
        import_name: str | None = None,
        template_folder: str | None = None,
        static_folder: str | None = None,
        create_package: bool = True,
    ) -> Result:
        """
        Add a new blueprint to the Flask application.

        Parameters
        ----------
        name : str
            Name of the blueprint.
        url_prefix : str | None
            URL prefix for all routes in this blueprint.
        import_name : str | None
            Import name for the blueprint. Defaults to the blueprint name.
        template_folder : str | None
            Template folder relative to blueprint package.
        static_folder : str | None
            Static folder relative to blueprint package.
        create_package : bool
            If True, create a package directory for the blueprint.

        Returns
        -------
        Result
            Result with success status.
        """
        return self._blueprints.add_blueprint(
            name, url_prefix, import_name, template_folder, static_folder, create_package
        )

    def register_blueprint(
        self,
        blueprint_var: str,
        import_path: str,
        url_prefix: str | None = None,
        app_file: Path | None = None,
    ) -> Result:
        """
        Register an existing blueprint with the Flask app.

        Parameters
        ----------
        blueprint_var : str
            Variable name of the blueprint (e.g., 'admin_bp').
        import_path : str
            Import path for the blueprint (e.g., 'app.admin').
        url_prefix : str | None
            URL prefix for the blueprint.
        app_file : Path | None
            File containing the Flask app. Defaults to main app file.

        Returns
        -------
        Result
            Result with success status.
        """
        return self._blueprints.register_blueprint(blueprint_var, import_path, url_prefix, app_file)

    def remove_blueprint(
        self,
        name: str,
        remove_package: bool = False,
    ) -> Result:
        """
        Remove a blueprint from the Flask application.

        Parameters
        ----------
        name : str
            Name of the blueprint to remove.
        remove_package : bool
            If True, also remove the blueprint package directory.

        Returns
        -------
        Result
            Result with success status.
        """
        return self._blueprints.remove_blueprint(name, remove_package)

    # -------------------------------------------------------------------------
    # OpenAPI/Swagger Generation
    # -------------------------------------------------------------------------

    def generate_openapi_spec(
        self,
        output_file: Path | None = None,
        title: str = "Flask API",
        version: str = "1.0.0",
        description: str = "",
    ) -> Result:
        """
        Generate an OpenAPI specification from Flask routes.

        Parameters
        ----------
        output_file : Path | None
            File to write spec to. If None, returns spec in result.data.
        title : str
            API title.
        version : str
            API version.
        description : str
            API description.

        Returns
        -------
        Result
            Result with spec in data field or file written.
        """
        routes = self.find_routes()
        if not routes:
            return Result(
                success=False,
                message="No routes found in Flask application",
            )

        # Build OpenAPI spec
        paths: dict[str, dict] = {}
        for route in routes:
            path = route.get("path", "/")
            methods = route.get("methods", "GET").lower().split(", ")
            function = route.get("function", "unknown")

            if path not in paths:
                paths[path] = {}

            for method in methods:
                method = method.strip().lower()
                if method not in ["get", "post", "put", "delete", "patch", "head", "options"]:
                    continue
                paths[path][method] = {
                    "operationId": function,
                    "summary": f"{function.replace('_', ' ').title()}",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                        }
                    },
                }

        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": title,
                "version": version,
                "description": description,
            },
            "paths": paths,
        }

        if output_file:
            import json

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would write OpenAPI spec to {output_file}",
                    data=spec,
                )

            output_path = Path(output_file)
            if output_path.suffix in (".yaml", ".yml"):
                try:
                    import yaml
                    content = yaml.dump(spec, default_flow_style=False, sort_keys=False)
                except ImportError:
                    content = json.dumps(spec, indent=2)
            else:
                content = json.dumps(spec, indent=2)

            output_path.write_text(content)
            return Result(
                success=True,
                message=f"Generated OpenAPI spec at {output_file}",
                files_changed=[output_path],
                data=spec,
            )

        return Result(
            success=True,
            message="Generated OpenAPI spec",
            data=spec,
        )
