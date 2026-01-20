"""Diff generation utilities.

This module provides functions for generating unified diffs between
original and modified content.
"""
from __future__ import annotations

import difflib
from pathlib import Path


def generate_diff(
    original: str,
    modified: str,
    path: Path,
    context_lines: int = 3,
) -> str:
    """Generate unified diff between original and modified content.

    Parameters
    ----------
    original : str
        Original file content.
    modified : str
        Modified file content.
    path : Path
        Path to the file (used in diff header).
    context_lines : int
        Number of context lines to include around changes.

    Returns
    -------
    str
        Unified diff string, or empty string if no changes.

    Examples
    --------
    >>> diff = generate_diff("hello\\n", "hello world\\n", Path("test.py"))
    >>> print(diff)
    --- a/test.py
    +++ b/test.py
    @@ -1 +1 @@
    -hello
    +hello world
    """
    if original == modified:
        return ""

    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)

    # Ensure files end with newlines for proper diff formatting
    if original_lines and not original_lines[-1].endswith("\n"):
        original_lines[-1] += "\n"
    if modified_lines and not modified_lines[-1].endswith("\n"):
        modified_lines[-1] += "\n"

    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        n=context_lines,
    )
    return "".join(diff)


def combine_diffs(diffs: dict[Path, str]) -> str:
    """Combine multiple file diffs into a single diff string.

    Parameters
    ----------
    diffs : dict[Path, str]
        Dictionary mapping file paths to their individual diffs.

    Returns
    -------
    str
        Combined diff string with all file diffs.

    Examples
    --------
    >>> diffs = {
    ...     Path("a.py"): "--- a/a.py\\n+++ b/a.py\\n...",
    ...     Path("b.py"): "--- a/b.py\\n+++ b/b.py\\n...",
    ... }
    >>> combined = combine_diffs(diffs)
    """
    # Filter out empty diffs
    non_empty = {p: d for p, d in diffs.items() if d}
    if not non_empty:
        return ""

    # Sort by path for consistent output
    sorted_diffs = sorted(non_empty.items(), key=lambda x: str(x[0]))
    return "\n".join(d for _, d in sorted_diffs)
