"""DependenciesTarget - Target for managing pyproject.toml dependencies."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from rejig.core.results import Result
from rejig.targets.config.toml import TomlTarget

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig
    from rejig.packaging.models import Dependency


class DependenciesTarget(TomlTarget):
    """Target for managing dependencies in pyproject.toml.

    Handles both PEP 621 format (project.dependencies) and Poetry format
    (tool.poetry.dependencies).

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    path : Path
        Path to pyproject.toml.
    group : str | None
        Optional dependency group name. None for main dependencies,
        "dev" for dev dependencies, or any other group name.

    Examples
    --------
    >>> # Main dependencies
    >>> deps = pyproject.dependencies()
    >>> deps.add("requests", ">=2.28.0")
    >>> deps.remove("old-package")
    >>> deps.update("django", ">=5.0")
    >>>
    >>> # Dev dependencies
    >>> dev_deps = pyproject.dev_dependencies()
    >>> dev_deps.add("pytest", ">=7.0")
    >>>
    >>> # Optional dependency group
    >>> cache_deps = pyproject.optional_dependencies("cache")
    >>> cache_deps.add("redis", ">=4.0")
    """

    def __init__(
        self,
        rejig: Rejig,
        path: Path,
        group: str | None = None,
    ) -> None:
        super().__init__(rejig, path)
        self._group = group

    def __repr__(self) -> str:
        if self._group:
            return f"DependenciesTarget({self.path}, group={self._group!r})"
        return f"DependenciesTarget({self.path})"

    @property
    def group(self) -> str | None:
        """The dependency group name."""
        return self._group

    def _get_key_path(self) -> str:
        """Get the dotted key path for this dependencies section."""
        data = self._load()
        if data is None:
            return "project.dependencies"

        # Check format
        is_poetry = "tool" in data and "poetry" in data.get("tool", {})

        if is_poetry:
            if self._group is None:
                return "tool.poetry.dependencies"
            elif self._group == "dev":
                return "tool.poetry.group.dev.dependencies"
            else:
                return f"tool.poetry.group.{self._group}.dependencies"
        else:
            # PEP 621 format
            if self._group is None:
                return "project.dependencies"
            else:
                return f"project.optional-dependencies.{self._group}"

    def _normalize_name(self, name: str) -> str:
        """Normalize package name per PEP 503."""
        import re
        return re.sub(r"[-_.]+", "-", name).lower()

    # =========================================================================
    # Read Operations
    # =========================================================================

    def list(self) -> list[str]:
        """List all dependencies in this section.

        Returns
        -------
        list[str]
            List of dependency specifications.

        Examples
        --------
        >>> deps = pyproject.dependencies().list()
        >>> for dep in deps:
        ...     print(dep)
        """
        key_path = self._get_key_path()
        value = self.get(key_path)

        if value is None:
            return []

        # PEP 621 format: list of strings
        if isinstance(value, list):
            return value

        # Poetry format: dict of name -> spec
        if isinstance(value, dict):
            result = []
            for name, spec in value.items():
                if name == "python":
                    continue
                if isinstance(spec, str):
                    if spec == "*":
                        result.append(name)
                    else:
                        result.append(f"{name}{spec}")
                elif isinstance(spec, dict):
                    version = spec.get("version", "*")
                    if version == "*":
                        result.append(name)
                    else:
                        result.append(f"{name}{version}")
            return result

        return []

    def has(self, name: str) -> bool:
        """Check if a dependency exists.

        Parameters
        ----------
        name : str
            Package name.

        Returns
        -------
        bool
            True if dependency exists.
        """
        normalized = self._normalize_name(name)
        for dep in self.list():
            dep_name = self._normalize_name(dep.split("[")[0].split("<")[0].split(">")[0].split("=")[0].split("!")[0])
            if dep_name == normalized:
                return True
        return False

    def get_version(self, name: str) -> str | None:
        """Get the version spec for a dependency.

        Parameters
        ----------
        name : str
            Package name.

        Returns
        -------
        str | None
            Version specification, or None if not found.
        """
        normalized = self._normalize_name(name)
        for dep in self.list():
            dep_name = self._normalize_name(dep.split("[")[0].split("<")[0].split(">")[0].split("=")[0].split("!")[0])
            if dep_name == normalized:
                # Extract version from spec
                import re
                match = re.search(r"[<>=!~].+$", dep)
                return match.group(0) if match else None
        return None

    # =========================================================================
    # Write Operations
    # =========================================================================

    def add(
        self,
        name: str,
        version: str | None = None,
        extras: list[str] | None = None,
    ) -> Result:
        """Add a dependency.

        Parameters
        ----------
        name : str
            Package name.
        version : str | None
            Version specification (e.g., ">=2.28.0", "^1.0").
        extras : list[str] | None
            Optional extras (e.g., ["security"]).

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> deps.add("requests", ">=2.28.0")
        >>> deps.add("fastapi", ">=0.100", extras=["standard"])
        """
        if self.has(name):
            return Result(success=True, message=f"Dependency {name} already exists")

        data = self._load()
        if data is None:
            return self._operation_failed("add", "Failed to load pyproject.toml")

        key_path = self._get_key_path()
        is_poetry = key_path.startswith("tool.poetry")

        # Build the spec
        spec: str | dict[str, Any]
        if is_poetry:
            # Poetry format
            if extras:
                spec = {"version": version or "*", "extras": extras}
            else:
                spec = version or "*"
        else:
            # PEP 621 format
            spec = name
            if extras:
                spec += f"[{','.join(extras)}]"
            if version:
                spec += version

        # Ensure section exists and add
        keys = key_path.split(".")
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        final_key = keys[-1]
        if final_key not in current:
            current[final_key] = [] if not is_poetry else {}

        if is_poetry:
            current[final_key][name] = spec
        else:
            current[final_key].append(spec)

        return self._save(data)

    def remove(self, name: str) -> Result:
        """Remove a dependency.

        Parameters
        ----------
        name : str
            Package name to remove.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> deps.remove("old-package")
        """
        if not self.has(name):
            return Result(success=True, message=f"Dependency {name} not found")

        data = self._load()
        if data is None:
            return self._operation_failed("remove", "Failed to load pyproject.toml")

        key_path = self._get_key_path()
        normalized = self._normalize_name(name)

        # Navigate to the section
        keys = key_path.split(".")
        current = data
        for key in keys[:-1]:
            if key not in current:
                return Result(success=True, message=f"Dependency {name} not found")
            current = current[key]

        final_key = keys[-1]
        if final_key not in current:
            return Result(success=True, message=f"Dependency {name} not found")

        section = current[final_key]

        if isinstance(section, list):
            # PEP 621 format
            new_deps = []
            for dep in section:
                dep_name = self._normalize_name(dep.split("[")[0].split("<")[0].split(">")[0].split("=")[0].split("!")[0])
                if dep_name != normalized:
                    new_deps.append(dep)
            current[final_key] = new_deps
        elif isinstance(section, dict):
            # Poetry format
            if name in section:
                del section[name]

        return self._save(data)

    def update(
        self,
        name: str,
        version: str,
        extras: list[str] | None = None,
    ) -> Result:
        """Update a dependency's version.

        Parameters
        ----------
        name : str
            Package name.
        version : str
            New version specification.
        extras : list[str] | None
            Optional extras.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> deps.update("django", ">=5.0")
        """
        # Remove then add
        self.remove(name)
        return self.add(name, version, extras)

    def clear(self) -> Result:
        """Remove all dependencies from this section.

        Returns
        -------
        Result
            Result of the operation.
        """
        data = self._load()
        if data is None:
            return self._operation_failed("clear", "Failed to load pyproject.toml")

        key_path = self._get_key_path()
        keys = key_path.split(".")
        current = data

        for key in keys[:-1]:
            if key not in current:
                return Result(success=True, message="Section is empty")
            current = current[key]

        final_key = keys[-1]
        if final_key in current:
            if isinstance(current[final_key], list):
                current[final_key] = []
            elif isinstance(current[final_key], dict):
                current[final_key] = {}

        return self._save(data)

    # =========================================================================
    # Bulk Operations
    # =========================================================================

    def add_many(self, dependencies: dict[str, str | None]) -> Result:
        """Add multiple dependencies at once.

        Parameters
        ----------
        dependencies : dict[str, str | None]
            Dictionary mapping package names to version specs.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> deps.add_many({
        ...     "requests": ">=2.28.0",
        ...     "aiohttp": ">=3.8.0",
        ...     "pydantic": ">=2.0",
        ... })
        """
        data = self._load()
        if data is None:
            return self._operation_failed("add_many", "Failed to load pyproject.toml")

        key_path = self._get_key_path()
        is_poetry = key_path.startswith("tool.poetry")

        # Ensure section exists
        keys = key_path.split(".")
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        final_key = keys[-1]
        if final_key not in current:
            current[final_key] = [] if not is_poetry else {}

        section = current[final_key]

        for name, version in dependencies.items():
            if is_poetry:
                section[name] = version or "*"
            else:
                spec = name
                if version:
                    spec += version
                if spec not in section:
                    section.append(spec)

        return self._save(data)

    def sync_from_imports(self, source_dirs: list[Path] | None = None) -> Result:
        """Suggest dependencies based on imports in source code.

        Scans Python files and returns suggested dependencies.

        Parameters
        ----------
        source_dirs : list[Path] | None
            Directories to scan. Defaults to ["src", "."].

        Returns
        -------
        Result
            Result with suggested dependencies in `data` field.
        """
        import ast
        import sys
        import importlib.util

        if source_dirs is None:
            root = self.path.parent
            source_dirs = [root / "src", root]

        # Get declared dependencies
        declared = {self._normalize_name(dep.split("[")[0].split("<")[0].split(">")[0].split("=")[0].split("!")[0])
                    for dep in self.list()}

        # Scan for imports
        imported_modules: set[str] = set()

        for src_dir in source_dirs:
            if not src_dir.exists():
                continue

            for py_file in src_dir.rglob("*.py"):
                try:
                    content = py_file.read_text()
                    tree = ast.parse(content)

                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                top_module = alias.name.split(".")[0]
                                imported_modules.add(top_module)
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                top_module = node.module.split(".")[0]
                                imported_modules.add(top_module)
                except Exception:
                    continue

        # Filter to likely external packages
        suggestions: list[str] = []
        stdlib_modules = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else set()

        for module in imported_modules:
            if module in stdlib_modules:
                continue
            normalized = self._normalize_name(module)
            if normalized not in declared:
                suggestions.append(module)

        return Result(
            success=True,
            message=f"Found {len(suggestions)} potentially missing dependencies",
            data=sorted(suggestions),
        )
