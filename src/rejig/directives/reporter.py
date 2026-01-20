"""Directive reporter for generating reports on linting directive usage."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from rejig.directives.finder import DirectiveFinder
from rejig.directives.parser import DirectiveType
from rejig.directives.targets import DirectiveTargetList

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


@dataclass
class DirectiveReport:
    """Report on linting directive usage in a codebase.

    Attributes
    ----------
    total_count : int
        Total number of directives.
    by_type : dict[DirectiveType, int]
        Count of directives by type.
    by_file : dict[Path, int]
        Count of directives by file.
    by_code : dict[str, int]
        Count of directives by error code.
    bare_count : int
        Number of bare directives (without codes).
    specific_count : int
        Number of directives with specific codes.
    without_reason_count : int
        Number of directives without reason comments.
    files_with_most_directives : list[tuple[Path, int]]
        Top files by directive count.
    most_common_codes : list[tuple[str, int]]
        Most commonly suppressed error codes.
    """

    total_count: int = 0
    by_type: dict[DirectiveType, int] = field(default_factory=dict)
    by_file: dict[Path, int] = field(default_factory=dict)
    by_code: dict[str, int] = field(default_factory=dict)
    bare_count: int = 0
    specific_count: int = 0
    without_reason_count: int = 0
    files_with_most_directives: list[tuple[Path, int]] = field(default_factory=list)
    most_common_codes: list[tuple[str, int]] = field(default_factory=list)

    def __str__(self) -> str:
        """Generate a human-readable summary."""
        lines = [
            "Directive Report",
            "=" * 50,
            f"Total directives: {self.total_count}",
            f"Bare directives (no codes): {self.bare_count}",
            f"Specific directives (with codes): {self.specific_count}",
            f"Without reason: {self.without_reason_count}",
            "",
            "By Type:",
        ]

        for dtype, count in sorted(self.by_type.items(), key=lambda x: -x[1]):
            lines.append(f"  {dtype}: {count}")

        if self.most_common_codes:
            lines.append("")
            lines.append("Most Common Codes:")
            for code, count in self.most_common_codes[:10]:
                lines.append(f"  {code}: {count}")

        if self.files_with_most_directives:
            lines.append("")
            lines.append("Files with Most Directives:")
            for file_path, count in self.files_with_most_directives[:10]:
                lines.append(f"  {file_path}: {count}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_count": self.total_count,
            "by_type": {str(k): v for k, v in self.by_type.items()},
            "by_file": {str(k): v for k, v in self.by_file.items()},
            "by_code": self.by_code,
            "bare_count": self.bare_count,
            "specific_count": self.specific_count,
            "without_reason_count": self.without_reason_count,
            "files_with_most_directives": [
                (str(p), c) for p, c in self.files_with_most_directives
            ],
            "most_common_codes": self.most_common_codes,
        }


class DirectiveReporter:
    """Generate reports on linting directive usage.

    Parameters
    ----------
    rejig : Rejig
        The Rejig instance to use for finding directives.

    Examples
    --------
    >>> reporter = DirectiveReporter(rj)
    >>> report = reporter.audit()
    >>> print(report)
    >>> print(f"Total suppressions: {report.total_count}")
    """

    def __init__(self, rejig: Rejig) -> None:
        self._rejig = rejig
        self._finder = DirectiveFinder(rejig)

    def audit(self) -> DirectiveReport:
        """Generate a comprehensive audit of all directives.

        Returns
        -------
        DirectiveReport
            Report on all linting directives in the codebase.
        """
        all_directives = self._finder.find_all()

        report = DirectiveReport(
            total_count=len(all_directives),
            by_type=all_directives.count_by_type(),
            by_file=all_directives.count_by_file(),
            by_code=all_directives.count_by_code(),
            bare_count=len(all_directives.bare()),
            specific_count=len(all_directives.specific()),
            without_reason_count=len(all_directives.without_reason()),
        )

        # Get top files
        sorted_files = sorted(report.by_file.items(), key=lambda x: -x[1])
        report.files_with_most_directives = sorted_files[:20]

        # Get most common codes
        sorted_codes = sorted(report.by_code.items(), key=lambda x: -x[1])
        report.most_common_codes = sorted_codes[:20]

        return report

    def audit_type_ignores(self) -> DirectiveReport:
        """Generate a report specifically for type: ignore directives.

        Returns
        -------
        DirectiveReport
            Report on type: ignore directives.
        """
        type_ignores = self._finder.find_type_ignores()

        report = DirectiveReport(
            total_count=len(type_ignores),
            by_type={"type_ignore": len(type_ignores)},
            by_file=type_ignores.count_by_file(),
            by_code=type_ignores.count_by_code(),
            bare_count=len(type_ignores.bare()),
            specific_count=len(type_ignores.specific()),
            without_reason_count=len(type_ignores.without_reason()),
        )

        # Get top files
        sorted_files = sorted(report.by_file.items(), key=lambda x: -x[1])
        report.files_with_most_directives = sorted_files[:20]

        # Get most common codes
        sorted_codes = sorted(report.by_code.items(), key=lambda x: -x[1])
        report.most_common_codes = sorted_codes[:20]

        return report

    def audit_noqa(self) -> DirectiveReport:
        """Generate a report specifically for noqa directives.

        Returns
        -------
        DirectiveReport
            Report on noqa directives.
        """
        noqa = self._finder.find_noqa_comments()

        report = DirectiveReport(
            total_count=len(noqa),
            by_type={"noqa": len(noqa)},
            by_file=noqa.count_by_file(),
            by_code=noqa.count_by_code(),
            bare_count=len(noqa.bare()),
            specific_count=len(noqa.specific()),
            without_reason_count=len(noqa.without_reason()),
        )

        # Get top files
        sorted_files = sorted(report.by_file.items(), key=lambda x: -x[1])
        report.files_with_most_directives = sorted_files[:20]

        # Get most common codes
        sorted_codes = sorted(report.by_code.items(), key=lambda x: -x[1])
        report.most_common_codes = sorted_codes[:20]

        return report

    def count_by_type(self) -> dict[DirectiveType, int]:
        """Get counts of directives by type.

        Returns
        -------
        dict[DirectiveType, int]
            Counts by directive type.
        """
        return self._finder.find_all().count_by_type()

    def format_markdown(self, report: DirectiveReport) -> str:
        """Format a report as Markdown.

        Parameters
        ----------
        report : DirectiveReport
            The report to format.

        Returns
        -------
        str
            Markdown-formatted report.
        """
        lines = [
            "# Directive Audit Report",
            "",
            "## Summary",
            "",
            f"- **Total directives**: {report.total_count}",
            f"- **Bare directives** (no codes): {report.bare_count}",
            f"- **Specific directives** (with codes): {report.specific_count}",
            f"- **Without reason**: {report.without_reason_count}",
            "",
            "## By Type",
            "",
            "| Type | Count |",
            "|------|-------|",
        ]

        for dtype, count in sorted(report.by_type.items(), key=lambda x: -x[1]):
            lines.append(f"| {dtype} | {count} |")

        if report.most_common_codes:
            lines.extend([
                "",
                "## Most Common Error Codes",
                "",
                "| Code | Count |",
                "|------|-------|",
            ])
            for code, count in report.most_common_codes[:15]:
                lines.append(f"| {code} | {count} |")

        if report.files_with_most_directives:
            lines.extend([
                "",
                "## Files with Most Directives",
                "",
                "| File | Count |",
                "|------|-------|",
            ])
            for file_path, count in report.files_with_most_directives[:15]:
                lines.append(f"| {file_path} | {count} |")

        return "\n".join(lines)

    def format_json(self, report: DirectiveReport) -> str:
        """Format a report as JSON.

        Parameters
        ----------
        report : DirectiveReport
            The report to format.

        Returns
        -------
        str
            JSON-formatted report.
        """
        import json
        return json.dumps(report.to_dict(), indent=2)
