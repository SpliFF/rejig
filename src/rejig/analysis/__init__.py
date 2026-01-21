"""Code analysis module for identifying complexity, patterns, and unused code.

This module provides tools for analyzing Python code:
- Pattern detection (missing type hints, docstrings, bare excepts, etc.)
- Complexity analysis (cyclomatic complexity, nesting depth, etc.)
- Dead code detection (unused functions, classes, variables)
- Code metrics collection and reporting
"""
from rejig.analysis.complexity import (
    ComplexityAnalyzer,
    ComplexityResult,
    NestingResult,
)
from rejig.analysis.dead_code import (
    DeadCodeAnalyzer,
    UnusedCodeResult,
)
from rejig.analysis.metrics import (
    CodeMetrics,
    FileMetrics,
    ModuleMetrics,
)
from rejig.analysis.patterns import (
    PatternFinder,
    PatternMatch,
)
from rejig.analysis.reporter import (
    AnalysisReport,
    AnalysisReporter,
)
from rejig.analysis.targets import (
    AnalysisTarget,
    AnalysisTargetList,
)

__all__ = [
    # Analyzers
    "ComplexityAnalyzer",
    "DeadCodeAnalyzer",
    "PatternFinder",
    "CodeMetrics",
    "AnalysisReporter",
    # Results
    "ComplexityResult",
    "NestingResult",
    "UnusedCodeResult",
    "PatternMatch",
    "FileMetrics",
    "ModuleMetrics",
    "AnalysisReport",
    # Targets
    "AnalysisTarget",
    "AnalysisTargetList",
]
