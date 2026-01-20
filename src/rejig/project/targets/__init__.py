"""Target classes for pyproject.toml sections.

Provides a Target-based API for working with pyproject.toml sections,
enabling fluent navigation and modification.
"""

from rejig.project.targets.pyproject import PyprojectTarget
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

__all__ = [
    "PyprojectTarget",
    "ProjectSectionTarget",
    "DependenciesTarget",
    "ScriptsTarget",
    "ToolConfigTarget",
    "BlackConfigTarget",
    "RuffConfigTarget",
    "MypyConfigTarget",
    "PytestConfigTarget",
    "IsortConfigTarget",
    "CoverageConfigTarget",
]
