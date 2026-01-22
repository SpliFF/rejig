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
>>> # Use the target API
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

Result
    Result class for all operations. Contains success status, message, and
    list of changed files. Operations never raise exceptions.

ErrorResult
    Result class for failed operations.

BatchResult
    Aggregate result for operations applied to multiple targets.

Target
    Base class for all targets.

ErrorTarget
    Sentinel for failed lookups - all operations return ErrorResult.

TargetList
    List of targets for batch operations.

Python Targets
--------------
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

CodeBlockTarget
    Target for code blocks (if/for/while/try/with/class/function).

CommentTarget
    Target for Python comments.

StringLiteralTarget
    Target for string literals.

Config Targets
--------------
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

TextBlock
    Target for raw text pattern-based manipulation.

TextMatch
    Target for individual pattern matches.

Transaction
    Atomic batch operations with commit/rollback.

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

Import Management
-----------------
ImportTarget
    Target for individual import statements.

ImportTargetList
    List of import targets for batch operations.

ImportAnalyzer
    Analyze imports in Python files.

ImportInfo
    Information about an import statement.

ImportOrganizer
    Organize imports (isort-like).

ImportGraph
    Import dependency graph for analysis.

CircularImport
    Represents a circular import chain.

Project Management
------------------
PythonProject
    High-level Python project configuration manager.

Code Analysis
-------------
AnalysisTarget
    Target for code analysis findings.

AnalysisTargetList
    List of analysis targets for batch operations.

AnalysisType
    Types of code analysis findings.

AnalysisFinding
    A single finding from code analysis.

AnalysisReport
    Comprehensive code analysis report.

ComplexityAnalyzer
    Analyze cyclomatic complexity and code metrics.

PatternFinder
    Find code patterns needing attention.

DeadCodeAnalyzer
    Detect potentially unused code.

CodeMetrics
    Collect and analyze code metrics.

Security Analysis
-----------------
SecurityTarget
    Target for security analysis findings.

SecurityTargetList
    List of security targets for batch operations.

SecurityType
    Types of security findings.

SecurityFinding
    A single finding from security analysis.

SecurityReport
    Comprehensive security analysis report.

SecretsScanner
    Detect hardcoded secrets and credentials.

VulnerabilityScanner
    Detect common security vulnerabilities.

SecurityReporter
    Generate security analysis reports.

Code Optimization
-----------------
OptimizeTarget
    Target for code optimization findings.

OptimizeTargetList
    List of optimization targets for batch operations.

OptimizeType
    Types of optimization findings.

OptimizeFinding
    A single finding from code optimization analysis.

DRYAnalyzer
    Detect duplicate code, expressions, and literals.

LoopOptimizer
    Find loops that can be replaced with comprehensions or builtins.

Patching
--------
Patch
    A complete patch containing changes to one or more files.

FilePatch
    All changes to a single file.

Hunk
    A contiguous block of changes in a file.

Change
    A single line addition, deletion, or context line.

PatchFormat
    Enum for patch formats (UNIFIED, GIT).

ChangeType
    Enum for change types (ADD, DELETE, CONTEXT).

PatchTarget
    Target for a complete patch (fluent API).

PatchFileTarget
    Target for a single file within a patch.

PatchHunkTarget
    Target for a single hunk within a file patch.

PatchParser
    Parser for unified diff and git diff formats.

PatchGenerator
    Generator for creating patches from rejig operations.

PatchConverter
    Converter for patches to rejig operations.

PatchAnalyzer
    Analyzer for detecting higher-level operations in patches.

DetectedOperation
    A detected operation from patch analysis.

OperationType
    Enum for types of operations detected in patches.

Framework Extensions
--------------------
FlaskProject
    Flask-specific refactoring operations (routes, blueprints, error handlers).

FastAPIProject
    FastAPI-specific refactoring operations (endpoints, dependencies, middleware).

SQLAlchemyProject
    SQLAlchemy-specific refactoring operations (models, relationships, columns).
