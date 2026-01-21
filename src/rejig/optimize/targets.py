"""Target classes for code optimization results.

Provides Target and TargetList classes for working with optimization findings
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


class OptimizeTarget(FindingTarget[OptimizeFinding]):
    """Target representing a single code optimization finding.

    Allows navigation to the underlying code element and
    provides methods to apply the optimization.
    """

    @property
    def type(self) -> OptimizeType:
        """Type of the finding."""
        return self._finding.type

    @property
    def end_line(self) -> int:
        """End line number of the finding."""
        return self._finding.end_line

    @property
    def original_code(self) -> str:
        """The original code that can be optimized."""
        return self._finding.original_code

    @property
    def suggested_code(self) -> str:
        """The suggested optimized replacement."""
        return self._finding.suggested_code

    def __repr__(self) -> str:
        return f"OptimizeTarget({self._finding.type.name}, {self.location})"

    def to_line_block_target(self) -> Target:
        """Navigate to the line range containing this finding."""
        return self._rejig.file(self._finding.file_path).lines(
            self._finding.line_number, self._finding.end_line
        )


class OptimizeTargetList(FindingTargetList[OptimizeTarget, OptimizeType]):
    """A list of optimization targets with filtering and aggregation methods.

    Provides domain-specific filtering for optimization results.
    """

    def __init__(
        self, rejig: Rejig, targets: list[OptimizeTarget] | None = None
    ) -> None:
        super().__init__(rejig, targets or [])

    def __repr__(self) -> str:
        return f"OptimizeTargetList({len(self._targets)} findings)"

    def _create_list(self, targets: list[OptimizeTarget]) -> Self:
        """Create a new OptimizeTargetList instance."""
        return OptimizeTargetList(self._rejig, targets)

    @property
    def _severity_order(self) -> dict[str, int]:
        """Return severity ordering for optimization (warning > suggestion > info)."""
        return {"warning": 0, "suggestion": 1, "info": 2}

    @property
    def _summary_prefix(self) -> str:
        """Return the prefix for summary output."""
        return "optimization opportunities"

    # ===== Severity shortcuts =====

    def suggestions(self) -> Self:
        """Filter to suggestion-level findings."""
        return self.by_severity("suggestion")

    def warnings(self) -> Self:
        """Filter to warning-level findings."""
        return self.by_severity("warning")

    def info(self) -> Self:
        """Filter to info-level findings."""
        return self.by_severity("info")

    # ===== Category shortcuts =====

    def dry_issues(self) -> Self:
        """Filter to DRY (Don't Repeat Yourself) findings."""
        dry_types = {
            OptimizeType.DUPLICATE_CODE_BLOCK,
            OptimizeType.DUPLICATE_EXPRESSION,
            OptimizeType.DUPLICATE_LITERAL,
            OptimizeType.SIMILAR_FUNCTION,
            OptimizeType.REPEATED_PATTERN,
        }
        return self._create_list(
            [t for t in self._targets if t.type in dry_types]
        )

    def loop_issues(self) -> Self:
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
        return self._create_list(
            [t for t in self._targets if t.type in loop_types]
        )

    def efficiency_issues(self) -> Self:
        """Filter to general efficiency findings."""
        efficiency_types = {
            OptimizeType.INEFFICIENT_STRING_CONCAT,
            OptimizeType.INEFFICIENT_LIST_EXTEND,
            OptimizeType.UNNECESSARY_LIST_CONVERSION,
        }
        return self._create_list(
            [t for t in self._targets if t.type in efficiency_types]
        )

    # ===== Output methods (override to include optimization-specific fields) =====

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
