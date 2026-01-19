"""TextFileTarget for operations on any text file."""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from rejig.targets.base import Result, Target

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class TextFileTarget(Target):
    """Target for any text file.

    Provides basic line-based operations for text files that don't have
    a specific format (like Python, TOML, JSON, etc.).

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    path : str | Path
        Path to the text file.

    Examples
    --------
    >>> readme = rj.text_file("README.md")
    >>> readme.get_content()
    >>> readme.replace("old text", "new text")
    """

    def __init__(self, rejig: Rejig, path: str | Path) -> None:
        super().__init__(rejig)
        self.path = Path(path) if isinstance(path, str) else path

    @property
    def file_path(self) -> Path:
        """Path to the text file."""
        return self.path

    def __repr__(self) -> str:
        return f"TextFileTarget({self.path})"

    def exists(self) -> bool:
        """Check if this file exists."""
        return self.path.exists() and self.path.is_file()

    def get_content(self) -> Result:
        """Get the content of this file.

        Returns
        -------
        Result
            Result with file content in `data` field if successful.
        """
        if not self.exists():
            return self._operation_failed("get_content", f"File not found: {self.path}")

        try:
            content = self.path.read_text()
            return Result(success=True, message="OK", data=content)
        except Exception as e:
            return self._operation_failed("get_content", f"Failed to read file: {e}", e)

    def _write_content(self, content: str) -> Result:
        """Write content to this file (internal helper)."""
        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would modify {self.path}",
                files_changed=[self.path],
            )
        try:
            self.path.write_text(content)
            return Result(
                success=True,
                message=f"Modified {self.path}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("write", f"Failed to write file: {e}", e)

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
        return self._write_content(new_content)

    def replace(self, pattern: str, replacement: str, count: int = 0) -> Result:
        """Replace pattern in the file content.

        Parameters
        ----------
        pattern : str
            Regex pattern to search for.
        replacement : str
            Replacement string.
        count : int
            Maximum number of replacements (0 = all).

        Returns
        -------
        Result
            Result of the operation.
        """
        result = self.get_content()
        if result.is_error():
            return result

        content = result.data
        try:
            new_content = re.sub(pattern, replacement, content, count=count)

            if new_content == content:
                return Result(success=True, message="No matches found")

            return self._write_content(new_content)
        except Exception as e:
            return self._operation_failed("replace", f"Failed to replace: {e}", e)

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
        result = self.get_content()
        if result.is_error():
            # File doesn't exist, create it
            return self._write_content(content)

        current = result.data
        if not current.endswith("\n"):
            current += "\n"

        return self._write_content(current + content)

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
        result = self.get_content()
        if result.is_error():
            return self._write_content(content)

        current = result.data
        if not content.endswith("\n"):
            content += "\n"

        return self._write_content(content + current)

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
        result = self.get_content()
        if result.is_error():
            return result

        lines = result.data.splitlines(keepends=True)

        if not (1 <= line_number <= len(lines) + 1):
            return self._operation_failed(
                "insert_at_line",
                f"Line {line_number} out of range (file has {len(lines)} lines)",
            )

        if not content.endswith("\n"):
            content += "\n"

        lines.insert(line_number - 1, content)
        return self._write_content("".join(lines))

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
        result = self.get_content()
        if result.is_error():
            return result

        lines = result.data.splitlines(keepends=True)

        if not (1 <= line_number <= len(lines)):
            return self._operation_failed(
                "delete_line",
                f"Line {line_number} out of range (file has {len(lines)} lines)",
            )

        del lines[line_number - 1]
        return self._write_content("".join(lines))

    def delete_lines(self, start: int, end: int) -> Result:
        """Delete a range of lines.

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
        result = self.get_content()
        if result.is_error():
            return result

        lines = result.data.splitlines(keepends=True)

        if not (1 <= start <= len(lines) and 1 <= end <= len(lines) and start <= end):
            return self._operation_failed(
                "delete_lines",
                f"Invalid line range {start}-{end} (file has {len(lines)} lines)",
            )

        del lines[start - 1 : end]
        return self._write_content("".join(lines))

    def get_line(self, line_number: int) -> str | None:
        """Get a specific line.

        Parameters
        ----------
        line_number : int
            1-based line number.

        Returns
        -------
        str | None
            The line content, or None if out of range.
        """
        result = self.get_content()
        if result.is_error():
            return None

        lines = result.data.splitlines()
        if 1 <= line_number <= len(lines):
            return lines[line_number - 1]
        return None

    def line_count(self) -> int:
        """Get the number of lines in the file.

        Returns
        -------
        int
            Number of lines.
        """
        result = self.get_content()
        if result.is_error():
            return 0

        return len(result.data.splitlines())

    def find_lines(self, pattern: str) -> list[tuple[int, str]]:
        """Find lines matching a pattern.

        Parameters
        ----------
        pattern : str
            Regex pattern to search for.

        Returns
        -------
        list[tuple[int, str]]
            List of (line_number, line_content) tuples.
        """
        result = self.get_content()
        if result.is_error():
            return []

        matches = []
        regex = re.compile(pattern)
        for i, line in enumerate(result.data.splitlines(), 1):
            if regex.search(line):
                matches.append((i, line))
        return matches

    def delete(self) -> Result:
        """Delete this file.

        Returns
        -------
        Result
            Result of the operation.
        """
        if not self.exists():
            return self._operation_failed("delete", f"File not found: {self.path}")

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would delete {self.path}",
                files_changed=[self.path],
            )

        try:
            self.path.unlink()
            return Result(
                success=True,
                message=f"Deleted {self.path}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("delete", f"Failed to delete file: {e}", e)
