"""Patch analyzer for detecting higher-level operations.

This module provides the PatchAnalyzer class for analyzing patches
to detect what kind of operations they represent (class renames,
method additions, etc.) which can be used to generate more idiomatic
rejig code.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rejig.patching.models import FilePatch, Hunk, Patch


class OperationType(Enum):
    """Types of operations detected in patches."""

    # Class operations
    CLASS_ADD = "class_add"
    CLASS_DELETE = "class_delete"
    CLASS_RENAME = "class_rename"

    # Function operations
    FUNCTION_ADD = "function_add"
    FUNCTION_DELETE = "function_delete"
    FUNCTION_RENAME = "function_rename"

    # Method operations
    METHOD_ADD = "method_add"
    METHOD_DELETE = "method_delete"
    METHOD_RENAME = "method_rename"

    # Decorator operations
    DECORATOR_ADD = "decorator_add"
    DECORATOR_REMOVE = "decorator_remove"

    # Import operations
    IMPORT_ADD = "import_add"
    IMPORT_REMOVE = "import_remove"

    # General operations
    LINE_REWRITE = "line_rewrite"
    LINE_INSERT = "line_insert"
    LINE_DELETE = "line_delete"

    # File operations
    FILE_CREATE = "file_create"
    FILE_DELETE = "file_delete"
    FILE_RENAME = "file_rename"


@dataclass
class DetectedOperation:
    """A detected operation from patch analysis.

    Attributes:
        type: Type of operation detected
        file_path: Path to the affected file
        details: Operation-specific details
        hunk_index: Index of hunk this was detected in (if applicable)
        confidence: Confidence score (0.0 - 1.0)
    """

    type: OperationType
    file_path: Path
    details: dict[str, Any] = field(default_factory=dict)
    hunk_index: int | None = None
    confidence: float = 1.0


class PatchAnalyzer:
    """Analyzer for detecting operations in patches.

    Examines patches to identify higher-level refactoring operations
    that can be expressed more idiomatically in rejig code.

    Examples
    --------
    >>> analyzer = PatchAnalyzer()
    >>> ops = analyzer.analyze(patch)
    >>> for op in ops:
    ...     print(f"{op.type.name}: {op.details}")
    """

    # Regex patterns for Python code detection
    _CLASS_DEF = re.compile(r"^(\s*)class\s+(\w+)(?:\s*\([^)]*\))?\s*:")
    _FUNCTION_DEF = re.compile(r"^(\s*)def\s+(\w+)\s*\([^)]*\)\s*(?:->.*)?:")
    _DECORATOR = re.compile(r"^(\s*)@(\w+(?:\.\w+)*(?:\([^)]*\))?)")
    _IMPORT = re.compile(r"^(from\s+[\w.]+\s+import\s+.+|import\s+[\w.,\s]+)$")
    _DOCSTRING_START = re.compile(r'^(\s*)("""|\'\'\').*$')

    def analyze(self, patch: Patch) -> list[DetectedOperation]:
        """Analyze a patch and detect operations.

        Parameters
        ----------
        patch : Patch
            The patch to analyze.

        Returns
        -------
        list[DetectedOperation]
            List of detected operations.
        """
        operations: list[DetectedOperation] = []

        for file_patch in patch.files:
            ops = self.analyze_file_patch(file_patch)
            operations.extend(ops)

        return operations

    def analyze_file_patch(self, file_patch: FilePatch) -> list[DetectedOperation]:
        """Analyze a single file patch.

        Parameters
        ----------
        file_patch : FilePatch
            The file patch to analyze.

        Returns
        -------
        list[DetectedOperation]
            Detected operations for this file.
        """
        operations: list[DetectedOperation] = []
        path = file_patch.path or Path("unknown")

        # File-level operations
        if file_patch.is_new:
            operations.append(DetectedOperation(
                type=OperationType.FILE_CREATE,
                file_path=path,
                details={"path": str(path)},
            ))
            return operations

        if file_patch.is_deleted:
            operations.append(DetectedOperation(
                type=OperationType.FILE_DELETE,
                file_path=path,
                details={"path": str(file_patch.old_path or path)},
            ))
            return operations

        if file_patch.is_renamed:
            operations.append(DetectedOperation(
                type=OperationType.FILE_RENAME,
                file_path=path,
                details={
                    "old_path": str(file_patch.old_path),
                    "new_path": str(file_patch.new_path),
                },
            ))
            # Continue analyzing hunks for content changes

        # Analyze each hunk
        for i, hunk in enumerate(file_patch.hunks):
            hunk_ops = self.analyze_hunk(hunk, path, i)
            operations.extend(hunk_ops)

        # Post-process to detect renames
        operations = self._detect_renames(operations)

        return operations

    def analyze_hunk(
        self,
        hunk: Hunk,
        path: Path,
        hunk_index: int,
    ) -> list[DetectedOperation]:
        """Analyze a single hunk for operations.

        Parameters
        ----------
        hunk : Hunk
            The hunk to analyze.
        path : Path
            Path to the file.
        hunk_index : int
            Index of the hunk in the file.

        Returns
        -------
        list[DetectedOperation]
            Detected operations.
        """
        operations: list[DetectedOperation] = []

        deleted_lines = [c.content for c in hunk.deletions]
        added_lines = [c.content for c in hunk.additions]

        # Check for class definitions
        deleted_classes = self._find_class_defs(deleted_lines)
        added_classes = self._find_class_defs(added_lines)

        for cls in added_classes:
            if cls not in deleted_classes:
                operations.append(DetectedOperation(
                    type=OperationType.CLASS_ADD,
                    file_path=path,
                    details={"name": cls},
                    hunk_index=hunk_index,
                ))

        for cls in deleted_classes:
            if cls not in added_classes:
                operations.append(DetectedOperation(
                    type=OperationType.CLASS_DELETE,
                    file_path=path,
                    details={"name": cls},
                    hunk_index=hunk_index,
                ))

        # Check for function definitions (module-level only)
        deleted_funcs = self._find_function_defs(deleted_lines, module_level=True)
        added_funcs = self._find_function_defs(added_lines, module_level=True)

        for func in added_funcs:
            if func not in deleted_funcs:
                operations.append(DetectedOperation(
                    type=OperationType.FUNCTION_ADD,
                    file_path=path,
                    details={"name": func},
                    hunk_index=hunk_index,
                ))

        for func in deleted_funcs:
            if func not in added_funcs:
                operations.append(DetectedOperation(
                    type=OperationType.FUNCTION_DELETE,
                    file_path=path,
                    details={"name": func},
                    hunk_index=hunk_index,
                ))

        # Check for method definitions (indented)
        deleted_methods = self._find_function_defs(deleted_lines, module_level=False)
        added_methods = self._find_function_defs(added_lines, module_level=False)

        for method in added_methods:
            if method not in deleted_methods:
                operations.append(DetectedOperation(
                    type=OperationType.METHOD_ADD,
                    file_path=path,
                    details={
                        "name": method,
                        "class": hunk.function_context,  # May be set from @@ line
                    },
                    hunk_index=hunk_index,
                ))

        for method in deleted_methods:
            if method not in added_methods:
                operations.append(DetectedOperation(
                    type=OperationType.METHOD_DELETE,
                    file_path=path,
                    details={
                        "name": method,
                        "class": hunk.function_context,
                    },
                    hunk_index=hunk_index,
                ))

        # Check for decorators
        deleted_decorators = self._find_decorators(deleted_lines)
        added_decorators = self._find_decorators(added_lines)

        for dec in added_decorators:
            if dec not in deleted_decorators:
                operations.append(DetectedOperation(
                    type=OperationType.DECORATOR_ADD,
                    file_path=path,
                    details={"decorator": dec},
                    hunk_index=hunk_index,
                ))

        for dec in deleted_decorators:
            if dec not in added_decorators:
                operations.append(DetectedOperation(
                    type=OperationType.DECORATOR_REMOVE,
                    file_path=path,
                    details={"decorator": dec},
                    hunk_index=hunk_index,
                ))

        # Check for import changes
        deleted_imports = self._find_imports(deleted_lines)
        added_imports = self._find_imports(added_lines)

        for imp in added_imports:
            if imp not in deleted_imports:
                operations.append(DetectedOperation(
                    type=OperationType.IMPORT_ADD,
                    file_path=path,
                    details={"import": imp},
                    hunk_index=hunk_index,
                ))

        for imp in deleted_imports:
            if imp not in added_imports:
                operations.append(DetectedOperation(
                    type=OperationType.IMPORT_REMOVE,
                    file_path=path,
                    details={"import": imp},
                    hunk_index=hunk_index,
                ))

        # If no specific operations detected, fall back to line operations
        if not operations:
            if deleted_lines and added_lines:
                operations.append(DetectedOperation(
                    type=OperationType.LINE_REWRITE,
                    file_path=path,
                    details={
                        "start_line": hunk.old_start,
                        "end_line": hunk.old_start + hunk.old_count - 1,
                        "old_content": "\n".join(deleted_lines),
                        "new_content": "\n".join(added_lines),
                    },
                    hunk_index=hunk_index,
                ))
            elif added_lines:
                operations.append(DetectedOperation(
                    type=OperationType.LINE_INSERT,
                    file_path=path,
                    details={
                        "at_line": hunk.new_start,
                        "content": "\n".join(added_lines),
                    },
                    hunk_index=hunk_index,
                ))
            elif deleted_lines:
                operations.append(DetectedOperation(
                    type=OperationType.LINE_DELETE,
                    file_path=path,
                    details={
                        "start_line": hunk.old_start,
                        "end_line": hunk.old_start + hunk.old_count - 1,
                    },
                    hunk_index=hunk_index,
                ))

        return operations

    def _find_class_defs(self, lines: list[str]) -> list[str]:
        """Find class definitions in lines."""
        classes = []
        for line in lines:
            match = self._CLASS_DEF.match(line)
            if match:
                classes.append(match.group(2))
        return classes

    def _find_function_defs(
        self,
        lines: list[str],
        module_level: bool,
    ) -> list[str]:
        """Find function definitions in lines.

        Parameters
        ----------
        lines : list[str]
            Lines to search.
        module_level : bool
            If True, only find module-level (non-indented) functions.
            If False, only find indented (method-like) functions.
        """
        funcs = []
        for line in lines:
            match = self._FUNCTION_DEF.match(line)
            if match:
                indent = match.group(1)
                name = match.group(2)
                is_module_level = len(indent) == 0
                if module_level == is_module_level:
                    funcs.append(name)
        return funcs

    def _find_decorators(self, lines: list[str]) -> list[str]:
        """Find decorator lines."""
        decorators = []
        for line in lines:
            match = self._DECORATOR.match(line)
            if match:
                decorators.append(match.group(2))
        return decorators

    def _find_imports(self, lines: list[str]) -> list[str]:
        """Find import statements."""
        imports = []
        for line in lines:
            match = self._IMPORT.match(line.strip())
            if match:
                imports.append(match.group(1))
        return imports

    def _detect_renames(
        self,
        operations: list[DetectedOperation],
    ) -> list[DetectedOperation]:
        """Post-process to detect renames (paired add/delete).

        If we see a class delete and add in the same file, it might
        be a rename operation.
        """
        result = []
        processed_indices: set[int] = set()

        for i, op in enumerate(operations):
            if i in processed_indices:
                continue

            # Look for potential rename pairs
            if op.type == OperationType.CLASS_DELETE:
                # Look for a class add in same file
                for j, other in enumerate(operations):
                    if j in processed_indices or j == i:
                        continue
                    if (
                        other.type == OperationType.CLASS_ADD
                        and other.file_path == op.file_path
                    ):
                        # This looks like a rename
                        result.append(DetectedOperation(
                            type=OperationType.CLASS_RENAME,
                            file_path=op.file_path,
                            details={
                                "old_name": op.details["name"],
                                "new_name": other.details["name"],
                            },
                            confidence=0.8,
                        ))
                        processed_indices.add(i)
                        processed_indices.add(j)
                        break
                else:
                    result.append(op)

            elif op.type == OperationType.FUNCTION_DELETE:
                for j, other in enumerate(operations):
                    if j in processed_indices or j == i:
                        continue
                    if (
                        other.type == OperationType.FUNCTION_ADD
                        and other.file_path == op.file_path
                    ):
                        result.append(DetectedOperation(
                            type=OperationType.FUNCTION_RENAME,
                            file_path=op.file_path,
                            details={
                                "old_name": op.details["name"],
                                "new_name": other.details["name"],
                            },
                            confidence=0.8,
                        ))
                        processed_indices.add(i)
                        processed_indices.add(j)
                        break
                else:
                    result.append(op)

            elif op.type == OperationType.METHOD_DELETE:
                for j, other in enumerate(operations):
                    if j in processed_indices or j == i:
                        continue
                    if (
                        other.type == OperationType.METHOD_ADD
                        and other.file_path == op.file_path
                        and other.details.get("class") == op.details.get("class")
                    ):
                        result.append(DetectedOperation(
                            type=OperationType.METHOD_RENAME,
                            file_path=op.file_path,
                            details={
                                "old_name": op.details["name"],
                                "new_name": other.details["name"],
                                "class": op.details.get("class"),
                            },
                            confidence=0.8,
                        ))
                        processed_indices.add(i)
                        processed_indices.add(j)
                        break
                else:
                    result.append(op)

            elif op.type not in (
                OperationType.CLASS_ADD,
                OperationType.FUNCTION_ADD,
                OperationType.METHOD_ADD,
            ):
                result.append(op)

        # Add remaining adds that weren't paired
        for i, op in enumerate(operations):
            if i not in processed_indices and op.type in (
                OperationType.CLASS_ADD,
                OperationType.FUNCTION_ADD,
                OperationType.METHOD_ADD,
            ):
                result.append(op)

        return result

    def get_optimal_operations(
        self,
        patch: Patch,
    ) -> list[DetectedOperation]:
        """Get the optimal set of operations to represent a patch.

        This filters and consolidates detected operations to provide
        the most efficient set of rejig operations.

        Parameters
        ----------
        patch : Patch
            The patch to analyze.

        Returns
        -------
        list[DetectedOperation]
            Optimized list of operations.
        """
        operations = self.analyze(patch)

        # Sort by confidence (higher first), then by operation type
        # (prefer specific operations over generic line operations)
        type_priority = {
            OperationType.CLASS_RENAME: 0,
            OperationType.FUNCTION_RENAME: 0,
            OperationType.METHOD_RENAME: 0,
            OperationType.CLASS_ADD: 1,
            OperationType.CLASS_DELETE: 1,
            OperationType.FUNCTION_ADD: 1,
            OperationType.FUNCTION_DELETE: 1,
            OperationType.METHOD_ADD: 2,
            OperationType.METHOD_DELETE: 2,
            OperationType.DECORATOR_ADD: 3,
            OperationType.DECORATOR_REMOVE: 3,
            OperationType.IMPORT_ADD: 4,
            OperationType.IMPORT_REMOVE: 4,
            OperationType.LINE_REWRITE: 5,
            OperationType.LINE_INSERT: 5,
            OperationType.LINE_DELETE: 5,
            OperationType.FILE_CREATE: 6,
            OperationType.FILE_DELETE: 6,
            OperationType.FILE_RENAME: 6,
        }

        operations.sort(
            key=lambda op: (
                -op.confidence,
                type_priority.get(op.type, 99),
                str(op.file_path),
            )
        )

        return operations
