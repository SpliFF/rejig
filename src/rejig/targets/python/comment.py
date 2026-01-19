"""CommentTarget for operations on Python comments."""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from rejig.targets.base import Result, Target

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class CommentTarget(Target):
    """Target for a Python comment.

    Provides operations for reading, modifying, and deleting comments
    in Python source files.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    file_path : Path
        Path to the file containing the comment.
    line_number : int
        1-based line number where the comment is located.
    content : str
        The comment content (including # prefix).

    Examples
    --------
    >>> comments = rj.file("utils.py").find_comments(pattern="TODO")
    >>> for comment in comments:
    ...     print(f"{comment.line_number}: {comment.text}")
    """

    def __init__(
        self,
        rejig: Rejig,
        file_path: Path,
        line_number: int,
        content: str,
    ) -> None:
        super().__init__(rejig)
        self.path = file_path
        self.line_number = line_number
        self._content = content

    @property
    def file_path(self) -> Path:
        """Path to the file containing this comment."""
        return self.path

    @property
    def text(self) -> str:
        """The comment text without the # prefix."""
        match = re.match(r"#\s*(.*)", self._content)
        return match.group(1) if match else self._content

    @property
    def name(self) -> str:
        """Alias for text, used by TargetList filtering."""
        return self.text

    def __repr__(self) -> str:
        preview = self.text[:30] + "..." if len(self.text) > 30 else self.text
        return f"CommentTarget({self.path}:{self.line_number}, {preview!r})"

    def exists(self) -> bool:
        """Check if this comment still exists at the recorded location."""
        if not self.path.exists():
            return False
        try:
            content = self.path.read_text()
            lines = content.splitlines()
            if not (1 <= self.line_number <= len(lines)):
                return False
            return "#" in lines[self.line_number - 1]
        except Exception:
            return False

    def get_content(self) -> Result:
        """Get the content of this comment.

        Returns
        -------
        Result
            Result with comment content in `data` field if successful.
        """
        return Result(success=True, message="OK", data=self._content)

    def rewrite(self, new_content: str) -> Result:
        """Replace the comment with new content.

        Parameters
        ----------
        new_content : str
            New comment content (with or without # prefix).

        Returns
        -------
        Result
            Result of the operation.
        """
        if not self.path.exists():
            return self._operation_failed("rewrite", f"File not found: {self.path}")

        try:
            content = self.path.read_text()
            lines = content.splitlines(keepends=True)

            if not (1 <= self.line_number <= len(lines)):
                return self._operation_failed("rewrite", f"Line {self.line_number} out of range")

            line = lines[self.line_number - 1]

            # Ensure new content has # prefix
            if not new_content.strip().startswith("#"):
                new_content = f"# {new_content}"

            # Find and replace the comment
            comment_match = re.search(r"#.*$", line)
            if not comment_match:
                return self._operation_failed("rewrite", "Comment not found on line")

            # Get the part before the comment
            before_comment = line[: comment_match.start()]
            new_line = before_comment + new_content

            # Preserve trailing newline
            if line.endswith("\n"):
                new_line = new_line.rstrip("\n") + "\n"

            lines[self.line_number - 1] = new_line
            new_file_content = "".join(lines)

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would rewrite comment at line {self.line_number}",
                    files_changed=[self.path],
                )

            self.path.write_text(new_file_content)
            self._content = new_content
            return Result(
                success=True,
                message=f"Rewrote comment at line {self.line_number}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("rewrite", f"Failed to rewrite comment: {e}", e)

    def delete(self) -> Result:
        """Delete this comment from the file.

        If the comment is on a line by itself, the entire line is removed.
        If it's an inline comment, only the comment portion is removed.

        Returns
        -------
        Result
            Result of the operation.
        """
        if not self.path.exists():
            return self._operation_failed("delete", f"File not found: {self.path}")

        try:
            content = self.path.read_text()
            lines = content.splitlines(keepends=True)

            if not (1 <= self.line_number <= len(lines)):
                return self._operation_failed("delete", f"Line {self.line_number} out of range")

            line = lines[self.line_number - 1]
            stripped = line.strip()

            # Check if the line is only a comment
            if stripped.startswith("#"):
                # Remove the entire line
                del lines[self.line_number - 1]
            else:
                # Remove inline comment
                comment_match = re.search(r"\s*#.*$", line.rstrip("\n"))
                if comment_match:
                    new_line = line[: comment_match.start()]
                    if line.endswith("\n"):
                        new_line += "\n"
                    lines[self.line_number - 1] = new_line
                else:
                    return self._operation_failed("delete", "Comment not found on line")

            new_content = "".join(lines)

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would delete comment at line {self.line_number}",
                    files_changed=[self.path],
                )

            self.path.write_text(new_content)
            return Result(
                success=True,
                message=f"Deleted comment at line {self.line_number}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("delete", f"Failed to delete comment: {e}", e)

    @property
    def is_todo(self) -> bool:
        """Check if this is a TODO comment."""
        return bool(re.search(r"\bTODO\b", self.text, re.IGNORECASE))

    @property
    def is_fixme(self) -> bool:
        """Check if this is a FIXME comment."""
        return bool(re.search(r"\bFIXME\b", self.text, re.IGNORECASE))

    @property
    def is_hack(self) -> bool:
        """Check if this is a HACK comment."""
        return bool(re.search(r"\bHACK\b", self.text, re.IGNORECASE))

    @property
    def is_xxx(self) -> bool:
        """Check if this is an XXX comment."""
        return bool(re.search(r"\bXXX\b", self.text, re.IGNORECASE))

    @property
    def is_type_ignore(self) -> bool:
        """Check if this is a type: ignore comment."""
        return "type: ignore" in self.text.lower()

    @property
    def is_noqa(self) -> bool:
        """Check if this is a noqa comment."""
        return "noqa" in self.text.lower()
