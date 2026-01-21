"""Target classes for code analysis results.

Provides Target and TargetList classes for working with analysis results
in a fluent, chainable way consistent with the rest of the rejig API.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING

from rejig.targets.base import FindingTarget, FindingTargetList, Target

if TYPE_CHECKING:
    from typing import Self

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


class AnalysisTarget(FindingTarget[AnalysisFinding]):
    """Target representing a single code analysis finding.

    Allows navigation to the underlying code element and
    provides methods to address the finding.
    """

    @property
    def type(self) -> AnalysisType:
        """Type of the finding."""
        return self._finding.type

    @property
    def value(self) -> int | float | str | None:
        """The relevant value (complexity, line count, etc.)."""
        return self._finding.value

    def __repr__(self) -> str:
        return f"AnalysisTarget({self._finding.type.name}, {self.location})"

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


class AnalysisTargetList(FindingTargetList[AnalysisTarget, AnalysisType]):
    """A list of analysis targets with filtering and aggregation methods.

    Provides domain-specific filtering for analysis results.
    """

    def __init__(
        self, rejig: Rejig, targets: list[AnalysisTarget] | None = None
    ) -> None:
        super().__init__(rejig, targets or [])

    def __repr__(self) -> str:
        return f"AnalysisTargetList({len(self._targets)} findings)"

    def _create_list(self, targets: list[AnalysisTarget]) -> Self:
        """Create a new AnalysisTargetList instance."""
        return AnalysisTargetList(self._rejig, targets)

    @property
    def _severity_order(self) -> dict[str, int]:
        """Return severity ordering for analysis (error > warning > info)."""
        return {"error": 0, "warning": 1, "info": 2}

    @property
    def _summary_prefix(self) -> str:
        """Return the prefix for summary output."""
        return "findings"

    # ===== Severity shortcuts =====

    def errors(self) -> Self:
        """Filter to error-level findings."""
        return self.by_severity("error")

    def warnings(self) -> Self:
        """Filter to warning-level findings."""
        return self.by_severity("warning")

    def info(self) -> Self:
        """Filter to info-level findings."""
        return self.by_severity("info")

    # ===== Value filtering (analysis-specific) =====

    def above_threshold(self, threshold: int | float) -> Self:
        """Filter to findings where value exceeds a threshold.

        Parameters
        ----------
        threshold : int | float
            Minimum value to include.

        Returns
        -------
        Self
            Filtered list of findings.
        """
        return self._create_list(
            [
                t
                for t in self._targets
                if t.value is not None
                and isinstance(t.value, (int, float))
                and t.value > threshold
            ]
        )

    def below_threshold(self, threshold: int | float) -> Self:
        """Filter to findings where value is below a threshold.

        Parameters
        ----------
        threshold : int | float
            Maximum value to include.

        Returns
        -------
        Self
            Filtered list of findings.
        """
        return self._create_list(
            [
                t
                for t in self._targets
                if t.value is not None
                and isinstance(t.value, (int, float))
                and t.value < threshold
            ]
        )

    # ===== Category shortcuts =====

    def complexity_issues(self) -> Self:
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
        return self._create_list(
            [t for t in self._targets if t.type in complexity_types]
        )

    def dead_code(self) -> Self:
        """Filter to dead code findings."""
        dead_code_types = {
            AnalysisType.UNUSED_FUNCTION,
            AnalysisType.UNUSED_CLASS,
            AnalysisType.UNUSED_VARIABLE,
            AnalysisType.UNUSED_IMPORT,
            AnalysisType.UNREACHABLE_CODE,
        }
        return self._create_list(
            [t for t in self._targets if t.type in dead_code_types]
        )

    def pattern_issues(self) -> Self:
        """Filter to pattern-related findings."""
        pattern_types = {
            AnalysisType.MISSING_TYPE_HINT,
            AnalysisType.MISSING_DOCSTRING,
            AnalysisType.BARE_EXCEPT,
            AnalysisType.HARDCODED_STRING,
            AnalysisType.MAGIC_NUMBER,
            AnalysisType.TODO_COMMENT,
        }
        return self._create_list(
            [t for t in self._targets if t.type in pattern_types]
        )

    # ===== Sorting (analysis-specific) =====

    def sorted_by_value(self, descending: bool = True) -> Self:
        """Sort findings by value (complexity, line count, etc.).

        Parameters
        ----------
        descending : bool
            If True, highest values first.

        Returns
        -------
        Self
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
        return self._create_list(sorted_targets)

    # ===== Output methods (override to include value) =====

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
