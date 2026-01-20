"""BlackConfigTarget - Target for [tool.black] configuration."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rejig.core.results import Result
from rejig.project.targets.tools.base import ToolConfigTarget

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class BlackConfigTarget(ToolConfigTarget):
    """Target for Black formatter configuration.

    Manages [tool.black] section in pyproject.toml.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    path : Path
        Path to pyproject.toml.

    Examples
    --------
    >>> black = pyproject.black()
    >>> black.set(line_length=110, target_version=["py310", "py311"])
    >>> black.set_line_length(110)
    >>> black.skip_string_normalization()
    """

    TOOL_NAME = "black"

    def __init__(self, rejig: Rejig, path: Path) -> None:
        super().__init__(rejig, path, "black")

    def __repr__(self) -> str:
        return f"BlackConfigTarget({self.path})"

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def line_length(self) -> int:
        """Get the line length setting."""
        return self.get_option("line-length", 88)

    @property
    def target_version(self) -> list[str]:
        """Get the target Python versions."""
        return self.get_option("target-version", [])

    @property
    def skip_string_normalization(self) -> bool:
        """Check if string normalization is skipped."""
        return self.get_option("skip-string-normalization", False)

    @property
    def extend_exclude(self) -> str:
        """Get the extend-exclude pattern."""
        return self.get_option("extend-exclude", "")

    # =========================================================================
    # Setters
    # =========================================================================

    def set_line_length(self, length: int) -> Result:
        """Set the maximum line length.

        Parameters
        ----------
        length : int
            Maximum line length.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> black.set_line_length(110)
        """
        return self.set_option("line-length", length)

    def set_target_version(self, versions: list[str]) -> Result:
        """Set the target Python versions.

        Parameters
        ----------
        versions : list[str]
            Python versions (e.g., ["py310", "py311"]).

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> black.set_target_version(["py310", "py311", "py312"])
        """
        return self.set_option("target-version", versions)

    def enable_skip_string_normalization(self) -> Result:
        """Enable skip-string-normalization."""
        return self.set_option("skip-string-normalization", True)

    def disable_skip_string_normalization(self) -> Result:
        """Disable skip-string-normalization."""
        return self.set_option("skip-string-normalization", False)

    def set_extend_exclude(self, pattern: str) -> Result:
        """Set the extend-exclude pattern.

        Parameters
        ----------
        pattern : str
            Regex pattern for files to exclude.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set_option("extend-exclude", pattern)

    def add_exclude_pattern(self, pattern: str) -> Result:
        """Add a pattern to extend-exclude.

        Parameters
        ----------
        pattern : str
            Pattern to add.

        Returns
        -------
        Result
            Result of the operation.
        """
        current = self.extend_exclude
        if current:
            new_pattern = f"{current}|{pattern}"
        else:
            new_pattern = pattern
        return self.set_extend_exclude(new_pattern)
