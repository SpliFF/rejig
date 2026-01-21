"""Security report generation.

Generates comprehensive security reports in various formats:
- JSON reports for automated processing
- Markdown reports for human review
- SARIF format for tool integration
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from rejig.core.results import Result
from rejig.security.secrets import SecretsScanner
from rejig.security.targets import SecurityTargetList, SecurityType
from rejig.security.vulnerabilities import VulnerabilityScanner

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


@dataclass
class SecurityReport:
    """A comprehensive security analysis report.

    Attributes
    ----------
    generated_at : datetime
        When the report was generated.
    project_root : Path
        Root path of the analyzed project.
    summary : dict
        Summary statistics.
    secrets : SecurityTargetList | None
        Hardcoded secrets findings.
    vulnerabilities : SecurityTargetList | None
        Vulnerability findings.
    """

    generated_at: datetime
    project_root: Path
    summary: dict = field(default_factory=dict)
    secrets: SecurityTargetList | None = None
    vulnerabilities: SecurityTargetList | None = None

    @property
    def all_findings(self) -> SecurityTargetList | None:
        """Combine all findings into a single list."""
        if self.secrets is None and self.vulnerabilities is None:
            return None

        from rejig.security.targets import SecurityTargetList

        all_targets = []
        if self.secrets:
            all_targets.extend(self.secrets._targets)
        if self.vulnerabilities:
            all_targets.extend(self.vulnerabilities._targets)

        if not all_targets:
            return None

        # Use the rejig instance from first available list
        rejig = None
        if self.secrets:
            rejig = self.secrets._rejig
        elif self.vulnerabilities:
            rejig = self.vulnerabilities._rejig

        if rejig:
            return SecurityTargetList(rejig, all_targets)
        return None

    @property
    def total_findings(self) -> int:
        """Total number of security findings."""
        total = 0
        if self.secrets:
            total += len(self.secrets)
        if self.vulnerabilities:
            total += len(self.vulnerabilities)
        return total

    @property
    def critical_count(self) -> int:
        """Number of critical findings."""
        findings = self.all_findings
        return len(findings.critical()) if findings else 0

    @property
    def high_count(self) -> int:
        """Number of high severity findings."""
        findings = self.all_findings
        return len(findings.high()) if findings else 0

    def __str__(self) -> str:
        """Generate a human-readable report summary."""
        lines = [
            "# Security Analysis Report",
            f"Generated: {self.generated_at.isoformat()}",
            f"Project: {self.project_root}",
            "",
        ]

        # Summary
        lines.extend([
            "## Summary",
            f"- Total findings: {self.total_findings}",
            f"- Critical: {self.critical_count}",
            f"- High: {self.high_count}",
            "",
        ])

        if self.summary:
            lines.extend([
                f"- Files scanned: {self.summary.get('files_scanned', 0)}",
                "",
            ])

        # Secrets
        if self.secrets and len(self.secrets) > 0:
            lines.extend([
                "## Hardcoded Secrets",
                f"Found {len(self.secrets)} potential secrets",
                "",
            ])
            for finding in self.secrets.sorted_by_severity()[:10]:
                lines.append(f"- [{finding.severity.upper()}] {finding.location}: {finding.message}")
            if len(self.secrets) > 10:
                lines.append(f"  ... and {len(self.secrets) - 10} more")
            lines.append("")

        # Vulnerabilities
        if self.vulnerabilities and len(self.vulnerabilities) > 0:
            lines.extend([
                "## Vulnerabilities",
                f"Found {len(self.vulnerabilities)} potential vulnerabilities",
                "",
            ])
            for finding in self.vulnerabilities.sorted_by_severity()[:10]:
                lines.append(f"- [{finding.severity.upper()}] {finding.location}: {finding.message}")
            if len(self.vulnerabilities) > 10:
                lines.append(f"  ... and {len(self.vulnerabilities) - 10} more")
            lines.append("")

        return "\n".join(lines)


class SecurityReporter:
    """Generate security analysis reports.

    Provides methods to generate comprehensive security reports
    in various formats.
    """

    def __init__(self, rejig: Rejig) -> None:
        self._rejig = rejig
        self._secrets_scanner = SecretsScanner(rejig)
        self._vulnerability_scanner = VulnerabilityScanner(rejig)

    def generate_full_report(
        self,
        include_secrets: bool = True,
        include_vulnerabilities: bool = True,
    ) -> SecurityReport:
        """Generate a comprehensive security report.

        Parameters
        ----------
        include_secrets : bool
            Include hardcoded secrets analysis. Default True.
        include_vulnerabilities : bool
            Include vulnerability analysis. Default True.

        Returns
        -------
        SecurityReport
            The complete security report.
        """
        report = SecurityReport(
            generated_at=datetime.now(),
            project_root=self._rejig.root,
            summary={"files_scanned": len(self._rejig.files)},
        )

        if include_secrets:
            report.secrets = self._secrets_scanner.find_hardcoded_secrets()

        if include_vulnerabilities:
            report.vulnerabilities = self._vulnerability_scanner.find_all_vulnerabilities()

        return report

    def generate_security_report(
        self,
        output_path: Path | str | None = None,
        format: str = "json",
    ) -> Result:
        """Generate a security report file.

        Parameters
        ----------
        output_path : Path | str | None
            Path to write the report. If None, returns data in result.
        format : str
            Output format: "json", "markdown", or "sarif". Default "json".

        Returns
        -------
        Result
            Result containing the report data or file path.
        """
        report = self.generate_full_report()

        if format == "json":
            content = self._format_json(report)
        elif format == "markdown":
            content = self._format_markdown(report)
        elif format == "sarif":
            content = self._format_sarif(report)
        else:
            return Result(
                success=False,
                message=f"Unknown format: {format}. Use 'json', 'markdown', or 'sarif'.",
            )

        if output_path:
            output_path = Path(output_path)
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(content)
                return Result(
                    success=True,
                    message=f"Security report written to {output_path}",
                    files_changed=[output_path],
                )
            except Exception as e:
                return Result(
                    success=False,
                    message=f"Failed to write security report: {e}",
                )

        return Result(
            success=True,
            message="Security report generated",
            data=content if format != "json" else json.loads(content),
        )

    def _format_json(self, report: SecurityReport) -> str:
        """Format report as JSON."""
        data = {
            "generated_at": report.generated_at.isoformat(),
            "project_root": str(report.project_root),
            "summary": {
                "total_findings": report.total_findings,
                "critical": report.critical_count,
                "high": report.high_count,
                "files_scanned": report.summary.get("files_scanned", 0),
            },
            "findings": [],
        }

        all_findings = report.all_findings
        if all_findings:
            data["findings"] = all_findings.to_list_of_dicts()

            # Add severity breakdown
            severity_counts = all_findings.count_by_severity()
            data["summary"]["by_severity"] = severity_counts

            # Add type breakdown
            type_counts = all_findings.count_by_type()
            data["summary"]["by_type"] = {k.name: v for k, v in type_counts.items()}

        return json.dumps(data, indent=2, default=str)

    def _format_markdown(self, report: SecurityReport) -> str:
        """Format report as Markdown."""
        lines = [
            "# Security Analysis Report",
            "",
            f"**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Project:** `{report.project_root}`",
            "",
            "## Summary",
            "",
            "| Metric | Count |",
            "|--------|-------|",
            f"| Total Findings | {report.total_findings} |",
            f"| Critical | {report.critical_count} |",
            f"| High | {report.high_count} |",
            f"| Files Scanned | {report.summary.get('files_scanned', 0)} |",
            "",
        ]

        all_findings = report.all_findings
        if all_findings and len(all_findings) > 0:
            # Group by severity
            lines.append("## Findings by Severity")
            lines.append("")

            for severity in ["critical", "high", "medium", "low"]:
                severity_findings = all_findings.by_severity(severity)
                if len(severity_findings) > 0:
                    lines.append(f"### {severity.upper()} ({len(severity_findings)})")
                    lines.append("")

                    for finding in severity_findings.sorted_by_location():
                        lines.append(f"#### {finding.type.name}")
                        lines.append(f"- **File:** `{finding.file_path}:{finding.line_number}`")
                        lines.append(f"- **Message:** {finding.message}")
                        if finding.code_snippet:
                            lines.append(f"- **Code:** `{finding.code_snippet}`")
                        if finding.recommendation:
                            lines.append(f"- **Recommendation:** {finding.recommendation}")
                        lines.append("")

            # Group by type
            lines.append("## Findings by Type")
            lines.append("")

            type_counts = all_findings.count_by_type()
            for stype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
                lines.append(f"- **{stype.name}:** {count}")
            lines.append("")

            # Files affected
            lines.append("## Affected Files")
            lines.append("")

            file_counts = all_findings.count_by_file()
            for file_path, count in sorted(file_counts.items(), key=lambda x: -x[1])[:20]:
                try:
                    rel_path = file_path.relative_to(report.project_root)
                except ValueError:
                    rel_path = file_path
                lines.append(f"- `{rel_path}`: {count} findings")
            if len(file_counts) > 20:
                lines.append(f"- ... and {len(file_counts) - 20} more files")

        else:
            lines.append("**No security findings detected.**")

        return "\n".join(lines)

    def _format_sarif(self, report: SecurityReport) -> str:
        """Format report in SARIF format for tool integration."""
        # SARIF 2.1.0 format
        sarif = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "rejig-security",
                            "version": "0.1.0",
                            "informationUri": "https://github.com/example/rejig",
                            "rules": self._get_sarif_rules(),
                        }
                    },
                    "results": [],
                }
            ],
        }

        all_findings = report.all_findings
        if all_findings:
            for finding in all_findings:
                sarif["runs"][0]["results"].append({
                    "ruleId": finding.type.name,
                    "level": self._severity_to_sarif_level(finding.severity),
                    "message": {
                        "text": finding.message,
                    },
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {
                                    "uri": str(finding.file_path),
                                },
                                "region": {
                                    "startLine": finding.line_number,
                                },
                            }
                        }
                    ],
                })

        return json.dumps(sarif, indent=2)

    def _get_sarif_rules(self) -> list[dict]:
        """Get SARIF rule definitions."""
        rules = []
        for stype in SecurityType:
            rules.append({
                "id": stype.name,
                "name": stype.name.replace("_", " ").title(),
                "shortDescription": {
                    "text": stype.name.replace("_", " ").lower(),
                },
            })
        return rules

    def _severity_to_sarif_level(self, severity: str) -> str:
        """Convert severity to SARIF level."""
        mapping = {
            "critical": "error",
            "high": "error",
            "medium": "warning",
            "low": "note",
        }
        return mapping.get(severity, "warning")

    def quick_scan(self) -> SecurityTargetList:
        """Perform a quick security scan for critical issues.

        Returns
        -------
        SecurityTargetList
            Critical and high severity findings only.
        """
        secrets = self._secrets_scanner.find_hardcoded_secrets()
        vulns = self._vulnerability_scanner.find_all_vulnerabilities()

        all_targets = list(secrets._targets) + list(vulns._targets)
        all_findings = SecurityTargetList(self._rejig, all_targets)

        return all_findings.at_least("high")
