"""TextBlock target for raw text manipulation without AST parsing."""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from rejig.core.results import Result
from rejig.targets.base import Target, TargetList
from rejig.targets.text.text_match import TextMatch

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class TextBlock(Target):
    """Raw text manipulation without AST parsing.

    Use this for any text file where you need pattern-based
    manipulation without language-specific parsing.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    path : Path
        Path to the text file.

    Examples
    --------
    >>> block = rj.text_block("README.md")
    >>> block.find_pattern(r"version: .*").first().replace("version: 2.0.0")
    >>>
    >>> # Or use class method
    >>> block = TextBlock.from_file(Path("config.txt"))
    >>> block.replace_pattern(r"DEBUG = \\w+", "DEBUG = False")
    """

    def __init__(self, rejig: Rejig, path: Path) -> None:
        super().__init__(rejig)
        self.path = path

    @classmethod
    def from_file(cls, path: Path, dry_run: bool = False) -> TextBlock:
        """Create a TextBlock from a file path without a Rejig instance.

        Parameters
        ----------
        path : Path
            Path to the text file.
        dry_run : bool
            Whether to run in dry-run mode.

        Returns
        -------
        TextBlock
            A TextBlock for the specified file.

        Examples
        --------
        >>> block = TextBlock.from_file(Path("config.txt"))
        >>> block.replace_pattern(r"DEBUG = \\w+", "DEBUG = False")
        """
        from rejig.core.rejig import Rejig

        # Create a minimal Rejig instance
        rj = Rejig(path.parent, dry_run=dry_run)
        return cls(rj, path)

    @property
    def file_path(self) -> Path:
        """Path to the text file."""
        return self.path

    def __repr__(self) -> str:
        return f"TextBlock({self.path})"

    def exists(self) -> bool:
        """Check if this file exists.

        Returns
        -------
        bool
            True if the file exists.
        """
        return self.path.exists() and self.path.is_file()

    def get_content(self) -> Result:
        """Get the content of this file.

        Returns
        -------
        Result
            Result with file content in `data` field.
        """
        content = self._get_file_content(self.path)
        if content is None:
            return self._operation_failed("get_content", f"File not found: {self.path}")
        return Result(success=True, message="OK", data=content)

    def find_pattern(self, pattern: str, flags: int = 0) -> TargetList[TextMatch]:
        """Find all matches of a regex pattern.

        Parameters
        ----------
        pattern : str
            Regular expression pattern to search for.
        flags : int
            Regex flags (e.g., re.IGNORECASE, re.MULTILINE).

        Returns
        -------
        TargetList[TextMatch]
            List of TextMatch targets for each match.

        Examples
        --------
        >>> matches = block.find_pattern(r"TODO:.*")
        >>> for match in matches:
        ...     print(f"Line {match.line_number}: {match.text}")
        """
        content = self._get_file_content(self.path)
        if content is None:
            return TargetList(self._rejig, [])

        regex = re.compile(pattern, flags)
        matches = [
            TextMatch(self._rejig, self.path, m, content)
            for m in regex.finditer(content)
        ]

        return TargetList(self._rejig, matches)

    def find_first(self, pattern: str, flags: int = 0) -> TextMatch | None:
        """Find the first match of a pattern.

        Parameters
        ----------
        pattern : str
            Regular expression pattern.
        flags : int
            Regex flags.

        Returns
        -------
        TextMatch | None
            First match, or None if not found.
        """
        matches = self.find_pattern(pattern, flags)
        return matches.first() if matches else None

    def replace_pattern(
        self,
        pattern: str,
        replacement: str,
        count: int = 0,
        flags: int = 0,
    ) -> Result:
        """Replace all occurrences of a pattern.

        Parameters
        ----------
        pattern : str
            Regular expression pattern to replace.
        replacement : str
            Replacement string (can use backreferences like \\1).
        count : int
            Maximum replacements (0 = unlimited).
        flags : int
            Regex flags.

        Returns
        -------
        Result
            Result of the operation.
        """
        content = self._get_file_content(self.path)
        if content is None:
            return self._operation_failed("replace_pattern", f"File not found: {self.path}")

        new_content = re.sub(pattern, replacement, content, count=count, flags=flags)

        if new_content == content:
            return Result(success=True, message="No matches found")

        return self._write_with_diff(
            self.path,
            content,
            new_content,
            f"replace pattern {pattern!r}",
        )

    def insert_at_line(self, line_number: int, content: str) -> Result:
        """Insert content at a specific line.

        Parameters
        ----------
        line_number : int
            1-based line number to insert at.
        content : str
            Content to insert.

        Returns
        -------
        Result
            Result of the operation.
        """
        file_content = self._get_file_content(self.path)
        if file_content is None:
            return self._operation_failed("insert_at_line", f"File not found: {self.path}")

        lines = file_content.splitlines(keepends=True)

        if not (1 <= line_number <= len(lines) + 1):
            return self._operation_failed(
                "insert_at_line",
                f"Line {line_number} out of range (file has {len(lines)} lines)",
            )

        if not content.endswith("\n"):
            content += "\n"

        lines.insert(line_number - 1, content)
        new_content = "".join(lines)

        return self._write_with_diff(
            self.path,
            file_content,
            new_content,
            f"insert at line {line_number}",
        )

    def delete_line(self, line_number: int) -> Result:
        """Delete a specific line.

        Parameters
        ----------
        line_number : int
            1-based line number to delete.

        Returns
        -------
        Result
            Result of the operation.
        """
        file_content = self._get_file_content(self.path)
        if file_content is None:
            return self._operation_failed("delete_line", f"File not found: {self.path}")

        lines = file_content.splitlines(keepends=True)

        if not (1 <= line_number <= len(lines)):
            return self._operation_failed(
                "delete_line",
                f"Line {line_number} out of range",
            )

        del lines[line_number - 1]
        new_content = "".join(lines)

        return self._write_with_diff(
            self.path,
            file_content,
            new_content,
            f"delete line {line_number}",
        )

    def delete_lines(self, start: int, end: int) -> Result:
        """Delete a range of lines (inclusive).

        Parameters
        ----------
        start : int
            1-based starting line number.
        end : int
            1-based ending line number (inclusive).

        Returns
        -------
        Result
            Result of the operation.
        """
        file_content = self._get_file_content(self.path)
        if file_content is None:
            return self._operation_failed("delete_lines", f"File not found: {self.path}")

        lines = file_content.splitlines(keepends=True)

        if not (1 <= start <= len(lines) and 1 <= end <= len(lines) and start <= end):
            return self._operation_failed(
                "delete_lines",
                f"Invalid line range {start}-{end}",
            )

        del lines[start - 1 : end]
        new_content = "".join(lines)

        return self._write_with_diff(
            self.path,
            file_content,
            new_content,
            f"delete lines {start}-{end}",
        )

    def append(self, content: str) -> Result:
        """Append content to the end of the file.

        Parameters
        ----------
        content : str
            Content to append.

        Returns
        -------
        Result
            Result of the operation.
        """
        file_content = self._get_file_content(self.path) or ""

        if file_content and not file_content.endswith("\n"):
            file_content += "\n"

        new_content = file_content + content

        return self._write_with_diff(
            self.path,
            file_content,
            new_content,
            "append content",
        )

    def prepend(self, content: str) -> Result:
        """Prepend content to the beginning of the file.

        Parameters
        ----------
        content : str
            Content to prepend.

        Returns
        -------
        Result
            Result of the operation.
        """
        file_content = self._get_file_content(self.path) or ""

        if not content.endswith("\n"):
            content += "\n"

        new_content = content + file_content

        return self._write_with_diff(
            self.path,
            file_content,
            new_content,
            "prepend content",
        )

    def rewrite(self, new_content: str) -> Result:
        """Replace the entire content of this file.

        Parameters
        ----------
        new_content : str
            New content for the file.

        Returns
        -------
        Result
            Result of the operation.
        """
        file_content = self._get_file_content(self.path) or ""

        return self._write_with_diff(
            self.path,
            file_content,
            new_content,
            "rewrite file",
        )
