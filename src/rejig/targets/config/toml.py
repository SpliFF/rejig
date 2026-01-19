"""TomlTarget for operations on TOML configuration files."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rejig.targets.base import Result, Target

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig

# Python 3.11+ has tomllib built-in
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # type: ignore

# For writing TOML, we need tomli-w or tomlkit
try:
    import tomli_w
except ImportError:
    tomli_w = None  # type: ignore


class TomlTarget(Target):
    """Target for a TOML configuration file.

    Provides operations for reading, modifying, and querying TOML files
    like pyproject.toml.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    path : str | Path
        Path to the TOML file.

    Examples
    --------
    >>> toml = rj.toml("pyproject.toml")
    >>> toml.get("project.name")
    >>> toml.set("project.version", "1.0.0")
    >>> toml.get_section("tool.black")
    """

    def __init__(self, rejig: Rejig, path: str | Path) -> None:
        super().__init__(rejig)
        self.path = Path(path) if isinstance(path, str) else path
        self._data: dict[str, Any] | None = None

    @property
    def file_path(self) -> Path:
        """Path to the TOML file."""
        return self.path

    def __repr__(self) -> str:
        return f"TomlTarget({self.path})"

    def exists(self) -> bool:
        """Check if this TOML file exists."""
        return self.path.exists() and self.path.is_file()

    def _load(self) -> dict[str, Any] | None:
        """Load and cache the TOML data."""
        if self._data is not None:
            return self._data

        if tomllib is None:
            return None

        if not self.exists():
            return None

        try:
            with open(self.path, "rb") as f:
                self._data = tomllib.load(f)
            return self._data
        except Exception:
            return None

    def _save(self, data: dict[str, Any]) -> Result:
        """Save data to the TOML file."""
        if tomli_w is None:
            return self._operation_failed(
                "save",
                "tomli-w is required to write TOML files. Install with: pip install tomli-w",
            )

        try:
            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would modify {self.path}",
                    files_changed=[self.path],
                )

            with open(self.path, "wb") as f:
                tomli_w.dump(data, f)

            self._data = data
            return Result(
                success=True,
                message=f"Modified {self.path}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("save", f"Failed to save TOML: {e}", e)

    def get_content(self) -> Result:
        """Get the raw content of the TOML file.

        Returns
        -------
        Result
            Result with file content in `data` field if successful.
        """
        if not self.exists():
            return self._operation_failed("get_content", f"File not found: {self.path}")

        try:
            content = self.path.read_text()
            return Result(success=True, message="OK", data=content)
        except Exception as e:
            return self._operation_failed("get_content", f"Failed to read file: {e}", e)

    def get_data(self) -> Result:
        """Get the parsed TOML data as a dictionary.

        Returns
        -------
        Result
            Result with parsed dict in `data` field if successful.
        """
        if tomllib is None:
            return self._operation_failed(
                "get_data",
                "tomllib (Python 3.11+) or tomli is required. Install with: pip install tomli",
            )

        data = self._load()
        if data is None:
            return self._operation_failed("get_data", f"Failed to load TOML from {self.path}")

        return Result(success=True, message="OK", data=data)

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get a value by dotted key path.

        Parameters
        ----------
        key_path : str
            Dotted path to the key (e.g., "project.name", "tool.black.line-length").
        default : Any
            Default value if key not found.

        Returns
        -------
        Any
            The value at the key path, or default if not found.

        Examples
        --------
        >>> toml.get("project.name")
        "myproject"
        >>> toml.get("tool.black.line-length", 88)
        110
        """
        data = self._load()
        if data is None:
            return default

        keys = key_path.split(".")
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def set(self, key_path: str, value: Any) -> Result:
        """Set a value by dotted key path.

        Parameters
        ----------
        key_path : str
            Dotted path to the key (e.g., "project.version").
        value : Any
            Value to set.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> toml.set("project.version", "2.0.0")
        >>> toml.set("tool.black.line-length", 110)
        """
        data = self._load()
        if data is None:
            data = {}

        keys = key_path.split(".")
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

        return self._save(data)

    def delete(self, key_path: str) -> Result:
        """Delete a key by dotted key path.

        Parameters
        ----------
        key_path : str
            Dotted path to the key to delete.

        Returns
        -------
        Result
            Result of the operation.
        """
        data = self._load()
        if data is None:
            return self._operation_failed("delete", f"Failed to load TOML from {self.path}")

        keys = key_path.split(".")
        current = data
        for key in keys[:-1]:
            if key not in current:
                return self._operation_failed("delete", f"Key path not found: {key_path}")
            current = current[key]

        if keys[-1] not in current:
            return self._operation_failed("delete", f"Key not found: {key_path}")

        del current[keys[-1]]
        return self._save(data)

    def get_section(self, section_path: str) -> dict[str, Any] | None:
        """Get a section as a dictionary.

        Parameters
        ----------
        section_path : str
            Dotted path to the section (e.g., "tool.black").

        Returns
        -------
        dict | None
            The section dictionary, or None if not found.
        """
        value = self.get(section_path)
        if isinstance(value, dict):
            return value
        return None

    def set_section(self, section_path: str, data: dict[str, Any]) -> Result:
        """Set an entire section.

        Parameters
        ----------
        section_path : str
            Dotted path to the section (e.g., "tool.ruff").
        data : dict
            Section data to set.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set(section_path, data)

    def has_key(self, key_path: str) -> bool:
        """Check if a key exists.

        Parameters
        ----------
        key_path : str
            Dotted path to check.

        Returns
        -------
        bool
            True if the key exists.
        """
        sentinel = object()
        return self.get(key_path, sentinel) is not sentinel

    def keys(self, section_path: str | None = None) -> list[str]:
        """Get keys at a section path.

        Parameters
        ----------
        section_path : str | None
            Dotted path to section, or None for root keys.

        Returns
        -------
        list[str]
            List of keys at the section.
        """
        if section_path:
            section = self.get_section(section_path)
            return list(section.keys()) if section else []
        data = self._load()
        return list(data.keys()) if data else []

    # ===== pyproject.toml specific helpers =====

    def get_project_name(self) -> str | None:
        """Get the project name from pyproject.toml."""
        return self.get("project.name")

    def get_project_version(self) -> str | None:
        """Get the project version from pyproject.toml."""
        return self.get("project.version")

    def set_project_version(self, version: str) -> Result:
        """Set the project version in pyproject.toml."""
        return self.set("project.version", version)

    def get_dependencies(self) -> list[str]:
        """Get project dependencies from pyproject.toml."""
        return self.get("project.dependencies", [])

    def add_dependency(self, dependency: str) -> Result:
        """Add a dependency to project.dependencies.

        Parameters
        ----------
        dependency : str
            Dependency specification (e.g., "requests>=2.28.0").

        Returns
        -------
        Result
            Result of the operation.
        """
        deps = self.get("project.dependencies", [])
        if dependency not in deps:
            deps.append(dependency)
            return self.set("project.dependencies", deps)
        return Result(success=True, message="Dependency already exists")

    def remove_dependency(self, package_name: str) -> Result:
        """Remove a dependency from project.dependencies.

        Parameters
        ----------
        package_name : str
            Package name to remove (version spec ignored).

        Returns
        -------
        Result
            Result of the operation.
        """
        deps = self.get("project.dependencies", [])
        new_deps = [d for d in deps if not d.lower().startswith(package_name.lower())]
        if len(new_deps) == len(deps):
            return Result(success=True, message=f"Dependency {package_name} not found")
        return self.set("project.dependencies", new_deps)

    def get_optional_dependencies(self, group: str) -> list[str]:
        """Get optional dependencies for a group."""
        return self.get(f"project.optional-dependencies.{group}", [])

    def get_tool_config(self, tool_name: str) -> dict[str, Any] | None:
        """Get configuration for a specific tool.

        Parameters
        ----------
        tool_name : str
            Tool name (e.g., "black", "ruff", "mypy").

        Returns
        -------
        dict | None
            Tool configuration, or None if not found.
        """
        return self.get_section(f"tool.{tool_name}")

    def set_tool_config(self, tool_name: str, config: dict[str, Any]) -> Result:
        """Set configuration for a specific tool.

        Parameters
        ----------
        tool_name : str
            Tool name (e.g., "black", "ruff").
        config : dict
            Tool configuration.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set_section(f"tool.{tool_name}", config)
