"""IniTarget for operations on INI/CFG configuration files."""
from __future__ import annotations

import configparser
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rejig.targets.base import Result, Target

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class IniTarget(Target):
    """Target for an INI or CFG configuration file.

    Provides operations for reading, modifying, and querying INI/CFG files
    using Python's configparser.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    path : str | Path
        Path to the INI/CFG file.

    Examples
    --------
    >>> ini = rj.ini("setup.cfg")
    >>> ini.get("metadata", "name")
    >>> ini.set("metadata", "version", "1.0.0")
    """

    def __init__(self, rejig: Rejig, path: str | Path) -> None:
        super().__init__(rejig)
        self.path = Path(path) if isinstance(path, str) else path
        self._config: configparser.ConfigParser | None = None

    @property
    def file_path(self) -> Path:
        """Path to the INI file."""
        return self.path

    def __repr__(self) -> str:
        return f"IniTarget({self.path})"

    def exists(self) -> bool:
        """Check if this INI file exists."""
        return self.path.exists() and self.path.is_file()

    def _load(self) -> configparser.ConfigParser | None:
        """Load and cache the INI data."""
        if self._config is not None:
            return self._config

        if not self.exists():
            return None

        try:
            self._config = configparser.ConfigParser()
            self._config.read(self.path)
            return self._config
        except Exception:
            return None

    def _save(self) -> Result:
        """Save the config to the INI file."""
        if self._config is None:
            return self._operation_failed("save", "No config loaded")

        try:
            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would modify {self.path}",
                    files_changed=[self.path],
                )

            with open(self.path, "w") as f:
                self._config.write(f)

            return Result(
                success=True,
                message=f"Modified {self.path}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("save", f"Failed to save INI: {e}", e)

    def get_content(self) -> Result:
        """Get the raw content of the INI file.

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
        """Get the parsed INI data as a nested dictionary.

        Returns
        -------
        Result
            Result with parsed dict in `data` field if successful.
            The dict has section names as keys and section data dicts as values.

        Examples
        --------
        >>> result = ini.get_data()
        >>> if result.success:
        ...     for section, values in result.data.items():
        ...         print(f"[{section}]")
        """
        config = self._load()
        if config is None:
            return self._operation_failed("get_data", f"Failed to load INI from {self.path}")

        # Convert ConfigParser to nested dict
        data: dict[str, dict[str, str]] = {}
        for section in config.sections():
            data[section] = dict(config.items(section))

        return Result(success=True, message="OK", data=data)

    def get(self, section: str, key: str, default: str | None = None) -> str | None:
        """Get a value from a section.

        Parameters
        ----------
        section : str
            Section name.
        key : str
            Key name within the section.
        default : str | None
            Default value if key not found.

        Returns
        -------
        str | None
            The value, or default if not found.

        Examples
        --------
        >>> ini.get("metadata", "name")
        "my-project"
        >>> ini.get("metadata", "license", "MIT")
        """
        config = self._load()
        if config is None:
            return default

        try:
            return config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default

    def get_int(self, section: str, key: str, default: int = 0) -> int:
        """Get an integer value from a section.

        Parameters
        ----------
        section : str
            Section name.
        key : str
            Key name within the section.
        default : int
            Default value if key not found.

        Returns
        -------
        int
            The integer value.
        """
        config = self._load()
        if config is None:
            return default

        try:
            return config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default

    def get_float(self, section: str, key: str, default: float = 0.0) -> float:
        """Get a float value from a section.

        Parameters
        ----------
        section : str
            Section name.
        key : str
            Key name within the section.
        default : float
            Default value if key not found.

        Returns
        -------
        float
            The float value.
        """
        config = self._load()
        if config is None:
            return default

        try:
            return config.getfloat(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default

    def get_bool(self, section: str, key: str, default: bool = False) -> bool:
        """Get a boolean value from a section.

        Parameters
        ----------
        section : str
            Section name.
        key : str
            Key name within the section.
        default : bool
            Default value if key not found.

        Returns
        -------
        bool
            The boolean value.
        """
        config = self._load()
        if config is None:
            return default

        try:
            return config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default

    def set(self, section: str, key: str, value: str) -> Result:
        """Set a value in a section.

        Parameters
        ----------
        section : str
            Section name.
        key : str
            Key name within the section.
        value : str
            Value to set.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> ini.set("metadata", "version", "2.0.0")
        """
        config = self._load()
        if config is None:
            config = configparser.ConfigParser()
            self._config = config

        if not config.has_section(section):
            config.add_section(section)

        config.set(section, key, str(value))
        return self._save()

    def delete_key(self, section: str, key: str) -> Result:
        """Delete a key from a section.

        Parameters
        ----------
        section : str
            Section name.
        key : str
            Key to delete.

        Returns
        -------
        Result
            Result of the operation.
        """
        config = self._load()
        if config is None:
            return self._operation_failed("delete_key", f"Failed to load INI from {self.path}")

        try:
            if not config.has_option(section, key):
                return Result(success=True, message=f"Key {key} not found in [{section}]")

            config.remove_option(section, key)
            return self._save()
        except configparser.NoSectionError:
            return self._operation_failed("delete_key", f"Section [{section}] not found")

    def delete_section(self, section: str) -> Result:
        """Delete an entire section.

        Parameters
        ----------
        section : str
            Section name to delete.

        Returns
        -------
        Result
            Result of the operation.
        """
        config = self._load()
        if config is None:
            return self._operation_failed("delete_section", f"Failed to load INI from {self.path}")

        if not config.has_section(section):
            return Result(success=True, message=f"Section [{section}] not found")

        config.remove_section(section)
        return self._save()

    def has_section(self, section: str) -> bool:
        """Check if a section exists.

        Parameters
        ----------
        section : str
            Section name to check.

        Returns
        -------
        bool
            True if section exists.
        """
        config = self._load()
        if config is None:
            return False
        return config.has_section(section)

    def has_key(self, section: str, key: str) -> bool:
        """Check if a key exists in a section.

        Parameters
        ----------
        section : str
            Section name.
        key : str
            Key name.

        Returns
        -------
        bool
            True if key exists.
        """
        config = self._load()
        if config is None:
            return False
        return config.has_option(section, key)

    def sections(self) -> list[str]:
        """Get all section names.

        Returns
        -------
        list[str]
            List of section names.
        """
        config = self._load()
        if config is None:
            return []
        return config.sections()

    def keys(self, section: str) -> list[str]:
        """Get all keys in a section.

        Parameters
        ----------
        section : str
            Section name.

        Returns
        -------
        list[str]
            List of keys in the section.
        """
        config = self._load()
        if config is None:
            return []

        try:
            return list(config.options(section))
        except configparser.NoSectionError:
            return []

    def get_section(self, section: str) -> dict[str, str]:
        """Get all key-value pairs in a section.

        Parameters
        ----------
        section : str
            Section name.

        Returns
        -------
        dict[str, str]
            Dictionary of key-value pairs.
        """
        config = self._load()
        if config is None:
            return {}

        try:
            return dict(config.items(section))
        except configparser.NoSectionError:
            return {}

    def set_section(self, section: str, data: dict[str, str]) -> Result:
        """Set all key-value pairs in a section.

        Parameters
        ----------
        section : str
            Section name.
        data : dict[str, str]
            Key-value pairs to set.

        Returns
        -------
        Result
            Result of the operation.
        """
        config = self._load()
        if config is None:
            config = configparser.ConfigParser()
            self._config = config

        # Remove existing section if present
        if config.has_section(section):
            config.remove_section(section)

        config.add_section(section)
        for key, value in data.items():
            config.set(section, key, str(value))

        return self._save()

    def add_section(self, section: str) -> Result:
        """Add a new section.

        Parameters
        ----------
        section : str
            Section name to add.

        Returns
        -------
        Result
            Result of the operation.
        """
        config = self._load()
        if config is None:
            config = configparser.ConfigParser()
            self._config = config

        if config.has_section(section):
            return Result(success=True, message=f"Section [{section}] already exists")

        config.add_section(section)
        return self._save()

    def rewrite(self, new_content: str) -> Result:
        """Replace the entire content of the INI file.

        Parameters
        ----------
        new_content : str
            New INI content.

        Returns
        -------
        Result
            Result of the operation.
        """
        try:
            # Validate INI format
            config = configparser.ConfigParser()
            config.read_string(new_content)

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would modify {self.path}",
                    files_changed=[self.path],
                )

            self.path.write_text(new_content)
            self._config = config
            return Result(
                success=True,
                message=f"Modified {self.path}",
                files_changed=[self.path],
            )
        except configparser.Error as e:
            return self._operation_failed("rewrite", f"Invalid INI format: {e}", e)
