"""Project configuration management.

High-level API for managing Python project configuration files,
including pyproject.toml, dependencies, scripts, and tool configuration.

Classes
-------
PythonProject
    High-level facade for Python project configuration.

PyprojectTarget
    Target for pyproject.toml with section navigation.

ProjectSectionTarget
    Target for [project] section metadata.

DependenciesTarget
    Target for managing dependencies.

ScriptsTarget
    Target for managing console scripts.

ToolConfigTarget
    Base target for tool configurations.

BlackConfigTarget, RuffConfigTarget, MypyConfigTarget, etc.
    Specialized targets for specific tools.

Examples
--------
High-level facade usage:

>>> from rejig.project import PythonProject
>>>
>>> project = PythonProject("/path/to/project")
>>>
>>> # Convenience methods
>>> project.add_dependency("requests", ">=2.28.0")
>>> project.add_dev_dependency("pytest", ">=7.0.0")
>>> project.bump_version("minor")  # 1.2.0 → 1.3.0
>>> project.configure_black(line_length=110)
>>> project.configure_ruff(select=["E", "F"])

Target-based usage (more control):

>>> # Navigate to sections as targets
>>> project.pyproject.dependencies().add("aiohttp", ">=3.8.0")
>>> project.pyproject.black().set(target_version=["py310"])
>>> project.pyproject.project().set_homepage("https://example.com")
>>>
>>> # Or use TomlTarget methods directly
>>> project.pyproject.set("project.version", "2.0.0")
>>> project.pyproject.get("tool.black.line-length")

Direct target instantiation (via Rejig):

>>> from rejig import Rejig
>>>
>>> rj = Rejig("/path/to/project")
>>> pyproject = rj.pyproject()  # Returns PyprojectTarget
>>>
>>> pyproject.dependencies().add("requests")
>>> pyproject.black().set(line_length=110)
>>> pyproject.project().bump_version("minor")
"""

from rejig.project.python_project import PythonProject
from rejig.project.targets import (
    PyprojectTarget,
    ProjectSectionTarget,
    DependenciesTarget,
    ScriptsTarget,
    ToolConfigTarget,
    BlackConfigTarget,
    RuffConfigTarget,
    MypyConfigTarget,
    PytestConfigTarget,
    IsortConfigTarget,
    CoverageConfigTarget,
)

__all__ = [
    # Main facade
    "PythonProject",
    # Targets
    "PyprojectTarget",
    "ProjectSectionTarget",
    "DependenciesTarget",
    "ScriptsTarget",
    # Tool configuration targets
    "ToolConfigTarget",
    "BlackConfigTarget",
    "RuffConfigTarget",
    "MypyConfigTarget",
    "PytestConfigTarget",
    "IsortConfigTarget",
    "CoverageConfigTarget",
]
