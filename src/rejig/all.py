"""Full re-export of all rejig public symbols.

This module provides backward compatibility for code that relied on all
symbols being in __all__ at the top level. New code should prefer importing
from specific subpackages instead.

Usage:
    from rejig.all import *
"""
from __future__ import annotations

# Core
from rejig.core import BatchResult, ErrorResult, Rejig, Result  # noqa: F401
from rejig.core.cache import CSTCache  # noqa: F401
from rejig.core.transaction import Transaction  # noqa: F401

# Targets
from rejig.targets import (  # noqa: F401
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

# Imports
from rejig.imports import (  # noqa: F401
    CircularImport,
    ImportAnalyzer,
    ImportGraph,
    ImportInfo,
    ImportOrganizer,
    ImportTarget,
    ImportTargetList,
)

# Packaging
from rejig.packaging import (  # noqa: F401
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

# Project
from rejig.project import (  # noqa: F401
    BlackConfigTarget,
    CoverageConfigTarget,
    DependenciesTarget,
    IsortConfigTarget,
    MypyConfigTarget,
    ProjectSectionTarget,
    PytestConfigTarget,
    PythonProject,
    PyprojectTarget,
    RuffConfigTarget,
    ScriptsTarget,
    ToolConfigTarget,
)

# Analysis
from rejig.analysis import (  # noqa: F401
    AnalysisReport,
    AnalysisReporter,
    AnalysisTarget,
    AnalysisTargetList,
    CodeMetrics,
    ComplexityAnalyzer,
    ComplexityResult,
    DeadCodeAnalyzer,
    FileMetrics,
    ModuleMetrics,
    NestingResult,
    PatternFinder,
    PatternMatch,
    UnusedCodeResult,
)
from rejig.analysis.targets import AnalysisFinding, AnalysisType  # noqa: F401

# Security
from rejig.security import (  # noqa: F401
    SecurityFinding,
    SecurityReport,
    SecurityReporter,
    SecretsScanner,
    SecurityTarget,
    SecurityTargetList,
    SecurityType,
    VulnerabilityScanner,
)

# Frameworks
from rejig.frameworks import (  # noqa: F401
    FastAPIProject,
    FlaskProject,
    SQLAlchemyProject,
)

# Optimization
from rejig.optimize import (  # noqa: F401
    DRYAnalyzer,
    LoopOptimizer,
    OptimizeFinding,
    OptimizeTarget,
    OptimizeTargetList,
    OptimizeType,
)

# Patching
from rejig.patching import (  # noqa: F401
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

__all__ = [
    # Core
    "Rejig", "Result", "ErrorResult", "BatchResult", "Transaction", "CSTCache",
    # Target base
    "Target", "ErrorTarget", "TargetList",
    # Python targets
    "FileTarget", "ModuleTarget", "PackageTarget", "ClassTarget",
    "FunctionTarget", "MethodTarget", "LineTarget", "LineBlockTarget",
    "CodeBlockTarget", "CommentTarget", "StringLiteralTarget",
    # Config targets
    "TomlTarget", "YamlTarget", "JsonTarget", "IniTarget",
    # Text targets
    "TextFileTarget", "TextBlock", "TextMatch",
    # Packaging
    "Dependency", "PackageMetadata", "PackageConfig", "RequirementsParser",
    "PEP621Parser", "PoetryParser", "UVParser", "FormatDetector", "PackageConfigConverter",
    # Import Management
    "ImportTarget", "ImportTargetList", "ImportAnalyzer", "ImportInfo",
    "ImportOrganizer", "ImportGraph", "CircularImport",
    # Project Management
    "PythonProject", "PyprojectTarget", "ProjectSectionTarget",
    "DependenciesTarget", "ScriptsTarget", "ToolConfigTarget",
    "BlackConfigTarget", "RuffConfigTarget", "MypyConfigTarget",
    "PytestConfigTarget", "IsortConfigTarget", "CoverageConfigTarget",
    # Code Analysis
    "AnalysisTarget", "AnalysisTargetList", "AnalysisType", "AnalysisFinding",
    "AnalysisReport", "AnalysisReporter", "ComplexityAnalyzer", "ComplexityResult",
    "NestingResult", "DeadCodeAnalyzer", "UnusedCodeResult", "PatternFinder",
    "PatternMatch", "CodeMetrics", "FileMetrics", "ModuleMetrics",
    # Security Analysis
    "SecurityTarget", "SecurityTargetList", "SecurityType", "SecurityFinding",
    "SecurityReport", "SecurityReporter", "SecretsScanner", "VulnerabilityScanner",
    # Code Optimization
    "OptimizeTarget", "OptimizeTargetList", "OptimizeType", "OptimizeFinding",
    "DRYAnalyzer", "LoopOptimizer",
    # Patching
    "Patch", "FilePatch", "Hunk", "Change", "PatchFormat", "ChangeType",
    "PatchTarget", "PatchFileTarget", "PatchHunkTarget", "PatchParser",
    "PatchGenerator", "PatchConverter", "PatchAnalyzer", "DetectedOperation", "OperationType",
    # Framework Extensions
    "FlaskProject", "FastAPIProject", "SQLAlchemyProject",
]
