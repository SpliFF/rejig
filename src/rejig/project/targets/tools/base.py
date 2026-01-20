"""ToolConfigTarget - Base target for tool configurations in pyproject.toml."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from rejig.core.results import Result
from rejig.targets.config.toml import TomlTarget

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class ToolConfigTarget(TomlTarget):
    """Base target for tool configuration in pyproject.toml [tool.*] sections.

    Provides common functionality for reading and writing tool configurations.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    path : Path
        Path to pyproject.toml.
    tool_name : str
        Name of the tool (e.g., "black", "ruff", "mypy").

    Examples
    --------
    >>> tool = ToolConfigTarget(rj, path, "black")
    >>> tool.get_config()
    {'line-length': 110}
    >>> tool.set(line_length=110)
    """

    # Subclasses should set this
    TOOL_NAME: str = ""

    def __init__(self, rejig: Rejig, path: Path, tool_name: str | None = None) -> None:
        super().__init__(rejig, path)
        self._tool_name = tool_name or self.TOOL_NAME

    def __repr__(self) -> str:
        return f"ToolConfigTarget({self.path}, tool={self._tool_name!r})"

    @property
    def tool_name(self) -> str:
        """The tool name."""
        return self._tool_name

    @property
    def key_path(self) -> str:
        """The dotted key path for this tool's config."""
        return f"tool.{self._tool_name}"

    # =========================================================================
    # Read Operations
    # =========================================================================

    def get_config(self) -> dict[str, Any]:
        """Get the entire tool configuration.

        Returns
        -------
        dict
            Tool configuration dictionary.

        Examples
        --------
        >>> config = tool.get_config()
        >>> print(config)
        """
        return self.get(self.key_path, {})

    def get_option(self, option: str, default: Any = None) -> Any:
        """Get a specific configuration option.

        Parameters
        ----------
        option : str
            Option name (can be dotted for nested keys).
        default : Any
            Default value if not found.

        Returns
        -------
        Any
            Option value, or default if not found.

        Examples
        --------
        >>> tool.get_option("line-length", 88)
        110
        """
        return self.get(f"{self.key_path}.{option}", default)

    def has_config(self) -> bool:
        """Check if this tool has any configuration."""
        return self.has_key(self.key_path)

    # =========================================================================
    # Write Operations
    # =========================================================================

    def set_config(self, config: dict[str, Any]) -> Result:
        """Set the entire tool configuration.

        Parameters
        ----------
        config : dict
            Tool configuration dictionary.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> tool.set_config({"line-length": 110, "target-version": ["py310"]})
        """
        return self.set(self.key_path, config)

    def set_option(self, option: str, value: Any) -> Result:
        """Set a specific configuration option.

        Parameters
        ----------
        option : str
            Option name (can be dotted for nested keys).
        value : Any
            Option value.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> tool.set_option("line-length", 110)
        """
        return self.set(f"{self.key_path}.{option}", value)

    def update_config(self, **options: Any) -> Result:
        """Update configuration with multiple options.

        Parameters
        ----------
        **options : Any
            Configuration options to set. Underscores in names
            are converted to hyphens.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> tool.update_config(line_length=110, target_version=["py310"])
        """
        data = self._load()
        if data is None:
            return self._operation_failed("update_config", "Failed to load pyproject.toml")

        # Ensure tool section exists
        if "tool" not in data:
            data["tool"] = {}
        if self._tool_name not in data["tool"]:
            data["tool"][self._tool_name] = {}

        tool_config = data["tool"][self._tool_name]

        # Update options, converting underscores to hyphens
        for key, value in options.items():
            key = key.replace("_", "-")
            tool_config[key] = value

        return self._save(data)

    def remove_option(self, option: str) -> Result:
        """Remove a configuration option.

        Parameters
        ----------
        option : str
            Option name to remove.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.delete(f"{self.key_path}.{option}")

    def clear(self) -> Result:
        """Remove all tool configuration.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.delete(self.key_path)

    # =========================================================================
    # Fluent API
    # =========================================================================

    def set(self, **options: Any) -> Result:  # type: ignore[override]
        """Fluent API to set configuration options.

        Parameters
        ----------
        **options : Any
            Configuration options. Underscores in names are
            converted to hyphens.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> tool.set(line_length=110, target_version=["py310"])
        """
        return self.update_config(**options)
