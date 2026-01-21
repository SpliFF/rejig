"""Target classes for security analysis results.

Provides Target and TargetList classes for working with security findings
in a fluent, chainable way consistent with the rest of the rejig API.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING

from rejig.targets.base import FindingTarget, FindingTargetList

if TYPE_CHECKING:
    from typing import Self

    from rejig.core.rejig import Rejig


class SecurityType(Enum):
    """Types of security findings."""

    # Secrets and credentials
    HARDCODED_SECRET = auto()
    HARDCODED_API_KEY = auto()
    HARDCODED_PASSWORD = auto()
    HARDCODED_TOKEN = auto()

    # Injection vulnerabilities
    SQL_INJECTION = auto()
    SHELL_INJECTION = auto()
    COMMAND_INJECTION = auto()
    CODE_INJECTION = auto()

    # Unsafe operations
    UNSAFE_YAML_LOAD = auto()
    UNSAFE_PICKLE = auto()
    UNSAFE_EVAL = auto()
    UNSAFE_EXEC = auto()
    UNSAFE_DESERIALIZE = auto()

    # Path and file security
    PATH_TRAVERSAL = auto()
    INSECURE_FILE_PERMISSIONS = auto()

    # Cryptography
    INSECURE_RANDOM = auto()
    WEAK_CRYPTO = auto()
    HARDCODED_CRYPTO_KEY = auto()

    # Network security
    INSECURE_SSL = auto()
    DISABLED_CERT_VERIFICATION = auto()

    # Other
    DEBUG_CODE = auto()
    SENSITIVE_DATA_EXPOSURE = auto()


@dataclass
class SecurityFinding:
    """A single finding from security analysis.

    Attributes
    ----------
    type : SecurityType
        The type of security finding.
    file_path : Path
        Path to the file containing the finding.
    line_number : int
        1-based line number of the finding.
    name : str | None
        Name of the element (function, variable).
    message : str
        Human-readable description of the finding.
    severity : str
        Severity level: "low", "medium", "high", "critical".
    code_snippet : str | None
        The relevant code snippet.
    context : dict
        Additional context about the finding.
    recommendation : str | None
        Suggested fix for the issue.
    """

    type: SecurityType
    file_path: Path
    line_number: int
    name: str | None = None
    message: str = ""
    severity: str = "medium"
    code_snippet: str | None = None
    context: dict = None
    recommendation: str | None = None

    def __post_init__(self) -> None:
        if self.context is None:
            self.context = {}

    @property
    def location(self) -> str:
        """Return a formatted location string."""
        return f"{self.file_path}:{self.line_number}"


class SecurityTarget(FindingTarget[SecurityFinding]):
    """Target representing a single security finding.

    Allows navigation to the underlying code element and
    provides methods to address the finding.
    """

    @property
    def type(self) -> SecurityType:
        """Type of the finding."""
        return self._finding.type

    @property
    def code_snippet(self) -> str | None:
        """The relevant code snippet."""
        return self._finding.code_snippet

    @property
    def recommendation(self) -> str | None:
        """Suggested fix for this issue."""
        return self._finding.recommendation

    def __repr__(self) -> str:
        return f"SecurityTarget({self._finding.type.name}, {self.location})"


class SecurityTargetList(FindingTargetList[SecurityTarget, SecurityType]):
    """A list of security targets with filtering and aggregation methods.

    Provides domain-specific filtering for security analysis results.
    """

    def __init__(
        self, rejig: Rejig, targets: list[SecurityTarget] | None = None
    ) -> None:
        super().__init__(rejig, targets or [])

    def __repr__(self) -> str:
        return f"SecurityTargetList({len(self._targets)} findings)"

    def _create_list(self, targets: list[SecurityTarget]) -> Self:
        """Create a new SecurityTargetList instance."""
        return SecurityTargetList(self._rejig, targets)

    @property
    def _severity_order(self) -> dict[str, int]:
        """Return severity ordering for security (critical > high > medium > low)."""
        return {"critical": 0, "high": 1, "medium": 2, "low": 3}

    @property
    def _summary_prefix(self) -> str:
        """Return the prefix for summary output."""
        return "security findings"

    # ===== Severity shortcuts =====

    def critical(self) -> Self:
        """Filter to critical-level findings."""
        return self.by_severity("critical")

    def high(self) -> Self:
        """Filter to high-level findings."""
        return self.by_severity("high")

    def medium(self) -> Self:
        """Filter to medium-level findings."""
        return self.by_severity("medium")

    def low(self) -> Self:
        """Filter to low-level findings."""
        return self.by_severity("low")

    def at_least(self, min_severity: str) -> Self:
        """Filter to findings at or above a severity level.

        Parameters
        ----------
        min_severity : str
            Minimum severity: "low", "medium", "high", or "critical".

        Returns
        -------
        Self
            Filtered list of findings at or above the given severity.
        """
        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        min_level = severity_order.get(min_severity, 0)
        return self._create_list(
            [
                t
                for t in self._targets
                if severity_order.get(t.severity, 0) >= min_level
            ]
        )

    # ===== Category shortcuts =====

    def secrets(self) -> Self:
        """Filter to hardcoded secrets/credentials findings."""
        secret_types = {
            SecurityType.HARDCODED_SECRET,
            SecurityType.HARDCODED_API_KEY,
            SecurityType.HARDCODED_PASSWORD,
            SecurityType.HARDCODED_TOKEN,
            SecurityType.HARDCODED_CRYPTO_KEY,
        }
        return self._create_list(
            [t for t in self._targets if t.type in secret_types]
        )

    def injection_risks(self) -> Self:
        """Filter to injection vulnerability findings."""
        injection_types = {
            SecurityType.SQL_INJECTION,
            SecurityType.SHELL_INJECTION,
            SecurityType.COMMAND_INJECTION,
            SecurityType.CODE_INJECTION,
        }
        return self._create_list(
            [t for t in self._targets if t.type in injection_types]
        )

    def unsafe_operations(self) -> Self:
        """Filter to unsafe deserialization/eval findings."""
        unsafe_types = {
            SecurityType.UNSAFE_YAML_LOAD,
            SecurityType.UNSAFE_PICKLE,
            SecurityType.UNSAFE_EVAL,
            SecurityType.UNSAFE_EXEC,
            SecurityType.UNSAFE_DESERIALIZE,
        }
        return self._create_list(
            [t for t in self._targets if t.type in unsafe_types]
        )

    def crypto_issues(self) -> Self:
        """Filter to cryptography-related findings."""
        crypto_types = {
            SecurityType.INSECURE_RANDOM,
            SecurityType.WEAK_CRYPTO,
            SecurityType.HARDCODED_CRYPTO_KEY,
        }
        return self._create_list(
            [t for t in self._targets if t.type in crypto_types]
        )

    # ===== Aggregation (security-specific) =====

    def group_by_severity(self) -> dict[str, Self]:
        """Group findings by severity.

        Returns
        -------
        dict[str, Self]
            Mapping of severity levels to their findings.
        """
        groups: dict[str, list[SecurityTarget]] = {}
        for t in self._targets:
            if t.severity not in groups:
                groups[t.severity] = []
            groups[t.severity].append(t)

        return {
            severity: self._create_list(targets)
            for severity, targets in groups.items()
        }

    # ===== Output methods (override to include security-specific fields) =====

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
                "code_snippet": t.code_snippet,
                "recommendation": t.recommendation,
            }
            for t in self._targets
        ]

    def summary(self) -> str:
        """Generate a summary string of findings.

        Returns
        -------
        str
            Summary of findings by severity and type.
        """
        if not self._targets:
            return "No security findings"

        lines = [f"Total: {len(self._targets)} security findings"]

        # Severity breakdown
        severity_counts = self.count_by_severity()
        for severity in ["critical", "high", "medium", "low"]:
            if severity in severity_counts:
                lines.append(f"  {severity.upper()}: {severity_counts[severity]}")

        # Type breakdown
        lines.append("")
        type_counts = self.count_by_type()
        for stype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {stype.name}: {count}")

        return "\n".join(lines)
