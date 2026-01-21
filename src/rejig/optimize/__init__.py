"""Code optimization module for improving Python code efficiency.

This module provides tools for optimizing Python code:
- DRY (Don't Repeat Yourself) analysis for finding duplicate code
- Loop optimization for replacing slow loops with comprehensions and builtins

Example
-------
>>> from rejig import Rejig
>>> from rejig.optimize import DRYAnalyzer, LoopOptimizer
>>>
>>> rj = Rejig("src/")
>>>
>>> # Find DRY violations
>>> dry = DRYAnalyzer(rj)
>>> duplicates = dry.find_all_issues()
>>> print(duplicates.summary())
>>>
>>> # Find loop optimization opportunities
>>> loops = LoopOptimizer(rj)
>>> optimizations = loops.find_all_issues()
>>> print(optimizations.summary())
"""
from rejig.optimize.dry import (
    CodeFragment,
    DRYAnalyzer,
    DuplicateGroup,
)
from rejig.optimize.loops import (
    LoopOptimizer,
    LoopPattern,
)
from rejig.optimize.targets import (
    OptimizeFinding,
    OptimizeTarget,
    OptimizeTargetList,
    OptimizeType,
)

__all__ = [
    # Analyzers
    "DRYAnalyzer",
    "LoopOptimizer",
    # Targets
    "OptimizeTarget",
    "OptimizeTargetList",
    "OptimizeType",
    "OptimizeFinding",
    # Supporting classes
    "CodeFragment",
    "DuplicateGroup",
    "LoopPattern",
]
