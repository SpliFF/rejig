"""
Tests for rejig.security.reporter module.

This module tests security report generation:
- SecurityReport dataclass
- SecurityReporter class
- JSON, Markdown, and SARIF output formats
"""
from __future__ import annotations

import json
import textwrap
from datetime import datetime
from pathlib import Path

import pytest

from rejig import Rejig
from rejig.security.reporter import SecurityReport, SecurityReporter
from rejig.security.targets import (
    SecurityFinding,
    SecurityTarget,
    SecurityTargetList,
    SecurityType,
)


# =============================================================================
# SecurityReport Tests
# =============================================================================

class TestSecurityReport:
    """Tests for SecurityReport dataclass."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_create_basic_report(self, tmp_path: Path):
        """Should create basic report."""
        report = SecurityReport(
            generated_at=datetime.now(),
            project_root=tmp_path,
        )
        assert report.project_root == tmp_path
        assert report.secrets is None
        assert report.vulnerabilities is None

    def test_total_findings_empty(self, tmp_path: Path):
        """Should return 0 for empty report."""
        report = SecurityReport(
            generated_at=datetime.now(),
            project_root=tmp_path,
        )
        assert report.total_findings == 0

    def test_total_findings_with_secrets(self, rejig: Rejig, tmp_path: Path):
        """Should count secrets in total."""
        findings = [
            SecurityTarget(rejig, SecurityFinding(
                type=SecurityType.HARDCODED_PASSWORD,
                file_path=tmp_path / "test.py",
                line_number=1,
            ))
        ]
        secrets = SecurityTargetList(rejig, findings)

        report = SecurityReport(
            generated_at=datetime.now(),
            project_root=tmp_path,
            secrets=secrets,
        )
        assert report.total_findings == 1

    def test_total_findings_combined(self, rejig: Rejig, tmp_path: Path):
        """Should count both secrets and vulnerabilities."""
        secret_findings = [
            SecurityTarget(rejig, SecurityFinding(
                type=SecurityType.HARDCODED_PASSWORD,
                file_path=tmp_path / "test.py",
                line_number=1,
            ))
        ]
        vuln_findings = [
            SecurityTarget(rejig, SecurityFinding(
                type=SecurityType.SQL_INJECTION,
                file_path=tmp_path / "test.py",
                line_number=5,
            ))
        ]

        report = SecurityReport(
            generated_at=datetime.now(),
            project_root=tmp_path,
            secrets=SecurityTargetList(rejig, secret_findings),
            vulnerabilities=SecurityTargetList(rejig, vuln_findings),
        )
        assert report.total_findings == 2

    def test_critical_count(self, rejig: Rejig, tmp_path: Path):
        """Should count critical findings."""
        findings = [
            SecurityTarget(rejig, SecurityFinding(
                type=SecurityType.SQL_INJECTION,
                file_path=tmp_path / "test.py",
                line_number=1,
                severity="critical",
            )),
            SecurityTarget(rejig, SecurityFinding(
                type=SecurityType.HARDCODED_PASSWORD,
                file_path=tmp_path / "test.py",
                line_number=2,
                severity="high",
            )),
        ]
        report = SecurityReport(
            generated_at=datetime.now(),
            project_root=tmp_path,
            vulnerabilities=SecurityTargetList(rejig, findings),
        )
        assert report.critical_count == 1

    def test_high_count(self, rejig: Rejig, tmp_path: Path):
        """Should count high severity findings."""
        findings = [
            SecurityTarget(rejig, SecurityFinding(
                type=SecurityType.HARDCODED_PASSWORD,
                file_path=tmp_path / "test.py",
                line_number=1,
                severity="high",
            )),
        ]
        report = SecurityReport(
            generated_at=datetime.now(),
            project_root=tmp_path,
            vulnerabilities=SecurityTargetList(rejig, findings),
        )
        assert report.high_count == 1

    def test_all_findings_combined(self, rejig: Rejig, tmp_path: Path):
        """Should combine all findings."""
        secret_findings = [
            SecurityTarget(rejig, SecurityFinding(
                type=SecurityType.HARDCODED_PASSWORD,
                file_path=tmp_path / "test.py",
                line_number=1,
            ))
        ]
        vuln_findings = [
            SecurityTarget(rejig, SecurityFinding(
                type=SecurityType.SQL_INJECTION,
                file_path=tmp_path / "test.py",
                line_number=5,
            ))
        ]

        report = SecurityReport(
            generated_at=datetime.now(),
            project_root=tmp_path,
            secrets=SecurityTargetList(rejig, secret_findings),
            vulnerabilities=SecurityTargetList(rejig, vuln_findings),
        )

        all_findings = report.all_findings
        assert all_findings is not None
        assert len(all_findings) == 2

    def test_str_output(self, rejig: Rejig, tmp_path: Path):
        """Should generate human-readable string."""
        findings = [
            SecurityTarget(rejig, SecurityFinding(
                type=SecurityType.HARDCODED_PASSWORD,
                file_path=tmp_path / "test.py",
                line_number=1,
                severity="critical",
            ))
        ]
        report = SecurityReport(
            generated_at=datetime.now(),
            project_root=tmp_path,
            secrets=SecurityTargetList(rejig, findings),
        )

        output = str(report)
        assert "Security Analysis Report" in output
        assert "Total findings" in output


# =============================================================================
# SecurityReporter Tests
# =============================================================================

class TestSecurityReporter:
    """Tests for SecurityReporter class."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_init(self, rejig: Rejig):
        """Should initialize with rejig instance."""
        reporter = SecurityReporter(rejig)
        assert reporter._rejig is rejig

    def test_generate_full_report_empty(self, rejig: Rejig, tmp_path: Path):
        """Should generate report for empty project."""
        reporter = SecurityReporter(rejig)
        report = reporter.generate_full_report()

        assert report.project_root == tmp_path
        assert report.generated_at is not None
        assert report.total_findings == 0

    def test_generate_full_report_with_findings(self, rejig: Rejig, tmp_path: Path):
        """Should generate report with findings."""
        file_path = tmp_path / "config.py"
        file_path.write_text('password = "supersecretpassword123"')

        reporter = SecurityReporter(rejig)
        report = reporter.generate_full_report()

        assert report.total_findings >= 1

    def test_generate_report_include_secrets_only(self, rejig: Rejig, tmp_path: Path):
        """Should generate report with only secrets."""
        file_path = tmp_path / "config.py"
        file_path.write_text('password = "supersecretpassword123"')

        reporter = SecurityReporter(rejig)
        report = reporter.generate_full_report(
            include_secrets=True,
            include_vulnerabilities=False,
        )

        assert report.secrets is not None
        assert report.vulnerabilities is None

    def test_generate_report_include_vulnerabilities_only(self, rejig: Rejig, tmp_path: Path):
        """Should generate report with only vulnerabilities."""
        file_path = tmp_path / "db.py"
        file_path.write_text('cursor.execute(f"SELECT * FROM {table}")')

        reporter = SecurityReporter(rejig)
        report = reporter.generate_full_report(
            include_secrets=False,
            include_vulnerabilities=True,
        )

        assert report.secrets is None
        assert report.vulnerabilities is not None

    # -------------------------------------------------------------------------
    # JSON Output
    # -------------------------------------------------------------------------

    def test_generate_security_report_json(self, rejig: Rejig, tmp_path: Path):
        """Should generate JSON report."""
        reporter = SecurityReporter(rejig)
        result = reporter.generate_security_report(format="json")

        assert result.success is True
        assert "data" in result.__dict__ or result.data is not None
        # Data should be a dict (parsed JSON)
        assert isinstance(result.data, dict)

    def test_generate_security_report_json_to_file(self, rejig: Rejig, tmp_path: Path):
        """Should write JSON report to file."""
        output_path = tmp_path / "report.json"
        reporter = SecurityReporter(rejig)
        result = reporter.generate_security_report(
            output_path=output_path,
            format="json",
        )

        assert result.success is True
        assert output_path.exists()

        # Verify valid JSON
        data = json.loads(output_path.read_text())
        assert "generated_at" in data
        assert "summary" in data

    # -------------------------------------------------------------------------
    # Markdown Output
    # -------------------------------------------------------------------------

    def test_generate_security_report_markdown(self, rejig: Rejig, tmp_path: Path):
        """Should generate Markdown report."""
        reporter = SecurityReporter(rejig)
        result = reporter.generate_security_report(format="markdown")

        assert result.success is True
        content = result.data
        assert "# Security Analysis Report" in content

    def test_generate_security_report_markdown_to_file(self, rejig: Rejig, tmp_path: Path):
        """Should write Markdown report to file."""
        output_path = tmp_path / "report.md"
        reporter = SecurityReporter(rejig)
        result = reporter.generate_security_report(
            output_path=output_path,
            format="markdown",
        )

        assert result.success is True
        assert output_path.exists()

        content = output_path.read_text()
        assert "# Security Analysis Report" in content

    def test_markdown_with_findings(self, rejig: Rejig, tmp_path: Path):
        """Should include findings in Markdown report."""
        file_path = tmp_path / "config.py"
        file_path.write_text('password = "supersecretpassword123"')

        reporter = SecurityReporter(rejig)
        result = reporter.generate_security_report(format="markdown")

        content = result.data
        assert "Findings" in content or "findings" in content.lower()

    # -------------------------------------------------------------------------
    # SARIF Output
    # -------------------------------------------------------------------------

    def test_generate_security_report_sarif(self, rejig: Rejig, tmp_path: Path):
        """Should generate SARIF report."""
        reporter = SecurityReporter(rejig)
        result = reporter.generate_security_report(format="sarif")

        assert result.success is True

    def test_generate_security_report_sarif_to_file(self, rejig: Rejig, tmp_path: Path):
        """Should write SARIF report to file."""
        output_path = tmp_path / "report.sarif"
        reporter = SecurityReporter(rejig)
        result = reporter.generate_security_report(
            output_path=output_path,
            format="sarif",
        )

        assert result.success is True
        assert output_path.exists()

        # Verify valid SARIF structure
        data = json.loads(output_path.read_text())
        assert "version" in data
        assert "runs" in data
        assert data["version"] == "2.1.0"

    def test_sarif_contains_rules(self, rejig: Rejig, tmp_path: Path):
        """SARIF should contain rule definitions."""
        output_path = tmp_path / "report.sarif"
        reporter = SecurityReporter(rejig)
        reporter.generate_security_report(
            output_path=output_path,
            format="sarif",
        )

        data = json.loads(output_path.read_text())
        rules = data["runs"][0]["tool"]["driver"]["rules"]
        assert len(rules) > 0

    # -------------------------------------------------------------------------
    # Error Cases
    # -------------------------------------------------------------------------

    def test_unknown_format_error(self, rejig: Rejig, tmp_path: Path):
        """Should return error for unknown format."""
        reporter = SecurityReporter(rejig)
        result = reporter.generate_security_report(format="xml")

        assert result.success is False
        assert "Unknown format" in result.message

    def test_write_to_invalid_path(self, rejig: Rejig, tmp_path: Path):
        """Should handle invalid output path."""
        # Create file where directory is expected
        blocking_file = tmp_path / "blocker"
        blocking_file.write_text("blocking")
        invalid_path = blocking_file / "report.json"

        reporter = SecurityReporter(rejig)
        result = reporter.generate_security_report(
            output_path=invalid_path,
            format="json",
        )

        assert result.success is False

    # -------------------------------------------------------------------------
    # Quick Scan
    # -------------------------------------------------------------------------

    def test_quick_scan_empty(self, rejig: Rejig, tmp_path: Path):
        """Should return empty for clean project."""
        reporter = SecurityReporter(rejig)
        findings = reporter.quick_scan()

        assert len(findings) == 0

    def test_quick_scan_filters_severity(self, rejig: Rejig, tmp_path: Path):
        """Should only return high+ severity."""
        file_path = tmp_path / "code.py"
        file_path.write_text(textwrap.dedent('''
            password = "supersecretpassword123"
            code = random.random()
        '''))

        reporter = SecurityReporter(rejig)
        findings = reporter.quick_scan()

        # All findings should be high or critical
        for finding in findings:
            assert finding.severity in ["high", "critical"]


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for reporter module."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_full_report_workflow(self, rejig: Rejig, tmp_path: Path):
        """Should complete full report workflow."""
        # Create vulnerable project
        (tmp_path / "config.py").write_text('password = "supersecretpassword123"')
        (tmp_path / "db.py").write_text('cursor.execute(f"SELECT * FROM {table}")')

        reporter = SecurityReporter(rejig)

        # Generate full report
        report = reporter.generate_full_report()
        assert report.total_findings >= 1

        # Write JSON report
        json_path = tmp_path / "reports" / "security.json"
        result = reporter.generate_security_report(
            output_path=json_path,
            format="json",
        )
        assert result.success is True
        assert json_path.exists()

        # Write Markdown report
        md_path = tmp_path / "reports" / "security.md"
        result = reporter.generate_security_report(
            output_path=md_path,
            format="markdown",
        )
        assert result.success is True
        assert md_path.exists()

    def test_report_content_accuracy(self, rejig: Rejig, tmp_path: Path):
        """Should accurately report findings."""
        file_path = tmp_path / "config.py"
        file_path.write_text('password = "mysupersecretpassword"')

        reporter = SecurityReporter(rejig)
        result = reporter.generate_security_report(format="json")

        data = result.data
        findings = data.get("findings", [])

        # Should have at least one finding
        assert len(findings) >= 1

        # Finding should reference the correct file
        file_refs = [f["file"] for f in findings]
        assert any("config.py" in f for f in file_refs)
