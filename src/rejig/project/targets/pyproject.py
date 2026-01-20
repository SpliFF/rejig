"""PyprojectTarget - Target for pyproject.toml with section navigation."""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rejig.core.results import Result
from rejig.targets.config.toml import TomlTarget

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class PyprojectTarget(TomlTarget):
    """Target for pyproject.toml with fluent navigation to sections.

    Extends TomlTarget with methods to navigate to specific sections
    as their own Target objects.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    path : str | Path | None
        Path to pyproject.toml. If None, uses "pyproject.toml" in rejig.root.

    Examples
    --------
    >>> pyproject = rj.pyproject()  # or PyprojectTarget(rj)
    >>>
    >>> # Navigate to sections as targets
    >>> pyproject.project().set_version("2.0.0")
    >>> pyproject.dependencies().add("requests", ">=2.28.0")
    >>> pyproject.scripts().add("mycli", "mypackage:main")
    >>>
    >>> # Configure tools
    >>> pyproject.black().set(line_length=110)
    >>> pyproject.ruff().set(select=["E", "F"])
    >>> pyproject.mypy().set(strict=True)
    >>>
    >>> # Or use dotted path access from TomlTarget
    >>> pyproject.set("project.version", "2.0.0")
    """

    def __init__(self, rejig: Rejig, path: str | Path | None = None) -> None:
        if path is None:
            path = rejig.root / "pyproject.toml"
        super().__init__(rejig, path)

    def __repr__(self) -> str:
        return f"PyprojectTarget({self.path})"

    # =========================================================================
    # Section Navigation
    # =========================================================================

    def project(self) -> ProjectSectionTarget:
        """Navigate to the [project] section.

        Returns
        -------
        ProjectSectionTarget
            Target for the [project] section.

        Examples
        --------
        >>> pyproject.project().name
        'myproject'
        >>> pyproject.project().set_version("2.0.0")
        """
        from rejig.project.targets.project_section import ProjectSectionTarget

        return ProjectSectionTarget(self._rejig, self.path)

    def dependencies(self) -> DependenciesTarget:
        """Navigate to project.dependencies.

        Returns
        -------
        DependenciesTarget
            Target for managing dependencies.

        Examples
        --------
        >>> pyproject.dependencies().add("requests", ">=2.28.0")
        >>> pyproject.dependencies().remove("old-package")
        """
        from rejig.project.targets.dependencies import DependenciesTarget

        return DependenciesTarget(self._rejig, self.path)

    def dev_dependencies(self) -> DependenciesTarget:
        """Navigate to project.optional-dependencies.dev.

        Returns
        -------
        DependenciesTarget
            Target for managing dev dependencies.

        Examples
        --------
        >>> pyproject.dev_dependencies().add("pytest", ">=7.0.0")
        """
        from rejig.project.targets.dependencies import DependenciesTarget

        return DependenciesTarget(self._rejig, self.path, group="dev")

    def optional_dependencies(self, group: str) -> DependenciesTarget:
        """Navigate to a specific optional-dependencies group.

        Parameters
        ----------
        group : str
            Name of the optional dependency group.

        Returns
        -------
        DependenciesTarget
            Target for managing the group's dependencies.

        Examples
        --------
        >>> pyproject.optional_dependencies("cache").add("redis", ">=4.0")
        """
        from rejig.project.targets.dependencies import DependenciesTarget

        return DependenciesTarget(self._rejig, self.path, group=group)

    def scripts(self) -> ScriptsTarget:
        """Navigate to project.scripts.

        Returns
        -------
        ScriptsTarget
            Target for managing console scripts.

        Examples
        --------
        >>> pyproject.scripts().add("mycli", "mypackage.cli:main")
        >>> pyproject.scripts().remove("old-command")
        """
        from rejig.project.targets.scripts import ScriptsTarget

        return ScriptsTarget(self._rejig, self.path)

    def gui_scripts(self) -> ScriptsTarget:
        """Navigate to project.gui-scripts.

        Returns
        -------
        ScriptsTarget
            Target for managing GUI scripts.
        """
        from rejig.project.targets.scripts import ScriptsTarget

        return ScriptsTarget(self._rejig, self.path, section="gui-scripts")

    # =========================================================================
    # Tool Configuration Navigation
    # =========================================================================

    def tool(self, name: str) -> ToolConfigTarget:
        """Navigate to a tool configuration section.

        Parameters
        ----------
        name : str
            Tool name (e.g., "black", "ruff", "mypy").

        Returns
        -------
        ToolConfigTarget
            Target for the tool configuration.

        Examples
        --------
        >>> pyproject.tool("black").set(line_length=110)
        >>> pyproject.tool("coverage").set({"run": {"source": ["src"]}})
        """
        from rejig.project.targets.tools import ToolConfigTarget

        return ToolConfigTarget(self._rejig, self.path, name)

    def black(self) -> BlackConfigTarget:
        """Navigate to [tool.black] configuration.

        Returns
        -------
        BlackConfigTarget
            Target for Black configuration.

        Examples
        --------
        >>> pyproject.black().set(line_length=110, target_version=["py310"])
        """
        from rejig.project.targets.tools import BlackConfigTarget

        return BlackConfigTarget(self._rejig, self.path)

    def ruff(self) -> RuffConfigTarget:
        """Navigate to [tool.ruff] configuration.

        Returns
        -------
        RuffConfigTarget
            Target for Ruff configuration.

        Examples
        --------
        >>> pyproject.ruff().set(select=["E", "F"], ignore=["E501"])
        """
        from rejig.project.targets.tools import RuffConfigTarget

        return RuffConfigTarget(self._rejig, self.path)

    def mypy(self) -> MypyConfigTarget:
        """Navigate to [tool.mypy] configuration.

        Returns
        -------
        MypyConfigTarget
            Target for Mypy configuration.

        Examples
        --------
        >>> pyproject.mypy().set(strict=True)
        """
        from rejig.project.targets.tools import MypyConfigTarget

        return MypyConfigTarget(self._rejig, self.path)

    def pytest(self) -> PytestConfigTarget:
        """Navigate to [tool.pytest.ini_options] configuration.

        Returns
        -------
        PytestConfigTarget
            Target for Pytest configuration.

        Examples
        --------
        >>> pyproject.pytest().set(testpaths=["tests"], addopts="-v")
        """
        from rejig.project.targets.tools import PytestConfigTarget

        return PytestConfigTarget(self._rejig, self.path)

    def isort(self) -> IsortConfigTarget:
        """Navigate to [tool.isort] configuration.

        Returns
        -------
        IsortConfigTarget
            Target for isort configuration.

        Examples
        --------
        >>> pyproject.isort().set(profile="black")
        """
        from rejig.project.targets.tools import IsortConfigTarget

        return IsortConfigTarget(self._rejig, self.path)

    def coverage(self) -> CoverageConfigTarget:
        """Navigate to [tool.coverage] configuration.

        Returns
        -------
        CoverageConfigTarget
            Target for coverage configuration.

        Examples
        --------
        >>> pyproject.coverage().set_source(["src"])
        """
        from rejig.project.targets.tools import CoverageConfigTarget

        return CoverageConfigTarget(self._rejig, self.path)

    # =========================================================================
    # High-Level Operations
    # =========================================================================

    def get_format(self) -> str | None:
        """Detect the pyproject.toml format.

        Returns
        -------
        str | None
            "pep621" if has [project], "poetry" if has [tool.poetry],
            "uv" if has [tool.uv], or None.
        """
        data = self._load()
        if data is None:
            return None

        if "tool" in data:
            if "poetry" in data["tool"]:
                return "poetry"
            if "uv" in data["tool"]:
                return "uv"

        if "project" in data:
            return "pep621"

        return None

    def is_pep621(self) -> bool:
        """Check if this is a PEP 621 format pyproject.toml."""
        return self.get_format() == "pep621"

    def is_poetry(self) -> bool:
        """Check if this is a Poetry format pyproject.toml."""
        return self.get_format() == "poetry"

    def init(
        self,
        name: str,
        version: str = "0.1.0",
        description: str | None = None,
        python_requires: str = ">=3.10",
    ) -> Result:
        """Initialize a new pyproject.toml with PEP 621 format.

        Parameters
        ----------
        name : str
            Project name.
        version : str
            Initial version.
        description : str | None
            Project description.
        python_requires : str
            Python version requirement.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> pyproject.init("myproject", description="A great project")
        """
        if self.exists():
            return self._operation_failed("init", "pyproject.toml already exists")

        data: dict[str, Any] = {
            "build-system": {
                "requires": ["setuptools>=61.0", "wheel"],
                "build-backend": "setuptools.build_meta",
            },
            "project": {
                "name": name,
                "version": version,
                "requires-python": python_requires,
                "dependencies": [],
            },
        }

        if description:
            data["project"]["description"] = description

        return self._save(data)

    def bump_version(self, part: str = "patch") -> Result:
        """Bump the version number.

        Parameters
        ----------
        part : str
            Which part to bump: "major", "minor", or "patch".

        Returns
        -------
        Result
            Result with the new version in the message.

        Examples
        --------
        >>> pyproject.bump_version("minor")  # 1.2.3 → 1.3.0
        """
        current = self.get("project.version")
        if current is None:
            # Try Poetry format
            current = self.get("tool.poetry.version")

        if current is None:
            return self._operation_failed("bump_version", "Version not found")

        match = re.match(r"^(\d+)\.(\d+)\.(\d+)(.*)$", current)
        if not match:
            return self._operation_failed("bump_version", f"Cannot parse version: {current}")

        major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))

        if part == "major":
            major, minor, patch = major + 1, 0, 0
        elif part == "minor":
            minor, patch = minor + 1, 0
        elif part == "patch":
            patch += 1
        else:
            return self._operation_failed("bump_version", f"Invalid version part: {part}")

        new_version = f"{major}.{minor}.{patch}"

        # Set in appropriate location
        if self.has_key("project.version"):
            result = self.set("project.version", new_version)
        elif self.has_key("tool.poetry.version"):
            result = self.set("tool.poetry.version", new_version)
        else:
            result = self.set("project.version", new_version)

        if result.success:
            result.message = f"Bumped version from {current} to {new_version}"

        return result


# Import these here to avoid circular imports
from rejig.project.targets.project_section import ProjectSectionTarget
from rejig.project.targets.dependencies import DependenciesTarget
from rejig.project.targets.scripts import ScriptsTarget
from rejig.project.targets.tools import (
    ToolConfigTarget,
    BlackConfigTarget,
    RuffConfigTarget,
    MypyConfigTarget,
    PytestConfigTarget,
    IsortConfigTarget,
    CoverageConfigTarget,
)
