"""Target classes for code optimization results.

Provides Target and TargetList classes for working with optimization findings
in a fluent, chainable way consistent with the rest of the rejig API.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING

from rejig.targets.base import Target, TargetList

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class OptimizeType(Enum):
    """Types of code optimization findings."""

    # DRY (Don't Repeat Yourself) findings
    DUPLICATE_CODE_BLOCK = auto()
    DUPLICATE_EXPRESSION = auto()
    DUPLICATE_LITERAL = auto()
    SIMILAR_FUNCTION = auto()
    REPEATED_PATTERN = auto()

    # Loop optimization findings
    SLOW_LOOP_TO_COMPREHENSION = auto()
    SLOW_LOOP_TO_DICT_COMPREHENSION = auto()
    SLOW_LOOP_TO_SET_COMPREHENSION = auto()
    SLOW_LOOP_TO_MAP = auto()
    SLOW_LOOP_TO_FILTER = auto()
    SLOW_LOOP_TO_ANY_ALL = auto()
    SLOW_LOOP_TO_SUM = auto()
    SLOW_LOOP_TO_JOIN = auto()
    SLOW_LOOP_TO_ENUMERATE = auto()
    SLOW_LOOP_TO_ZIP = auto()

    # General efficiency findings
    INEFFICIENT_STRING_CONCAT = auto()
    INEFFICIENT_LIST_EXTEND = auto()
    UNNECESSARY_LIST_CONVERSION = auto()


@dataclass
class OptimizeFinding:
    """A single finding from code optimization analysis.

    Attributes
    ----------
    type : OptimizeType
        The type of optimization finding.
    file_path : Path
        Path to the file containing the finding.
    line_number : int
        1-based line number of the finding.
    end_line : int
        1-based end line number of the finding.
    name : str | None
        Name of the element (function, variable, etc.).
    message : str
        Human-readable description of the finding.
    severity : str
        Severity level: "info", "warning", "suggestion".
    original_code : str
        The original code that can be optimized.
    suggested_code : str
        The suggested optimized replacement.
    estimated_improvement : str
        Description of expected improvement (readability, performance, etc.).
    context : dict
        Additional context about the finding.
    """

    type: OptimizeType
    file_path: Path
    line_number: int
    end_line: int = 0
    name: str | None = None
    message: str = ""
    severity: str = "suggestion"
    original_code: str = ""
    suggested_code: str = ""
    estimated_improvement: str = ""
    context: dict = None

    def __post_init__(self) -> None:
        if self.context is None:
            self.context = {}
        if self.end_line == 0:
            self.end_line = self.line_number

    @property
    def location(self) -> str:
        """Return a formatted location string."""
        if self.end_line > self.line_number:
            return f"{self.file_path}:{self.line_number}-{self.end_line}"
        return f"{self.file_path}:{self.line_number}"


class OptimizeTarget(Target):
    """Target representing a single code optimization finding.

    Allows navigation to the underlying code element and
    provides methods to apply the optimization.
    """

    def __init__(self, rejig: Rejig, finding: OptimizeFinding) -> None:
        super().__init__(rejig)
        self._finding = finding

    @property
    def finding(self) -> OptimizeFinding:
        """The underlying optimization finding."""
        return self._finding

    @property
    def file_path(self) -> Path:
        """Path to the file containing the finding."""
        return self._finding.file_path

    @property
    def line_number(self) -> int:
        """Line number of the finding."""
        return self._finding.line_number

    @property
    def end_line(self) -> int:
        """End line number of the finding."""
        return self._finding.end_line

    @property
    def name(self) -> str | None:
        """Name of the code element (if applicable)."""
        return self._finding.name

    @property
    def type(self) -> OptimizeType:
        """Type of the finding."""
        return self._finding.type

    @property
    def message(self) -> str:
        """Description of the finding."""
        return self._finding.message

    @property
    def severity(self) -> str:
        """Severity level of the finding."""
        return self._finding.severity

    @property
    def original_code(self) -> str:
        """The original code that can be optimized."""
        return self._finding.original_code

    @property
    def suggested_code(self) -> str:
        """The suggested optimized replacement."""
        return self._finding.suggested_code

    @property
    def location(self) -> str:
        """Formatted location string (file:line)."""
        return self._finding.location

    def exists(self) -> bool:
        """Check if the underlying file exists."""
        return self._finding.file_path.exists()

    def __repr__(self) -> str:
        return f"OptimizeTarget({self._finding.type.name}, {self.location})"

    def to_file_target(self) -> Target:
        """Navigate to the file containing this finding."""
        return self._rejig.file(self._finding.file_path)

    def to_line_target(self) -> Target:
        """Navigate to the line containing this finding."""
        return self._rejig.file(self._finding.file_path).line(self._finding.line_number)

    def to_line_block_target(self) -> Target:
        """Navigate to the line range containing this finding."""
        return self._rejig.file(self._finding.file_path).lines(
            self._finding.line_number, self._finding.end_line
        )


class OptimizeTargetList(TargetList[OptimizeTarget]):
    """A list of optimization targets with filtering and aggregation methods.

    Provides domain-specific filtering for optimization results.
    """

    def __init__(
        self, rejig: Rejig, targets: list[OptimizeTarget] | None = None
    ) -> None:
        super().__init__(rejig, targets or [])

    def __repr__(self) -> str:
        return f"OptimizeTargetList({len(self._targets)} findings)"

    # ===== Type-based filtering =====

    def by_type(self, optimize_type: OptimizeType) -> OptimizeTargetList:
        """Filter to findings of a specific type.

        Parameters
        ----------
        optimize_type : OptimizeType
            The type of findings to include.

        Returns
        -------
        OptimizeTargetList
            Filtered list of findings.
        """
        return OptimizeTargetList(
            self._rejig,
            [t for t in self._targets if t.type == optimize_type],
        )

    def by_types(self, *types: OptimizeType) -> OptimizeTargetList:
        """Filter to findings matching any of the given types.

        Parameters
        ----------
        *types : OptimizeType
            Types of findings to include.

        Returns
        -------
        OptimizeTargetList
            Filtered list of findings.
        """
        type_set = set(types)
        return OptimizeTargetList(
            self._rejig,
            [t for t in self._targets if t.type in type_set],
        )

    # ===== Severity filtering =====

    def by_severity(self, severity: str) -> OptimizeTargetList:
        """Filter to findings with a specific severity.

        Parameters
        ----------
        severity : str
            Severity level: "info", "warning", or "suggestion".

        Returns
        -------
        OptimizeTargetList
            Filtered list of findings.
        """
        return OptimizeTargetList(
            self._rejig,
            [t for t in self._targets if t.severity == severity],
        )

    def suggestions(self) -> OptimizeTargetList:
        """Filter to suggestion-level findings."""
        return self.by_severity("suggestion")

    def warnings(self) -> OptimizeTargetList:
        """Filter to warning-level findings."""
        return self.by_severity("warning")

    def info(self) -> OptimizeTargetList:
        """Filter to info-level findings."""
        return self.by_severity("info")

    # ===== Location filtering =====

    def in_file(self, path: Path | str) -> OptimizeTargetList:
        """Filter to findings in a specific file.

        Parameters
        ----------
        path : Path | str
            Path to the file.

        Returns
        -------
        OptimizeTargetList
            Filtered list of findings.
        """
        path = Path(path) if isinstance(path, str) else path
        return OptimizeTargetList(
            self._rejig,
            [t for t in self._targets if t.file_path == path],
        )

    def in_directory(self, directory: Path | str) -> OptimizeTargetList:
        """Filter to findings in a specific directory (recursive).

        Parameters
        ----------
        directory : Path | str
            Path to the directory.

        Returns
        -------
        OptimizeTargetList
            Filtered list of findings.
        """
        directory = Path(directory) if isinstance(directory, str) else directory
        return OptimizeTargetList(
            self._rejig,
            [
                t
                for t in self._targets
                if t.file_path == directory or directory in t.file_path.parents
            ],
        )

    # ===== Category shortcuts =====

    def dry_issues(self) -> OptimizeTargetList:
        """Filter to DRY (Don't Repeat Yourself) findings."""
        dry_types = {
            OptimizeType.DUPLICATE_CODE_BLOCK,
            OptimizeType.DUPLICATE_EXPRESSION,
            OptimizeType.DUPLICATE_LITERAL,
            OptimizeType.SIMILAR_FUNCTION,
            OptimizeType.REPEATED_PATTERN,
        }
        return OptimizeTargetList(
            self._rejig,
            [t for t in self._targets if t.type in dry_types],
        )

    def loop_issues(self) -> OptimizeTargetList:
        """Filter to loop optimization findings."""
        loop_types = {
            OptimizeType.SLOW_LOOP_TO_COMPREHENSION,
            OptimizeType.SLOW_LOOP_TO_DICT_COMPREHENSION,
            OptimizeType.SLOW_LOOP_TO_SET_COMPREHENSION,
            OptimizeType.SLOW_LOOP_TO_MAP,
            OptimizeType.SLOW_LOOP_TO_FILTER,
            OptimizeType.SLOW_LOOP_TO_ANY_ALL,
            OptimizeType.SLOW_LOOP_TO_SUM,
            OptimizeType.SLOW_LOOP_TO_JOIN,
            OptimizeType.SLOW_LOOP_TO_ENUMERATE,
            OptimizeType.SLOW_LOOP_TO_ZIP,
        }
        return OptimizeTargetList(
            self._rejig,
            [t for t in self._targets if t.type in loop_types],
        )

    def efficiency_issues(self) -> OptimizeTargetList:
        """Filter to general efficiency findings."""
        efficiency_types = {
            OptimizeType.INEFFICIENT_STRING_CONCAT,
            OptimizeType.INEFFICIENT_LIST_EXTEND,
            OptimizeType.UNNECESSARY_LIST_CONVERSION,
        }
        return OptimizeTargetList(
            self._rejig,
            [t for t in self._targets if t.type in efficiency_types],
        )

    # ===== Aggregation =====

    def group_by_file(self) -> dict[Path, OptimizeTargetList]:
        """Group findings by file.

        Returns
        -------
        dict[Path, OptimizeTargetList]
            Mapping of file paths to their findings.
        """
        groups: dict[Path, list[OptimizeTarget]] = {}
        for t in self._targets:
            if t.file_path not in groups:
                groups[t.file_path] = []
            groups[t.file_path].append(t)

        return {
            path: OptimizeTargetList(self._rejig, targets)
            for path, targets in groups.items()
        }

    def group_by_type(self) -> dict[OptimizeType, OptimizeTargetList]:
        """Group findings by type.

        Returns
        -------
        dict[OptimizeType, OptimizeTargetList]
            Mapping of types to their findings.
        """
        groups: dict[OptimizeType, list[OptimizeTarget]] = {}
        for t in self._targets:
            if t.type not in groups:
                groups[t.type] = []
            groups[t.type].append(t)

        return {
            otype: OptimizeTargetList(self._rejig, targets)
            for otype, targets in groups.items()
        }

    def count_by_type(self) -> dict[OptimizeType, int]:
        """Get counts by finding type.

        Returns
        -------
        dict[OptimizeType, int]
            Mapping of types to counts.
        """
        counts: dict[OptimizeType, int] = {}
        for t in self._targets:
            counts[t.type] = counts.get(t.type, 0) + 1
        return counts

    def count_by_severity(self) -> dict[str, int]:
        """Get counts by severity level.

        Returns
        -------
        dict[str, int]
            Mapping of severity levels to counts.
        """
        counts: dict[str, int] = {}
        for t in self._targets:
            counts[t.severity] = counts.get(t.severity, 0) + 1
        return counts

    def count_by_file(self) -> dict[Path, int]:
        """Get counts by file.

        Returns
        -------
        dict[Path, int]
            Mapping of file paths to finding counts.
        """
        counts: dict[Path, int] = {}
        for t in self._targets:
            counts[t.file_path] = counts.get(t.file_path, 0) + 1
        return counts

    # ===== Sorting =====

    def sorted_by_severity(self, descending: bool = True) -> OptimizeTargetList:
        """Sort findings by severity.

        Parameters
        ----------
        descending : bool
            If True, warnings first. If False, info first.

        Returns
        -------
        OptimizeTargetList
            Sorted list of findings.
        """
        severity_order = {"warning": 0, "suggestion": 1, "info": 2}
        sorted_targets = sorted(
            self._targets,
            key=lambda t: severity_order.get(t.severity, 3),
            reverse=not descending,
        )
        return OptimizeTargetList(self._rejig, sorted_targets)

    def sorted_by_location(self) -> OptimizeTargetList:
        """Sort findings by file and line number.

        Returns
        -------
        OptimizeTargetList
            Sorted list of findings.
        """
        sorted_targets = sorted(
            self._targets,
            key=lambda t: (str(t.file_path), t.line_number),
        )
        return OptimizeTargetList(self._rejig, sorted_targets)

    # ===== Output methods =====

    def to_list_of_dicts(self) -> list[dict]:
        """Convert to list of dictionaries for serialization.

        Returns
        -------
        list[dict]
            List of finding dictionaries.
        """
        return [
            {
                "type": t.type.name,
                "file": str(t.file_path),
                "line": t.line_number,
                "end_line": t.end_line,
                "name": t.name,
                "message": t.message,
                "severity": t.severity,
                "original_code": t.original_code,
                "suggested_code": t.suggested_code,
            }
            for t in self._targets
        ]

    def summary(self) -> str:
        """Generate a summary string of findings.

        Returns
        -------
        str
            Summary of findings by type.
        """
        counts = self.count_by_type()
        if not counts:
            return "No optimization findings"

        lines = [f"Total: {len(self._targets)} optimization opportunities"]
        for otype, count in sorted(counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {otype.name}: {count}")
        return "\n".join(lines)
