"""Result types for find operations.

Note: For refactoring operations, use Result from rejig.targets.base instead.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


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
