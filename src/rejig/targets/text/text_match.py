"""TextMatch target for pattern match results."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from rejig.core.results import Result
from rejig.targets.base import Target

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


@dataclass
class MatchPosition:
    """Position of a text match.

    Attributes:
        start: Character offset of match start.
        end: Character offset of match end.
        line: 1-based line number.
        column: 1-based column number.
    """

    start: int
    end: int
    line: int
    column: int


class TextMatch(Target):
    """Target for a pattern match within a text file.

    Represents a specific match found by TextBlock.find_pattern().
    Allows chaining operations on the matched text.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    path : Path
        Path to the file containing the match.
    match : re.Match
        The regex match object.
    content : str
        The full file content (for position calculations).

    Examples
    --------
    >>> matches = rj.text_block("config.py").find_pattern(r"VERSION = ['\"].*['\"]")
    >>> for match in matches:
    ...     match.replace("VERSION = '2.0.0'")
    """

    def __init__(
        self,
        rejig: Rejig,
        path: Path,
        match: re.Match[str],
        content: str,
    ) -> None:
        super().__init__(rejig)
        self.path = path
        self._match = match
        self._content = content
        self._position: MatchPosition | None = None

    @property
    def file_path(self) -> Path:
        """Path to the file containing this match."""
        return self.path

    @property
    def text(self) -> str:
        """The matched text."""
        return self._match.group(0)

    @property
    def groups(self) -> tuple[str | None, ...]:
        """Captured groups from the match."""
        return self._match.groups()

    @property
    def start(self) -> int:
        """Character offset of match start."""
        return self._match.start()

    @property
    def end(self) -> int:
        """Character offset of match end."""
        return self._match.end()

    @property
    def position(self) -> MatchPosition:
        """Get line/column position of match.

        Returns
        -------
        MatchPosition
            Position information for the match.
        """
        if self._position is None:
            # Calculate line number
            text_before = self._content[: self.start]
            line_num = text_before.count("\n") + 1

            # Calculate column (1-based)
            last_newline = text_before.rfind("\n")
            if last_newline >= 0:
                column = self.start - last_newline
            else:
                column = self.start + 1

            self._position = MatchPosition(
                start=self.start,
                end=self.end,
                line=line_num,
                column=column,
            )
        return self._position

    @property
    def line_number(self) -> int:
        """1-based line number of match start."""
        return self.position.line

    def __repr__(self) -> str:
        text_preview = self.text[:30] + "..." if len(self.text) > 30 else self.text
        return f"TextMatch({self.path}:{self.line_number}, {text_preview!r})"

    def exists(self) -> bool:
        """Check if the match still exists in the file.

        Returns
        -------
        bool
            True if the exact matched text is still in the file.
        """
        content = self._get_file_content(self.path)
        if content is None:
            return False
        return self.text in content

    def get_content(self) -> Result:
        """Get the matched text.

        Returns
        -------
        Result
            Result with matched text in `data` field.
        """
        return Result(success=True, message="OK", data=self.text)

    def replace(self, replacement: str) -> Result:
        """Replace this match with new text.

        Parameters
        ----------
        replacement : str
            Text to replace the match with.

        Returns
        -------
        Result
            Result of the operation.
        """
        # Get current content (transaction-aware)
        current = self._get_file_content(self.path)
        if current is None:
            return self._operation_failed("replace", f"File not found: {self.path}")

        # Verify the match still exists at the expected position
        if current[self.start : self.end] != self.text:
            return self._operation_failed(
                "replace",
                f"Match no longer exists at expected position (file may have changed)",
            )

        # Perform replacement at the exact position
        new_content = current[: self.start] + replacement + current[self.end :]

        return self._write_with_diff(
            self.path,
            current,
            new_content,
            f"replace match at line {self.line_number}",
        )

    def delete(self) -> Result:
        """Delete this match.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.replace("")

    def insert_before(self, content: str) -> Result:
        """Insert content before this match.

        Parameters
        ----------
        content : str
            Content to insert.

        Returns
        -------
        Result
            Result of the operation.
        """
        current = self._get_file_content(self.path)
        if current is None:
            return self._operation_failed("insert_before", f"File not found: {self.path}")

        # Verify the match still exists
        if current[self.start : self.end] != self.text:
            return self._operation_failed(
                "insert_before",
                f"Match no longer exists at expected position",
            )

        new_content = current[: self.start] + content + current[self.start :]

        return self._write_with_diff(
            self.path,
            current,
            new_content,
            f"insert before match at line {self.line_number}",
        )

    def insert_after(self, content: str) -> Result:
        """Insert content after this match.

        Parameters
        ----------
        content : str
            Content to insert.

        Returns
        -------
        Result
            Result of the operation.
        """
        current = self._get_file_content(self.path)
        if current is None:
            return self._operation_failed("insert_after", f"File not found: {self.path}")

        # Verify the match still exists
        if current[self.start : self.end] != self.text:
            return self._operation_failed(
                "insert_after",
                f"Match no longer exists at expected position",
            )

        new_content = current[: self.end] + content + current[self.end :]

        return self._write_with_diff(
            self.path,
            current,
            new_content,
            f"insert after match at line {self.line_number}",
        )
