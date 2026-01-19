"""Package format detection.

Detects which package manager format is used in a project.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from rejig.packaging.models import PackageConfig, PackageFormat

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig

# Python 3.11+ has tomllib built-in
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # type: ignore


class FormatDetector:
    """Detect package configuration format in a directory.

    Examines files in a directory to determine which package manager
    format is being used. Supports detection of:

    - requirements.txt (pip)
    - PEP 621 pyproject.toml
    - Poetry pyproject.toml
    - UV pyproject.toml

    Parameters
    ----------
    rejig : Rejig | None
        Optional Rejig instance.

    Examples
    --------
    >>> detector = FormatDetector()
    >>> format = detector.detect(Path("."))
    >>> print(format)  # "pep621", "poetry", "uv", "requirements", or None
    """

    def __init__(self, rejig: Rejig | None = None) -> None:
        self._rejig = rejig

    def detect(self, path: Path) -> PackageFormat | None:
        """Detect the package format in a directory or from a file.

        Parameters
        ----------
        path : Path
            Directory or file path to examine.

        Returns
        -------
        PackageFormat | None
            Detected format, or None if no known format found.
        """
        if path.is_file():
            return self._detect_from_file(path)
        return self._detect_from_directory(path)

    def _detect_from_file(self, path: Path) -> PackageFormat | None:
        """Detect format from a specific file."""
        name = path.name.lower()

        if name == "pyproject.toml":
            return self._detect_pyproject_format(path)
        elif name.startswith("requirements") and name.endswith(".txt"):
            return "requirements"
        elif name == "setup.py" or name == "setup.cfg":
            return None  # Legacy formats not supported
        elif name == "pipfile":
            return None  # Pipenv not supported

        return None

    def _detect_from_directory(self, path: Path) -> PackageFormat | None:
        """Detect format from a directory.

        Priority:
        1. pyproject.toml (Poetry > UV > PEP 621)
        2. requirements.txt
        """
        pyproject = path / "pyproject.toml"
        if pyproject.exists():
            fmt = self._detect_pyproject_format(pyproject)
            if fmt:
                return fmt

        # Check for requirements.txt
        requirements = path / "requirements.txt"
        if requirements.exists():
            return "requirements"

        # Also check for requirements/*.txt pattern
        requirements_dir = path / "requirements"
        if requirements_dir.is_dir():
            for req_file in requirements_dir.glob("*.txt"):
                if req_file.is_file():
                    return "requirements"

        return None

    def _detect_pyproject_format(self, path: Path) -> PackageFormat | None:
        """Detect the specific format of a pyproject.toml file."""
        if tomllib is None:
            return None

        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
        except Exception:
            return None

        tool = data.get("tool", {})

        # Check for Poetry
        if "poetry" in tool:
            return "poetry"

        # Check for UV-specific configuration
        if "uv" in tool:
            return "uv"

        # Check for standard PEP 621
        if "project" in data:
            return "pep621"

        return None

    def detect_all(self, path: Path) -> list[tuple[PackageFormat, Path]]:
        """Detect all package configuration files in a directory.

        Parameters
        ----------
        path : Path
            Directory to search.

        Returns
        -------
        list[tuple[PackageFormat, Path]]
            List of (format, file_path) tuples for all found configs.
        """
        results: list[tuple[PackageFormat, Path]] = []

        if not path.is_dir():
            fmt = self.detect(path)
            if fmt:
                results.append((fmt, path))
            return results

        # Check pyproject.toml
        pyproject = path / "pyproject.toml"
        if pyproject.exists():
            fmt = self._detect_pyproject_format(pyproject)
            if fmt:
                results.append((fmt, pyproject))

        # Check requirements files
        requirements = path / "requirements.txt"
        if requirements.exists():
            results.append(("requirements", requirements))

        # Check requirements directory
        requirements_dir = path / "requirements"
        if requirements_dir.is_dir():
            for req_file in sorted(requirements_dir.glob("*.txt")):
                if req_file.is_file():
                    results.append(("requirements", req_file))

        return results

    def get_config_path(self, path: Path) -> Path | None:
        """Get the primary configuration file path.

        Parameters
        ----------
        path : Path
            Directory to search.

        Returns
        -------
        Path | None
            Path to the primary configuration file.
        """
        if path.is_file():
            return path

        # Prefer pyproject.toml
        pyproject = path / "pyproject.toml"
        if pyproject.exists():
            return pyproject

        # Fall back to requirements.txt
        requirements = path / "requirements.txt"
        if requirements.exists():
            return requirements

        return None


def detect_format(path: Path) -> PackageFormat | None:
    """Convenience function to detect package format.

    Parameters
    ----------
    path : Path
        Directory or file path.

    Returns
    -------
    PackageFormat | None
        Detected format, or None if unknown.
    """
    return FormatDetector().detect(path)


def get_package_config(path: Path) -> PackageConfig | None:
    """Detect format and parse package configuration.

    Parameters
    ----------
    path : Path
        Directory or file path.

    Returns
    -------
    PackageConfig | None
        Parsed configuration, or None if not found.
    """
    detector = FormatDetector()
    fmt = detector.detect(path)

    if fmt is None:
        return None

    config_path = detector.get_config_path(path)
    if config_path is None:
        return None

    if fmt == "requirements":
        from rejig.packaging.requirements import RequirementsParser
        return RequirementsParser().parse(config_path)

    elif fmt == "pep621":
        from rejig.packaging.pep621 import PEP621Parser
        return PEP621Parser().parse(config_path)

    elif fmt == "poetry":
        from rejig.packaging.poetry import PoetryParser
        return PoetryParser().parse(config_path)

    elif fmt == "uv":
        from rejig.packaging.uv import UVParser
        return UVParser().parse(config_path)

    return None
