"""
Tests for rejig.directives.reporter module.

This module tests DirectiveReporter and DirectiveReport:
- DirectiveReport data class for storing audit results
- DirectiveReporter.audit() for comprehensive reports
- DirectiveReporter.audit_type_ignores() for type: ignore reports
- DirectiveReporter.audit_noqa() for noqa reports
- DirectiveReporter.count_by_type() for quick counts
- DirectiveReporter.format_markdown() for markdown output
- DirectiveReporter.format_json() for JSON output

DirectiveReporter provides audit functionality for understanding
and managing linting directive usage across a codebase.

Coverage targets:
- DirectiveReport properties and methods
- DirectiveReport __str__() formatting
- DirectiveReport to_dict() conversion
- Various audit methods
- Output formatting (markdown, JSON)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from rejig import Rejig
from rejig.directives.reporter import DirectiveReport, DirectiveReporter


# =============================================================================
# DirectiveReport Tests
# =============================================================================

class TestDirectiveReport:
    """Tests for DirectiveReport data class."""

    def test_default_values(self):
        """
        DirectiveReport should have sensible default values.

        An empty report should have zero counts and empty collections.
        """
        report = DirectiveReport()

        assert report.total_count == 0
        assert report.bare_count == 0
        assert report.specific_count == 0
        assert report.without_reason_count == 0
        assert report.by_type == {}
        assert report.by_file == {}
        assert report.by_code == {}
        assert report.files_with_most_directives == []
        assert report.most_common_codes == []

    def test_str_output_empty_report(self):
        """
        __str__() should produce readable output for empty reports.
        """
        report = DirectiveReport()

        output = str(report)

        assert "Directive Report" in output
        assert "Total directives: 0" in output

    def test_str_output_with_data(self, tmp_path: Path):
        """
        __str__() should include all relevant information.
        """
        file_path = tmp_path / "test.py"

        report = DirectiveReport(
            total_count=5,
            by_type={"type_ignore": 3, "noqa": 2},
            by_file={file_path: 3},
            by_code={"arg-type": 2, "E501": 1},
            bare_count=1,
            specific_count=4,
            without_reason_count=3,
            files_with_most_directives=[(file_path, 3)],
            most_common_codes=[("arg-type", 2), ("E501", 1)],
        )

        output = str(report)

        assert "Total directives: 5" in output
        assert "Bare directives" in output
        assert "Specific directives" in output
        assert "Without reason" in output
        assert "By Type:" in output
        assert "type_ignore" in output

    def test_to_dict(self, tmp_path: Path):
        """
        to_dict() should convert report to a dictionary.

        This is useful for serialization to JSON or other formats.
        """
        file_path = tmp_path / "test.py"

        report = DirectiveReport(
            total_count=2,
            by_type={"type_ignore": 2},
            by_file={file_path: 2},
            by_code={"arg-type": 1},
            bare_count=1,
            specific_count=1,
            without_reason_count=0,
            files_with_most_directives=[(file_path, 2)],
            most_common_codes=[("arg-type", 1)],
        )

        data = report.to_dict()

        assert data["total_count"] == 2
        assert data["bare_count"] == 1
        assert data["specific_count"] == 1
        assert "type_ignore" in data["by_type"]
        assert str(file_path) in data["by_file"]


# =============================================================================
# DirectiveReporter Audit Tests
# =============================================================================

class TestDirectiveReporterAudit:
    """Tests for DirectiveReporter audit methods."""

    @pytest.fixture
    def project_with_directives(self, tmp_path: Path) -> Rejig:
        """Create a project with various directives for auditing."""
        (tmp_path / "module1.py").write_text('''\
import os  # noqa: F401
x = foo()  # type: ignore
y = bar()  # type: ignore[arg-type]  # Legacy API
z = baz()  # type: ignore[return-value]
''')
        (tmp_path / "module2.py").write_text('''\
a = 1  # noqa
b = 2  # noqa: E501
c = 3  # pylint: disable=invalid-name
if DEBUG:  # pragma: no cover
    pass
''')
        return Rejig(str(tmp_path))

    def test_audit_comprehensive(self, project_with_directives: Rejig):
        """
        audit() should generate a comprehensive report of all directives.
        """
        reporter = DirectiveReporter(project_with_directives)

        report = reporter.audit()

        # Check total count
        assert report.total_count >= 8

        # Check by_type has entries
        assert len(report.by_type) >= 3

        # Check bare vs specific counts
        assert report.bare_count >= 2  # bare type: ignore, bare noqa
        assert report.specific_count >= 4

    def test_audit_files_with_most_directives(
        self, project_with_directives: Rejig, tmp_path: Path
    ):
        """
        audit() should identify files with the most directives.
        """
        reporter = DirectiveReporter(project_with_directives)

        report = reporter.audit()

        # Should have top files list
        assert len(report.files_with_most_directives) >= 2

        # module1.py should have more directives
        top_file_path, top_count = report.files_with_most_directives[0]
        assert top_count >= 3

    def test_audit_most_common_codes(self, project_with_directives: Rejig):
        """
        audit() should identify the most commonly suppressed codes.
        """
        reporter = DirectiveReporter(project_with_directives)

        report = reporter.audit()

        # Should have common codes list
        assert len(report.most_common_codes) >= 1

    def test_audit_empty_project(self, tmp_path: Path):
        """
        audit() should handle empty projects gracefully.
        """
        rejig = Rejig(str(tmp_path))
        reporter = DirectiveReporter(rejig)

        report = reporter.audit()

        assert report.total_count == 0
        assert report.bare_count == 0
        assert report.specific_count == 0


# =============================================================================
# DirectiveReporter Type-specific Audit Tests
# =============================================================================

class TestDirectiveReporterTypeAudits:
    """Tests for type-specific audit methods."""

    @pytest.fixture
    def project(self, tmp_path: Path) -> Rejig:
        """Create a project for type-specific audits."""
        (tmp_path / "test.py").write_text('''\
x = foo()  # type: ignore
y = bar()  # type: ignore[arg-type]
z = baz()  # type: ignore[return-value]
a = 1  # noqa
b = 2  # noqa: E501
c = 3  # noqa: E501, F401
''')
        return Rejig(str(tmp_path))

    def test_audit_type_ignores(self, project: Rejig):
        """
        audit_type_ignores() should report only on type: ignore directives.
        """
        reporter = DirectiveReporter(project)

        report = reporter.audit_type_ignores()

        assert report.total_count == 3
        assert "type_ignore" in report.by_type
        assert report.by_type["type_ignore"] == 3
        assert report.bare_count == 1  # One bare type: ignore
        assert report.specific_count == 2  # Two with codes

    def test_audit_noqa(self, project: Rejig):
        """
        audit_noqa() should report only on noqa directives.
        """
        reporter = DirectiveReporter(project)

        report = reporter.audit_noqa()

        assert report.total_count == 3
        assert "noqa" in report.by_type
        assert report.by_type["noqa"] == 3
        assert report.bare_count == 1  # One bare noqa
        assert report.specific_count == 2  # Two with codes


# =============================================================================
# DirectiveReporter Count Methods Tests
# =============================================================================

class TestDirectiveReporterCounts:
    """Tests for DirectiveReporter count methods."""

    @pytest.fixture
    def project(self, tmp_path: Path) -> Rejig:
        """Create a project for count tests."""
        (tmp_path / "test.py").write_text('''\
x = 1  # type: ignore
y = 2  # type: ignore
z = 3  # noqa
w = 4  # pylint: disable=C0103
''')
        return Rejig(str(tmp_path))

    def test_count_by_type(self, project: Rejig):
        """
        count_by_type() should return counts of each directive type.
        """
        reporter = DirectiveReporter(project)

        counts = reporter.count_by_type()

        assert counts["type_ignore"] == 2
        assert counts["noqa"] == 1
        assert counts["pylint_disable"] == 1


# =============================================================================
# DirectiveReporter Formatting Tests
# =============================================================================

class TestDirectiveReporterFormatting:
    """Tests for DirectiveReporter output formatting."""

    @pytest.fixture
    def report(self, tmp_path: Path) -> DirectiveReport:
        """Create a sample report for formatting tests."""
        file_path = tmp_path / "test.py"

        return DirectiveReport(
            total_count=10,
            by_type={"type_ignore": 5, "noqa": 3, "pylint_disable": 2},
            by_file={file_path: 8, tmp_path / "other.py": 2},
            by_code={"arg-type": 3, "E501": 2, "F401": 1},
            bare_count=2,
            specific_count=8,
            without_reason_count=7,
            files_with_most_directives=[
                (file_path, 8),
                (tmp_path / "other.py", 2),
            ],
            most_common_codes=[
                ("arg-type", 3),
                ("E501", 2),
                ("F401", 1),
            ],
        )

    @pytest.fixture
    def reporter(self, tmp_path: Path) -> DirectiveReporter:
        """Create a reporter instance."""
        rejig = Rejig(str(tmp_path))
        return DirectiveReporter(rejig)

    def test_format_markdown(self, reporter: DirectiveReporter, report: DirectiveReport):
        """
        format_markdown() should produce valid markdown output.
        """
        output = reporter.format_markdown(report)

        # Check markdown structure
        assert "# Directive Audit Report" in output
        assert "## Summary" in output
        assert "## By Type" in output

        # Check markdown table format
        assert "|" in output
        assert "---" in output

        # Check data is present
        assert "10" in output  # total count
        assert "type_ignore" in output
        assert "arg-type" in output

    def test_format_json(self, reporter: DirectiveReporter, report: DirectiveReport):
        """
        format_json() should produce valid JSON output.
        """
        import json

        output = reporter.format_json(report)

        # Should be parseable JSON
        data = json.loads(output)

        assert data["total_count"] == 10
        assert "type_ignore" in data["by_type"]
        assert data["bare_count"] == 2
        assert len(data["most_common_codes"]) == 3


# =============================================================================
# DirectiveReporter Integration Tests
# =============================================================================

class TestDirectiveReporterIntegration:
    """Integration tests for DirectiveReporter."""

    def test_full_audit_workflow(self, tmp_path: Path):
        """
        Test complete audit workflow from files to formatted report.
        """
        # Create files with various directives
        (tmp_path / "main.py").write_text('''\
import os  # noqa: F401
x = foo()  # type: ignore[arg-type]  # Legacy API requires this
y = bar()  # type: ignore
''')
        (tmp_path / "utils.py").write_text('''\
# fmt: off
MATRIX = [[1, 2, 3]]
# fmt: on
z = 1  # pylint: disable=invalid-name
''')

        rejig = Rejig(str(tmp_path))
        reporter = DirectiveReporter(rejig)

        # Generate audit
        report = reporter.audit()

        # Verify report contents
        assert report.total_count >= 5
        assert report.bare_count >= 1
        assert report.without_reason_count >= 3

        # Format outputs
        markdown = reporter.format_markdown(report)
        json_output = reporter.format_json(report)

        # Verify outputs are non-empty and well-formed
        assert len(markdown) > 100
        assert "Directive Audit Report" in markdown

        import json
        data = json.loads(json_output)
        assert data["total_count"] == report.total_count

    def test_audit_helps_identify_tech_debt(self, tmp_path: Path):
        """
        DirectiveReporter helps identify technical debt patterns.

        A codebase with many bare directives or directives without
        reasons indicates potential tech debt that needs attention.
        """
        (tmp_path / "legacy.py").write_text('''\
# This file has poor directive hygiene
x = foo()  # type: ignore
y = bar()  # type: ignore
z = baz()  # noqa
w = qux()  # noqa
a = 1  # pylint: disable=C0103
''')
        (tmp_path / "modern.py").write_text('''\
# This file follows best practices
x = foo()  # type: ignore[arg-type]  # Third-party library issue
y = bar()  # noqa: E501  # URL cannot be shortened
''')

        rejig = Rejig(str(tmp_path))
        reporter = DirectiveReporter(rejig)

        report = reporter.audit()

        # Identify the tech debt
        # Bare directives (no specific codes) are often a code smell
        assert report.bare_count >= 4

        # Directives without reasons make code harder to maintain
        assert report.without_reason_count >= 5

        # Can identify which files need attention
        assert len(report.files_with_most_directives) >= 1
        top_file, count = report.files_with_most_directives[0]
        assert count >= 3  # legacy.py has more directives
