"""YamlTarget for operations on YAML configuration files."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from rejig.targets.base import Result, Target

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig

# Try to import PyYAML
try:
    import yaml

    HAS_YAML = True
except ImportError:
    yaml = None  # type: ignore
    HAS_YAML = False


class YamlTarget(Target):
    """Target for a YAML configuration file.

    Provides operations for reading, modifying, and querying YAML files.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    path : str | Path
        Path to the YAML file.

    Examples
    --------
    >>> yaml_file = rj.yaml("config.yaml")
    >>> yaml_file.get("database.host")
    >>> yaml_file.set("database.port", 5432)
    """

    def __init__(self, rejig: Rejig, path: str | Path) -> None:
        super().__init__(rejig)
        self.path = Path(path) if isinstance(path, str) else path
        self._data: dict[str, Any] | list[Any] | None = None

    @property
    def file_path(self) -> Path:
        """Path to the YAML file."""
        return self.path

    def __repr__(self) -> str:
        return f"YamlTarget({self.path})"

    def exists(self) -> bool:
        """Check if this YAML file exists."""
        return self.path.exists() and self.path.is_file()

    def _load(self) -> dict[str, Any] | list[Any] | None:
        """Load and cache the YAML data."""
        if self._data is not None:
            return self._data

        if not HAS_YAML:
            return None

        if not self.exists():
            return None

        try:
            with open(self.path) as f:
                self._data = yaml.safe_load(f)
            return self._data
        except Exception:
            return None

    def _save(self, data: dict[str, Any] | list[Any]) -> Result:
        """Save data to the YAML file."""
        if not HAS_YAML:
            return self._operation_failed(
                "save",
                "PyYAML is required to write YAML files. Install with: pip install pyyaml",
            )

        try:
            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would modify {self.path}",
                    files_changed=[self.path],
                )

            with open(self.path, "w") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

            self._data = data
            return Result(
                success=True,
                message=f"Modified {self.path}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("save", f"Failed to save YAML: {e}", e)

    def get_content(self) -> Result:
        """Get the raw content of the YAML file.

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
        """Get the parsed YAML data.

        Returns
        -------
        Result
            Result with parsed data in `data` field if successful.
        """
        if not HAS_YAML:
            return self._operation_failed(
                "get_data",
                "PyYAML is required. Install with: pip install pyyaml",
            )

        data = self._load()
        if data is None:
            return self._operation_failed("get_data", f"Failed to load YAML from {self.path}")

        return Result(success=True, message="OK", data=data)

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get a value by dotted key path.

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
        >>> yaml_file.get("database.host")
        "localhost"
        >>> yaml_file.get("database.port", 5432)
        5432
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
            Dotted path to the key (e.g., "database.host").
        value : Any
            Value to set.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> yaml_file.set("database.host", "localhost")
        >>> yaml_file.set("database.port", 5432)
        """
        data = self._load()
        if data is None:
            data = {}

        if not isinstance(data, dict):
            return self._operation_failed("set", "Root YAML must be a mapping for key path access")

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
            return self._operation_failed("delete", f"Failed to load YAML from {self.path}")

        if not isinstance(data, dict):
            return self._operation_failed("delete", "Root YAML must be a mapping")

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

    def rewrite(self, new_content: str) -> Result:
        """Replace the entire content of the YAML file.

        Parameters
        ----------
        new_content : str
            New YAML content.

        Returns
        -------
        Result
            Result of the operation.
        """
        if not HAS_YAML:
            return self._operation_failed(
                "rewrite",
                "PyYAML is required. Install with: pip install pyyaml",
            )

        try:
            # Validate YAML
            data = yaml.safe_load(new_content)
            return self._save(data)
        except yaml.YAMLError as e:
            return self._operation_failed("rewrite", f"Invalid YAML: {e}", e)

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