"""
from __future__ import annotations

from .core import BatchResult, ErrorResult, Rejig, Result
from .core.transaction import Transaction
from .imports import (
    CircularImport,
    ImportAnalyzer,
    ImportGraph,
    ImportInfo,
    ImportOrganizer,
    ImportTarget,
    ImportTargetList,
)
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
from .project import (
    PythonProject,
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
from .analysis import (
    AnalysisTarget,
    AnalysisTargetList,
    AnalysisReport,
    AnalysisReporter,
    ComplexityAnalyzer,
    ComplexityResult,
    NestingResult,
    DeadCodeAnalyzer,
    UnusedCodeResult,
    PatternFinder,
    PatternMatch,
    CodeMetrics,
    FileMetrics,
    ModuleMetrics,
)
from .analysis.targets import AnalysisFinding, AnalysisType
from .security import (
    SecurityFinding,
    SecurityReport,
    SecurityReporter,
    SecretsScanner,
    SecurityTarget,
    SecurityTargetList,
    SecurityType,
    VulnerabilityScanner,
)
from .frameworks import (
    FlaskProject,
    FastAPIProject,
    SQLAlchemyProject,
)
from .optimize import (
    DRYAnalyzer,
    LoopOptimizer,
    OptimizeFinding,
    OptimizeTarget,
    OptimizeTargetList,
    OptimizeType,
)
from .patching import (
    Change,
    ChangeType,
    DetectedOperation,
    FilePatch,
    Hunk,
    OperationType,
    Patch,
    PatchAnalyzer,
    PatchConverter,
    PatchFileTarget,
    PatchFormat,
    PatchGenerator,
    PatchHunkTarget,
    PatchParser,
    PatchTarget,
)
from .targets import (
    ClassTarget,
    CodeBlockTarget,
    CommentTarget,
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
    StringLiteralTarget,
    Target,
    TargetList,
    TextBlock,
    TextFileTarget,
    TextMatch,
    TomlTarget,
    YamlTarget,
)

__version__ = "0.1.0"
__all__ = [
    # Main entry point
    "Rejig",
    # Result classes
    "Result",
    "ErrorResult",
    "BatchResult",
    # Transaction support
    "Transaction",
    # Target base classes
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
    "TextBlock",
    "TextMatch",
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
    # Import Management
    "ImportTarget",
    "ImportTargetList",
    "ImportAnalyzer",
    "ImportInfo",
    "ImportOrganizer",
    "ImportGraph",
    "CircularImport",
    # Project Management
    "PythonProject",
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
    # Code Analysis
    "AnalysisTarget",
    "AnalysisTargetList",
    "AnalysisType",
    "AnalysisFinding",
    "AnalysisReport",
    "AnalysisReporter",
    "ComplexityAnalyzer",
    "ComplexityResult",
    "NestingResult",
    "DeadCodeAnalyzer",
    "UnusedCodeResult",
    "PatternFinder",
    "PatternMatch",
    "CodeMetrics",
    "FileMetrics",
    "ModuleMetrics",
    # Security Analysis
    "SecurityTarget",
    "SecurityTargetList",
    "SecurityType",
    "SecurityFinding",
    "SecurityReport",
    "SecurityReporter",
    "SecretsScanner",
    "VulnerabilityScanner",
    # Code Optimization
    "OptimizeTarget",
    "OptimizeTargetList",
    "OptimizeType",
    "OptimizeFinding",
    "DRYAnalyzer",
    "LoopOptimizer",
    # Patching
    "Patch",
    "FilePatch",
    "Hunk",
    "Change",
    "PatchFormat",
    "ChangeType",
    "PatchTarget",
    "PatchFileTarget",
    "PatchHunkTarget",
    "PatchParser",
    "PatchGenerator",
    "PatchConverter",
    "PatchAnalyzer",
    "DetectedOperation",
    "OperationType",
    # Framework Extensions
    "FlaskProject",
    "FastAPIProject",
    "SQLAlchemyProject",
]
