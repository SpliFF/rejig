"""Route management for Flask applications.

This module provides the RouteManager class for managing Flask routes,
view functions, and error handlers.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from rejig.core.results import Result

if TYPE_CHECKING:
    from .project import FlaskProject


class RouteManager:
    """Manages routes and error handlers in a Flask application."""

    def __init__(self, project: FlaskProject):
        self.project = project

    @property
    def dry_run(self) -> bool:
        return self.project.dry_run

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
        routes: list[dict[str, str]] = []

        # Search all Python files
        for py_file in self.project.project_root.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            try:
                content = py_file.read_text()
            except (OSError, UnicodeDecodeError):
                continue

            # Match route decorators: @app.route('/path') or @bp.route('/path', methods=['GET'])
            # Also matches @app.get('/path'), @app.post('/path'), etc.
            route_pattern = re.compile(
                r"@(\w+)\.(route|get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]"
                r"(?:\s*,\s*methods\s*=\s*\[([^\]]+)\])?\s*\)\s*\n"
                r"(?:@[^\n]+\n)*"  # Skip additional decorators
                r"def\s+(\w+)\s*\(",
                re.MULTILINE,
            )

            for match in route_pattern.finditer(content):
                decorator_obj = match.group(1)
                route_type = match.group(2)
                path = match.group(3)
                methods_str = match.group(4)
                func_name = match.group(5)

                # Determine methods
                if route_type == "route":
                    if methods_str:
                        methods = [m.strip().strip("'\"") for m in methods_str.split(",")]
                    else:
                        methods = ["GET"]
                else:
                    methods = [route_type.upper()]

                # Determine blueprint
                bp_name = None
                if decorator_obj not in ("app", "application"):
                    bp_name = decorator_obj

                if blueprint is not None and bp_name != blueprint:
                    continue

                routes.append({
                    "path": path,
                    "function": func_name,
                    "methods": ", ".join(methods),
                    "blueprint": bp_name or "",
                    "file": str(py_file),
                })

        return routes

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
            URL path for the route.
        function_name : str
            Name of the view function.
        methods : list[str] | None
            HTTP methods. Defaults to ['GET'].
        blueprint : str | None
            Blueprint name if adding to a blueprint.
        file_path : Path | None
            File to add route to.
        body : str
            Function body.

        Returns
        -------
        Result
            Result with success status.
        """
        methods = methods or ["GET"]
        target_file = file_path or self.project.routes_file

        if not target_file.exists():
            return Result(
                success=False,
                message=f"Routes file not found: {target_file}",
            )

        content = target_file.read_text()

        # Check if function already exists
        if re.search(rf"\bdef\s+{function_name}\s*\(", content):
            return Result(
                success=False,
                message=f"Function '{function_name}' already exists in {target_file}",
            )

        # Determine decorator object
        if blueprint:
            decorator_obj = blueprint
        else:
            app_var = self.project.find_flask_app_variable(target_file)
            decorator_obj = app_var or "app"

        # Build route decorator
        if len(methods) == 1 and methods[0].upper() == "GET":
            decorator = f"@{decorator_obj}.route('{path}')"
        else:
            methods_list = ", ".join(f"'{m.upper()}'" for m in methods)
            decorator = f"@{decorator_obj}.route('{path}', methods=[{methods_list}])"

        # Build function
        route_code = f"\n\n{decorator}\ndef {function_name}():\n    {body}\n"

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would add route '{path}' -> {function_name}()",
                files_changed=[target_file],
            )

        # Append to file
        new_content = content.rstrip() + route_code
        target_file.write_text(new_content)

        return Result(
            success=True,
            message=f"Added route '{path}' -> {function_name}()",
            files_changed=[target_file],
        )

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
        target_file = file_path or self.project.routes_file

        if not target_file.exists():
            return Result(
                success=False,
                message=f"File not found: {target_file}",
            )

        content = target_file.read_text()

        # Pattern to match the decorator(s) and function definition
        # This matches route decorators followed by the function
        pattern = re.compile(
            r"(\n*)(@\w+\.(route|get|post|put|delete|patch)\s*\([^)]*\)\s*\n"
            r"(?:@[^\n]+\n)*"  # Additional decorators
            r"def\s+" + re.escape(function_name) + r"\s*\([^)]*\):[^\n]*\n"
            r"(?:[ \t]+[^\n]*\n)*)",  # Function body (indented lines)
            re.MULTILINE,
        )

        match = pattern.search(content)
        if not match:
            return Result(
                success=False,
                message=f"Route function '{function_name}' not found in {target_file}",
            )

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would remove route function '{function_name}'",
                files_changed=[target_file],
            )

        # Remove the matched content, preserving one newline
        new_content = pattern.sub("\n", content)
        # Clean up extra newlines
        new_content = re.sub(r"\n{3,}", "\n\n", new_content)
        target_file.write_text(new_content)

        return Result(
            success=True,
            message=f"Removed route function '{function_name}'",
            files_changed=[target_file],
        )

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
            HTTP error code to handle.
        function_name : str
            Name of the handler function.
        file_path : Path | None
            File to add handler to.
        body : str | None
            Function body.

        Returns
        -------
        Result
            Result with success status.
        """
        target_file = file_path or self.project.main_app_file

        if not target_file.exists():
            return Result(
                success=False,
                message=f"File not found: {target_file}",
            )

        content = target_file.read_text()

        # Check if function already exists
        if re.search(rf"\bdef\s+{function_name}\s*\(", content):
            return Result(
                success=False,
                message=f"Function '{function_name}' already exists",
            )

        # Determine app variable
        app_var = self.project.find_flask_app_variable(target_file)
        app_var = app_var or "app"

        # Default body
        if body is None:
            body = f'return {{"error": "{error_code}", "message": str(error)}}, {error_code}'

        # Build error handler
        handler_code = f"""

@{app_var}.errorhandler({error_code})
def {function_name}(error):
    {body}
"""

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would add error handler for {error_code}",
                files_changed=[target_file],
            )

        new_content = content.rstrip() + handler_code
        target_file.write_text(new_content)

        return Result(
            success=True,
            message=f"Added error handler for {error_code} -> {function_name}()",
            files_changed=[target_file],
        )
