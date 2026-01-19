"""LineTarget for operations on a single line in a Python file."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rejig.targets.base import Result, Target

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class LineTarget(Target):
    """Target for a single line in a Python file.

    Provides operations for reading, modifying, and adding directives
    to a specific line of code.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    file_path : Path
        Path to the file containing the line.
    line_number : int
        1-based line number.

    Examples
    --------
    >>> line = rj.file("utils.py").line(42)
    >>> line.add_type_ignore("arg-type")
    >>> line.add_noqa("E501")
    """

    def __init__(self, rejig: Rejig, file_path: Path, line_number: int) -> None:
        super().__init__(rejig)
        self.path = file_path
        self.line_number = line_number

    @property
    def file_path(self) -> Path:
        """Path to the file containing this line."""
        return self.path

    def __repr__(self) -> str:
        return f"LineTarget({self.path}:{self.line_number})"

    def exists(self) -> bool:
        """Check if this line exists in the file."""
        if not self.path.exists():
            return False
        try:
            content = self.path.read_text()
            lines = content.splitlines()
            return 1 <= self.line_number <= len(lines)
        except Exception:
            return False

    def get_content(self) -> Result:
        """Get the content of this line.

        Returns
        -------
        Result
            Result with line content in `data` field if successful.
        """
        if not self.path.exists():
            return self._operation_failed("get_content", f"File not found: {self.path}")

        try:
            content = self.path.read_text()
            lines = content.splitlines()
            if not (1 <= self.line_number <= len(lines)):
                return self._operation_failed(
                    "get_content",
                    f"Line {self.line_number} out of range (file has {len(lines)} lines)",
                )
            return Result(success=True, message="OK", data=lines[self.line_number - 1])
        except Exception as e:
            return self._operation_failed("get_content", f"Failed to read line: {e}", e)

    def _modify_line(self, modifier) -> Result:
        """Apply a modification function to this line."""
        if not self.path.exists():
            return self._operation_failed("modify", f"File not found: {self.path}")

        try:
            content = self.path.read_text()
            lines = content.splitlines(keepends=True)

            # Handle case where last line doesn't have newline
            if lines and not lines[-1].endswith("\n"):
                lines[-1] += "\n"

            if not (1 <= self.line_number <= len(lines)):
                return self._operation_failed(
                    "modify",
                    f"Line {self.line_number} out of range (file has {len(lines)} lines)",
                )

            idx = self.line_number - 1
            original_line = lines[idx].rstrip("\n\r")
            new_line = modifier(original_line)

            if new_line == original_line:
                return Result(success=True, message=f"No changes needed at line {self.line_number}")

            lines[idx] = new_line + "\n"
            new_content = "".join(lines)

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would modify line {self.line_number}",
                    files_changed=[self.path],
                )

            self.path.write_text(new_content)
            return Result(
                success=True,
                message=f"Modified line {self.line_number}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("modify", f"Failed to modify line: {e}", e)

    # ===== Directive operations =====

    def add_type_ignore(self, error_code: str | None = None, reason: str | None = None) -> Result:
        """Add a type: ignore comment to this line.

        Parameters
        ----------
        error_code : str | None
            Specific mypy error code to ignore (e.g., "arg-type").
        reason : str | None
            Optional reason for the ignore.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> line.add_type_ignore()  # Generic ignore
        >>> line.add_type_ignore("arg-type")
        >>> line.add_type_ignore("arg-type", reason="Legacy API")
        """
        def add_ignore(line: str) -> str:
            # Check if type: ignore already exists
            if "# type: ignore" in line:
                return line

            comment = "# type: ignore"
            if error_code:
                comment = f"# type: ignore[{error_code}]"
            if reason:
                comment = f"{comment}  # {reason}"

            # Add before any existing comment
            if "  #" in line:
                # Insert before existing comment
                parts = line.rsplit("  #", 1)
                return f"{parts[0]}  {comment}  #{parts[1]}"
            return f"{line}  {comment}"

        return self._modify_line(add_ignore)

    def add_noqa(self, codes: str | list[str] | None = None) -> Result:
        """Add a noqa comment to this line.

        Parameters
        ----------
        codes : str | list[str] | None
            Specific error codes to suppress (e.g., "E501" or ["E501", "F401"]).

        Returns
        -------
        Result
            Result of the operation.
        """
        def add_noqa_comment(line: str) -> str:
            if "# noqa" in line.lower():
                return line

            if codes:
                if isinstance(codes, list):
                    code_str = ", ".join(codes)
                else:
                    code_str = codes
                comment = f"# noqa: {code_str}"
            else:
                comment = "# noqa"

            if "  #" in line:
                parts = line.rsplit("  #", 1)
                return f"{parts[0]}  {comment}  #{parts[1]}"
            return f"{line}  {comment}"

        return self._modify_line(add_noqa_comment)

    def add_no_cover(self) -> Result:
        """Add a pragma: no cover comment to this line.

        Returns
        -------
        Result
            Result of the operation.
        """
        def add_pragma(line: str) -> str:
            if "# pragma: no cover" in line:
                return line

            if "  #" in line:
                parts = line.rsplit("  #", 1)
                return f"{parts[0]}  # pragma: no cover  #{parts[1]}"
            return f"{line}  # pragma: no cover"

        return self._modify_line(add_pragma)

    def add_fmt_skip(self) -> Result:
        """Add a fmt: skip comment to this line (for black/formatter).

        Returns
        -------
        Result
            Result of the operation.
        """
        def add_fmt(line: str) -> str:
            if "# fmt: skip" in line:
                return line

            if "  #" in line:
                parts = line.rsplit("  #", 1)
                return f"{parts[0]}  # fmt: skip  #{parts[1]}"
            return f"{line}  # fmt: skip"

        return self._modify_line(add_fmt)

    # ===== General modification operations =====

    def rewrite(self, new_content: str) -> Result:
        """Replace the content of this line.

        Parameters
        ----------
        new_content : str
            New content for the line.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self._modify_line(lambda _: new_content)

    def insert_before(self, content: str) -> Result:
        """Insert content before this line.

        Parameters
        ----------
        content : str
            Content to insert (will be added as a new line).

        Returns
        -------
        Result
            Result of the operation.
        """
        if not self.path.exists():
            return self._operation_failed("insert_before", f"File not found: {self.path}")

        try:
            file_content = self.path.read_text()
            lines = file_content.splitlines(keepends=True)

            if not (1 <= self.line_number <= len(lines) + 1):
                return self._operation_failed(
                    "insert_before",
                    f"Line {self.line_number} out of range",
                )

            # Get indentation from the current line
            if self.line_number <= len(lines):
                current_line = lines[self.line_number - 1]
                indent = len(current_line) - len(current_line.lstrip())
                new_line = " " * indent + content + "\n"
            else:
                new_line = content + "\n"

            lines.insert(self.line_number - 1, new_line)
            new_content = "".join(lines)

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would insert before line {self.line_number}",
                    files_changed=[self.path],
                )

            self.path.write_text(new_content)
            return Result(
                success=True,
                message=f"Inserted before line {self.line_number}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("insert_before", f"Failed to insert: {e}", e)

    def insert_after(self, content: str) -> Result:
        """Insert content after this line.

        Parameters
        ----------
        content : str
            Content to insert (will be added as a new line).

        Returns
        -------
        Result
            Result of the operation.
        """
        if not self.path.exists():
            return self._operation_failed("insert_after", f"File not found: {self.path}")

        try:
            file_content = self.path.read_text()
            lines = file_content.splitlines(keepends=True)

            if not (1 <= self.line_number <= len(lines)):
                return self._operation_failed(
                    "insert_after",
                    f"Line {self.line_number} out of range",
                )

            # Get indentation from the current line
            current_line = lines[self.line_number - 1]
            indent = len(current_line) - len(current_line.lstrip())
            new_line = " " * indent + content + "\n"

            lines.insert(self.line_number, new_line)
            new_content = "".join(lines)

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would insert after line {self.line_number}",
                    files_changed=[self.path],
                )

            self.path.write_text(new_content)
            return Result(
                success=True,
                message=f"Inserted after line {self.line_number}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("insert_after", f"Failed to insert: {e}", e)

    def delete(self) -> Result:
        """Delete this line from the file.

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
                return self._operation_failed(
                    "delete",
                    f"Line {self.line_number} out of range",
                )

            del lines[self.line_number - 1]
            new_content = "".join(lines)

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would delete line {self.line_number}",
                    files_changed=[self.path],
                )

            self.path.write_text(new_content)
            return Result(
                success=True,
                message=f"Deleted line {self.line_number}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("delete", f"Failed to delete line: {e}", e)
