"""FastAPI project class for refactoring operations.

This module provides the main FastAPIProject class that combines all
FastAPI-specific refactoring capabilities.
"""
from __future__ import annotations

import re
from pathlib import Path

from rejig.core import Rejig
from rejig.core.results import Result

from .dependencies import DependencyManager
from .endpoints import EndpointManager
from .middleware import MiddlewareManager


class FastAPIProject:
    """
    Represents a FastAPI project for refactoring operations.

    This is the main entry point for FastAPI-specific refactoring operations.
    Initialize with the path to your FastAPI application directory.

    Parameters
    ----------
    project_root : Path | str
        Path to the project root directory containing the FastAPI app.
    app_module : str, optional
        Name of the main FastAPI application module/package. Defaults to "app".
    dry_run : bool, optional
        If True, all operations will report what they would do without making
        actual changes. Defaults to False.

    Attributes
    ----------
    project_root : Path
        Resolved absolute path to the project root directory.
    app_path : Path
        Path to the FastAPI application module.
    dry_run : bool
        Whether operations are in dry-run mode.

    Examples
    --------
    >>> fastapi = FastAPIProject("/path/to/myproject")
    >>> fastapi.add_endpoint("/items/{id}", "get_item", method="GET", response_model="Item")
    Result(success=True, ...)

    >>> # Preview changes without modifying files
    >>> fastapi = FastAPIProject("/path/to/myproject", dry_run=True)
    >>> result = fastapi.add_middleware("CORSMiddleware", allow_origins=["*"])
    >>> print(result.message)
    [DRY RUN] Would add middleware 'CORSMiddleware'
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

        # Determine app path
        self.app_path = self._find_app_path()

        # Initialize sub-managers
        self._endpoints = EndpointManager(self)
        self._dependencies = DependencyManager(self)
        self._middleware = MiddlewareManager(self)

        # Create internal Rejig instance for CST operations
        self._rejig = Rejig(self.project_root, dry_run=dry_run)

    def _find_app_path(self) -> Path:
        """Find the FastAPI application path (file or directory)."""
        # Try as a package directory
        pkg_path = self.project_root / self.app_module
        if pkg_path.is_dir() and (pkg_path / "__init__.py").exists():
            return pkg_path

        # Try as a single file
        file_path = self.project_root / f"{self.app_module}.py"
        if file_path.is_file():
            return file_path

        # Also check for main.py (common FastAPI convention)
        main_path = self.project_root / "main.py"
        if main_path.is_file():
            return main_path

        return pkg_path

    @property
    def main_app_file(self) -> Path:
        """Path to the main FastAPI app file (where FastAPI() is instantiated)."""
        if self.app_path.is_file():
            return self.app_path
        # Check common patterns
        for name in ("main.py", "__init__.py", "app.py"):
            candidate = self.app_path / name
            if candidate.exists():
                content = candidate.read_text()
                if "FastAPI(" in content:
                    return candidate
        return self.app_path / "main.py"

    @property
    def routers_dir(self) -> Path:
        """Path to the routers/endpoints directory."""
        if self.app_path.is_file():
            return self.app_path.parent / "routers"
        for name in ("routers", "endpoints", "api"):
            candidate = self.app_path / name
            if candidate.is_dir():
                return candidate
        return self.app_path / "routers"

    @property
    def models_dir(self) -> Path:
        """Path to the Pydantic models directory."""
        if self.app_path.is_file():
            return self.app_path.parent / "models"
        for name in ("models", "schemas"):
            candidate = self.app_path / name
            if candidate.is_dir():
                return candidate
        return self.app_path / "models"

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

    def find_fastapi_app_variable(self, file_path: Path | None = None) -> str | None:
        """
        Find the FastAPI app variable name in a file.

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
        # Match patterns like: app = FastAPI(...) or application = FastAPI()
        match = re.search(r"(\w+)\s*=\s*FastAPI\s*\(", content)
        return match.group(1) if match else None

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
            List of dicts with 'path', 'function', 'method', and 'router' keys.
        """
        return self._endpoints.find_endpoints(router)

    def find_routers(self) -> list[dict[str, str]]:
        """
        Find all routers in the project.

        Returns
        -------
        list[dict[str, str]]
            List of dicts with 'variable', 'prefix', and 'file' keys.
        """
        return self._endpoints.find_routers()

    # -------------------------------------------------------------------------
    # Endpoint Management (delegated to EndpointManager)
    # -------------------------------------------------------------------------

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
            URL path for the endpoint (e.g., '/items/{id}').
        function_name : str
            Name of the endpoint function.
        method : str
            HTTP method (GET, POST, PUT, DELETE, etc.).
        response_model : str | None
            Pydantic model for response validation.
        status_code : int | None
            Default HTTP status code.
        tags : list[str] | None
            OpenAPI tags for grouping.
        router : str | None
            Router variable name if adding to a router.
        file_path : Path | None
            File to add endpoint to.
        body : str
            Function body.
        parameters : list[dict[str, str]] | None
            Function parameters as list of dicts with 'name', 'type', 'default' keys.

        Returns
        -------
        Result
            Result with success status.
        """
        return self._endpoints.add_endpoint(
            path, function_name, method, response_model, status_code, tags,
            router, file_path, body, parameters
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
        return self._endpoints.remove_endpoint(function_name, file_path)

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
            URL prefix for all routes in this router.
        tags : list[str] | None
            OpenAPI tags for the router.
        create_file : bool
            If True, create a new file for the router.

        Returns
        -------
        Result
            Result with success status.
        """
        return self._endpoints.add_router(name, prefix, tags, create_file)

    # -------------------------------------------------------------------------
    # Dependency Management (delegated to DependencyManager)
    # -------------------------------------------------------------------------

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
        return self._dependencies.add_dependency(name, body, file_path, is_async)

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
        return self._dependencies.add_depends_parameter(endpoint_name, param_name, dependency, file_path)

    # -------------------------------------------------------------------------
    # Middleware Management (delegated to MiddlewareManager)
    # -------------------------------------------------------------------------

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
            Import path for the middleware. Common ones are auto-detected.
        **kwargs
            Arguments to pass to the middleware constructor.

        Returns
        -------
        Result
            Result with success status.
        """
        return self._middleware.add_middleware(middleware_class, import_path, **kwargs)

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
        return self._middleware.remove_middleware(middleware_class)

    # -------------------------------------------------------------------------
    # Pydantic Model Generation
    # -------------------------------------------------------------------------

    def generate_pydantic_model(
        self,
        name: str,
        fields: dict[str, str],
        file_path: Path | None = None,
        base_class: str = "BaseModel",
    ) -> Result:
        """
        Generate a Pydantic model.

        Parameters
        ----------
        name : str
            Name of the model class.
        fields : dict[str, str]
            Dict mapping field name to type annotation.
        file_path : Path | None
            File to add model to.
        base_class : str
            Base class for the model.

        Returns
        -------
        Result
            Result with success status.
        """
        target_file = file_path
        if target_file is None:
            self.models_dir.mkdir(exist_ok=True)
            target_file = self.models_dir / f"{name.lower()}.py"

        # Build fields
        field_lines = []
        for field_name, field_type in fields.items():
            field_lines.append(f"    {field_name}: {field_type}")

        fields_code = "\n".join(field_lines) if field_lines else "    pass"

        model_code = f'''"""Pydantic model for {name}."""
from pydantic import {base_class}


class {name}({base_class}):
    """{name} model."""
{fields_code}
'''

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would generate Pydantic model '{name}'",
                files_changed=[target_file],
            )

        # If file exists, append to it
        if target_file.exists():
            content = target_file.read_text()
            # Check if model already exists
            if re.search(rf"\bclass\s+{name}\s*\(", content):
                return Result(
                    success=False,
                    message=f"Model '{name}' already exists in {target_file}",
                )
            # Append model
            new_content = content.rstrip() + f"\n\n\nclass {name}({base_class}):\n    \"\"\"{name} model.\"\"\"\n{fields_code}\n"
            target_file.write_text(new_content)
        else:
            target_file.write_text(model_code)

        return Result(
            success=True,
            message=f"Generated Pydantic model '{name}'",
            files_changed=[target_file],
        )

    def generate_pydantic_models_from_schema(
        self,
        schema_file: Path,
        output_file: Path | None = None,
    ) -> Result:
        """
        Generate Pydantic models from a JSON schema file.

        Parameters
        ----------
        schema_file : Path
            Path to JSON schema file.
        output_file : Path | None
            File to write models to.

        Returns
        -------
        Result
            Result with success status.
        """
        import json

        schema_path = Path(schema_file)
        if not schema_path.exists():
            return Result(
                success=False,
                message=f"Schema file not found: {schema_file}",
            )

        try:
            schema = json.loads(schema_path.read_text())
        except json.JSONDecodeError as e:
            return Result(
                success=False,
                message=f"Invalid JSON schema: {e}",
            )

        # Extract models from JSON schema
        models: list[str] = []

        def type_mapping(json_type: str, format_: str | None = None) -> str:
            """Map JSON schema types to Python types."""
            mappings = {
                "string": "str",
                "integer": "int",
                "number": "float",
                "boolean": "bool",
                "array": "list",
                "object": "dict",
            }
            if format_ == "date-time":
                return "datetime"
            if format_ == "date":
                return "date"
            if format_ == "email":
                return "EmailStr"
            if format_ == "uri":
                return "HttpUrl"
            return mappings.get(json_type, "Any")

        def process_schema(name: str, schema_def: dict) -> str:
            """Process a schema definition into a model."""
            fields: list[str] = []
            required = set(schema_def.get("required", []))

            for prop_name, prop_def in schema_def.get("properties", {}).items():
                prop_type = prop_def.get("type", "string")
                prop_format = prop_def.get("format")
                python_type = type_mapping(prop_type, prop_format)

                if prop_type == "array":
                    items_type = type_mapping(prop_def.get("items", {}).get("type", "Any"))
                    python_type = f"list[{items_type}]"

                if prop_name not in required:
                    python_type = f"{python_type} | None = None"

                fields.append(f"    {prop_name}: {python_type}")

            fields_code = "\n".join(fields) if fields else "    pass"
            return f"class {name}(BaseModel):\n    \"\"\"{name} model.\"\"\"\n{fields_code}\n"

        # Process main schema
        if "title" in schema:
            models.append(process_schema(schema["title"], schema))

        # Process definitions
        for def_name, def_schema in schema.get("definitions", {}).items():
            models.append(process_schema(def_name, def_schema))

        # Also check $defs (JSON Schema draft 2019+)
        for def_name, def_schema in schema.get("$defs", {}).items():
            models.append(process_schema(def_name, def_schema))

        if not models:
            return Result(
                success=False,
                message="No models could be extracted from schema",
            )

        # Build output
        imports = "from pydantic import BaseModel\nfrom typing import Any\nfrom datetime import datetime, date\n\n"
        content = imports + "\n\n".join(models)

        target_file = output_file or (self.models_dir / "generated.py")

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would generate {len(models)} Pydantic models",
                data={"models": [m.split("(")[0].split()[-1] for m in models]},
            )

        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(content)

        return Result(
            success=True,
            message=f"Generated {len(models)} Pydantic models from schema",
            files_changed=[target_file],
            data={"models": [m.split("(")[0].split()[-1] for m in models]},
        )
