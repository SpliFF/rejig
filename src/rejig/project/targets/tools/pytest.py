"""PytestConfigTarget - Target for [tool.pytest.ini_options] configuration."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rejig.core.results import Result
from rejig.project.targets.tools.base import ToolConfigTarget

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class PytestConfigTarget(ToolConfigTarget):
    """Target for pytest configuration.

    Manages [tool.pytest.ini_options] section in pyproject.toml.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    path : Path
        Path to pyproject.toml.

    Examples
    --------
    >>> pytest = pyproject.pytest()
    >>> pytest.set(testpaths=["tests"], addopts="-v --tb=short")
    >>> pytest.set_testpaths(["tests", "integration_tests"])
    >>> pytest.add_marker("slow", "marks tests as slow")
    """

    TOOL_NAME = "pytest"

    def __init__(self, rejig: Rejig, path: Path) -> None:
        super().__init__(rejig, path, "pytest")

    def __repr__(self) -> str:
        return f"PytestConfigTarget({self.path})"

    @property
    def key_path(self) -> str:
        """The dotted key path for pytest config (uses ini_options)."""
        return "tool.pytest.ini_options"

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def testpaths(self) -> list[str]:
        """Get the test paths."""
        return self.get_option("testpaths", [])

    @property
    def addopts(self) -> str:
        """Get additional options."""
        return self.get_option("addopts", "")

    @property
    def python_files(self) -> list[str]:
        """Get python file patterns."""
        return self.get_option("python_files", [])

    @property
    def python_classes(self) -> list[str]:
        """Get python class patterns."""
        return self.get_option("python_classes", [])

    @property
    def python_functions(self) -> list[str]:
        """Get python function patterns."""
        return self.get_option("python_functions", [])

    @property
    def markers(self) -> list[str]:
        """Get registered markers."""
        return self.get_option("markers", [])

    @property
    def filterwarnings(self) -> list[str]:
        """Get warning filters."""
        return self.get_option("filterwarnings", [])

    # =========================================================================
    # Setters
    # =========================================================================

    def set_testpaths(self, paths: list[str]) -> Result:
        """Set the test paths.

        Parameters
        ----------
        paths : list[str]
            Directories to search for tests.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> pytest.set_testpaths(["tests", "integration"])
        """
        return self.set_option("testpaths", paths)

    def set_addopts(self, opts: str) -> Result:
        """Set additional command line options.

        Parameters
        ----------
        opts : str
            Command line options (e.g., "-v --tb=short").

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> pytest.set_addopts("-v --tb=short --cov=mypackage")
        """
        return self.set_option("addopts", opts)

    def add_addopt(self, opt: str) -> Result:
        """Add an option to addopts.

        Parameters
        ----------
        opt : str
            Option to add.

        Returns
        -------
        Result
            Result of the operation.
        """
        current = self.addopts
        if opt not in current:
            new_opts = f"{current} {opt}".strip()
            return self.set_addopts(new_opts)
        return Result(success=True, message=f"Option {opt} already exists")

    def set_python_files(self, patterns: list[str]) -> Result:
        """Set python file patterns.

        Parameters
        ----------
        patterns : list[str]
            File patterns (e.g., ["test_*.py", "*_test.py"]).

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set_option("python_files", patterns)

    def set_python_classes(self, patterns: list[str]) -> Result:
        """Set python class patterns.

        Parameters
        ----------
        patterns : list[str]
            Class patterns (e.g., ["Test*"]).

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set_option("python_classes", patterns)

    def set_python_functions(self, patterns: list[str]) -> Result:
        """Set python function patterns.

        Parameters
        ----------
        patterns : list[str]
            Function patterns (e.g., ["test_*"]).

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set_option("python_functions", patterns)

    # =========================================================================
    # Markers
    # =========================================================================

    def add_marker(self, name: str, description: str) -> Result:
        """Register a custom marker.

        Parameters
        ----------
        name : str
            Marker name.
        description : str
            Marker description.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> pytest.add_marker("slow", "marks tests as slow (deselect with '-m \"not slow\"')")
        """
        markers = self.markers
        marker_str = f"{name}: {description}"

        # Check if marker already exists
        for m in markers:
            if m.startswith(f"{name}:"):
                return Result(success=True, message=f"Marker {name} already exists")

        markers.append(marker_str)
        return self.set_option("markers", markers)

    def remove_marker(self, name: str) -> Result:
        """Remove a custom marker.

        Parameters
        ----------
        name : str
            Marker name to remove.

        Returns
        -------
        Result
            Result of the operation.
        """
        markers = self.markers
        new_markers = [m for m in markers if not m.startswith(f"{name}:")]

        if len(new_markers) == len(markers):
            return Result(success=True, message=f"Marker {name} not found")

        return self.set_option("markers", new_markers)

    # =========================================================================
    # Warning Filters
    # =========================================================================

    def add_filterwarning(self, filter_spec: str) -> Result:
        """Add a warning filter.

        Parameters
        ----------
        filter_spec : str
            Warning filter specification.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> pytest.add_filterwarning("ignore::DeprecationWarning")
        """
        filters = self.filterwarnings
        if filter_spec not in filters:
            filters.append(filter_spec)
            return self.set_option("filterwarnings", filters)
        return Result(success=True, message="Filter already exists")

    def ignore_deprecation_warnings(self, module: str | None = None) -> Result:
        """Add filter to ignore deprecation warnings.

        Parameters
        ----------
        module : str | None
            Optional module to limit filter to.

        Returns
        -------
        Result
            Result of the operation.
        """
        if module:
            return self.add_filterwarning(f"ignore::DeprecationWarning:{module}")
        return self.add_filterwarning("ignore::DeprecationWarning")
