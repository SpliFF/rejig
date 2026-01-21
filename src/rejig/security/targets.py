"""Target classes for security analysis results.

Provides Target and TargetList classes for working with security findings
in a fluent, chainable way consistent with the rest of the rejig API.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING

from rejig.targets.base import Target, TargetList

if TYPE_CHECKING:
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


class SecurityTarget(Target):
    """Target representing a single security finding.

    Allows navigation to the underlying code element and
    provides methods to address the finding.
    """

    def __init__(self, rejig: Rejig, finding: SecurityFinding) -> None:
        super().__init__(rejig)
        self._finding = finding

    @property
    def finding(self) -> SecurityFinding:
        """The underlying security finding."""
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
    def type(self) -> SecurityType:
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
    def code_snippet(self) -> str | None:
        """The relevant code snippet."""
        return self._finding.code_snippet

    @property
    def recommendation(self) -> str | None:
        """Suggested fix for this issue."""
        return self._finding.recommendation

    @property
    def location(self) -> str:
        """Formatted location string (file:line)."""
        return self._finding.location

    def exists(self) -> bool:
        """Check if the underlying file exists."""
        return self._finding.file_path.exists()

    def __repr__(self) -> str:
        return f"SecurityTarget({self._finding.type.name}, {self.location})"

    def to_file_target(self) -> Target:
        """Navigate to the file containing this finding."""
        return self._rejig.file(self._finding.file_path)

    def to_line_target(self) -> Target:
        """Navigate to the line containing this finding."""
        return self._rejig.file(self._finding.file_path).line(self._finding.line_number)


class SecurityTargetList(TargetList[SecurityTarget]):
    """A list of security targets with filtering and aggregation methods.

    Provides domain-specific filtering for security analysis results.
    """

    def __init__(
        self, rejig: Rejig, targets: list[SecurityTarget] | None = None
    ) -> None:
        super().__init__(rejig, targets or [])

    def __repr__(self) -> str:
        return f"SecurityTargetList({len(self._targets)} findings)"

    # ===== Type-based filtering =====

    def by_type(self, security_type: SecurityType) -> SecurityTargetList:
        """Filter to findings of a specific type.

        Parameters
        ----------
        security_type : SecurityType
            The type of findings to include.

        Returns
        -------
        SecurityTargetList
            Filtered list of findings.
        """
        return SecurityTargetList(
            self._rejig,
            [t for t in self._targets if t.type == security_type],
        )

    def by_types(self, *types: SecurityType) -> SecurityTargetList:
        """Filter to findings matching any of the given types.

        Parameters
        ----------
        *types : SecurityType
            Types of findings to include.

        Returns
        -------
        SecurityTargetList
            Filtered list of findings.
        """
        type_set = set(types)
        return SecurityTargetList(
            self._rejig,
            [t for t in self._targets if t.type in type_set],
        )

    # ===== Severity filtering =====

    def by_severity(self, severity: str) -> SecurityTargetList:
        """Filter to findings with a specific severity.

        Parameters
        ----------
        severity : str
            Severity level: "low", "medium", "high", or "critical".

        Returns
        -------
        SecurityTargetList
            Filtered list of findings.
        """
        return SecurityTargetList(
            self._rejig,
            [t for t in self._targets if t.severity == severity],
        )

    def critical(self) -> SecurityTargetList:
        """Filter to critical-level findings."""
        return self.by_severity("critical")

    def high(self) -> SecurityTargetList:
        """Filter to high-level findings."""
        return self.by_severity("high")

    def medium(self) -> SecurityTargetList:
        """Filter to medium-level findings."""
        return self.by_severity("medium")

    def low(self) -> SecurityTargetList:
        """Filter to low-level findings."""
        return self.by_severity("low")

    def at_least(self, min_severity: str) -> SecurityTargetList:
        """Filter to findings at or above a severity level.

        Parameters
        ----------
        min_severity : str
            Minimum severity: "low", "medium", "high", or "critical".

        Returns
        -------
        SecurityTargetList
            Filtered list of findings at or above the given severity.
        """
        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        min_level = severity_order.get(min_severity, 0)
        return SecurityTargetList(
            self._rejig,
            [
                t
                for t in self._targets
                if severity_order.get(t.severity, 0) >= min_level
            ],
        )

    # ===== Location filtering =====

    def in_file(self, path: Path | str) -> SecurityTargetList:
        """Filter to findings in a specific file.

        Parameters
        ----------
        path : Path | str
            Path to the file.

        Returns
        -------
        SecurityTargetList
            Filtered list of findings.
        """
        path = Path(path) if isinstance(path, str) else path
        return SecurityTargetList(
            self._rejig,
            [t for t in self._targets if t.file_path == path],
        )

    def in_directory(self, directory: Path | str) -> SecurityTargetList:
        """Filter to findings in a specific directory (recursive).

        Parameters
        ----------
        directory : Path | str
            Path to the directory.

        Returns
        -------
        SecurityTargetList
            Filtered list of findings.
        """
        directory = Path(directory) if isinstance(directory, str) else directory
        return SecurityTargetList(
            self._rejig,
            [
                t
                for t in self._targets
                if t.file_path == directory or directory in t.file_path.parents
            ],
        )

    # ===== Category shortcuts =====

    def secrets(self) -> SecurityTargetList:
        """Filter to hardcoded secrets/credentials findings."""
        secret_types = {
            SecurityType.HARDCODED_SECRET,
            SecurityType.HARDCODED_API_KEY,
            SecurityType.HARDCODED_PASSWORD,
            SecurityType.HARDCODED_TOKEN,
            SecurityType.HARDCODED_CRYPTO_KEY,
        }
        return SecurityTargetList(
            self._rejig,
            [t for t in self._targets if t.type in secret_types],
        )

    def injection_risks(self) -> SecurityTargetList:
        """Filter to injection vulnerability findings."""
        injection_types = {
            SecurityType.SQL_INJECTION,
            SecurityType.SHELL_INJECTION,
            SecurityType.COMMAND_INJECTION,
            SecurityType.CODE_INJECTION,
        }
        return SecurityTargetList(
            self._rejig,
            [t for t in self._targets if t.type in injection_types],
        )

    def unsafe_operations(self) -> SecurityTargetList:
        """Filter to unsafe deserialization/eval findings."""
        unsafe_types = {
            SecurityType.UNSAFE_YAML_LOAD,
            SecurityType.UNSAFE_PICKLE,
            SecurityType.UNSAFE_EVAL,
            SecurityType.UNSAFE_EXEC,
            SecurityType.UNSAFE_DESERIALIZE,
        }
        return SecurityTargetList(
            self._rejig,
            [t for t in self._targets if t.type in unsafe_types],
        )

    def crypto_issues(self) -> SecurityTargetList:
        """Filter to cryptography-related findings."""
        crypto_types = {
            SecurityType.INSECURE_RANDOM,
            SecurityType.WEAK_CRYPTO,
            SecurityType.HARDCODED_CRYPTO_KEY,
        }
        return SecurityTargetList(
            self._rejig,
            [t for t in self._targets if t.type in crypto_types],
        )

    # ===== Aggregation =====

    def group_by_file(self) -> dict[Path, SecurityTargetList]:
        """Group findings by file.

        Returns
        -------
        dict[Path, SecurityTargetList]
            Mapping of file paths to their findings.
        """
        groups: dict[Path, list[SecurityTarget]] = {}
        for t in self._targets:
            if t.file_path not in groups:
                groups[t.file_path] = []
            groups[t.file_path].append(t)

        return {
            path: SecurityTargetList(self._rejig, targets)
            for path, targets in groups.items()
        }

    def group_by_type(self) -> dict[SecurityType, SecurityTargetList]:
        """Group findings by type.

        Returns
        -------
        dict[SecurityType, SecurityTargetList]
            Mapping of types to their findings.
        """
        groups: dict[SecurityType, list[SecurityTarget]] = {}
        for t in self._targets:
            if t.type not in groups:
                groups[t.type] = []
            groups[t.type].append(t)

        return {
            stype: SecurityTargetList(self._rejig, targets)
            for stype, targets in groups.items()
        }

    def group_by_severity(self) -> dict[str, SecurityTargetList]:
        """Group findings by severity.

        Returns
        -------
        dict[str, SecurityTargetList]
            Mapping of severity levels to their findings.
        """
        groups: dict[str, list[SecurityTarget]] = {}
        for t in self._targets:
            if t.severity not in groups:
                groups[t.severity] = []
            groups[t.severity].append(t)

        return {
            severity: SecurityTargetList(self._rejig, targets)
            for severity, targets in groups.items()
        }

    def count_by_type(self) -> dict[SecurityType, int]:
        """Get counts by finding type.

        Returns
        -------
        dict[SecurityType, int]
            Mapping of types to counts.
        """
        counts: dict[SecurityType, int] = {}
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

    def sorted_by_severity(self, descending: bool = True) -> SecurityTargetList:
        """Sort findings by severity.

        Parameters
        ----------
        descending : bool
            If True, critical first. If False, low first.

        Returns
        -------
        SecurityTargetList
            Sorted list of findings.
        """
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_targets = sorted(
            self._targets,
            key=lambda t: severity_order.get(t.severity, 4),
            reverse=not descending,
        )
        return SecurityTargetList(self._rejig, sorted_targets)

    def sorted_by_location(self) -> SecurityTargetList:
        """Sort findings by file and line number.

        Returns
        -------
        SecurityTargetList
            Sorted list of findings.
        """
        sorted_targets = sorted(
            self._targets,
            key=lambda t: (str(t.file_path), t.line_number),
        )
        return SecurityTargetList(self._rejig, sorted_targets)

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
