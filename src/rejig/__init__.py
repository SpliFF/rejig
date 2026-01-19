"""
Rejig - A Python library for programmatic code refactoring.

A comprehensive toolkit for programmatic refactoring of Python projects using
LibCST. Provides a fluent API for finding and modifying code elements.

Example
-------
>>> from rejig import Rejig
>>>
>>> # Initialize with a directory
>>> rj = Rejig("src/")
>>>
>>> # Find and modify a class
>>> rj.find_class("MyClass").add_attribute("count", "int", "0")
>>>
>>> # Chain operations on methods
>>> rj.find_class("MyClass").find_method("process").insert_statement("self.validate()")
>>>
>>> # Use the new target API
>>> rj.file("mymodule.py").find_class("MyClass").add_method("process")
>>> rj.toml("pyproject.toml").set("project.version", "2.0.0")
>>>
>>> # Preview changes without modifying files
>>> rj = Rejig("src/", dry_run=True)
>>> result = rj.find_class("MyClass").add_attribute("x", "int", "0")
>>> print(result.message)  # [DRY RUN] Would add attribute...

Classes
-------
Rejig
    Main entry point for all refactoring operations.

RefactorResult
    Dataclass returned by all refactoring methods containing success status,
    message, and list of changed files.

FindResult
    Result of find operations containing matched locations.

Match
    A single match from a find operation.

ClassScope
    Scope for operations on a specific class.

MethodScope
    Scope for operations on a specific method within a class.

FunctionScope
    Scope for operations on a module-level function.

Targets
-------
Result
    Result class for target operations.

ErrorResult
    Result class for failed operations.

Target
    Base class for all targets.

TargetList
    List of targets for batch operations.

FileTarget
    Target for Python files.

ModuleTarget
    Target for Python modules.

PackageTarget
    Target for Python packages.

ClassTarget
    Target for class definitions.

FunctionTarget
    Target for module-level functions.

MethodTarget
    Target for class methods.

LineTarget
    Target for single lines.

LineBlockTarget
    Target for line ranges.

TomlTarget
    Target for TOML files.

YamlTarget
    Target for YAML files.

JsonTarget
    Target for JSON files.

IniTarget
    Target for INI/CFG files.

TextFileTarget
    Target for generic text files.

Packaging
---------
Dependency
    Unified representation of a Python dependency.

PackageConfig
    Complete package configuration.

PackageMetadata
    Package metadata (name, version, authors, etc.).

RequirementsParser
    Parse requirements.txt files.

PEP621Parser
    Parse PEP 621 pyproject.toml files.

PoetryParser
    Parse Poetry pyproject.toml files.

FormatDetector
    Detect package configuration format.

PackageConfigConverter
    Convert between different formats.
"""
from __future__ import annotations

from .core import Rejig
from .packaging import (
    Dependency,
    FormatDetector,
    PackageConfig,
    PackageConfigConverter,
    PackageMetadata,
    PEP621Parser,
    PoetryParser,
    RequirementsParser,
    UVParser,
)
from .result import FindResult, Match, RefactorResult
from .scope import ClassScope, FunctionScope, MethodScope
from .targets import (
    BatchResult,
    ClassTarget,
    CodeBlockTarget,
    CommentTarget,
    ErrorResult,
    ErrorTarget,
    FileTarget,
    FunctionTarget,
    IniTarget,
    JsonTarget,
    LineBlockTarget,
    LineTarget,
    MethodTarget,
    ModuleTarget,
    PackageTarget,
    Result,
    StringLiteralTarget,
    Target,
    TargetList,
    TextFileTarget,
    TomlTarget,
    YamlTarget,
)

__version__ = "0.1.0"
__all__ = [
    # Main entry point
    "Rejig",
    # Legacy result classes
    "RefactorResult",
    "FindResult",
    "Match",
    # Legacy scope classes
    "ClassScope",
    "MethodScope",
    "FunctionScope",
    # Target base classes
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
    "YamlTarget",
    "JsonTarget",
    "IniTarget",
    # Text targets
    "TextFileTarget",
    # Packaging
    "Dependency",
    "PackageMetadata",
    "PackageConfig",
    "RequirementsParser",
    "PEP621Parser",
    "PoetryParser",
    "UVParser",
    "FormatDetector",
    "PackageConfigConverter",
]
