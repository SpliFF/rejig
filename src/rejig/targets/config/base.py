"""Base class for configuration file targets.

This module provides a common base class for config targets (TOML, YAML, JSON)
that share similar functionality like dotted-path access.
"""
from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rejig.targets.base import Result, Target

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class ConfigTarget(Target):
    """Abstract base class for configuration file targets.

    Provides common functionality for config files that support hierarchical
    key-value storage with dotted-path access.

    Subclasses must implement:
    - _load(): Load and parse the config file
    - _save(data): Save data to the config file
    - rewrite(content): Replace file content

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    path : str | Path
        Path to the configuration file.
    """

    def __init__(self, rejig: Rejig, path: str | Path) -> None:
        super().__init__(rejig)
        self.path = Path(path) if isinstance(path, str) else path
        self._cached_data: dict[str, Any] | list[Any] | None = None

    @property
    def file_path(self) -> Path:
        """Path to the configuration file."""
        return self.path

    def exists(self) -> bool:
        """Check if this config file exists."""
        return self.path.exists() and self.path.is_file()

    @abstractmethod
    def _load(self) -> dict[str, Any] | list[Any] | None:
        """Load and cache the configuration data.

        Returns
        -------
        dict | list | None
            Parsed configuration data, or None if loading failed.
        """
        ...

    @abstractmethod
    def _save(self, data: dict[str, Any] | list[Any]) -> Result:
        """Save data to the configuration file.

        Parameters
        ----------
        data : dict | list
            Data to save.

        Returns
        -------
        Result
            Result of the operation.
        """
        ...

    def get_content(self) -> Result:
        """Get the raw content of the config file.

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
        """Get the parsed configuration data.

        Returns
        -------
        Result
            Result with parsed data in `data` field if successful.
        """
        data = self._load()
        if data is None:
            return self._operation_failed("get_data", f"Failed to load config from {self.path}")
        return Result(success=True, message="OK", data=data)

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get a value by dotted key path.

        Supports nested access using dots and list indexing with integers.

        Parameters
        ----------
        key_path : str
            Dotted path to the key (e.g., "database.host", "servers.0.name").
        default : Any
            Default value if key not found.

        Returns
        -------
        Any
            The value at the key path, or default if not found.

        Examples
        --------
        >>> config.get("database.host")
        "localhost"
        >>> config.get("database.port", 5432)
        5432
        >>> config.get("servers.0.name")
        "primary"
        """
        data = self._load()
        if data is None:
            return default

        if not isinstance(data, dict):
            return default

        return self._navigate_path(data, key_path, default)

    def _navigate_path(self, data: Any, key_path: str, default: Any = None) -> Any:
        """Navigate a dotted key path through nested data.

        Parameters
        ----------
        data : Any
            Data structure to navigate.
        key_path : str
            Dotted path to navigate.
        default : Any
            Default value if path not found.

        Returns
        -------
        Any
            Value at path or default.
        """
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

        Creates intermediate dictionaries as needed.

        Parameters
        ----------
        key_path : str
            Dotted path to the key.
        value : Any
            Value to set.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> config.set("database.host", "localhost")
        >>> config.set("database.port", 5432)
        """
        data = self._load()
        if data is None:
            data = {}

        if not isinstance(data, dict):
            return self._operation_failed("set", "Root config must be a mapping for key path access")

        keys = key_path.split(".")
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            elif not isinstance(current[key], dict):
                return self._operation_failed("set", f"Cannot set key in non-dict at {key}")
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
            return self._operation_failed("delete", f"Failed to load config from {self.path}")

        if not isinstance(data, dict):
            return self._operation_failed("delete", "Root config must be a mapping")

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
            Dotted path to the section.

        Returns
        -------
        dict | None
            The section dictionary, or None if not found or not a dict.
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
            Dotted path to the section.
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
        if isinstance(data, dict):
            return list(data.keys())
        return []

    def merge(self, other: dict[str, Any], deep: bool = True) -> Result:
        """Merge another dictionary into this config.

        Parameters
        ----------
        other : dict
            Dictionary to merge in.
        deep : bool
            If True, perform deep merge. If False, shallow merge.

        Returns
        -------
        Result
            Result of the operation.
        """
        data = self._load()
        if data is None:
            data = {}

        if not isinstance(data, dict):
            return self._operation_failed("merge", "Root config must be a mapping")

        if deep:
            self._deep_merge(data, other)
        else:
            data.update(other)

        return self._save(data)

    def _deep_merge(self, base: dict, other: dict) -> None:
        """Deep merge other into base (modifies base in place).

        Parameters
        ----------
        base : dict
            Base dictionary to merge into.
        other : dict
            Dictionary to merge from.
        """
        for key, value in other.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    # ===== List operations =====

    def append_to_list(self, key_path: str, value: Any) -> Result:
        """Append a value to a list at the specified key path.

        Parameters
        ----------
        key_path : str
            Dotted path to the list.
        value : Any
            Value to append.

        Returns
        -------
        Result
            Result of the operation.
        """
        current = self.get(key_path, [])
        if not isinstance(current, list):
            return self._operation_failed("append_to_list", f"{key_path} is not a list")

        current.append(value)
        return self.set(key_path, current)

    def remove_from_list(self, key_path: str, value: Any) -> Result:
        """Remove a value from a list at the specified key path.

        Parameters
        ----------
        key_path : str
            Dotted path to the list.
        value : Any
            Value to remove.

        Returns
        -------
        Result
            Result of the operation.
        """
        current = self.get(key_path, [])
        if not isinstance(current, list):
            return self._operation_failed("remove_from_list", f"{key_path} is not a list")

        if value not in current:
            return Result(success=True, message=f"Value not found in {key_path}")

        current.remove(value)
        return self.set(key_path, current)

    def clear_cache(self) -> None:
        """Clear the cached configuration data.

        Call this if the file has been modified externally.
        """
        self._cached_data = None
