"""JsonTarget for operations on JSON configuration files."""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rejig.targets.base import Result, Target

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class JsonTarget(Target):
    """Target for a JSON configuration file.

    Provides operations for reading, modifying, and querying JSON files.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    path : str | Path
        Path to the JSON file.

    Examples
    --------
    >>> json_file = rj.json("package.json")
    >>> json_file.get("name")
    >>> json_file.set("version", "1.0.0")
    """

    def __init__(self, rejig: Rejig, path: str | Path) -> None:
        super().__init__(rejig)
        self.path = Path(path) if isinstance(path, str) else path
        self._data: dict[str, Any] | list[Any] | None = None

    @property
    def file_path(self) -> Path:
        """Path to the JSON file."""
        return self.path

    def __repr__(self) -> str:
        return f"JsonTarget({self.path})"

    def exists(self) -> bool:
        """Check if this JSON file exists."""
        return self.path.exists() and self.path.is_file()

    def _load(self) -> dict[str, Any] | list[Any] | None:
        """Load and cache the JSON data."""
        if self._data is not None:
            return self._data

        if not self.exists():
            return None

        try:
            content = self.path.read_text()
            self._data = json.loads(content)
            return self._data
        except Exception:
            return None

    def _save(self, data: dict[str, Any] | list[Any], indent: int = 2) -> Result:
        """Save data to the JSON file."""
        try:
            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would modify {self.path}",
                    files_changed=[self.path],
                )

            content = json.dumps(data, indent=indent, ensure_ascii=False)
            self.path.write_text(content + "\n")

            self._data = data
            return Result(
                success=True,
                message=f"Modified {self.path}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("save", f"Failed to save JSON: {e}", e)

    def get_content(self) -> Result:
        """Get the raw content of the JSON file.

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
        """Get the parsed JSON data.

        Returns
        -------
        Result
            Result with parsed data in `data` field if successful.
        """
        data = self._load()
        if data is None:
            return self._operation_failed("get_data", f"Failed to load JSON from {self.path}")

        return Result(success=True, message="OK", data=data)

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get a value by dotted key path.

        Parameters
        ----------
        key_path : str
            Dotted path to the key (e.g., "scripts.build", "dependencies.react").
        default : Any
            Default value if key not found.

        Returns
        -------
        Any
            The value at the key path, or default if not found.

        Examples
        --------
        >>> json_file.get("name")
        "my-project"
        >>> json_file.get("scripts.test", "npm test")
        """
        data = self._load()
        if data is None:
            return default

        if not isinstance(data, dict):
            return default

        keys = key_path.split(".")
        current: Any = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            elif isinstance(current, list):
                try:
                    idx = int(key)
                    current = current[idx]
                except (ValueError, IndexError):
                    return default
            else:
                return default
        return current

    def set(self, key_path: str, value: Any) -> Result:
        """Set a value by dotted key path.

        Parameters
        ----------
        key_path : str
            Dotted path to the key (e.g., "version", "scripts.build").
        value : Any
            Value to set.

        Returns
        -------
        Result
            Result of the operation.
        """
        data = self._load()
        if data is None:
            data = {}

        if not isinstance(data, dict):
            return self._operation_failed("set", "Root JSON must be an object for key path access")

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
            return self._operation_failed("delete", f"Failed to load JSON from {self.path}")

        if not isinstance(data, dict):
            return self._operation_failed("delete", "Root JSON must be an object")

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
            section = self.get(section_path)
            if isinstance(section, dict):
                return list(section.keys())
            return []
        data = self._load()
        if isinstance(data, dict):
            return list(data.keys())
        return []

    def rewrite(self, new_content: str) -> Result:
        """Replace the entire content of the JSON file.

        Parameters
        ----------
        new_content : str
            New JSON content.

        Returns
        -------
        Result
            Result of the operation.
        """
        try:
            # Validate JSON
            data = json.loads(new_content)
            return self._save(data)
        except json.JSONDecodeError as e:
            return self._operation_failed("rewrite", f"Invalid JSON: {e}", e)

    # ===== package.json specific helpers =====

    def get_package_name(self) -> str | None:
        """Get the package name (for package.json)."""
        return self.get("name")

    def get_package_version(self) -> str | None:
        """Get the package version (for package.json)."""
        return self.get("version")

    def set_package_version(self, version: str) -> Result:
        """Set the package version (for package.json)."""
        return self.set("version", version)

    def get_scripts(self) -> dict[str, str]:
        """Get scripts (for package.json)."""
        return self.get("scripts", {})

    def add_script(self, name: str, command: str) -> Result:
        """Add a script (for package.json)."""
        scripts = self.get("scripts", {})
        scripts[name] = command
        return self.set("scripts", scripts)
