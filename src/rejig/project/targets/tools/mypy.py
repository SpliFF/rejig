"""MypyConfigTarget - Target for [tool.mypy] configuration."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rejig.core.results import Result
from rejig.project.targets.tools.base import ToolConfigTarget

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class MypyConfigTarget(ToolConfigTarget):
    """Target for Mypy type checker configuration.

    Manages [tool.mypy] section in pyproject.toml.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    path : Path
        Path to pyproject.toml.

    Examples
    --------
    >>> mypy = pyproject.mypy()
    >>> mypy.set(strict=True, python_version="3.10")
    >>> mypy.enable_strict()
    >>> mypy.ignore_missing_imports()
    """

    TOOL_NAME = "mypy"

    def __init__(self, rejig: Rejig, path: Path) -> None:
        super().__init__(rejig, path, "mypy")

    def __repr__(self) -> str:
        return f"MypyConfigTarget({self.path})"

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def strict(self) -> bool:
        """Check if strict mode is enabled."""
        return self.get_option("strict", False)

    @property
    def python_version(self) -> str | None:
        """Get the Python version."""
        return self.get_option("python_version")

    @property
    def ignore_missing_imports(self) -> bool:
        """Check if missing imports are ignored."""
        return self.get_option("ignore_missing_imports", False)

    @property
    def warn_return_any(self) -> bool:
        """Check if warn_return_any is enabled."""
        return self.get_option("warn_return_any", False)

    @property
    def warn_unused_configs(self) -> bool:
        """Check if warn_unused_configs is enabled."""
        return self.get_option("warn_unused_configs", False)

    @property
    def disallow_untyped_defs(self) -> bool:
        """Check if disallow_untyped_defs is enabled."""
        return self.get_option("disallow_untyped_defs", False)

    # =========================================================================
    # Setters
    # =========================================================================

    def enable_strict(self) -> Result:
        """Enable strict mode.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set_option("strict", True)

    def disable_strict(self) -> Result:
        """Disable strict mode.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set_option("strict", False)

    def set_python_version(self, version: str) -> Result:
        """Set the Python version.

        Parameters
        ----------
        version : str
            Python version (e.g., "3.10").

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set_option("python_version", version)

    def enable_ignore_missing_imports(self) -> Result:
        """Enable ignore_missing_imports.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set_option("ignore_missing_imports", True)

    def disable_ignore_missing_imports(self) -> Result:
        """Disable ignore_missing_imports.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set_option("ignore_missing_imports", False)

    def enable_warn_return_any(self) -> Result:
        """Enable warn_return_any.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set_option("warn_return_any", True)

    def enable_warn_unused_configs(self) -> Result:
        """Enable warn_unused_configs.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set_option("warn_unused_configs", True)

    def enable_disallow_untyped_defs(self) -> Result:
        """Enable disallow_untyped_defs.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set_option("disallow_untyped_defs", True)

    # =========================================================================
    # Per-module Configuration
    # =========================================================================

    def configure_module(
        self,
        module: str,
        ignore_missing_imports: bool | None = None,
        ignore_errors: bool | None = None,
        disallow_untyped_defs: bool | None = None,
    ) -> Result:
        """Configure per-module mypy settings.

        Parameters
        ----------
        module : str
            Module name pattern (e.g., "mypackage.*").
        ignore_missing_imports : bool | None
            Ignore missing imports for this module.
        ignore_errors : bool | None
            Ignore all errors for this module.
        disallow_untyped_defs : bool | None
            Disallow untyped defs for this module.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> mypy.configure_module("third_party.*", ignore_missing_imports=True)
        """
        data = self._load()
        if data is None:
            return self._operation_failed("configure_module", "Failed to load pyproject.toml")

        if "tool" not in data:
            data["tool"] = {}
        if "mypy" not in data["tool"]:
            data["tool"]["mypy"] = {}
        if "overrides" not in data["tool"]["mypy"]:
            data["tool"]["mypy"]["overrides"] = []

        # Find or create module config
        overrides = data["tool"]["mypy"]["overrides"]
        module_config = None

        for override in overrides:
            if override.get("module") == module:
                module_config = override
                break

        if module_config is None:
            module_config = {"module": module}
            overrides.append(module_config)

        if ignore_missing_imports is not None:
            module_config["ignore_missing_imports"] = ignore_missing_imports
        if ignore_errors is not None:
            module_config["ignore_errors"] = ignore_errors
        if disallow_untyped_defs is not None:
            module_config["disallow_untyped_defs"] = disallow_untyped_defs

        return self._save(data)
