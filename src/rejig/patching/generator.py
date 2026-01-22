"""Generator for creating patches from rejig operations.

This module provides the PatchGenerator class for generating Patch
objects from various rejig result types (Result, BatchResult, Transaction).
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rejig.core.results import BatchResult, ErrorResult, Result
from rejig.patching.models import Patch, PatchFormat
from rejig.patching.parser import PatchParser

if TYPE_CHECKING:
    from rejig.core.transaction import Transaction


class PatchGenerator:
    """Generator for creating Patch objects from rejig operations.

    Converts Results, BatchResults, and Transactions into structured
    Patch objects that can be saved, reversed, or converted to code.

    Examples
    --------
    >>> gen = PatchGenerator()
    >>> result = rj.find_class("Foo").rename("Bar")
    >>> patch = gen.from_result(result)
    >>> print(patch.to_unified_diff())

    >>> # From transaction
    >>> with rj.transaction() as tx:
    ...     rj.find_class("Foo").rename("Bar")
    ...     patch = gen.from_transaction(tx)
    """

    def __init__(self) -> None:
        """Initialize the patch generator."""
        self._parser = PatchParser()

    def from_result(self, result: Result) -> Patch:
        """Generate a Patch from a Result object.

        Parameters
        ----------
        result : Result
            A Result from a rejig operation (must have diff data).

        Returns
        -------
        Patch
            A Patch object representing the changes.
        """
        if result.is_error() or not result.diff:
            return Patch()

        return self._parser.parse(result.diff)

    def from_batch_result(self, batch: BatchResult) -> Patch:
        """Generate a Patch from a BatchResult.

        Combines diffs from all successful results into a single Patch.

        Parameters
        ----------
        batch : BatchResult
            A BatchResult from batch operations.

        Returns
        -------
        Patch
            A Patch containing all changes.
        """
        if not batch.diff:
            return Patch()

        return self._parser.parse(batch.diff)

    def from_transaction(self, tx: Transaction) -> Patch:
        """Generate a Patch from a Transaction.

        Parameters
        ----------
        tx : Transaction
            A transaction (can be pending or committed).

        Returns
        -------
        Patch
            A Patch representing all changes in the transaction.
        """
        preview = tx.preview()
        if not preview:
            return Patch()

        return self._parser.parse(preview)

    def from_files(
        self,
        original: dict[Path, str],
        modified: dict[Path, str],
        context_lines: int = 3,
    ) -> Patch:
        """Generate a Patch from before/after file contents.

        This is useful for creating patches from arbitrary file changes,
        not necessarily from rejig operations.

        Parameters
        ----------
        original : dict[Path, str]
            Original file contents keyed by path.
        modified : dict[Path, str]
            Modified file contents keyed by path.
        context_lines : int
            Number of context lines in the diff.

        Returns
        -------
        Patch
            A Patch representing the changes.
        """
        from rejig.core.diff import combine_diffs, generate_diff

        all_paths = set(original.keys()) | set(modified.keys())
        diffs: dict[Path, str] = {}

        for path in all_paths:
            orig = original.get(path, "")
            mod = modified.get(path, "")

            if orig != mod:
                diff = generate_diff(orig, mod, path, context_lines)
                if diff:
                    diffs[path] = diff

        if not diffs:
            return Patch()

        combined = combine_diffs(diffs)
        return self._parser.parse(combined)

    def from_diff_string(self, diff_text: str) -> Patch:
        """Generate a Patch from raw diff text.

        Parameters
        ----------
        diff_text : str
            Raw unified or git diff text.

        Returns
        -------
        Patch
            Parsed Patch object.
        """
        return self._parser.parse(diff_text)

    def to_file(self, patch: Patch, path: Path, overwrite: bool = False) -> Result:
        """Save a Patch to a file.

        Parameters
        ----------
        patch : Patch
            The patch to save.
        path : Path
            Output file path.
        overwrite : bool
            Whether to overwrite existing file.

        Returns
        -------
        Result
            Result indicating success or failure.
        """
        if path.exists() and not overwrite:
            return ErrorResult(
                message=f"File already exists: {path}",
                operation="to_file",
            )

        try:
            diff_text = patch.to_unified_diff()
            path.write_text(diff_text)
            return Result(
                success=True,
                message=f"Saved patch to {path}",
                files_changed=[path],
            )
        except Exception as e:
            return ErrorResult(
                message=f"Failed to write patch: {e}",
                operation="to_file",
                exception=e,
            )


def generate_patch_from_result(result: Result) -> Patch:
    """Convenience function to generate a Patch from a Result.

    Parameters
    ----------
    result : Result
        A Result from a rejig operation.

    Returns
    -------
    Patch
        A Patch representing the changes.
    """
    return PatchGenerator().from_result(result)


def generate_patch_from_batch(batch: BatchResult) -> Patch:
    """Convenience function to generate a Patch from a BatchResult.

    Parameters
    ----------
    batch : BatchResult
        A BatchResult from batch operations.

    Returns
    -------
    Patch
        A Patch containing all changes.
    """
    return PatchGenerator().from_batch_result(batch)
