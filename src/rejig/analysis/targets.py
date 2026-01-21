"""Target classes for code analysis results.

Provides Target and TargetList classes for working with analysis results
in a fluent, chainable way consistent with the rest of the rejig API.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Generic, Iterator, TypeVar

from rejig.targets.base import Target, TargetList

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class AnalysisType(Enum):
    """Types of code analysis findings."""

    # Pattern findings
    MISSING_TYPE_HINT = auto()
    MISSING_DOCSTRING = auto()
    BARE_EXCEPT = auto()
    HARDCODED_STRING = auto()
    MAGIC_NUMBER = auto()
    TODO_COMMENT = auto()

    # Complexity findings
    HIGH_CYCLOMATIC_COMPLEXITY = auto()
    LONG_FUNCTION = auto()
    LONG_CLASS = auto()
    DEEP_NESTING = auto()
    TOO_MANY_PARAMETERS = auto()
    TOO_MANY_BRANCHES = auto()
    TOO_MANY_RETURNS = auto()

    # Dead code findings
    UNUSED_FUNCTION = auto()
    UNUSED_CLASS = auto()
    UNUSED_VARIABLE = auto()
    UNUSED_IMPORT = auto()
    UNREACHABLE_CODE = auto()


@dataclass
class AnalysisFinding:
    """A single finding from code analysis.

    Attributes
    ----------
    type : AnalysisType
        The type of finding.
    file_path : Path
        Path to the file containing the finding.
    line_number : int
        1-based line number of the finding.
    name : str | None
        Name of the element (function, class, variable).
    message : str
        Human-readable description of the finding.
    severity : str
        Severity level: "info", "warning", "error".
    value : int | float | str | None
        The relevant value (complexity score, line count, etc.).
    threshold : int | float | None
        The threshold that was exceeded (if applicable).
    context : dict
        Additional context about the finding.
    """

    type: AnalysisType
    file_path: Path
    line_number: int
    name: str | None = None
    message: str = ""
    severity: str = "warning"
    value: int | float | str | None = None
    threshold: int | float | None = None
    context: dict = None

    def __post_init__(self) -> None:
        if self.context is None:
            self.context = {}

    @property
    def location(self) -> str:
        """Return a formatted location string."""
        return f"{self.file_path}:{self.line_number}"


class AnalysisTarget(Target):
    """Target representing a single code analysis finding.

    Allows navigation to the underlying code element and
    provides methods to address the finding.
    """

    def __init__(self, rejig: Rejig, finding: AnalysisFinding) -> None:
        super().__init__(rejig)
        self._finding = finding

    @property
    def finding(self) -> AnalysisFinding:
        """The underlying analysis finding."""
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
    def name(self) -> str | None:
        """Name of the code element (if applicable)."""
        return self._finding.name

    @property
    def type(self) -> AnalysisType:
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
    def value(self) -> int | float | str | None:
        """The relevant value (complexity, line count, etc.)."""
        return self._finding.value

    @property
    def location(self) -> str:
        """Formatted location string (file:line)."""
        return self._finding.location

    def exists(self) -> bool:
        """Check if the underlying file exists."""
        return self._finding.file_path.exists()

    def __repr__(self) -> str:
        return f"AnalysisTarget({self._finding.type.name}, {self.location})"

    def to_file_target(self) -> Target:
        """Navigate to the file containing this finding."""
        return self._rejig.file(self._finding.file_path)

    def to_function_target(self) -> Target:
        """Navigate to the function (if this finding is about a function)."""
        if self._finding.name:
            return self._rejig.file(self._finding.file_path).find_function(
                self._finding.name
            )
        from rejig.targets.base import ErrorTarget

        return ErrorTarget(self._rejig, "No function name associated with this finding")

    def to_class_target(self) -> Target:
        """Navigate to the class (if this finding is about a class)."""
        if self._finding.name:
            return self._rejig.file(self._finding.file_path).find_class(
                self._finding.name
            )
        from rejig.targets.base import ErrorTarget

        return ErrorTarget(self._rejig, "No class name associated with this finding")


T = TypeVar("T", bound=AnalysisTarget)


class AnalysisTargetList(TargetList[AnalysisTarget]):
    """A list of analysis targets with filtering and aggregation methods.

    Provides domain-specific filtering for analysis results.
    """

    def __init__(
        self, rejig: Rejig, targets: list[AnalysisTarget] | None = None
    ) -> None:
        super().__init__(rejig, targets or [])

    def __repr__(self) -> str:
        return f"AnalysisTargetList({len(self._targets)} findings)"

    # ===== Type-based filtering =====

    def by_type(self, analysis_type: AnalysisType) -> AnalysisTargetList:
        """Filter to findings of a specific type.

        Parameters
        ----------
        analysis_type : AnalysisType
            The type of findings to include.

        Returns
        -------
        AnalysisTargetList
            Filtered list of findings.
        """
        return AnalysisTargetList(
            self._rejig,
            [t for t in self._targets if t.type == analysis_type],
        )

    def by_types(self, *types: AnalysisType) -> AnalysisTargetList:
        """Filter to findings matching any of the given types.

        Parameters
        ----------
        *types : AnalysisType
            Types of findings to include.

        Returns
        -------
        AnalysisTargetList
            Filtered list of findings.
        """
        type_set = set(types)
        return AnalysisTargetList(
            self._rejig,
            [t for t in self._targets if t.type in type_set],
        )

    # ===== Severity filtering =====

    def by_severity(self, severity: str) -> AnalysisTargetList:
        """Filter to findings with a specific severity.

        Parameters
        ----------
        severity : str
            Severity level: "info", "warning", or "error".

        Returns
        -------
        AnalysisTargetList
            Filtered list of findings.
        """
        return AnalysisTargetList(
            self._rejig,
            [t for t in self._targets if t.severity == severity],
        )

    def errors(self) -> AnalysisTargetList:
        """Filter to error-level findings."""
        return self.by_severity("error")

    def warnings(self) -> AnalysisTargetList:
        """Filter to warning-level findings."""
        return self.by_severity("warning")

    def info(self) -> AnalysisTargetList:
        """Filter to info-level findings."""
        return self.by_severity("info")

    # ===== Location filtering =====

    def in_file(self, path: Path | str) -> AnalysisTargetList:
        """Filter to findings in a specific file.

        Parameters
        ----------
        path : Path | str
            Path to the file.

        Returns
        -------
        AnalysisTargetList
            Filtered list of findings.
        """
        path = Path(path) if isinstance(path, str) else path
        return AnalysisTargetList(
            self._rejig,
            [t for t in self._targets if t.file_path == path],
        )

    def in_directory(self, directory: Path | str) -> AnalysisTargetList:
        """Filter to findings in a specific directory (recursive).

        Parameters
        ----------
        directory : Path | str
            Path to the directory.

        Returns
        -------
        AnalysisTargetList
            Filtered list of findings.
        """
        directory = Path(directory) if isinstance(directory, str) else directory
        return AnalysisTargetList(
            self._rejig,
            [
                t
                for t in self._targets
                if t.file_path == directory
                or directory in t.file_path.parents
            ],
        )

    # ===== Value filtering =====

    def above_threshold(self, threshold: int | float) -> AnalysisTargetList:
        """Filter to findings where value exceeds a threshold.

        Parameters
        ----------
        threshold : int | float
            Minimum value to include.

        Returns
        -------
        AnalysisTargetList
            Filtered list of findings.
        """
        return AnalysisTargetList(
            self._rejig,
            [
                t
                for t in self._targets
                if t.value is not None
                and isinstance(t.value, (int, float))
                and t.value > threshold
            ],
        )

    def below_threshold(self, threshold: int | float) -> AnalysisTargetList:
        """Filter to findings where value is below a threshold.

        Parameters
        ----------
        threshold : int | float
            Maximum value to include.

        Returns
        -------
        AnalysisTargetList
            Filtered list of findings.
        """
        return AnalysisTargetList(
            self._rejig,
            [
                t
                for t in self._targets
                if t.value is not None
                and isinstance(t.value, (int, float))
                and t.value < threshold
            ],
        )

    # ===== Category shortcuts =====

    def complexity_issues(self) -> AnalysisTargetList:
        """Filter to complexity-related findings."""
        complexity_types = {
            AnalysisType.HIGH_CYCLOMATIC_COMPLEXITY,
            AnalysisType.LONG_FUNCTION,
            AnalysisType.LONG_CLASS,
            AnalysisType.DEEP_NESTING,
            AnalysisType.TOO_MANY_PARAMETERS,
            AnalysisType.TOO_MANY_BRANCHES,
            AnalysisType.TOO_MANY_RETURNS,
        }
        return AnalysisTargetList(
            self._rejig,
            [t for t in self._targets if t.type in complexity_types],
        )

    def dead_code(self) -> AnalysisTargetList:
        """Filter to dead code findings."""
        dead_code_types = {
            AnalysisType.UNUSED_FUNCTION,
            AnalysisType.UNUSED_CLASS,
            AnalysisType.UNUSED_VARIABLE,
            AnalysisType.UNUSED_IMPORT,
            AnalysisType.UNREACHABLE_CODE,
        }
        return AnalysisTargetList(
            self._rejig,
            [t for t in self._targets if t.type in dead_code_types],
        )

    def pattern_issues(self) -> AnalysisTargetList:
        """Filter to pattern-related findings."""
        pattern_types = {
            AnalysisType.MISSING_TYPE_HINT,
            AnalysisType.MISSING_DOCSTRING,
            AnalysisType.BARE_EXCEPT,
            AnalysisType.HARDCODED_STRING,
            AnalysisType.MAGIC_NUMBER,
            AnalysisType.TODO_COMMENT,
        }
        return AnalysisTargetList(
            self._rejig,
            [t for t in self._targets if t.type in pattern_types],
        )

    # ===== Aggregation =====

    def group_by_file(self) -> dict[Path, AnalysisTargetList]:
        """Group findings by file.

        Returns
        -------
        dict[Path, AnalysisTargetList]
            Mapping of file paths to their findings.
        """
        groups: dict[Path, list[AnalysisTarget]] = {}
        for t in self._targets:
            if t.file_path not in groups:
                groups[t.file_path] = []
            groups[t.file_path].append(t)

        return {
            path: AnalysisTargetList(self._rejig, targets)
            for path, targets in groups.items()
        }

    def group_by_type(self) -> dict[AnalysisType, AnalysisTargetList]:
        """Group findings by type.

        Returns
        -------
        dict[AnalysisType, AnalysisTargetList]
            Mapping of types to their findings.
        """
        groups: dict[AnalysisType, list[AnalysisTarget]] = {}
        for t in self._targets:
            if t.type not in groups:
                groups[t.type] = []
            groups[t.type].append(t)

        return {
            atype: AnalysisTargetList(self._rejig, targets)
            for atype, targets in groups.items()
        }

    def count_by_type(self) -> dict[AnalysisType, int]:
        """Get counts by finding type.

        Returns
        -------
        dict[AnalysisType, int]
            Mapping of types to counts.
        """
        counts: dict[AnalysisType, int] = {}
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

    def sorted_by_severity(self, descending: bool = True) -> AnalysisTargetList:
        """Sort findings by severity.

        Parameters
        ----------
        descending : bool
            If True, errors first. If False, info first.

        Returns
        -------
        AnalysisTargetList
            Sorted list of findings.
        """
        severity_order = {"error": 0, "warning": 1, "info": 2}
        sorted_targets = sorted(
            self._targets,
            key=lambda t: severity_order.get(t.severity, 3),
            reverse=not descending,
        )
        return AnalysisTargetList(self._rejig, sorted_targets)

    def sorted_by_value(self, descending: bool = True) -> AnalysisTargetList:
        """Sort findings by value (complexity, line count, etc.).

        Parameters
        ----------
        descending : bool
            If True, highest values first.

        Returns
        -------
        AnalysisTargetList
            Sorted list of findings.
        """

        def get_sort_key(t: AnalysisTarget) -> float:
            if t.value is None:
                return 0.0
            if isinstance(t.value, (int, float)):
                return float(t.value)
            return 0.0

        sorted_targets = sorted(
            self._targets,
            key=get_sort_key,
            reverse=descending,
        )
        return AnalysisTargetList(self._rejig, sorted_targets)

    def sorted_by_location(self) -> AnalysisTargetList:
        """Sort findings by file and line number.

        Returns
        -------
        AnalysisTargetList
            Sorted list of findings.
        """
        sorted_targets = sorted(
            self._targets,
            key=lambda t: (str(t.file_path), t.line_number),
        )
        return AnalysisTargetList(self._rejig, sorted_targets)

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
                "name": t.name,
                "message": t.message,
                "severity": t.severity,
                "value": t.value,
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
            return "No findings"

        lines = [f"Total: {len(self._targets)} findings"]
        for atype, count in sorted(counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {atype.name}: {count}")
        return "\n".join(lines)
