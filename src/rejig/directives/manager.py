"""Directive manager for adding, removing, and cleaning up linting directives."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rejig.core.results import ErrorResult, Result
from rejig.directives.parser import DirectiveParser, DirectiveType, DIRECTIVE_TYPES

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class DirectiveManager:
    """Manage linting directives in Python source files.

    Provides methods to add, remove, and clean up directive comments
    like ``# type: ignore``, ``# noqa``, ``# pylint: disable``, etc.

    Parameters
    ----------
    rejig : Rejig
        The Rejig instance to use.

    Examples
    --------
    >>> manager = DirectiveManager(rj)
    >>> manager.add_type_ignore("myfile.py", 42, codes=["arg-type"])
    >>> manager.add_noqa("myfile.py", 10, codes=["E501"])
    >>> manager.remove_directive("myfile.py", 42, "type_ignore")
    """

    def __init__(self, rejig: Rejig) -> None:
        self._rejig = rejig
        self._parser = DirectiveParser()

    def _resolve_path(self, file_path: str | Path) -> Path:
        """Resolve file path relative to the rejig root."""
        p = Path(file_path)
        if p.is_absolute():
            return p
        return self._rejig.root / p

    def _modify_line(self, file_path: str | Path, line_number: int, modifier) -> Result:
        """Apply a modifier function to a specific line in a file.

        Parameters
        ----------
        file_path : str | Path
            Path to the file.
        line_number : int
            1-based line number.
        modifier : callable
            Function that takes a line string and returns the modified line.
        """
        resolved = self._resolve_path(file_path)
        if not resolved.exists():
            return ErrorResult(
                message=f"File not found: {resolved}",
                operation="modify_line",
            )

        try:
            lines = resolved.read_text().splitlines(keepends=True)
        except (OSError, UnicodeDecodeError) as e:
            return ErrorResult(
                message=f"Cannot read {resolved}: {e}",
                operation="modify_line",
            )

        if line_number < 1 or line_number > len(lines):
            return ErrorResult(
                message=f"Line {line_number} is out of range (file has {len(lines)} lines)",
                operation="modify_line",
            )

        idx = line_number - 1
        original = lines[idx]
        modified = modifier(original)

        if modified == original:
            return Result(
                success=True,
                message=f"No change needed at {resolved}:{line_number}",
            )

        if self._rejig.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would modify {resolved}:{line_number}",
                files_changed=[resolved],
            )

        lines[idx] = modified
        resolved.write_text("".join(lines))
        return Result(
            success=True,
            message=f"Modified directive at {resolved}:{line_number}",
            files_changed=[resolved],
        )

    def _append_comment(self, line: str, comment: str) -> str:
        """Append a comment to a line, preserving the line ending."""
        stripped = line.rstrip("\n\r")
        ending = line[len(stripped):]
        # Remove trailing whitespace from code portion
        code = stripped.rstrip()
        if code:
            return f"{code}  {comment}{ending}"
        return f"{comment}{ending}"

    def add_type_ignore(
        self,
        file_path: str | Path,
        line_number: int,
        codes: list[str] | None = None,
        reason: str | None = None,
    ) -> Result:
        """Add a ``# type: ignore`` comment to a line.

        Parameters
        ----------
        file_path : str | Path
            Path to the file.
        line_number : int
            1-based line number.
        codes : list[str] | None
            Specific mypy error codes (e.g., ["arg-type", "return-value"]).
        reason : str | None
            Optional reason comment.
        """
        code_part = f"[{', '.join(codes)}]" if codes else ""
        reason_part = f"  # {reason}" if reason else ""
        comment = f"# type: ignore{code_part}{reason_part}"

        def modifier(line: str):
            if DirectiveParser.has_type_ignore(line):
                return line  # Already has type: ignore
            return self._append_comment(line, comment)

        return self._modify_line(file_path, line_number, modifier)

    def add_noqa(
        self,
        file_path: str | Path,
        line_number: int,
        codes: list[str] | None = None,
    ) -> Result:
        """Add a ``# noqa`` comment to a line.

        Parameters
        ----------
        file_path : str | Path
            Path to the file.
        line_number : int
            1-based line number.
        codes : list[str] | None
            Specific error codes (e.g., ["E501", "F401"]).
        """
        code_part = f": {', '.join(codes)}" if codes else ""
        comment = f"# noqa{code_part}"

        def modifier(line: str):
            if DirectiveParser.has_noqa(line):
                return line
            return self._append_comment(line, comment)

        return self._modify_line(file_path, line_number, modifier)

    def add_pylint_disable(
        self,
        file_path: str | Path,
        line_number: int,
        codes: list[str] | None = None,
    ) -> Result:
        """Add a ``# pylint: disable=...`` comment to a line.

        Parameters
        ----------
        file_path : str | Path
            Path to the file.
        line_number : int
            1-based line number.
        codes : list[str] | None
            Pylint message codes (e.g., ["line-too-long"]).
        """
        code_part = f"={','.join(codes)}" if codes else ""
        comment = f"# pylint: disable{code_part}"

        def modifier(line: str):
            if DirectiveParser.has_pylint_disable(line):
                return line
            return self._append_comment(line, comment)

        return self._modify_line(file_path, line_number, modifier)

    def add_pylint_enable(
        self,
        file_path: str | Path,
        line_number: int,
        codes: list[str] | None = None,
    ) -> Result:
        """Add a ``# pylint: enable=...`` comment to a line."""
        code_part = f"={','.join(codes)}" if codes else ""
        comment = f"# pylint: enable{code_part}"

        def modifier(line: str):
            return self._append_comment(line, comment)

        return self._modify_line(file_path, line_number, modifier)

    def add_fmt_skip(self, file_path: str | Path, line_number: int) -> Result:
        """Add ``# fmt: skip`` to a line."""
        def modifier(line: str):
            if DirectiveParser.has_fmt_skip(line):
                return line
            return self._append_comment(line, "# fmt: skip")
        return self._modify_line(file_path, line_number, modifier)

    def add_fmt_off(self, file_path: str | Path, line_number: int) -> Result:
        """Add ``# fmt: off`` to a line."""
        def modifier(line: str):
            return self._append_comment(line, "# fmt: off")
        return self._modify_line(file_path, line_number, modifier)

    def add_fmt_on(self, file_path: str | Path, line_number: int) -> Result:
        """Add ``# fmt: on`` to a line."""
        def modifier(line: str):
            return self._append_comment(line, "# fmt: on")
        return self._modify_line(file_path, line_number, modifier)

    def add_no_cover(self, file_path: str | Path, line_number: int) -> Result:
        """Add ``# pragma: no cover`` to a line."""
        def modifier(line: str):
            if DirectiveParser.has_no_cover(line):
                return line
            return self._append_comment(line, "# pragma: no cover")
        return self._modify_line(file_path, line_number, modifier)

    def remove_directive(
        self,
        file_path: str | Path,
        line_number: int,
        directive_type: DirectiveType,
    ) -> Result:
        """Remove a specific directive from a line.

        Parameters
        ----------
        file_path : str | Path
            Path to the file.
        line_number : int
            1-based line number.
        directive_type : DirectiveType
            Type of directive to remove.
        """
        def modifier(line: str):
            return DirectiveParser.remove_directive(line, directive_type) + "\n" if line.endswith("\n") else DirectiveParser.remove_directive(line, directive_type)
        return self._modify_line(file_path, line_number, modifier)

    def remove_all_in_file(
        self,
        file_path: str | Path,
        directive_type: DirectiveType | None = None,
    ) -> Result:
        """Remove all directives of a given type from a file.

        Parameters
        ----------
        file_path : str | Path
            Path to the file.
        directive_type : DirectiveType | None
            Type to remove. If None, removes all directive types.
        """
        resolved = self._resolve_path(file_path)
        if not resolved.exists():
            return ErrorResult(message=f"File not found: {resolved}", operation="remove_all_in_file")

        try:
            content = resolved.read_text()
        except (OSError, UnicodeDecodeError) as e:
            return ErrorResult(message=f"Cannot read {resolved}: {e}", operation="remove_all_in_file")

        lines = content.splitlines(keepends=True)
        changed = False
        types_to_check = [directive_type] if directive_type else list(DIRECTIVE_TYPES)

        for i, line in enumerate(lines):
            for dtype in types_to_check:
                new_line = DirectiveParser.remove_directive(line.rstrip("\n\r"), dtype)
                ending = line[len(line.rstrip("\n\r")):]
                new_line_with_ending = new_line + ending
                if new_line_with_ending != line:
                    lines[i] = new_line_with_ending
                    changed = True

        if not changed:
            return Result(success=True, message=f"No directives to remove in {resolved}")

        if self._rejig.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would remove directives from {resolved}",
                files_changed=[resolved],
            )

        resolved.write_text("".join(lines))
        return Result(
            success=True,
            message=f"Removed directives from {resolved}",
            files_changed=[resolved],
        )

    def cleanup_bare_directives(self, file_path: str | Path) -> Result:
        """Remove bare (non-specific) directives from a file.

        Bare directives like ``# type: ignore`` (no codes) and ``# noqa``
        (no codes) are less precise. This method removes only those,
        leaving specific directives intact.

        Parameters
        ----------
        file_path : str | Path
            Path to the file.
        """
        resolved = self._resolve_path(file_path)
        if not resolved.exists():
            return ErrorResult(message=f"File not found: {resolved}", operation="cleanup_bare_directives")

        try:
            content = resolved.read_text()
        except (OSError, UnicodeDecodeError) as e:
            return ErrorResult(message=f"Cannot read {resolved}: {e}", operation="cleanup_bare_directives")

        lines = content.splitlines(keepends=True)
        changed = False

        for i, line in enumerate(lines):
            directives = self._parser.parse_line(line)
            for d in directives:
                if d.is_bare and d.directive_type in ("type_ignore", "noqa"):
                    new_line = DirectiveParser.remove_directive(line.rstrip("\n\r"), d.directive_type)
                    ending = line[len(line.rstrip("\n\r")):]
                    new_line_with_ending = new_line + ending
                    if new_line_with_ending != line:
                        lines[i] = new_line_with_ending
                        changed = True

        if not changed:
            return Result(success=True, message=f"No bare directives to remove in {resolved}")

        if self._rejig.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would remove bare directives from {resolved}",
                files_changed=[resolved],
            )

        resolved.write_text("".join(lines))
        return Result(
            success=True,
            message=f"Removed bare directives from {resolved}",
            files_changed=[resolved],
        )
