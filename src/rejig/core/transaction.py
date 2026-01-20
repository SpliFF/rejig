"""Transaction support for atomic batch operations.

This module provides the Transaction class for grouping multiple
file modifications into an atomic unit that can be committed or
rolled back.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from rejig.core.diff import combine_diffs, generate_diff
from rejig.core.results import BatchResult, ErrorResult, Result

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


@dataclass
class PendingChange:
    """A pending file change within a transaction."""

    path: Path
    original_content: str
    new_content: str
    operation: str


@dataclass
class Transaction:
    """A transaction for atomic batch operations.

    All file writes within a transaction are collected and applied
    atomically on commit(). If any write fails, all changes are
    rolled back.

    This class should not be instantiated directly. Use the
    `Rejig.transaction()` context manager instead.

    Parameters
    ----------
    _rejig : Rejig
        The parent Rejig instance.

    Examples
    --------
    >>> with rj.transaction() as tx:
    ...     rj.find_class("Foo").rename("Bar")
    ...     rj.find_function("baz").delete()
    ...     print(tx.preview())  # See combined diff
    ...     result = tx.commit()  # Apply all changes atomically
    ...     # or tx.rollback()   # Discard all changes
    """

    _rejig: Rejig
    _pending: dict[Path, PendingChange] = field(default_factory=dict)
    _results: list[Result] = field(default_factory=list)
    _committed: bool = False
    _rolled_back: bool = False

    def add_change(
        self,
        path: Path,
        original: str,
        new_content: str,
        operation: str,
    ) -> Result:
        """Record a pending change (called internally by targets).

        Parameters
        ----------
        path : Path
            Path to the file being modified.
        original : str
            Original content before this change.
        new_content : str
            New content after this change.
        operation : str
            Description of the operation.

        Returns
        -------
        Result
            A "pending" result (change not yet applied).
        """
        if self._committed or self._rolled_back:
            return ErrorResult(
                message="Transaction already finalized",
                operation=operation,
            )

        # If we already have a pending change for this file,
        # the new change builds on the previous new_content
        if path in self._pending:
            existing = self._pending[path]
            # Keep original from first change, use new content
            self._pending[path] = PendingChange(
                path=path,
                original_content=existing.original_content,
                new_content=new_content,
                operation=f"{existing.operation}, {operation}",
            )
        else:
            self._pending[path] = PendingChange(
                path=path,
                original_content=original,
                new_content=new_content,
                operation=operation,
            )

        # Return a "pending" result (not yet applied)
        diff = generate_diff(original, new_content, path)
        result = Result(
            success=True,
            message=f"[PENDING] {operation}",
            files_changed=[path],
            diff=diff,
            diffs={path: diff},
        )
        self._results.append(result)
        return result

    def get_current_content(self, path: Path) -> str | None:
        """Get the current content for a file (pending changes or disk).

        Parameters
        ----------
        path : Path
            Path to the file.

        Returns
        -------
        str | None
            The current content (pending if modified, disk otherwise).
        """
        if path in self._pending:
            return self._pending[path].new_content
        if path.exists():
            return path.read_text()
        return None

    def commit(self) -> BatchResult:
        """Apply all pending changes atomically.

        Returns BatchResult with success if all writes succeed.
        On any failure, attempts to rollback already-written files.

        Returns
        -------
        BatchResult
            Result of the commit operation.
        """
        if self._committed:
            return BatchResult([ErrorResult(message="Transaction already committed")])
        if self._rolled_back:
            return BatchResult([ErrorResult(message="Transaction was rolled back")])

        self._committed = True

        if not self._pending:
            return BatchResult([Result(success=True, message="No changes to commit")])

        if self._rejig.dry_run:
            # In dry_run, just return the collected diffs
            diffs: dict[Path, str] = {}
            for path, change in self._pending.items():
                diffs[path] = generate_diff(
                    change.original_content,
                    change.new_content,
                    path,
                )
            return BatchResult([
                Result(
                    success=True,
                    message=f"[DRY RUN] Would apply {len(self._pending)} changes",
                    files_changed=list(self._pending.keys()),
                    diff=combine_diffs(diffs),
                    diffs=diffs,
                )
            ])

        # Write all changes
        written: list[Path] = []
        results: list[Result] = []

        try:
            for path, change in self._pending.items():
                path.write_text(change.new_content)
                written.append(path)

                diff = generate_diff(
                    change.original_content,
                    change.new_content,
                    path,
                )
                results.append(Result(
                    success=True,
                    message=f"Applied: {change.operation}",
                    files_changed=[path],
                    diff=diff,
                    diffs={path: diff},
                ))

            return BatchResult(results)

        except Exception as e:
            # Rollback already-written files
            for path in written:
                if path in self._pending:
                    try:
                        path.write_text(self._pending[path].original_content)
                    except Exception:
                        pass  # Best effort rollback

            return BatchResult([
                ErrorResult(
                    message=f"Transaction failed, rolled back: {e}",
                    exception=e,
                )
            ])

    def rollback(self) -> Result:
        """Discard all pending changes.

        Returns
        -------
        Result
            Result indicating how many changes were discarded.
        """
        if self._committed:
            return ErrorResult(message="Cannot rollback: transaction already committed")

        self._rolled_back = True
        count = len(self._pending)
        self._pending.clear()
        self._results.clear()

        return Result(success=True, message=f"Rolled back {count} pending changes")

    @property
    def pending_count(self) -> int:
        """Number of files with pending changes."""
        return len(self._pending)

    @property
    def pending_files(self) -> list[Path]:
        """List of files with pending changes."""
        return list(self._pending.keys())

    def preview(self) -> str:
        """Get combined diff of all pending changes.

        Returns
        -------
        str
            Combined unified diff of all pending changes.
        """
        diffs: dict[Path, str] = {}
        for path, change in self._pending.items():
            diffs[path] = generate_diff(
                change.original_content,
                change.new_content,
                path,
            )
        return combine_diffs(diffs)
