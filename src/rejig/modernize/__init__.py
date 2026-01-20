"""Code modernization utilities.

Provides transformers and utilities for updating code to modern Python:
- F-string conversion (from .format() and % formatting)
- Python 2 compatibility removal
- Context manager conversion
- Deprecated API replacement
"""
from __future__ import annotations

from rejig.modernize.context_manager import ConvertToContextManagerTransformer
from rejig.modernize.deprecated import (
    DEPRECATED_IMPORTS,
    DEPRECATED_METHODS,
    DeprecatedUsage,
    DeprecatedUsageFinder,
    OldStyleClassFinder,
    ReplaceDeprecatedTransformer,
    find_deprecated_usage,
    find_old_style_classes,
)
from rejig.modernize.fstrings import (
    FormatToFstringTransformer,
    PercentToFstringTransformer,
)
from rejig.modernize.python2 import (
    AddFutureAnnotationsTransformer,
    RemovePython2CompatTransformer,
    RemoveSixUsageTransformer,
)

__all__ = [
    # F-string conversion
    "FormatToFstringTransformer",
    "PercentToFstringTransformer",
    # Python 2 compatibility
    "RemovePython2CompatTransformer",
    "AddFutureAnnotationsTransformer",
    "RemoveSixUsageTransformer",
    # Context manager
    "ConvertToContextManagerTransformer",
    # Deprecated code
    "DeprecatedUsage",
    "DeprecatedUsageFinder",
    "OldStyleClassFinder",
    "ReplaceDeprecatedTransformer",
    "DEPRECATED_IMPORTS",
    "DEPRECATED_METHODS",
    "find_deprecated_usage",
    "find_old_style_classes",
]
