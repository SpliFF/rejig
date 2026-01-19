"""LineBlockTarget for operations on a range of lines in a Python file."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rejig.targets.base import Result, Target

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class LineBlockTarget(Target):
    """Target for a contiguous range of lines in a Python file.

    Provides operations for reading, modifying, moving, and
    transforming blocks of code by line numbers.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    file_path : Path
        Path to the file containing the lines.
    start_line : int
        1-based starting line number.
    end_line : int
        1-based ending line number (inclusive).

    Examples
    --------
    >>> block = rj.file("utils.py").lines(10, 20)
    >>> block.indent()
    >>> block.delete()
    """

    def __init__(
        self, rejig: Rejig, file_path: Path, start_line: int, end_line: int
    ) -> None:
        super().__init__(rejig)
        self.path = file_path
        self.start_line = start_line
        self.end_line = end_line

    @property
    def file_path(self) -> Path:
        """Path to the file containing this block."""
        return self.path

    def __repr__(self) -> str:
        return f"LineBlockTarget({self.path}:{self.start_line}-{self.end_line})"

    def exists(self) -> bool:
        """Check if this line range exists in the file."""
        if not self.path.exists():
            return False
        try:
            content = self.path.read_text()
            lines = content.splitlines()
            return (
                1 <= self.start_line <= len(lines)
                and 1 <= self.end_line <= len(lines)
                and self.start_line <= self.end_line
            )
        except Exception:
            return False

    def get_content(self) -> Result:
        """Get the content of this line block.

        Returns
        -------
        Result
            Result with block content in `data` field if successful.
        """
        if not self.path.exists():
            return self._operation_failed("get_content", f"File not found: {self.path}")

        try:
            content = self.path.read_text()
            lines = content.splitlines()

            if not (1 <= self.start_line <= len(lines)):
                return self._operation_failed(
                    "get_content",
                    f"Start line {self.start_line} out of range",
                )
            if not (1 <= self.end_line <= len(lines)):
                return self._operation_failed(
                    "get_content",
                    f"End line {self.end_line} out of range",
                )
            if self.start_line > self.end_line:
                return self._operation_failed(
                    "get_content",
                    f"Invalid range: start ({self.start_line}) > end ({self.end_line})",
                )

            block_lines = lines[self.start_line - 1 : self.end_line]
            return Result(success=True, message="OK", data="\n".join(block_lines))
        except Exception as e:
            return self._operation_failed("get_content", f"Failed to read block: {e}", e)

    def _validate_range(self, lines: list[str]) -> Result | None:
        """Validate that the line range is valid. Returns ErrorResult if invalid."""
        if not (1 <= self.start_line <= len(lines)):
            return self._operation_failed(
                "validate",
                f"Start line {self.start_line} out of range (file has {len(lines)} lines)",
            )
        if not (1 <= self.end_line <= len(lines)):
            return self._operation_failed(
                "validate",
                f"End line {self.end_line} out of range (file has {len(lines)} lines)",
            )
        if self.start_line > self.end_line:
            return self._operation_failed(
                "validate",
                f"Invalid range: start ({self.start_line}) > end ({self.end_line})",
            )
        return None

    # ===== Modification operations =====

    def rewrite(self, new_content: str) -> Result:
        """Replace the content of this line block.

        Parameters
        ----------
        new_content : str
            New content for the block.

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

            error = self._validate_range([l.rstrip("\n\r") for l in lines])
            if error:
                return error

            # Replace the block
            new_lines = new_content.splitlines(keepends=True)
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines[-1] += "\n"

            lines[self.start_line - 1 : self.end_line] = new_lines
            new_file_content = "".join(lines)

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would rewrite lines {self.start_line}-{self.end_line}",
                    files_changed=[self.path],
                )

            self.path.write_text(new_file_content)
            return Result(
                success=True,
                message=f"Rewrote lines {self.start_line}-{self.end_line}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("rewrite", f"Failed to rewrite block: {e}", e)

    def indent(self, levels: int = 1, spaces_per_level: int = 4) -> Result:
        """Indent this line block.

        Parameters
        ----------
        levels : int
            Number of indentation levels to add (default: 1).
        spaces_per_level : int
            Number of spaces per indentation level (default: 4).

        Returns
        -------
        Result
            Result of the operation.
        """
        if not self.path.exists():
            return self._operation_failed("indent", f"File not found: {self.path}")

        try:
            content = self.path.read_text()
            lines = content.splitlines(keepends=True)

            error = self._validate_range([l.rstrip("\n\r") for l in lines])
            if error:
                return error

            indent_str = " " * (levels * spaces_per_level)
            for i in range(self.start_line - 1, self.end_line):
                if lines[i].strip():  # Only indent non-empty lines
                    lines[i] = indent_str + lines[i]

            new_content = "".join(lines)

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would indent lines {self.start_line}-{self.end_line}",
                    files_changed=[self.path],
                )

            self.path.write_text(new_content)
            return Result(
                success=True,
                message=f"Indented lines {self.start_line}-{self.end_line}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("indent", f"Failed to indent block: {e}", e)

    def dedent(self, levels: int = 1, spaces_per_level: int = 4) -> Result:
        """Dedent (unindent) this line block.

        Parameters
        ----------
        levels : int
            Number of indentation levels to remove (default: 1).
        spaces_per_level : int
            Number of spaces per indentation level (default: 4).

        Returns
        -------
        Result
            Result of the operation.
        """
        if not self.path.exists():
            return self._operation_failed("dedent", f"File not found: {self.path}")

        try:
            content = self.path.read_text()
            lines = content.splitlines(keepends=True)

            error = self._validate_range([l.rstrip("\n\r") for l in lines])
            if error:
                return error

            dedent_chars = levels * spaces_per_level
            for i in range(self.start_line - 1, self.end_line):
                line = lines[i]
                # Count leading spaces
                leading_spaces = len(line) - len(line.lstrip(" "))
                # Remove up to dedent_chars spaces
                remove = min(leading_spaces, dedent_chars)
                lines[i] = line[remove:]

            new_content = "".join(lines)

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would dedent lines {self.start_line}-{self.end_line}",
                    files_changed=[self.path],
                )

            self.path.write_text(new_content)
            return Result(
                success=True,
                message=f"Dedented lines {self.start_line}-{self.end_line}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("dedent", f"Failed to dedent block: {e}", e)

    def insert_before(self, content: str) -> Result:
        """Insert content before this line block.

        Parameters
        ----------
        content : str
            Content to insert.

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

            error = self._validate_range([l.rstrip("\n\r") for l in lines])
            if error:
                return error

            # Get indentation from the first line of the block
            first_line = lines[self.start_line - 1]
            indent = len(first_line) - len(first_line.lstrip())

            # Add content with proper indentation
            new_lines = []
            for line in content.splitlines():
                new_lines.append(" " * indent + line + "\n")

            # Insert before the block
            for i, new_line in enumerate(new_lines):
                lines.insert(self.start_line - 1 + i, new_line)

            new_file_content = "".join(lines)

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would insert before line {self.start_line}",
                    files_changed=[self.path],
                )

            self.path.write_text(new_file_content)
            return Result(
                success=True,
                message=f"Inserted before line {self.start_line}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("insert_before", f"Failed to insert: {e}", e)

    def insert_after(self, content: str) -> Result:
        """Insert content after this line block.

        Parameters
        ----------
        content : str
            Content to insert.

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

            error = self._validate_range([l.rstrip("\n\r") for l in lines])
            if error:
                return error

            # Get indentation from the last line of the block
            last_line = lines[self.end_line - 1]
            indent = len(last_line) - len(last_line.lstrip())

            # Add content with proper indentation
            new_lines = []
            for line in content.splitlines():
                new_lines.append(" " * indent + line + "\n")

            # Insert after the block
            for i, new_line in enumerate(new_lines):
                lines.insert(self.end_line + i, new_line)

            new_file_content = "".join(lines)

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would insert after line {self.end_line}",
                    files_changed=[self.path],
                )

            self.path.write_text(new_file_content)
            return Result(
                success=True,
                message=f"Inserted after line {self.end_line}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("insert_after", f"Failed to insert: {e}", e)

    def delete(self) -> Result:
        """Delete this line block from the file.

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

            error = self._validate_range([l.rstrip("\n\r") for l in lines])
            if error:
                return error

            del lines[self.start_line - 1 : self.end_line]
            new_content = "".join(lines)

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would delete lines {self.start_line}-{self.end_line}",
                    files_changed=[self.path],
                )

            self.path.write_text(new_content)
            return Result(
                success=True,
                message=f"Deleted lines {self.start_line}-{self.end_line}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("delete", f"Failed to delete block: {e}", e)

    def move_to(self, destination: int | Target) -> Result:
        """Move this line block to a different location in the same file.

        Parameters
        ----------
        destination : int | Target
            Target line number or LineTarget to move after.

        Returns
        -------
        Result
            Result of the operation.
        """
        if not self.path.exists():
            return self._operation_failed("move_to", f"File not found: {self.path}")

        try:
            content = self.path.read_text()
            lines = content.splitlines(keepends=True)

            error = self._validate_range([l.rstrip("\n\r") for l in lines])
            if error:
                return error

            # Get destination line number
            if isinstance(destination, int):
                dest_line = destination
            elif hasattr(destination, "line_number"):
                dest_line = destination.line_number
            else:
                return self._operation_failed("move_to", "Invalid destination")

            # Extract the block
            block = lines[self.start_line - 1 : self.end_line]

            # Remove the block from original position
            del lines[self.start_line - 1 : self.end_line]

            # Adjust destination if it's after the removed block
            if dest_line > self.end_line:
                dest_line -= len(block)
            elif dest_line >= self.start_line:
                dest_line = self.start_line - 1

            # Insert at destination
            for i, line in enumerate(block):
                lines.insert(dest_line + i, line)

            new_content = "".join(lines)

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would move lines {self.start_line}-{self.end_line} to line {dest_line + 1}",
                    files_changed=[self.path],
                )

            self.path.write_text(new_content)
            return Result(
                success=True,
                message=f"Moved lines {self.start_line}-{self.end_line} to line {dest_line + 1}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("move_to", f"Failed to move block: {e}", e)

    def move_to_file(self, file_path: str | Path, line_number: int) -> Result:
        """Move this line block to a different file.

        Parameters
        ----------
        file_path : str | Path
            Path to the destination file.
        line_number : int
            1-based line number to insert at in the destination file.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> block = rj.file("source.py").lines(10, 20)
        >>> block.move_to_file("destination.py", 5)
        """
        if not self.path.exists():
            return self._operation_failed("move_to_file", f"Source file not found: {self.path}")

        dest_path = Path(file_path) if isinstance(file_path, str) else file_path

        # Resolve relative paths against rejig root
        if not dest_path.is_absolute():
            dest_path = self._rejig.root / dest_path

        if not dest_path.exists():
            return self._operation_failed("move_to_file", f"Destination file not found: {dest_path}")

        try:
            # Read source file
            source_content = self.path.read_text()
            source_lines = source_content.splitlines(keepends=True)

            error = self._validate_range([l.rstrip("\n\r") for l in source_lines])
            if error:
                return error

            # Extract the block from source
            block = source_lines[self.start_line - 1 : self.end_line]

            # Read destination file
            dest_content = dest_path.read_text()
            dest_lines = dest_content.splitlines(keepends=True)

            # Ensure last line has newline
            if dest_lines and not dest_lines[-1].endswith("\n"):
                dest_lines[-1] += "\n"

            # Validate destination line number
            if not (1 <= line_number <= len(dest_lines) + 1):
                return self._operation_failed(
                    "move_to_file",
                    f"Destination line {line_number} out of range (file has {len(dest_lines)} lines)",
                )

            # Insert block at destination
            for i, line in enumerate(block):
                dest_lines.insert(line_number - 1 + i, line)

            # Remove block from source
            del source_lines[self.start_line - 1 : self.end_line]

            new_source_content = "".join(source_lines)
            new_dest_content = "".join(dest_lines)

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would move lines {self.start_line}-{self.end_line} from {self.path} to {dest_path}:{line_number}",
                    files_changed=[self.path, dest_path],
                )

            # Write both files
            self.path.write_text(new_source_content)
            dest_path.write_text(new_dest_content)

            return Result(
                success=True,
                message=f"Moved lines {self.start_line}-{self.end_line} from {self.path} to {dest_path}:{line_number}",
                files_changed=[self.path, dest_path],
            )
        except Exception as e:
            return self._operation_failed("move_to_file", f"Failed to move block: {e}", e)

    def replace(self, pattern: str, replacement: str) -> Result:
        """Replace pattern in this line block.

        Parameters
        ----------
        pattern : str
            Regex pattern to search for.
        replacement : str
            Replacement string.

        Returns
        -------
        Result
            Result of the operation.
        """
        import re

        if not self.path.exists():
            return self._operation_failed("replace", f"File not found: {self.path}")

        try:
            content = self.path.read_text()
            lines = content.splitlines(keepends=True)

            error = self._validate_range([l.rstrip("\n\r") for l in lines])
            if error:
                return error

            regex = re.compile(pattern)
            changed = False

            for i in range(self.start_line - 1, self.end_line):
                new_line = regex.sub(replacement, lines[i])
                if new_line != lines[i]:
                    lines[i] = new_line
                    changed = True

            if not changed:
                return Result(
                    success=True,
                    message=f"No matches found in lines {self.start_line}-{self.end_line}",
                )

            new_content = "".join(lines)

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would replace pattern in lines {self.start_line}-{self.end_line}",
                    files_changed=[self.path],
                )

            self.path.write_text(new_content)
            return Result(
                success=True,
                message=f"Replaced pattern in lines {self.start_line}-{self.end_line}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("replace", f"Failed to replace: {e}", e)
