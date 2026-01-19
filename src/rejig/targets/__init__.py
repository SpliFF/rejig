"""Unified Target architecture for code refactoring operations.

This package provides a consistent interface for manipulating Python code,
configuration files, and text files through Target objects.

Core Classes:
    Result: Success result from operations
    ErrorResult: Failure result from operations (never raises)
    BatchResult: Aggregate result for batch operations
    Target: Base class for all targets
    ErrorTarget: Sentinel for failed lookups (allows chaining)
    TargetList: Batch operations on multiple targets

Python Targets:
    FileTarget: Individual .py files
    ModuleTarget: Python modules by dotted path
    ClassTarget: Class definitions
    FunctionTarget: Module-level functions
    MethodTarget: Class methods
    LineTarget: Single lines
    LineBlockTarget: Line ranges
    CodeBlockTarget: Code structures (if, for, while, etc.)
    CommentTarget: Python comments
    StringLiteralTarget: String literals

Config Targets:
    TomlTarget: TOML files
    JsonTarget: JSON files

Text Targets:
    TextFileTarget: Any text file
"""

from rejig.targets.base import (
    BatchResult,
    ErrorResult,
    ErrorTarget,
    Result,
    Target,
    TargetList,
)
from rejig.targets.config import IniTarget, JsonTarget, TomlTarget, YamlTarget
from rejig.targets.python import (
    ClassTarget,
    CodeBlockTarget,
    CommentTarget,
    FileTarget,
    FunctionTarget,
    LineBlockTarget,
    LineTarget,
    MethodTarget,
    ModuleTarget,
    PackageTarget,
    StringLiteralTarget,
)
from rejig.targets.text import TextFileTarget

__all__ = [
    # Base classes
    "Result",
    "ErrorResult",
    "BatchResult",
    "Target",
    "ErrorTarget",
    "TargetList",
    # Python targets
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
    # Config targets
    "TomlTarget",
    "JsonTarget",
    "YamlTarget",
    "IniTarget",
    # Text targets
    "TextFileTarget",
]
