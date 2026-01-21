"""Dependency management for FastAPI applications.

This module provides the DependencyManager class for managing FastAPI
dependency injection functions.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from rejig.core.results import Result

if TYPE_CHECKING:
    from .project import FastAPIProject


class DependencyManager:
    """Manages dependencies in a FastAPI application."""

    def __init__(self, project: FastAPIProject):
        self.project = project

    @property
    def dry_run(self) -> bool:
        return self.project.dry_run

    def find_dependencies(self) -> list[dict[str, str]]:
        """
        Find all dependency functions in the project.

        Returns
        -------
        list[dict[str, str]]
            List of dicts with 'name', 'is_async', and 'file' keys.
        """
        deps: list[dict[str, str]] = []

        for py_file in self.project.project_root.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            try:
                content = py_file.read_text()
            except (OSError, UnicodeDecodeError):
                continue

            # Look for functions that are used with Depends()
            # Also look for common patterns like get_db, get_current_user, etc.
            depends_pattern = re.compile(r"Depends\s*\(\s*(\w+)\s*\)")
            dep_names = set(depends_pattern.findall(content))

            # Find the actual function definitions
            for dep_name in dep_names:
                func_pattern = re.compile(
                    rf"(async\s+)?def\s+{dep_name}\s*\(",
                    re.MULTILINE,
                )
                match = func_pattern.search(content)
                if match:
                    deps.append({
                        "name": dep_name,
                        "is_async": "async" if match.group(1) else "",
                        "file": str(py_file),
                    })

        return deps

    def add_dependency(
        self,
        name: str,
        body: str,
        file_path: Path | None = None,
        is_async: bool = False,
    ) -> Result:
        """
        Add a new dependency function.

        Parameters
        ----------
        name : str
            Name of the dependency function.
        body : str
            Function body.
        file_path : Path | None
            File to add dependency to.
        is_async : bool
            If True, create an async function.

        Returns
        -------
        Result
            Result with success status.
        """
        # Default to a deps.py file in app directory
        if file_path is None:
            if self.project.app_path.is_dir():
                file_path = self.project.app_path / "deps.py"
            else:
                file_path = self.project.app_path.parent / "deps.py"

        target_file = Path(file_path)

        # Create file if it doesn't exist
        if not target_file.exists():
            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would create dependency '{name}' in new file {target_file}",
                    files_changed=[target_file],
                )
            target_file.write_text('"""Dependency functions."""\n')

        content = target_file.read_text()

        # Check if function already exists
        if re.search(rf"\bdef\s+{name}\s*\(", content):
            return Result(
                success=False,
                message=f"Dependency '{name}' already exists in {target_file}",
            )

        # Build function
        func_keyword = "async def" if is_async else "def"
        dep_code = f"\n\n{func_keyword} {name}():\n    {body}\n"

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would add dependency '{name}'",
                files_changed=[target_file],
            )

        new_content = content.rstrip() + dep_code
        target_file.write_text(new_content)

        return Result(
            success=True,
            message=f"Added dependency '{name}'",
            files_changed=[target_file],
        )

    def add_depends_parameter(
        self,
        endpoint_name: str,
        param_name: str,
        dependency: str,
        file_path: Path | None = None,
    ) -> Result:
        """
        Add a Depends parameter to an endpoint.

        Parameters
        ----------
        endpoint_name : str
            Name of the endpoint function.
        param_name : str
            Name for the parameter.
        dependency : str
            Dependency function name or expression.
        file_path : Path | None
            File containing the endpoint.

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

        # Find the endpoint function
        func_pattern = re.compile(
            r"((?:async\s+)?def\s+" + re.escape(endpoint_name) + r"\s*\()([^)]*)(\))",
            re.MULTILINE,
        )

        match = func_pattern.search(content)
        if not match:
            return Result(
                success=False,
                message=f"Endpoint '{endpoint_name}' not found in {target_file}",
            )

        existing_params = match.group(2).strip()

        # Check if parameter already exists
        if param_name in existing_params:
            return Result(
                success=False,
                message=f"Parameter '{param_name}' already exists in '{endpoint_name}'",
            )

        # Build new parameter
        new_param = f"{param_name} = Depends({dependency})"

        if existing_params:
            new_params = f"{existing_params}, {new_param}"
        else:
            new_params = new_param

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would add Depends({dependency}) to '{endpoint_name}'",
                files_changed=[target_file],
            )

        # Replace the function signature
        new_content = func_pattern.sub(
            rf"\g<1>{new_params}\g<3>",
            content,
        )

        # Ensure Depends is imported
        if "from fastapi import" in new_content:
            if "Depends" not in new_content:
                new_content = re.sub(
                    r"(from fastapi import)([^\n]+)",
                    r"\1 Depends,\2",
                    new_content,
                    count=1,
                )
        elif "import Depends" not in new_content:
            # Add import at the top
            new_content = "from fastapi import Depends\n" + new_content

        target_file.write_text(new_content)

        return Result(
            success=True,
            message=f"Added Depends({dependency}) to '{endpoint_name}'",
            files_changed=[target_file],
        )
