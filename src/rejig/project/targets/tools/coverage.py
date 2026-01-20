"""CoverageConfigTarget - Target for [tool.coverage] configuration."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rejig.core.results import Result
from rejig.project.targets.tools.base import ToolConfigTarget

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class CoverageConfigTarget(ToolConfigTarget):
    """Target for coverage.py configuration.

    Manages [tool.coverage] section in pyproject.toml.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    path : Path
        Path to pyproject.toml.

    Examples
    --------
    >>> coverage = pyproject.coverage()
    >>> coverage.set_source(["src"])
    >>> coverage.set_fail_under(80)
    >>> coverage.exclude_lines(["pragma: no cover", "if TYPE_CHECKING:"])
    """

    TOOL_NAME = "coverage"

    def __init__(self, rejig: Rejig, path: Path) -> None:
        super().__init__(rejig, path, "coverage")

    def __repr__(self) -> str:
        return f"CoverageConfigTarget({self.path})"

    # =========================================================================
    # Run Configuration
    # =========================================================================

    @property
    def source(self) -> list[str]:
        """Get the source directories."""
        return self.get_option("run.source", [])

    @property
    def branch(self) -> bool:
        """Check if branch coverage is enabled."""
        return self.get_option("run.branch", False)

    @property
    def omit(self) -> list[str]:
        """Get omitted patterns."""
        return self.get_option("run.omit", [])

    def set_source(self, paths: list[str]) -> Result:
        """Set the source directories.

        Parameters
        ----------
        paths : list[str]
            Source directories (e.g., ["src"]).

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> coverage.set_source(["src", "mypackage"])
        """
        return self.set_option("run.source", paths)

    def enable_branch(self) -> Result:
        """Enable branch coverage.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set_option("run.branch", True)

    def disable_branch(self) -> Result:
        """Disable branch coverage.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set_option("run.branch", False)

    def set_omit(self, patterns: list[str]) -> Result:
        """Set patterns to omit from coverage.

        Parameters
        ----------
        patterns : list[str]
            Patterns to omit.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> coverage.set_omit(["**/tests/**", "**/conftest.py"])
        """
        return self.set_option("run.omit", patterns)

    def add_omit(self, pattern: str) -> Result:
        """Add a pattern to omit.

        Parameters
        ----------
        pattern : str
            Pattern to add.

        Returns
        -------
        Result
            Result of the operation.
        """
        patterns = self.omit
        if pattern not in patterns:
            patterns.append(pattern)
            return self.set_omit(patterns)
        return Result(success=True, message=f"Pattern {pattern} already omitted")

    # =========================================================================
    # Report Configuration
    # =========================================================================

    @property
    def fail_under(self) -> float | None:
        """Get the fail-under threshold."""
        return self.get_option("report.fail_under")

    @property
    def exclude_lines(self) -> list[str]:
        """Get excluded line patterns."""
        return self.get_option("report.exclude_lines", [])

    @property
    def show_missing(self) -> bool:
        """Check if show_missing is enabled."""
        return self.get_option("report.show_missing", False)

    def set_fail_under(self, threshold: float) -> Result:
        """Set the minimum coverage threshold.

        Parameters
        ----------
        threshold : float
            Minimum coverage percentage (0-100).

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> coverage.set_fail_under(80)
        """
        return self.set_option("report.fail_under", threshold)

    def set_exclude_lines(self, patterns: list[str]) -> Result:
        """Set patterns for lines to exclude from coverage.

        Parameters
        ----------
        patterns : list[str]
            Regex patterns.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> coverage.set_exclude_lines([
        ...     "pragma: no cover",
        ...     "if TYPE_CHECKING:",
        ...     "raise NotImplementedError",
        ... ])
        """
        return self.set_option("report.exclude_lines", patterns)

    def add_exclude_line(self, pattern: str) -> Result:
        """Add a pattern for lines to exclude.

        Parameters
        ----------
        pattern : str
            Regex pattern.

        Returns
        -------
        Result
            Result of the operation.
        """
        patterns = self.exclude_lines
        if pattern not in patterns:
            patterns.append(pattern)
            return self.set_exclude_lines(patterns)
        return Result(success=True, message="Pattern already excluded")

    def enable_show_missing(self) -> Result:
        """Enable show_missing in reports.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set_option("report.show_missing", True)

    # =========================================================================
    # HTML Report Configuration
    # =========================================================================

    def set_html_directory(self, directory: str) -> Result:
        """Set the HTML report output directory.

        Parameters
        ----------
        directory : str
            Output directory.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> coverage.set_html_directory("htmlcov")
        """
        return self.set_option("html.directory", directory)

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def configure_standard(
        self,
        source: list[str],
        fail_under: float = 80,
        branch: bool = True,
    ) -> Result:
        """Configure coverage with standard settings.

        Parameters
        ----------
        source : list[str]
            Source directories.
        fail_under : float
            Minimum coverage threshold.
        branch : bool
            Enable branch coverage.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> coverage.configure_standard(["src"], fail_under=90)
        """
        data = self._load()
        if data is None:
            return self._operation_failed("configure_standard", "Failed to load pyproject.toml")

        if "tool" not in data:
            data["tool"] = {}
        if "coverage" not in data["tool"]:
            data["tool"]["coverage"] = {}

        coverage = data["tool"]["coverage"]

        # Run config
        coverage["run"] = {
            "source": source,
            "branch": branch,
        }

        # Report config
        coverage["report"] = {
            "fail_under": fail_under,
            "show_missing": True,
            "exclude_lines": [
                "pragma: no cover",
                "if TYPE_CHECKING:",
                "raise NotImplementedError",
                "@abstractmethod",
            ],
        }

        return self._save(data)
