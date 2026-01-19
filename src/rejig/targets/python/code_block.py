"""CodeBlockTarget for operations on code structures (class, function, if, for, etc.)."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

import libcst as cst

from rejig.targets.base import Result, Target

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig
    from rejig.targets.python.line_block import LineBlockTarget

CodeBlockKind = Literal["class", "function", "method", "if", "for", "while", "try", "with"]


class CodeBlockTarget(Target):
    """Target for a detected code structure (class, function, if-block, etc.).

    This target represents a syntactic code block that can be manipulated
    as a unit. It can be converted to a LineBlockTarget for line-based operations.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    file_path : Path
        Path to the file containing the code block.
    kind : CodeBlockKind
        Type of code block (class, function, if, for, etc.).
    start_line : int
        1-based starting line number.
    end_line : int
        1-based ending line number.
    name : str | None
        Name of the block (for named blocks like classes/functions).

    Examples
    --------
    >>> block = rj.file("utils.py").find_block_at_line(42)
    >>> block.to_line_block().indent()
    """

    def __init__(
        self,
        rejig: Rejig,
        file_path: Path,
        kind: CodeBlockKind,
        start_line: int,
        end_line: int,
        name: str | None = None,
    ) -> None:
        super().__init__(rejig)
        self.path = file_path
        self.kind = kind
        self.start_line = start_line
        self.end_line = end_line
        self.name = name

    @property
    def file_path(self) -> Path:
        """Path to the file containing this code block."""
        return self.path

    def __repr__(self) -> str:
        if self.name:
            return f"CodeBlockTarget({self.kind} {self.name!r}, {self.path}:{self.start_line}-{self.end_line})"
        return f"CodeBlockTarget({self.kind}, {self.path}:{self.start_line}-{self.end_line})"

    def exists(self) -> bool:
        """Check if this code block still exists."""
        if not self.path.exists():
            return False
        try:
            content = self.path.read_text()
            lines = content.splitlines()
            return (
                1 <= self.start_line <= len(lines)
                and 1 <= self.end_line <= len(lines)
            )
        except Exception:
            return False

    def get_content(self) -> Result:
        """Get the content of this code block.

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
                return self._operation_failed("get_content", f"Start line {self.start_line} out of range")
            if not (1 <= self.end_line <= len(lines)):
                return self._operation_failed("get_content", f"End line {self.end_line} out of range")

            block_lines = lines[self.start_line - 1 : self.end_line]
            return Result(success=True, message="OK", data="\n".join(block_lines))
        except Exception as e:
            return self._operation_failed("get_content", f"Failed to read block: {e}", e)

    def to_line_block(self) -> LineBlockTarget:
        """Convert this code block to a LineBlockTarget.

        Returns
        -------
        LineBlockTarget
            A LineBlockTarget covering the same lines.
        """
        from rejig.targets.python.line_block import LineBlockTarget

        return LineBlockTarget(self._rejig, self.path, self.start_line, self.end_line)

    # ===== Delegate common operations to LineBlockTarget =====

    def rewrite(self, new_content: str) -> Result:
        """Replace the content of this code block.

        Parameters
        ----------
        new_content : str
            New content for the block.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.to_line_block().rewrite(new_content)

    def indent(self, levels: int = 1) -> Result:
        """Indent this code block.

        Parameters
        ----------
        levels : int
            Number of indentation levels to add.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.to_line_block().indent(levels)

    def dedent(self, levels: int = 1) -> Result:
        """Dedent (unindent) this code block.

        Parameters
        ----------
        levels : int
            Number of indentation levels to remove.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.to_line_block().dedent(levels)

    def insert_before(self, content: str) -> Result:
        """Insert content before this code block.

        Parameters
        ----------
        content : str
            Content to insert.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.to_line_block().insert_before(content)

    def insert_after(self, content: str) -> Result:
        """Insert content after this code block.

        Parameters
        ----------
        content : str
            Content to insert.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.to_line_block().insert_after(content)

    def delete(self) -> Result:
        """Delete this code block from the file.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.to_line_block().delete()

    def move_to(self, destination: int | Target) -> Result:
        """Move this code block to a different location in the same file.

        Parameters
        ----------
        destination : int | Target
            Target line number to move to.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.to_line_block().move_to(destination)

    def move_to_file(self, file_path: str | Path, line_number: int) -> Result:
        """Move this code block to a different file.

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
        >>> block = rj.file("source.py").block_at_line(10)
        >>> block.move_to_file("destination.py", 5)
        """
        return self.to_line_block().move_to_file(file_path, line_number)

    def replace(self, pattern: str, replacement: str) -> Result:
        """Replace pattern in this code block.

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
        return self.to_line_block().replace(pattern, replacement)

    @classmethod
    def find_at_line(cls, rejig: Rejig, file_path: Path, line_number: int) -> CodeBlockTarget | None:
        """Find the code block containing a specific line.

        Parameters
        ----------
        rejig : Rejig
            The Rejig instance.
        file_path : Path
            Path to the file.
        line_number : int
            1-based line number to search for.

        Returns
        -------
        CodeBlockTarget | None
            The innermost code block containing the line, or None if not found.
        """
        if not file_path.exists():
            return None

        try:
            content = file_path.read_text()
            tree = cst.parse_module(content)

            class BlockFinder(cst.CSTVisitor):
                def __init__(self):
                    self.blocks: list[tuple[CodeBlockKind, str | None, int, int]] = []
                    self._current_positions: list[int] = []

                def _get_line_number(self, node: cst.CSTNode) -> tuple[int, int]:
                    """Get start and end line numbers for a node."""
                    code = tree.code_for_node(node)
                    start_idx = content.find(code)
                    if start_idx == -1:
                        return (0, 0)
                    start_line = content[:start_idx].count("\n") + 1
                    end_line = start_line + code.count("\n")
                    return (start_line, end_line)

                def visit_ClassDef(self, node: cst.ClassDef) -> bool:
                    start, end = self._get_line_number(node)
                    self.blocks.append(("class", node.name.value, start, end))
                    return True

                def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
                    start, end = self._get_line_number(node)
                    self.blocks.append(("function", node.name.value, start, end))
                    return True

                def visit_If(self, node: cst.If) -> bool:
                    start, end = self._get_line_number(node)
                    self.blocks.append(("if", None, start, end))
                    return True

                def visit_For(self, node: cst.For) -> bool:
                    start, end = self._get_line_number(node)
                    self.blocks.append(("for", None, start, end))
                    return True

                def visit_While(self, node: cst.While) -> bool:
                    start, end = self._get_line_number(node)
                    self.blocks.append(("while", None, start, end))
                    return True

                def visit_Try(self, node: cst.Try) -> bool:
                    start, end = self._get_line_number(node)
                    self.blocks.append(("try", None, start, end))
                    return True

                def visit_With(self, node: cst.With) -> bool:
                    start, end = self._get_line_number(node)
                    self.blocks.append(("with", None, start, end))
                    return True

            finder = BlockFinder()
            tree.walk(finder)

            # Find the innermost block containing the line
            containing_blocks = [
                (kind, name, start, end)
                for kind, name, start, end in finder.blocks
                if start <= line_number <= end
            ]

            if not containing_blocks:
                return None

            # Return the smallest (innermost) block
            innermost = min(containing_blocks, key=lambda b: b[3] - b[2])
            kind, name, start, end = innermost

            return cls(rejig, file_path, kind, start, end, name)

        except Exception:
            return None
