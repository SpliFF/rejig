"""IsortConfigTarget - Target for [tool.isort] configuration."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rejig.core.results import Result
from rejig.project.targets.tools.base import ToolConfigTarget

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class IsortConfigTarget(ToolConfigTarget):
    """Target for isort configuration.

    Manages [tool.isort] section in pyproject.toml.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    path : Path
        Path to pyproject.toml.

    Examples
    --------
    >>> isort = pyproject.isort()
    >>> isort.set(profile="black", line_length=110)
    >>> isort.use_black_profile()
    >>> isort.add_known_first_party("mypackage")
    """

    TOOL_NAME = "isort"

    def __init__(self, rejig: Rejig, path: Path) -> None:
        super().__init__(rejig, path, "isort")

    def __repr__(self) -> str:
        return f"IsortConfigTarget({self.path})"

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def profile(self) -> str | None:
        """Get the isort profile."""
        return self.get_option("profile")

    @property
    def line_length(self) -> int:
        """Get the line length."""
        return self.get_option("line_length", 88)

    @property
    def known_first_party(self) -> list[str]:
        """Get known first-party packages."""
        return self.get_option("known_first_party", [])

    @property
    def known_third_party(self) -> list[str]:
        """Get known third-party packages."""
        return self.get_option("known_third_party", [])

    @property
    def skip(self) -> list[str]:
        """Get skipped files/directories."""
        return self.get_option("skip", [])

    @property
    def skip_glob(self) -> list[str]:
        """Get skipped glob patterns."""
        return self.get_option("skip_glob", [])

    # =========================================================================
    # Setters
    # =========================================================================

    def set_profile(self, profile: str) -> Result:
        """Set the isort profile.

        Parameters
        ----------
        profile : str
            Profile name (e.g., "black", "django", "pycharm").

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> isort.set_profile("black")
        """
        return self.set_option("profile", profile)

    def use_black_profile(self) -> Result:
        """Configure isort to be compatible with Black.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set_profile("black")

    def set_line_length(self, length: int) -> Result:
        """Set the line length.

        Parameters
        ----------
        length : int
            Maximum line length.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set_option("line_length", length)

    def set_known_first_party(self, packages: list[str]) -> Result:
        """Set known first-party packages.

        Parameters
        ----------
        packages : list[str]
            Package names.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> isort.set_known_first_party(["mypackage", "mypackage_utils"])
        """
        return self.set_option("known_first_party", packages)

    def add_known_first_party(self, package: str) -> Result:
        """Add a known first-party package.

        Parameters
        ----------
        package : str
            Package name.

        Returns
        -------
        Result
            Result of the operation.
        """
        packages = self.known_first_party
        if package not in packages:
            packages.append(package)
            return self.set_known_first_party(packages)
        return Result(success=True, message=f"Package {package} already known")

    def set_known_third_party(self, packages: list[str]) -> Result:
        """Set known third-party packages.

        Parameters
        ----------
        packages : list[str]
            Package names.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set_option("known_third_party", packages)

    def add_known_third_party(self, package: str) -> Result:
        """Add a known third-party package.

        Parameters
        ----------
        package : str
            Package name.

        Returns
        -------
        Result
            Result of the operation.
        """
        packages = self.known_third_party
        if package not in packages:
            packages.append(package)
            return self.set_known_third_party(packages)
        return Result(success=True, message=f"Package {package} already known")

    def set_skip(self, paths: list[str]) -> Result:
        """Set paths to skip.

        Parameters
        ----------
        paths : list[str]
            Paths to skip.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set_option("skip", paths)

    def add_skip(self, path: str) -> Result:
        """Add a path to skip.

        Parameters
        ----------
        path : str
            Path to skip.

        Returns
        -------
        Result
            Result of the operation.
        """
        paths = self.skip
        if path not in paths:
            paths.append(path)
            return self.set_skip(paths)
        return Result(success=True, message=f"Path {path} already skipped")

    def set_skip_glob(self, patterns: list[str]) -> Result:
        """Set glob patterns to skip.

        Parameters
        ----------
        patterns : list[str]
            Glob patterns.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set_option("skip_glob", patterns)
