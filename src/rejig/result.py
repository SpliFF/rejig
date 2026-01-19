"""Result types for refactoring operations."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RefactorResult:
    """
    Result of a refactoring operation.

    All refactoring methods return this dataclass to indicate success/failure
    and provide information about what was changed.

    Attributes
    ----------
    success : bool
        True if the operation completed successfully, False otherwise.
    message : str
        Human-readable description of what happened. In dry-run mode,
        messages are prefixed with "[DRY RUN]".
    files_changed : list[Path] | None
        List of file paths that were modified (or would be modified in
        dry-run mode). None if no files were changed.

    Examples
    --------
    >>> result = scope.add_attribute("new_attr", "str | None", "None")
    >>> if result.success:
    ...     print(f"Success: {result.message}")
    ...     for f in result.files_changed or []:
    ...         print(f"  Modified: {f}")
    ... else:
    ...     print(f"Failed: {result.message}")
    """

    success: bool
    message: str
    files_changed: list[Path] | None = None

    def __bool__(self) -> bool:
        """Allow using result in boolean context."""
        return self.success


@dataclass
class FindResult:
    """
    Result of a find operation containing matched locations.

    Attributes
    ----------
    matches : list[Match]
        List of matches found.
    """

    matches: list[Match] = field(default_factory=list)

    def __bool__(self) -> bool:
        """True if any matches were found."""
        return len(self.matches) > 0

    def __len__(self) -> int:
        """Number of matches found."""
        return len(self.matches)

    def __iter__(self):
        """Iterate over matches."""
        return iter(self.matches)


@dataclass
class Match:
    """
    A single match from a find operation.

    Attributes
    ----------
    file_path : Path
        Path to the file containing the match.
    name : str
        Name of the matched element (class, function, method, etc.).
    line_number : int
        Line number where the match starts (1-indexed).
    """

    file_path: Path
    name: str
    line_number: int
