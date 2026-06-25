"""TomlTarget for operations on TOML configuration files."""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rejig.targets.base import Result, Target
from rejig.targets.config.base import normalize_key_path
from rejig._tomlkit_io import TomlError, dump_toml, load_toml, loads_toml, toml_available

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


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

        if not toml_available():
            return None

        if not self.exists():
            return None

        try:
            self._data = load_toml(self.path)
            return self._data
        except (OSError, TomlError):
            return None

    def _save(self, data: dict[str, Any]) -> Result:
        """Save data to the TOML file."""
        if not toml_available():
            return self._operation_failed(
                "save",
                "tomlkit is required to write TOML files. Install with: pip install tomlkit",
            )

        try:
            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would modify {self.path}",
                    files_changed=[self.path],
                )

            dump_toml(data, self.path)

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
        if not toml_available():
            return self._operation_failed(
                "get_data",
                "tomlkit is required to read TOML files. Install with: pip install tomlkit",
            )

        data = self._load()
        if data is None:
            return self._operation_failed("get_data", f"Failed to load TOML from {self.path}")

        return Result(success=True, message="OK", data=data)

    def get(self, key_path: str | Sequence[str], default: Any = None) -> Any:
        """Get a value by key path.

        Parameters
        ----------
        key_path : str | Sequence[str]
            Path to the key: a dotted string (``"project.name"``,
            ``"tool.black.line-length"``), a list of literal segments
            (``["tool", "black", "line-length"]``), or a :class:`KeyPath` built
            with ``/`` (``KeyPath("tool") / "black" / "line-length"`` — use this
            when a key contains a literal ``.``).
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

        keys = normalize_key_path(key_path)
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def set(self, key_path: str | Sequence[str], value: Any) -> Result:
        """Set a value by key path.

        Parameters
        ----------
        key_path : str | Sequence[str]
            Path to the key: a dotted string (``"project.version"``), a list of
            literal segments, or a :class:`KeyPath` built with ``/``.
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

        keys = normalize_key_path(key_path)
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

        return self._save(data)

    def delete(self, key_path: str | Sequence[str]) -> Result:
        """Delete a key by key path.

        Parameters
        ----------
        key_path : str | Sequence[str]
            Path to the key to delete: a dotted string, a list of literal
            segments, or a :class:`KeyPath` built with ``/``.

        Returns
        -------
        Result
            Result of the operation.
        """
        data = self._load()
        if data is None:
            return self._operation_failed("delete", f"Failed to load TOML from {self.path}")

        keys = normalize_key_path(key_path)
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

    def rewrite(self, new_content: str) -> Result:
        """Replace the entire content of the TOML file.

        Validates the content is valid TOML before writing.

        Parameters
        ----------
        new_content : str
            New TOML content.

        Returns
        -------
        Result
            Result of the operation.
        """
        if not toml_available():
            return self._operation_failed(
                "rewrite",
                "tomlkit is required to read TOML files. Install with: pip install tomlkit",
            )

        try:
            # Validate TOML by parsing it
            data = loads_toml(new_content)
            return self._save(data)
        except Exception as e:
            return self._operation_failed("rewrite", f"Invalid TOML: {e}", e)
