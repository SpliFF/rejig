"""Tool configuration targets for pyproject.toml [tool.*] sections."""

from rejig.project.targets.tools.base import ToolConfigTarget
from rejig.project.targets.tools.black import BlackConfigTarget
from rejig.project.targets.tools.ruff import RuffConfigTarget
from rejig.project.targets.tools.mypy import MypyConfigTarget
from rejig.project.targets.tools.pytest import PytestConfigTarget
from rejig.project.targets.tools.isort import IsortConfigTarget
from rejig.project.targets.tools.coverage import CoverageConfigTarget

__all__ = [
    "ToolConfigTarget",
    "BlackConfigTarget",
    "RuffConfigTarget",
    "MypyConfigTarget",
    "PytestConfigTarget",
    "IsortConfigTarget",
    "CoverageConfigTarget",
]
