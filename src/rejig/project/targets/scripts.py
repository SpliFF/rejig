"""ScriptsTarget - Target for managing pyproject.toml scripts."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rejig.core.results import Result
from rejig.targets.config.toml import TomlTarget

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class ScriptsTarget(TomlTarget):
    """Target for managing scripts/entry points in pyproject.toml.

    Handles both PEP 621 format (project.scripts) and Poetry format
    (tool.poetry.scripts).

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    path : Path
        Path to pyproject.toml.
    section : str
        Script section: "scripts" (default) or "gui-scripts".

    Examples
    --------
    >>> scripts = pyproject.scripts()
    >>> scripts.add("mycli", "mypackage.cli:main")
    >>> scripts.remove("old-command")
    >>> scripts.rename("old-cli", "new-cli")
    """

    def __init__(
        self,
        rejig: Rejig,
        path: Path,
        section: str = "scripts",
    ) -> None:
        super().__init__(rejig, path)
        self._section = section

    def __repr__(self) -> str:
        return f"ScriptsTarget({self.path}, section={self._section!r})"

    def _get_key_path(self) -> str:
        """Get the dotted key path for this scripts section."""
        data = self._load()
        if data is None:
            return f"project.{self._section}"

        # Check format
        is_poetry = "tool" in data and "poetry" in data.get("tool", {})

        if is_poetry:
            return f"tool.poetry.{self._section}"
        else:
            return f"project.{self._section}"

    # =========================================================================
    # Read Operations
    # =========================================================================

    def list(self) -> dict[str, str]:
        """List all scripts.

        Returns
        -------
        dict[str, str]
            Dictionary mapping script names to entry points.

        Examples
        --------
        >>> for name, entry_point in scripts.list().items():
        ...     print(f"{name} = {entry_point}")
        """
        key_path = self._get_key_path()
        value = self.get(key_path)
        return dict(value) if isinstance(value, dict) else {}

    def has(self, name: str) -> bool:
        """Check if a script exists.

        Parameters
        ----------
        name : str
            Script name.

        Returns
        -------
        bool
            True if script exists.
        """
        return name in self.list()

    def get_entry_point(self, name: str) -> str | None:
        """Get the entry point for a script.

        Parameters
        ----------
        name : str
            Script name.

        Returns
        -------
        str | None
            Entry point, or None if not found.
        """
        return self.list().get(name)

    # =========================================================================
    # Write Operations
    # =========================================================================

    def add(self, name: str, entry_point: str) -> Result:
        """Add a script.

        Parameters
        ----------
        name : str
            Script name (the command users will run).
        entry_point : str
            Entry point (e.g., "package.module:function").

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> scripts.add("mycli", "mypackage.cli:main")
        >>> scripts.add("serve", "mypackage.server:run")
        """
        data = self._load()
        if data is None:
            return self._operation_failed("add", "Failed to load pyproject.toml")

        key_path = self._get_key_path()

        # Ensure section exists
        keys = key_path.split(".")
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        final_key = keys[-1]
        if final_key not in current:
            current[final_key] = {}

        current[final_key][name] = entry_point
        return self._save(data)

    def remove(self, name: str) -> Result:
        """Remove a script.

        Parameters
        ----------
        name : str
            Script name to remove.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> scripts.remove("old-command")
        """
        if not self.has(name):
            return Result(success=True, message=f"Script {name} not found")

        data = self._load()
        if data is None:
            return self._operation_failed("remove", "Failed to load pyproject.toml")

        key_path = self._get_key_path()

        # Navigate to section
        keys = key_path.split(".")
        current = data
        for key in keys[:-1]:
            if key not in current:
                return Result(success=True, message=f"Script {name} not found")
            current = current[key]

        final_key = keys[-1]
        if final_key in current and name in current[final_key]:
            del current[final_key][name]

        return self._save(data)

    def update(self, name: str, entry_point: str) -> Result:
        """Update a script's entry point.

        Parameters
        ----------
        name : str
            Script name.
        entry_point : str
            New entry point.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> scripts.update("mycli", "mypackage.cli:new_main")
        """
        return self.add(name, entry_point)

    def rename(self, old_name: str, new_name: str) -> Result:
        """Rename a script.

        Parameters
        ----------
        old_name : str
            Current script name.
        new_name : str
            New script name.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> scripts.rename("old-cli", "new-cli")
        """
        entry_point = self.get_entry_point(old_name)
        if entry_point is None:
            return self._operation_failed("rename", f"Script {old_name} not found")

        self.remove(old_name)
        return self.add(new_name, entry_point)

    def clear(self) -> Result:
        """Remove all scripts.

        Returns
        -------
        Result
            Result of the operation.
        """
        data = self._load()
        if data is None:
            return self._operation_failed("clear", "Failed to load pyproject.toml")

        key_path = self._get_key_path()

        # Navigate to section
        keys = key_path.split(".")
        current = data
        for key in keys[:-1]:
            if key not in current:
                return Result(success=True, message="Scripts section is empty")
            current = current[key]

        final_key = keys[-1]
        if final_key in current:
            current[final_key] = {}

        return self._save(data)

    # =========================================================================
    # Bulk Operations
    # =========================================================================

    def add_many(self, scripts: dict[str, str]) -> Result:
        """Add multiple scripts at once.

        Parameters
        ----------
        scripts : dict[str, str]
            Dictionary mapping script names to entry points.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> scripts.add_many({
        ...     "mycli": "mypackage.cli:main",
        ...     "serve": "mypackage.server:run",
        ...     "worker": "mypackage.worker:start",
        ... })
        """
        data = self._load()
        if data is None:
            return self._operation_failed("add_many", "Failed to load pyproject.toml")

        key_path = self._get_key_path()

        # Ensure section exists
        keys = key_path.split(".")
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        final_key = keys[-1]
        if final_key not in current:
            current[final_key] = {}

        current[final_key].update(scripts)
        return self._save(data)
