"""DirectiveTarget for operations on linting directives."""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterator

from rejig.directives.parser import DirectiveParser, DirectiveType, ParsedDirective
from rejig.targets.base import BatchResult, Result, Target, TargetList

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class DirectiveTarget(Target):
    """Target for a linting directive comment.

    Extends Target with directive-specific attributes and operations.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    file_path : Path
        Path to the file containing the directive.
    line_number : int
        1-based line number where the directive is located.
    directive : ParsedDirective
        The parsed directive information.

    Examples
    --------
    >>> directives = rj.find_type_ignores()
    >>> for d in directives:
    ...     print(f"{d.location}: {d.directive_type} - {d.codes}")
    """

    def __init__(
        self,
        rejig: Rejig,
        file_path: Path,
        line_number: int,
        directive: ParsedDirective,
    ) -> None:
        super().__init__(rejig)
        self.path = file_path
        self._line_number = line_number
        self._directive = directive

    @property
    def file_path(self) -> Path:
        """Path to the file containing this directive."""
        return self.path

    @property
    def line_number(self) -> int:
        """1-based line number."""
        return self._line_number

    @property
    def directive_type(self) -> DirectiveType:
        """Type of directive (type_ignore, noqa, etc.)."""
        return self._directive.directive_type

    @property
    def codes(self) -> list[str]:
        """Error codes associated with the directive."""
        return self._directive.codes

    @property
    def reason(self) -> str | None:
        """Optional reason/comment for the directive."""
        return self._directive.reason

    @property
    def raw_text(self) -> str:
        """The raw directive text as found in the source."""
        return self._directive.raw_text

    @property
    def is_bare(self) -> bool:
        """Check if this is a bare directive (no specific codes)."""
        return self._directive.is_bare

    @property
    def is_specific(self) -> bool:
        """Check if this directive specifies error codes."""
        return self._directive.is_specific

    @property
    def location(self) -> str:
        """Get the file:line location string."""
        return f"{self.path}:{self._line_number}"

    def exists(self) -> bool:
        """Check if this directive still exists in the file."""
        if not self.path.exists():
            return False

        try:
            content = self.path.read_text()
            lines = content.splitlines()
            if not (1 <= self._line_number <= len(lines)):
                return False

            line = lines[self._line_number - 1]
            parser = DirectiveParser()
            directives = parser.parse_line(line)
            return any(d.directive_type == self.directive_type for d in directives)
        except Exception:
            return False

    def __repr__(self) -> str:
        codes_str = f" [{', '.join(self.codes)}]" if self.codes else ""
        return f"DirectiveTarget({self.path}:{self._line_number}, {self.directive_type}{codes_str})"

    def get_content(self) -> Result:
        """Get the content of the line containing this directive.

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
            if not (1 <= self._line_number <= len(lines)):
                return self._operation_failed(
                    "get_content",
                    f"Line {self._line_number} out of range",
                )
            return Result(success=True, message="OK", data=lines[self._line_number - 1])
        except Exception as e:
            return self._operation_failed("get_content", f"Failed to read line: {e}", e)

    def delete(self) -> Result:
        """Remove this directive from the file.

        Returns
        -------
        Result
            Result of the deletion operation.
        """
        if not self.path.exists():
            return self._operation_failed("delete", f"File not found: {self.path}")

        try:
            content = self.path.read_text()
            lines = content.splitlines(keepends=True)

            if not (1 <= self._line_number <= len(lines)):
                return self._operation_failed(
                    "delete",
                    f"Line {self._line_number} out of range",
                )

            idx = self._line_number - 1
            original_line = lines[idx].rstrip("\n\r")
            new_line = DirectiveParser.remove_directive(original_line, self.directive_type)

            if new_line == original_line:
                return Result(success=True, message="Directive not found in line")

            lines[idx] = new_line + "\n"
            new_content = "".join(lines)

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would remove {self.directive_type} from line {self._line_number}",
                    files_changed=[self.path],
                )

            self.path.write_text(new_content)
            return Result(
                success=True,
                message=f"Removed {self.directive_type} from {self.path}:{self._line_number}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("delete", f"Failed to remove directive: {e}", e)

    def remove(self) -> Result:
        """Alias for delete()."""
        return self.delete()

    def add_code(self, code: str) -> Result:
        """Add an error code to this directive.

        Parameters
        ----------
        code : str
            Error code to add.

        Returns
        -------
        Result
            Result of the operation.
        """
        if code in self.codes:
            return Result(success=True, message=f"Code '{code}' already in directive")

        if not self.path.exists():
            return self._operation_failed("add_code", f"File not found: {self.path}")

        try:
            content = self.path.read_text()
            lines = content.splitlines(keepends=True)

            if not (1 <= self._line_number <= len(lines)):
                return self._operation_failed(
                    "add_code",
                    f"Line {self._line_number} out of range",
                )

            idx = self._line_number - 1
            original_line = lines[idx].rstrip("\n\r")

            # Build new directive based on type
            new_codes = self.codes + [code]

            if self.directive_type == "type_ignore":
                new_directive = f"# type: ignore[{', '.join(new_codes)}]"
            elif self.directive_type == "noqa":
                new_directive = f"# noqa: {', '.join(new_codes)}"
            elif self.directive_type == "pylint_disable":
                new_directive = f"# pylint: disable={','.join(new_codes)}"
            else:
                return self._operation_failed(
                    "add_code",
                    f"Cannot add code to {self.directive_type} directive",
                )

            # Replace old directive with new
            new_line = DirectiveParser.remove_directive(original_line, self.directive_type)
            new_line = f"{new_line}  {new_directive}" if new_line.strip() else new_directive

            lines[idx] = new_line + "\n"
            new_content = "".join(lines)

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would add code '{code}' to directive",
                    files_changed=[self.path],
                )

            self.path.write_text(new_content)
            self._directive.codes.append(code)
            return Result(
                success=True,
                message=f"Added code '{code}' to directive",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("add_code", f"Failed to add code: {e}", e)

    def remove_code(self, code: str) -> Result:
        """Remove an error code from this directive.

        Parameters
        ----------
        code : str
            Error code to remove.

        Returns
        -------
        Result
            Result of the operation.
        """
        if code not in self.codes:
            return Result(success=True, message=f"Code '{code}' not in directive")

        if len(self.codes) == 1:
            # Removing the only code makes it bare
            return self._operation_failed(
                "remove_code",
                "Cannot remove the only code - use delete() to remove the directive",
            )

        if not self.path.exists():
            return self._operation_failed("remove_code", f"File not found: {self.path}")

        try:
            content = self.path.read_text()
            lines = content.splitlines(keepends=True)

            if not (1 <= self._line_number <= len(lines)):
                return self._operation_failed(
                    "remove_code",
                    f"Line {self._line_number} out of range",
                )

            idx = self._line_number - 1
            original_line = lines[idx].rstrip("\n\r")

            # Build new directive with code removed
            new_codes = [c for c in self.codes if c != code]

            if self.directive_type == "type_ignore":
                new_directive = f"# type: ignore[{', '.join(new_codes)}]"
            elif self.directive_type == "noqa":
                new_directive = f"# noqa: {', '.join(new_codes)}"
            elif self.directive_type == "pylint_disable":
                new_directive = f"# pylint: disable={','.join(new_codes)}"
            else:
                return self._operation_failed(
                    "remove_code",
                    f"Cannot remove code from {self.directive_type} directive",
                )

            # Replace old directive with new
            new_line = DirectiveParser.remove_directive(original_line, self.directive_type)
            new_line = f"{new_line}  {new_directive}" if new_line.strip() else new_directive

            lines[idx] = new_line + "\n"
            new_content = "".join(lines)

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would remove code '{code}' from directive",
                    files_changed=[self.path],
                )

            self.path.write_text(new_content)
            self._directive.codes.remove(code)
            return Result(
                success=True,
                message=f"Removed code '{code}' from directive",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("remove_code", f"Failed to remove code: {e}", e)

    def set_reason(self, reason: str) -> Result:
        """Set or update the reason comment for this directive.

        Parameters
        ----------
        reason : str
            The reason to add after the directive.

        Returns
        -------
        Result
            Result of the operation.
        """
        if not self.path.exists():
            return self._operation_failed("set_reason", f"File not found: {self.path}")

        try:
            content = self.path.read_text()
            lines = content.splitlines(keepends=True)

            if not (1 <= self._line_number <= len(lines)):
                return self._operation_failed(
                    "set_reason",
                    f"Line {self._line_number} out of range",
                )

            idx = self._line_number - 1
            original_line = lines[idx].rstrip("\n\r")

            # Build new directive with reason
            if self.directive_type == "type_ignore":
                codes_part = f"[{', '.join(self.codes)}]" if self.codes else ""
                new_directive = f"# type: ignore{codes_part}  # {reason}"
            elif self.directive_type == "noqa":
                codes_part = f": {', '.join(self.codes)}" if self.codes else ""
                new_directive = f"# noqa{codes_part}  # {reason}"
            elif self.directive_type == "pylint_disable":
                new_directive = f"# pylint: disable={','.join(self.codes)}  # {reason}"
            else:
                return self._operation_failed(
                    "set_reason",
                    f"Cannot set reason on {self.directive_type} directive",
                )

            # Replace old directive with new
            new_line = DirectiveParser.remove_directive(original_line, self.directive_type)
            new_line = f"{new_line}  {new_directive}" if new_line.strip() else new_directive

            lines[idx] = new_line + "\n"
            new_content = "".join(lines)

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would set reason on directive",
                    files_changed=[self.path],
                )

            self.path.write_text(new_content)
            self._directive.reason = reason
            return Result(
                success=True,
                message=f"Set reason on directive",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("set_reason", f"Failed to set reason: {e}", e)


class DirectiveTargetList(TargetList[DirectiveTarget]):
    """Specialized TargetList for linting directives with filtering helpers.

    Extends TargetList with directive-specific filtering and batch operations.

    Examples
    --------
    >>> directives = rj.find_type_ignores()
    >>> bare = directives.bare()  # Without specific codes
    >>> specific = directives.with_code("arg-type")
    """

    def __repr__(self) -> str:
        return f"DirectiveTargetList({len(self._targets)} directives)"

    # ===== Directive-specific filtering methods =====

    def by_type(self, directive_type: DirectiveType) -> DirectiveTargetList:
        """Filter to directives of a specific type.

        Parameters
        ----------
        directive_type : DirectiveType
            Type to filter by.

        Returns
        -------
        DirectiveTargetList
            Directives matching the specified type.
        """
        return DirectiveTargetList(
            self._rejig, [t for t in self._targets if t.directive_type == directive_type]
        )

    def bare(self) -> DirectiveTargetList:
        """Filter to bare directives (without specific codes).

        Returns
        -------
        DirectiveTargetList
            Directives without specific error codes.
        """
        return DirectiveTargetList(
            self._rejig, [t for t in self._targets if t.is_bare]
        )

    def specific(self) -> DirectiveTargetList:
        """Filter to directives with specific codes.

        Returns
        -------
        DirectiveTargetList
            Directives with specific error codes.
        """
        return DirectiveTargetList(
            self._rejig, [t for t in self._targets if t.is_specific]
        )

    def with_code(self, code: str) -> DirectiveTargetList:
        """Filter to directives containing a specific code.

        Parameters
        ----------
        code : str
            Error code to filter by.

        Returns
        -------
        DirectiveTargetList
            Directives containing the specified code.
        """
        return DirectiveTargetList(
            self._rejig, [t for t in self._targets if code in t.codes]
        )

    def without_reason(self) -> DirectiveTargetList:
        """Filter to directives without a reason comment.

        Returns
        -------
        DirectiveTargetList
            Directives without reason comments.
        """
        return DirectiveTargetList(
            self._rejig, [t for t in self._targets if t.reason is None]
        )

    def with_reason(self) -> DirectiveTargetList:
        """Filter to directives with a reason comment.

        Returns
        -------
        DirectiveTargetList
            Directives with reason comments.
        """
        return DirectiveTargetList(
            self._rejig, [t for t in self._targets if t.reason is not None]
        )

    def in_file(self, file_path: Path | str) -> DirectiveTargetList:
        """Filter to directives in a specific file.

        Parameters
        ----------
        file_path : Path | str
            Path to the file.

        Returns
        -------
        DirectiveTargetList
            Directives in the specified file.
        """
        path = Path(file_path) if isinstance(file_path, str) else file_path
        return DirectiveTargetList(
            self._rejig, [t for t in self._targets if t.file_path == path]
        )

    def filter(self, predicate: Callable[[DirectiveTarget], bool]) -> DirectiveTargetList:
        """Filter directives by a predicate function.

        Parameters
        ----------
        predicate : Callable[[DirectiveTarget], bool]
            Function that returns True for directives to keep.

        Returns
        -------
        DirectiveTargetList
            Filtered list of directives.
        """
        return DirectiveTargetList(self._rejig, [t for t in self._targets if predicate(t)])

    # ===== Directive-specific batch operations =====

    def remove_all(self) -> BatchResult:
        """Remove all directives in this list.

        Returns
        -------
        BatchResult
            Results of the removal operations.
        """
        # Process in reverse order to avoid line number shifts
        sorted_targets = sorted(self._targets, key=lambda t: t.line_number, reverse=True)
        return BatchResult([t.remove() for t in sorted_targets])

    def delete(self) -> BatchResult:
        """Alias for remove_all()."""
        return self.remove_all()

    def add_reason_all(self, reason: str) -> BatchResult:
        """Add a reason to all directives.

        Parameters
        ----------
        reason : str
            Reason to add.

        Returns
        -------
        BatchResult
            Results of the operations.
        """
        return BatchResult([t.set_reason(reason) for t in self._targets])

    def add_code_all(self, code: str) -> BatchResult:
        """Add a code to all directives that support codes.

        Parameters
        ----------
        code : str
            Error code to add.

        Returns
        -------
        BatchResult
            Results of the operations.
        """
        return BatchResult([t.add_code(code) for t in self._targets])

    # ===== Statistics =====

    def count_by_type(self) -> dict[DirectiveType, int]:
        """Count directives by type.

        Returns
        -------
        dict[DirectiveType, int]
            Count of directives per type.
        """
        counts: dict[DirectiveType, int] = {}
        for t in self._targets:
            counts[t.directive_type] = counts.get(t.directive_type, 0) + 1
        return counts

    def count_by_file(self) -> dict[Path, int]:
        """Count directives by file.

        Returns
        -------
        dict[Path, int]
            Count of directives per file.
        """
        counts: dict[Path, int] = {}
        for t in self._targets:
            counts[t.file_path] = counts.get(t.file_path, 0) + 1
        return counts

    def count_by_code(self) -> dict[str, int]:
        """Count directives by error code.

        Returns
        -------
        dict[str, int]
            Count of directives per error code.
        """
        counts: dict[str, int] = {}
        for t in self._targets:
            for code in t.codes:
                counts[code] = counts.get(code, 0) + 1
        return counts
