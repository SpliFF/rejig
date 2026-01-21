"""Middleware management for FastAPI applications.

This module provides the MiddlewareManager class for managing FastAPI
middleware configuration.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from rejig.core.results import Result

if TYPE_CHECKING:
    from .project import FastAPIProject


# Common middleware and their import paths
COMMON_MIDDLEWARE = {
    "CORSMiddleware": "fastapi.middleware.cors",
    "TrustedHostMiddleware": "fastapi.middleware.trustedhost",
    "GZipMiddleware": "fastapi.middleware.gzip",
    "HTTPSRedirectMiddleware": "fastapi.middleware.httpsredirect",
    "SessionMiddleware": "starlette.middleware.sessions",
    "AuthenticationMiddleware": "starlette.middleware.authentication",
}


class MiddlewareManager:
    """Manages middleware in a FastAPI application."""

    def __init__(self, project: FastAPIProject):
        self.project = project

    @property
    def dry_run(self) -> bool:
        return self.project.dry_run

    def find_middleware(self) -> list[dict[str, str]]:
        """
        Find all middleware in the project.

        Returns
        -------
        list[dict[str, str]]
            List of dicts with 'class', 'args', and 'file' keys.
        """
        middleware_list: list[dict[str, str]] = []

        for py_file in self.project.project_root.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            try:
                content = py_file.read_text()
            except (OSError, UnicodeDecodeError):
                continue

            # Match add_middleware calls
            middleware_pattern = re.compile(
                r"\.add_middleware\s*\(\s*(\w+)(?:\s*,\s*([^)]*))?\s*\)",
                re.DOTALL,
            )

            for match in middleware_pattern.finditer(content):
                mw_class = match.group(1)
                mw_args = match.group(2) or ""

                middleware_list.append({
                    "class": mw_class,
                    "args": mw_args.strip(),
                    "file": str(py_file),
                })

        return middleware_list

    def add_middleware(
        self,
        middleware_class: str,
        import_path: str | None = None,
        **kwargs,
    ) -> Result:
        """
        Add middleware to the FastAPI application.

        Parameters
        ----------
        middleware_class : str
            Name of the middleware class.
        import_path : str | None
            Import path for the middleware.
        **kwargs
            Arguments to pass to the middleware.

        Returns
        -------
        Result
            Result with success status.
        """
        target_file = self.project.main_app_file

        if not target_file.exists():
            return Result(
                success=False,
                message=f"App file not found: {target_file}",
            )

        content = target_file.read_text()

        # Check if middleware already added
        if re.search(rf"add_middleware\s*\(\s*{middleware_class}", content):
            return Result(
                success=True,
                message=f"Middleware '{middleware_class}' already added",
            )

        # Determine import path
        if import_path is None:
            import_path = COMMON_MIDDLEWARE.get(middleware_class)
            if import_path is None:
                return Result(
                    success=False,
                    message=f"Unknown middleware '{middleware_class}'. Please provide import_path.",
                )

        # Build import statement
        import_stmt = f"from {import_path} import {middleware_class}"

        # Add import if not present
        if import_stmt not in content and middleware_class not in content.split("import")[0]:
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

        # Build middleware arguments
        args_list = []
        for key, value in kwargs.items():
            if isinstance(value, str):
                args_list.append(f'{key}="{value}"')
            elif isinstance(value, bool):
                args_list.append(f"{key}={str(value)}")
            elif isinstance(value, list):
                items = ", ".join(f'"{v}"' if isinstance(v, str) else str(v) for v in value)
                args_list.append(f"{key}=[{items}]")
            else:
                args_list.append(f"{key}={value}")

        args_str = ", ".join(args_list)
        if args_str:
            middleware_call = f"app.add_middleware({middleware_class}, {args_str})"
        else:
            middleware_call = f"app.add_middleware({middleware_class})"

        # Find app variable and add middleware after app creation
        app_var = self.project.find_fastapi_app_variable(target_file) or "app"
        middleware_call = middleware_call.replace("app.", f"{app_var}.")

        app_pattern = re.compile(
            rf"{app_var}\s*=\s*FastAPI\s*\([^)]*\)[^\n]*\n",
            re.MULTILINE,
        )
        match = app_pattern.search(content)

        if match:
            insert_pos = match.end()
            content = content[:insert_pos] + middleware_call + "\n" + content[insert_pos:]
        else:
            content = content.rstrip() + f"\n\n{middleware_call}\n"

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would add middleware '{middleware_class}'",
                files_changed=[target_file],
            )

        target_file.write_text(content)

        return Result(
            success=True,
            message=f"Added middleware '{middleware_class}'",
            files_changed=[target_file],
        )

    def remove_middleware(
        self,
        middleware_class: str,
    ) -> Result:
        """
        Remove middleware from the FastAPI application.

        Parameters
        ----------
        middleware_class : str
            Name of the middleware class to remove.

        Returns
        -------
        Result
            Result with success status.
        """
        target_file = self.project.main_app_file

        if not target_file.exists():
            return Result(
                success=False,
                message=f"App file not found: {target_file}",
            )

        content = target_file.read_text()

        # Remove the add_middleware call
        pattern = re.compile(
            rf"^\s*\w+\.add_middleware\s*\(\s*{middleware_class}[^)]*\)\s*\n?",
            re.MULTILINE,
        )

        if not pattern.search(content):
            return Result(
                success=False,
                message=f"Middleware '{middleware_class}' not found",
            )

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would remove middleware '{middleware_class}'",
                files_changed=[target_file],
            )

        new_content = pattern.sub("", content)

        # Optionally remove the import (only if not used elsewhere)
        if middleware_class not in new_content.replace(f"import {middleware_class}", ""):
            # Safe to remove import
            new_content = re.sub(
                rf"^from [^\n]* import {middleware_class}\n",
                "",
                new_content,
                flags=re.MULTILINE,
            )

        target_file.write_text(new_content)

        return Result(
            success=True,
            message=f"Removed middleware '{middleware_class}'",
            files_changed=[target_file],
        )
