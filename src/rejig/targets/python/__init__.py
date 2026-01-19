"""Python code targets for manipulating .py files.

This package provides Target classes for working with Python source code:

- FileTarget: Individual .py files
- ModuleTarget: Python modules by dotted path
- PackageTarget: Python packages (directories with __init__.py)
- ClassTarget: Class definitions
- FunctionTarget: Module-level functions
- MethodTarget: Class methods
- LineTarget: Single lines
- LineBlockTarget: Line ranges
- CodeBlockTarget: Code structures (if, for, while, try, with)
- CommentTarget: Python comments
- StringLiteralTarget: String literals
"""

from rejig.targets.python.class_ import ClassTarget
from rejig.targets.python.code_block import CodeBlockTarget
from rejig.targets.python.comment import CommentTarget
from rejig.targets.python.file import FileTarget
from rejig.targets.python.function import FunctionTarget
from rejig.targets.python.line import LineTarget
from rejig.targets.python.line_block import LineBlockTarget
from rejig.targets.python.method import MethodTarget
from rejig.targets.python.module import ModuleTarget
from rejig.targets.python.package import PackageTarget
from rejig.targets.python.string import StringLiteralTarget

__all__ = [
    "FileTarget",
    "ModuleTarget",
    "PackageTarget",
    "ClassTarget",
    "FunctionTarget",
    "MethodTarget",
    "LineTarget",
    "LineBlockTarget",
    "CodeBlockTarget",
    "CommentTarget",
    "StringLiteralTarget",
]
