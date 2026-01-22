"""Patching module for bidirectional conversion between diffs and rejig operations.

This module provides tools for:
1. Parsing unified diff and git diff formats into structured Patch objects
2. Generating patches from rejig operations (Results, BatchResults, Transactions)
3. Converting patches to equivalent rejig code
4. Applying patches using rejig's target system
5. Reversing patches to undo changes

Example: Parse and apply a patch
--------------------------------
>>> from rejig import Rejig
>>> rj = Rejig("src/")
>>> patch = rj.patch_from_file("changes.patch")
>>> print(f"Files: {patch.file_count}, +{patch.total_additions}/-{patch.total_deletions}")
>>> result = patch.apply()

Example: Generate a patch from rejig operations
----------------------------------------------
>>> rj = Rejig("src/", dry_run=True)
>>> result = rj.find_class("Foo").rename("Bar")
>>> patch = rj.generate_patch(result)
>>> patch.save("rename.patch")

Example: Convert patch to rejig code
-----------------------------------
>>> patch = rj.patch_from_file("changes.patch")
>>> code = patch.to_rejig_code()
>>> print(code)
rj.file("src/models.py").find_class("Foo").rename("Bar")

Example: Generate a Python script from patch
-------------------------------------------
>>> patch = rj.patch_from_file("changes.patch")
>>> script = patch.to_script(description="Apply refactoring")
>>> patch.save_script("apply_changes.py")

Example: Reverse a patch
-----------------------
>>> patch = rj.patch_from_file("changes.patch")
>>> undo = patch.reverse()
>>> undo.apply()

Classes
-------
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
"""
from __future__ import annotations

from rejig.patching.analyzer import (
    DetectedOperation,
    OperationType,
    PatchAnalyzer,
)
from rejig.patching.converter import (
    PatchConverter,
    apply_patch,
    convert_patch_to_code,
    generate_script_from_patch,
    save_script_from_patch,
)
from rejig.patching.generator import (
    PatchGenerator,
    generate_patch_from_batch,
    generate_patch_from_result,
)
from rejig.patching.models import (
    Change,
    ChangeType,
    FilePatch,
    Hunk,
    Patch,
    PatchFormat,
)
from rejig.patching.parser import (
    PatchParser,
    parse_patch,
    parse_patch_file,
)
from rejig.patching.targets import (
    PatchFileTarget,
    PatchHunkTarget,
    PatchTarget,
)

__all__ = [
    # Models
    "Patch",
    "FilePatch",
    "Hunk",
    "Change",
    "PatchFormat",
    "ChangeType",
    # Parser
    "PatchParser",
    "parse_patch",
    "parse_patch_file",
    # Generator
    "PatchGenerator",
    "generate_patch_from_result",
    "generate_patch_from_batch",
    # Converter
    "PatchConverter",
    "convert_patch_to_code",
    "apply_patch",
    "generate_script_from_patch",
    "save_script_from_patch",
    # Analyzer
    "PatchAnalyzer",
    "DetectedOperation",
    "OperationType",
    # Targets
    "PatchTarget",
    "PatchFileTarget",
    "PatchHunkTarget",
]
