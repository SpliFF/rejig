"""Blueprint management for Flask applications.

This module provides the BlueprintManager class for managing Flask blueprints,
including creation, registration, and removal.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from rejig.core.results import Result

if TYPE_CHECKING:
    from .project import FlaskProject


class BlueprintManager:
    """Manages blueprints in a Flask application."""

    def __init__(self, project: FlaskProject):
        self.project = project

    @property
    def dry_run(self) -> bool:
        return self.project.dry_run

    def find_blueprints(self) -> list[dict[str, str]]:
        """
        Find all registered blueprints in the project.

        Returns
        -------
        list[dict[str, str]]
            List of dicts with 'name', 'variable', 'url_prefix', and 'file' keys.
        """
        blueprints: list[dict[str, str]] = []

        # Search all Python files
        for py_file in self.project.project_root.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            try:
                content = py_file.read_text()
            except (OSError, UnicodeDecodeError):
                continue

            # Match Blueprint instantiation: bp = Blueprint('name', __name__, ...)
            bp_pattern = re.compile(
                r"(\w+)\s*=\s*Blueprint\s*\(\s*['\"](\w+)['\"]"
                r"[^)]*(?:url_prefix\s*=\s*['\"]([^'\"]*)['\"])?[^)]*\)",
                re.DOTALL,
            )

            for match in bp_pattern.finditer(content):
                var_name = match.group(1)
                bp_name = match.group(2)
                url_prefix = match.group(3) or ""

                blueprints.append({
                    "variable": var_name,
                    "name": bp_name,
                    "url_prefix": url_prefix,
                    "file": str(py_file),
                })

        return blueprints

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
            URL prefix for all routes.
        import_name : str | None
            Import name for the blueprint.
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
        import_name = import_name or name
        bp_var = f"{name}_bp"

        if self.dry_run:
            msg = f"[DRY RUN] Would add blueprint '{name}'"
            if url_prefix:
                msg += f" with prefix '{url_prefix}'"
            return Result(success=True, message=msg)

        files_changed: list[Path] = []

        if create_package:
            # Create blueprint package directory
            bp_dir = self.project.app_path / name if self.project.app_path.is_dir() else (
                self.project.project_root / name
            )
            bp_dir.mkdir(exist_ok=True)
            files_changed.append(bp_dir)

            # Build Blueprint arguments
            bp_args = [f"'{name}'", "__name__"]
            if url_prefix:
                bp_args.append(f"url_prefix='{url_prefix}'")
            if template_folder:
                bp_args.append(f"template_folder='{template_folder}'")
            if static_folder:
                bp_args.append(f"static_folder='{static_folder}'")

            # Create __init__.py with blueprint
            init_content = f'''"""Blueprint for {name}."""
from flask import Blueprint

{bp_var} = Blueprint({", ".join(bp_args)})

from . import routes  # noqa: E402, F401
'''
            init_file = bp_dir / "__init__.py"
            init_file.write_text(init_content)
            files_changed.append(init_file)

            # Create routes.py
            routes_content = f'''"""Routes for {name} blueprint."""
from flask import jsonify

from . import {bp_var}


@{bp_var}.route('/')
def index():
    return jsonify({{"blueprint": "{name}"}})
'''
            routes_file = bp_dir / "routes.py"
            routes_file.write_text(routes_content)
            files_changed.append(routes_file)

            # Register blueprint in main app
            register_result = self.register_blueprint(
                bp_var,
                f"{self.project.app_module}.{name}",
                url_prefix,
            )
            if register_result.files_changed:
                files_changed.extend(register_result.files_changed)

        return Result(
            success=True,
            message=f"Created blueprint '{name}' package",
            files_changed=files_changed,
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
            Variable name of the blueprint.
        import_path : str
            Import path for the blueprint.
        url_prefix : str | None
            URL prefix for the blueprint.
        app_file : Path | None
            File containing the Flask app.

        Returns
        -------
        Result
            Result with success status.
        """
        target_file = app_file or self.project.main_app_file

        if not target_file.exists():
            return Result(
                success=False,
                message=f"App file not found: {target_file}",
            )

        content = target_file.read_text()

        # Check if already registered
        if re.search(rf"register_blueprint\s*\(\s*{blueprint_var}", content):
            return Result(
                success=True,
                message=f"Blueprint '{blueprint_var}' already registered",
            )

        # Build import statement
        import_stmt = f"from {import_path} import {blueprint_var}"

        # Check if import exists
        if import_stmt not in content:
            # Add import after other imports
            lines = content.splitlines()
            last_import_idx = -1
            for i, line in enumerate(lines):
                if line.strip().startswith(("import ", "from ")) and not line.strip().startswith(
                    "from __future__"
                ):
                    last_import_idx = i

            if last_import_idx >= 0:
                lines.insert(last_import_idx + 1, import_stmt)
            else:
                lines.insert(0, import_stmt)
            content = "\n".join(lines)

        # Build registration call
        app_var = self.project.find_flask_app_variable(target_file) or "app"
        if url_prefix:
            register_call = f"{app_var}.register_blueprint({blueprint_var}, url_prefix='{url_prefix}')"
        else:
            register_call = f"{app_var}.register_blueprint({blueprint_var})"

        # Add registration after app creation
        app_creation_pattern = re.compile(
            rf"{app_var}\s*=\s*Flask\s*\([^)]*\)[^\n]*\n",
            re.MULTILINE,
        )
        match = app_creation_pattern.search(content)

        if match:
            # Insert after app creation line
            insert_pos = match.end()
            content = content[:insert_pos] + register_call + "\n" + content[insert_pos:]
        else:
            # Append to file
            content = content.rstrip() + f"\n\n{register_call}\n"

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would register blueprint '{blueprint_var}'",
                files_changed=[target_file],
            )

        target_file.write_text(content)

        return Result(
            success=True,
            message=f"Registered blueprint '{blueprint_var}'",
            files_changed=[target_file],
        )

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
        bp_var = f"{name}_bp"
        files_changed: list[Path] = []

        # Find and update main app file
        app_file = self.project.main_app_file
        if app_file.exists():
            content = app_file.read_text()

            # Remove import
            content = re.sub(
                rf"^from [^\n]*import {bp_var}\n",
                "",
                content,
                flags=re.MULTILINE,
            )

            # Remove registration
            content = re.sub(
                rf"^\s*\w+\.register_blueprint\s*\(\s*{bp_var}[^)]*\)\s*\n?",
                "",
                content,
                flags=re.MULTILINE,
            )

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would remove blueprint '{name}'",
                    files_changed=[app_file],
                )

            app_file.write_text(content)
            files_changed.append(app_file)

        # Remove package directory if requested
        if remove_package:
            bp_dir = self.project.app_path / name if self.project.app_path.is_dir() else (
                self.project.project_root / name
            )
            if bp_dir.exists():
                shutil.rmtree(bp_dir)
                files_changed.append(bp_dir)

        return Result(
            success=True,
            message=f"Removed blueprint '{name}'",
            files_changed=files_changed,
        )
