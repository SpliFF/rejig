"""Result types for all operations.

This module defines the core result classes:
- Result - Base result for all operations
- ErrorResult - Result for failed operations
- BatchResult - Aggregate result for batch operations
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator


@dataclass
class Result:
    """Base result for all operations.

    Operations never raise exceptions. Instead, they return Result objects
    that indicate success or failure.

    Attributes:
        success: Whether the operation succeeded
        message: Human-readable description of what happened
        files_changed: List of files that were modified
        data: Optional payload for operations that return data
        diff: Combined unified diff of all changes (if any)
        diffs: Per-file diffs mapping path to diff string
    """

    success: bool
    message: str
    files_changed: list[Path] = field(default_factory=list)
    data: Any = None
    diff: str | None = None
    diffs: dict[Path, str] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.success

    def is_error(self) -> bool:
        """Check if this result represents an error."""
        return not self.success

    def get_diff(self, path: Path | None = None) -> str | None:
        """Get diff for a specific file or combined diff.

        Parameters
        ----------
        path : Path | None
            If provided, returns diff for that specific file.
            If None, returns the combined diff.

        Returns
        -------
        str | None
            The diff string, or None if no diff available.
        """
        if path is not None:
            return self.diffs.get(path)
        return self.diff


@dataclass
class ErrorResult(Result):
    """Result for failed operations - never raises automatically.

    Attributes:
        exception: The original exception, if any
        operation: Name of the attempted operation
        target_repr: String representation of the target
    """

    success: bool = field(default=False, init=False)
    exception: Exception | None = None
    operation: str = ""
    target_repr: str = ""

    def raise_if_error(self) -> None:
        """Explicitly re-raise the exception if the programmer wants to."""
        if self.exception:
            raise self.exception
        raise RuntimeError(self.message)


@dataclass
class BatchResult:
    """Aggregate result for operations applied to multiple targets.

    Used by TargetList when performing batch operations.
    """

    results: list[Result] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """True if all operations succeeded."""
        return all(r.success for r in self.results)

    @property
    def partial_success(self) -> bool:
        """True if at least one operation succeeded."""
        return any(r.success for r in self.results)

    @property
    def all_failed(self) -> bool:
        """True if all operations failed."""
        return all(not r.success for r in self.results)

    @property
    def succeeded(self) -> list[Result]:
        """Results that succeeded."""
        return [r for r in self.results if r.success]

    @property
    def failed(self) -> list[Result]:
        """Results that failed."""
        return [r for r in self.results if not r.success]

    @property
    def files_changed(self) -> list[Path]:
        """All files changed across all operations."""
        files: list[Path] = []
        for r in self.results:
            files.extend(r.files_changed)
        return list(set(files))

    @property
    def diff(self) -> str | None:
        """Combined diff from all results."""
        from rejig.core.diff import combine_diffs

        all_diffs = self.diffs
        if not all_diffs:
            return None
        return combine_diffs(all_diffs)

    @property
    def diffs(self) -> dict[Path, str]:
        """Merged diffs from all results."""
        merged: dict[Path, str] = {}
        for r in self.results:
            merged.update(r.diffs)
        return merged

    def get_diff(self, path: Path | None = None) -> str | None:
        """Get diff for a specific file or combined diff.

        Parameters
        ----------
        path : Path | None
            If provided, returns diff for that specific file.
            If None, returns the combined diff.

        Returns
        -------
        str | None
            The diff string, or None if no diff available.
        """
        if path is not None:
            return self.diffs.get(path)
        return self.diff

    def __bool__(self) -> bool:
        return self.success

    def __len__(self) -> int:
        return len(self.results)

    def __iter__(self) -> Iterator[Result]:
        return iter(self.results)
