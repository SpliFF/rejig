"""Endpoint management for FastAPI applications.

This module provides the EndpointManager class for managing FastAPI endpoints,
routers, and path operations.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from rejig.core.results import Result

if TYPE_CHECKING:
    from .project import FastAPIProject


class EndpointManager:
    """Manages endpoints and routers in a FastAPI application."""

    def __init__(self, project: FastAPIProject):
        self.project = project

    @property
    def dry_run(self) -> bool:
        return self.project.dry_run

    def find_endpoints(self, router: str | None = None) -> list[dict[str, str]]:
        """
        Find all endpoints in the project.

        Parameters
        ----------
        router : str | None
            If provided, only return endpoints for this router.

        Returns
        -------
        list[dict[str, str]]
            List of dicts with endpoint information.
        """
        endpoints: list[dict[str, str]] = []

        # Search all Python files
        for py_file in self.project.project_root.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            try:
                content = py_file.read_text()
            except (OSError, UnicodeDecodeError):
                continue

            # Match endpoint decorators: @app.get('/path') or @router.post('/path')
            endpoint_pattern = re.compile(
                r"@(\w+)\.(get|post|put|delete|patch|options|head)\s*\(\s*['\"]([^'\"]+)['\"]"
                r"(?:[^)]*response_model\s*=\s*(\w+))?"
                r"(?:[^)]*status_code\s*=\s*(\d+))?"
                r"[^)]*\)\s*\n"
                r"(?:@[^\n]+\n)*"  # Skip additional decorators
                r"(?:async\s+)?def\s+(\w+)\s*\(",
                re.MULTILINE,
            )

            for match in endpoint_pattern.finditer(content):
                decorator_obj = match.group(1)
                method = match.group(2).upper()
                path = match.group(3)
                response_model = match.group(4) or ""
                status_code = match.group(5) or ""
                func_name = match.group(6)

                # Determine router
                router_name = None
                if decorator_obj not in ("app", "application"):
                    router_name = decorator_obj

                if router is not None and router_name != router:
                    continue

                endpoints.append({
                    "path": path,
                    "function": func_name,
                    "method": method,
                    "response_model": response_model,
                    "status_code": status_code,
                    "router": router_name or "",
                    "file": str(py_file),
                })

        return endpoints

    def find_routers(self) -> list[dict[str, str]]:
        """
        Find all routers in the project.

        Returns
        -------
        list[dict[str, str]]
            List of dicts with router information.
        """
        routers: list[dict[str, str]] = []

        for py_file in self.project.project_root.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            try:
                content = py_file.read_text()
            except (OSError, UnicodeDecodeError):
                continue

            # Match APIRouter instantiation
            router_pattern = re.compile(
                r"(\w+)\s*=\s*APIRouter\s*\("
                r"(?:[^)]*prefix\s*=\s*['\"]([^'\"]*)['\"])?"
                r"(?:[^)]*tags\s*=\s*\[([^\]]*)\])?"
                r"[^)]*\)",
                re.DOTALL,
            )

            for match in router_pattern.finditer(content):
                var_name = match.group(1)
                prefix = match.group(2) or ""
                tags_str = match.group(3) or ""

                # Parse tags
                tags = []
                if tags_str:
                    tags = [t.strip().strip("'\"") for t in tags_str.split(",")]

                routers.append({
                    "variable": var_name,
                    "prefix": prefix,
                    "tags": ", ".join(tags),
                    "file": str(py_file),
                })

        return routers

    def add_endpoint(
        self,
        path: str,
        function_name: str,
        method: str = "GET",
        response_model: str | None = None,
        status_code: int | None = None,
        tags: list[str] | None = None,
        router: str | None = None,
        file_path: Path | None = None,
        body: str = "pass",
        parameters: list[dict[str, str]] | None = None,
    ) -> Result:
        """
        Add a new endpoint to the FastAPI application.

        Parameters
        ----------
        path : str
            URL path for the endpoint.
        function_name : str
            Name of the endpoint function.
        method : str
            HTTP method.
        response_model : str | None
            Pydantic model for response.
        status_code : int | None
            Default HTTP status code.
        tags : list[str] | None
            OpenAPI tags.
        router : str | None
            Router variable name.
        file_path : Path | None
            File to add endpoint to.
        body : str
            Function body.
        parameters : list[dict[str, str]] | None
            Function parameters.

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
                message=f"Function '{function_name}' already exists in {target_file}",
            )

        # Determine decorator object
        if router:
            decorator_obj = router
        else:
            app_var = self.project.find_fastapi_app_variable(target_file)
            decorator_obj = app_var or "app"

        # Build decorator arguments
        method_lower = method.lower()
        decorator_args = [f"'{path}'"]

        if response_model:
            decorator_args.append(f"response_model={response_model}")
        if status_code:
            decorator_args.append(f"status_code={status_code}")
        if tags:
            tags_str = ", ".join(f"'{t}'" for t in tags)
            decorator_args.append(f"tags=[{tags_str}]")

        decorator = f"@{decorator_obj}.{method_lower}({', '.join(decorator_args)})"

        # Build function parameters
        params = []
        if parameters:
            for param in parameters:
                param_str = param["name"]
                if param.get("type"):
                    param_str += f": {param['type']}"
                if param.get("default"):
                    param_str += f" = {param['default']}"
                params.append(param_str)

        # Extract path parameters
        path_params = re.findall(r"\{(\w+)\}", path)
        for pp in path_params:
            if not any(p.startswith(pp) for p in params):
                params.insert(0, f"{pp}: str")

        params_str = ", ".join(params)

        # Build function
        endpoint_code = f"\n\n{decorator}\nasync def {function_name}({params_str}):\n    {body}\n"

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would add endpoint {method} '{path}' -> {function_name}()",
                files_changed=[target_file],
            )

        # Append to file
        new_content = content.rstrip() + endpoint_code
        target_file.write_text(new_content)

        return Result(
            success=True,
            message=f"Added endpoint {method} '{path}' -> {function_name}()",
            files_changed=[target_file],
        )

    def remove_endpoint(
        self,
        function_name: str,
        file_path: Path | None = None,
    ) -> Result:
        """
        Remove an endpoint from the FastAPI application.

        Parameters
        ----------
        function_name : str
            Name of the endpoint function to remove.
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

        # Pattern to match the decorator(s) and function definition
        pattern = re.compile(
            r"(\n*)(@\w+\.(get|post|put|delete|patch|options|head)\s*\([^)]*\)\s*\n"
            r"(?:@[^\n]+\n)*"  # Additional decorators
            r"(?:async\s+)?def\s+" + re.escape(function_name) + r"\s*\([^)]*\)(?:\s*->[^:]+)?:[^\n]*\n"
            r"(?:[ \t]+[^\n]*\n)*)",  # Function body
            re.MULTILINE,
        )

        match = pattern.search(content)
        if not match:
            return Result(
                success=False,
                message=f"Endpoint function '{function_name}' not found in {target_file}",
            )

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would remove endpoint function '{function_name}'",
                files_changed=[target_file],
            )

        new_content = pattern.sub("\n", content)
        new_content = re.sub(r"\n{3,}", "\n\n", new_content)
        target_file.write_text(new_content)

        return Result(
            success=True,
            message=f"Removed endpoint function '{function_name}'",
            files_changed=[target_file],
        )

    def add_router(
        self,
        name: str,
        prefix: str,
        tags: list[str] | None = None,
        create_file: bool = True,
    ) -> Result:
        """
        Add a new router to the FastAPI application.

        Parameters
        ----------
        name : str
            Name for the router module.
        prefix : str
            URL prefix for all routes.
        tags : list[str] | None
            OpenAPI tags.
        create_file : bool
            If True, create a new file for the router.

        Returns
        -------
        Result
            Result with success status.
        """
        files_changed: list[Path] = []
        router_var = f"{name}_router"

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would add router '{name}' with prefix '{prefix}'",
            )

        if create_file:
            # Create routers directory if needed
            self.project.routers_dir.mkdir(exist_ok=True)
            files_changed.append(self.project.routers_dir)

            # Create __init__.py if not exists
            init_file = self.project.routers_dir / "__init__.py"
            if not init_file.exists():
                init_file.write_text('"""Router modules."""\n')
                files_changed.append(init_file)

            # Build router arguments
            router_args = [f"prefix='{prefix}'"]
            if tags:
                tags_str = ", ".join(f"'{t}'" for t in tags)
                router_args.append(f"tags=[{tags_str}]")

            # Create router file
            router_content = f'''"""Router for {name}."""
from fastapi import APIRouter

{router_var} = APIRouter({", ".join(router_args)})


@{router_var}.get("/")
async def {name}_index():
    return {{"router": "{name}"}}
'''
            router_file = self.project.routers_dir / f"{name}.py"
            router_file.write_text(router_content)
            files_changed.append(router_file)

            # Add include in main app file
            app_file = self.project.main_app_file
            if app_file.exists():
                content = app_file.read_text()

                # Add import
                routers_module = self.project.routers_dir.name
                import_stmt = f"from {self.project.app_module}.{routers_module}.{name} import {router_var}"
                if import_stmt not in content:
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

                # Add include_router call
                app_var = self.project.find_fastapi_app_variable(app_file) or "app"
                include_call = f"{app_var}.include_router({router_var})"

                if include_call not in content:
                    # Find app creation and add after it
                    app_pattern = re.compile(
                        rf"{app_var}\s*=\s*FastAPI\s*\([^)]*\)[^\n]*\n",
                        re.MULTILINE,
                    )
                    match = app_pattern.search(content)
                    if match:
                        insert_pos = match.end()
                        content = content[:insert_pos] + include_call + "\n" + content[insert_pos:]
                    else:
                        content = content.rstrip() + f"\n\n{include_call}\n"

                app_file.write_text(content)
                files_changed.append(app_file)

        return Result(
            success=True,
            message=f"Created router '{name}' with prefix '{prefix}'",
            files_changed=files_changed,
        )
