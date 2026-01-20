"""Result types for rejig operations.

Note: This module is deprecated. Use Result from rejig.core.results instead.
"""
from __future__ import annotations

# This module previously contained FindResult and Match classes.
# These have been consolidated into the Target API:
# - find_classes() now returns TargetList[ClassTarget]
# - find_functions() now returns TargetList[FunctionTarget]
# - search() now returns TargetList[LineTarget]
