"""
Tests for rejig.analysis.targets module.

This module tests the target classes for analysis results:
- AnalysisType enum for categorizing findings
- AnalysisFinding dataclass for individual findings
- AnalysisTarget for wrapping findings
- AnalysisTargetList for collections of findings

These classes provide a fluent API for working with analysis results.

Coverage targets:
- AnalysisType enum values
- AnalysisFinding properties
- AnalysisTarget creation and properties
- AnalysisTargetList filtering methods
- Grouping and aggregation methods
- Sorting methods
- Output methods
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig import Rejig
from rejig.analysis.targets import (
    AnalysisFinding,
    AnalysisTarget,
    AnalysisTargetList,
    AnalysisType,
)


# =============================================================================
# AnalysisType Tests
# =============================================================================

class TestAnalysisType:
    """Tests for AnalysisType enum.

    AnalysisType categorizes different types of code analysis findings.
    """

    def test_pattern_types_exist(self):
        """
        AnalysisType should have pattern-related types.
        """
        assert hasattr(AnalysisType, "MISSING_TYPE_HINT")
        assert hasattr(AnalysisType, "MISSING_DOCSTRING")
        assert hasattr(AnalysisType, "BARE_EXCEPT")
        assert hasattr(AnalysisType, "HARDCODED_STRING")
        assert hasattr(AnalysisType, "MAGIC_NUMBER")

    def test_complexity_types_exist(self):
        """
        AnalysisType should have complexity-related types.
        """
        assert hasattr(AnalysisType, "HIGH_CYCLOMATIC_COMPLEXITY")
        assert hasattr(AnalysisType, "LONG_FUNCTION")
        assert hasattr(AnalysisType, "LONG_CLASS")
        assert hasattr(AnalysisType, "DEEP_NESTING")
        assert hasattr(AnalysisType, "TOO_MANY_PARAMETERS")

    def test_dead_code_types_exist(self):
        """
        AnalysisType should have dead code types.
        """
        assert hasattr(AnalysisType, "UNUSED_FUNCTION")
        assert hasattr(AnalysisType, "UNUSED_CLASS")
        assert hasattr(AnalysisType, "UNUSED_VARIABLE")
        assert hasattr(AnalysisType, "UNREACHABLE_CODE")


# =============================================================================
# AnalysisFinding Tests
# =============================================================================

class TestAnalysisFinding:
    """Tests for AnalysisFinding dataclass.

    AnalysisFinding represents a single code analysis finding.
    """

    def test_required_fields(self):
        """
        AnalysisFinding should require type, file_path, and line_number.
        """
        finding = AnalysisFinding(
            type=AnalysisType.MISSING_TYPE_HINT,
            file_path=Path("test.py"),
            line_number=10,
        )

        assert finding.type == AnalysisType.MISSING_TYPE_HINT
        assert finding.file_path == Path("test.py")
        assert finding.line_number == 10

    def test_optional_fields_have_defaults(self):
        """
        AnalysisFinding optional fields should have sensible defaults.
        """
        finding = AnalysisFinding(
            type=AnalysisType.BARE_EXCEPT,
            file_path=Path("test.py"),
            line_number=1,
        )

        assert finding.name is None
        assert finding.message == ""
        assert finding.severity == "warning"
        assert finding.value is None
        assert finding.threshold is None
        assert finding.context == {}

    def test_all_fields_settable(self):
        """
        AnalysisFinding should allow setting all optional fields.
        """
        finding = AnalysisFinding(
            type=AnalysisType.HIGH_CYCLOMATIC_COMPLEXITY,
            file_path=Path("app.py"),
            line_number=25,
            name="complex_function",
            message="Function has high complexity",
            severity="warning",
            value=15,
            threshold=10,
            context={"branch_count": 8},
        )

        assert finding.name == "complex_function"
        assert finding.message == "Function has high complexity"
        assert finding.value == 15
        assert finding.threshold == 10
        assert finding.context["branch_count"] == 8

    def test_location_property(self):
        """
        location property should return file:line format.
        """
        finding = AnalysisFinding(
            type=AnalysisType.LONG_FUNCTION,
            file_path=Path("app/core.py"),
            line_number=42,
        )

        assert finding.location == "app/core.py:42"


# =============================================================================
# AnalysisTarget Tests
# =============================================================================

class TestAnalysisTarget:
    """Tests for AnalysisTarget class.

    AnalysisTarget wraps an AnalysisFinding and provides methods
    for navigation and manipulation.
    """

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    @pytest.fixture
    def sample_finding(self) -> AnalysisFinding:
        """Create a sample finding for testing."""
        return AnalysisFinding(
            type=AnalysisType.MISSING_TYPE_HINT,
            file_path=Path("app.py"),
            line_number=10,
            name="my_function",
            message="Function lacks type hints",
            severity="warning",
            value=None,
        )

    def test_creation(self, rejig: Rejig, sample_finding: AnalysisFinding):
        """
        AnalysisTarget should wrap an AnalysisFinding.
        """
        target = AnalysisTarget(rejig, sample_finding)

        assert target.finding is sample_finding
        assert target.file_path == Path("app.py")
        assert target.line_number == 10

    def test_name_property(self, rejig: Rejig, sample_finding: AnalysisFinding):
        """
        name property should return the finding's name.
        """
        target = AnalysisTarget(rejig, sample_finding)

        assert target.name == "my_function"

    def test_type_property(self, rejig: Rejig, sample_finding: AnalysisFinding):
        """
        type property should return the AnalysisType.
        """
        target = AnalysisTarget(rejig, sample_finding)

        assert target.type == AnalysisType.MISSING_TYPE_HINT

    def test_message_property(self, rejig: Rejig, sample_finding: AnalysisFinding):
        """
        message property should return the finding's message.
        """
        target = AnalysisTarget(rejig, sample_finding)

        assert target.message == "Function lacks type hints"

    def test_severity_property(self, rejig: Rejig, sample_finding: AnalysisFinding):
        """
        severity property should return the finding's severity.
        """
        target = AnalysisTarget(rejig, sample_finding)

        assert target.severity == "warning"

    def test_location_property(self, rejig: Rejig, sample_finding: AnalysisFinding):
        """
        location property should return file:line format.
        """
        target = AnalysisTarget(rejig, sample_finding)

        assert target.location == "app.py:10"

    def test_exists(self, tmp_path: Path):
        """
        exists() should check if the underlying file exists.
        """
        (tmp_path / "exists.py").write_text("x = 1\n")

        rj = Rejig(str(tmp_path))

        exists_finding = AnalysisFinding(
            type=AnalysisType.BARE_EXCEPT,
            file_path=tmp_path / "exists.py",
            line_number=1,
        )
        missing_finding = AnalysisFinding(
            type=AnalysisType.BARE_EXCEPT,
            file_path=tmp_path / "missing.py",
            line_number=1,
        )

        assert AnalysisTarget(rj, exists_finding).exists() is True
        assert AnalysisTarget(rj, missing_finding).exists() is False

    def test_repr(self, rejig: Rejig, sample_finding: AnalysisFinding):
        """
        __repr__ should include type and location.
        """
        target = AnalysisTarget(rejig, sample_finding)
        repr_str = repr(target)

        assert "AnalysisTarget" in repr_str
        assert "MISSING_TYPE_HINT" in repr_str
        assert "app.py:10" in repr_str


# =============================================================================
# AnalysisTargetList Tests
# =============================================================================

class TestAnalysisTargetList:
    """Tests for AnalysisTargetList class.

    AnalysisTargetList provides filtering, grouping, and aggregation
    methods for collections of analysis findings.
    """

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    @pytest.fixture
    def sample_targets(self, rejig: Rejig) -> AnalysisTargetList:
        """Create a sample list of analysis targets."""
        findings = [
            AnalysisFinding(
                type=AnalysisType.MISSING_TYPE_HINT,
                file_path=Path("app/core.py"),
                line_number=10,
                name="func1",
                severity="warning",
                value=None,
            ),
            AnalysisFinding(
                type=AnalysisType.MISSING_TYPE_HINT,
                file_path=Path("app/utils.py"),
                line_number=5,
                name="func2",
                severity="warning",
                value=None,
            ),
            AnalysisFinding(
                type=AnalysisType.HIGH_CYCLOMATIC_COMPLEXITY,
                file_path=Path("app/core.py"),
                line_number=25,
                name="complex_func",
                severity="warning",
                value=15,
            ),
            AnalysisFinding(
                type=AnalysisType.UNUSED_FUNCTION,
                file_path=Path("app/legacy.py"),
                line_number=1,
                name="old_func",
                severity="info",
                value=None,
            ),
            AnalysisFinding(
                type=AnalysisType.BARE_EXCEPT,
                file_path=Path("app/core.py"),
                line_number=50,
                name=None,
                severity="error",
                value=None,
            ),
        ]
        targets = [AnalysisTarget(rejig, f) for f in findings]
        return AnalysisTargetList(rejig, targets)

    # ===== Basic Operations =====

    def test_len(self, sample_targets: AnalysisTargetList):
        """
        __len__ should return the number of targets.
        """
        assert len(sample_targets) == 5

    def test_iteration(self, sample_targets: AnalysisTargetList):
        """
        AnalysisTargetList should be iterable.
        """
        items = list(sample_targets)
        assert len(items) == 5
        assert all(isinstance(t, AnalysisTarget) for t in items)

    def test_empty_list(self, rejig: Rejig):
        """
        Empty AnalysisTargetList should work correctly.
        """
        empty = AnalysisTargetList(rejig, [])

        assert len(empty) == 0
        assert list(empty) == []

    # ===== Type Filtering =====

    def test_by_type(self, sample_targets: AnalysisTargetList):
        """
        by_type should filter to a specific AnalysisType.
        """
        missing_hints = sample_targets.by_type(AnalysisType.MISSING_TYPE_HINT)

        assert len(missing_hints) == 2
        for target in missing_hints:
            assert target.type == AnalysisType.MISSING_TYPE_HINT

    def test_by_types(self, sample_targets: AnalysisTargetList):
        """
        by_types should filter to multiple AnalysisTypes.
        """
        filtered = sample_targets.by_types(
            AnalysisType.MISSING_TYPE_HINT,
            AnalysisType.HIGH_CYCLOMATIC_COMPLEXITY
        )

        assert len(filtered) == 3
        for target in filtered:
            assert target.type in {
                AnalysisType.MISSING_TYPE_HINT,
                AnalysisType.HIGH_CYCLOMATIC_COMPLEXITY,
            }

    # ===== Severity Filtering =====

    def test_by_severity(self, sample_targets: AnalysisTargetList):
        """
        by_severity should filter to a specific severity level.
        """
        warnings = sample_targets.by_severity("warning")

        for target in warnings:
            assert target.severity == "warning"

    def test_errors(self, sample_targets: AnalysisTargetList):
        """
        errors() should filter to error-level findings.
        """
        errors = sample_targets.errors()

        assert len(errors) == 1
        assert errors[0].severity == "error"

    def test_warnings(self, sample_targets: AnalysisTargetList):
        """
        warnings() should filter to warning-level findings.
        """
        warnings = sample_targets.warnings()

        for target in warnings:
            assert target.severity == "warning"

    def test_info(self, sample_targets: AnalysisTargetList):
        """
        info() should filter to info-level findings.
        """
        info = sample_targets.info()

        assert len(info) == 1
        assert info[0].severity == "info"

    # ===== Location Filtering =====

    def test_in_file(self, sample_targets: AnalysisTargetList):
        """
        in_file should filter to findings in a specific file.
        """
        core_findings = sample_targets.in_file(Path("app/core.py"))

        assert len(core_findings) == 3
        for target in core_findings:
            assert target.file_path == Path("app/core.py")

    def test_in_directory(self, sample_targets: AnalysisTargetList):
        """
        in_directory should filter to findings in a directory.
        """
        app_findings = sample_targets.in_directory(Path("app"))

        # All findings are in the app/ directory
        assert len(app_findings) == 5

    # ===== Value Filtering =====

    def test_above_threshold(self, sample_targets: AnalysisTargetList):
        """
        above_threshold should filter to findings above a value.
        """
        high_value = sample_targets.above_threshold(10)

        # Only the complexity finding has value > 10
        assert len(high_value) == 1
        assert high_value[0].value == 15

    def test_below_threshold(self, sample_targets: AnalysisTargetList):
        """
        below_threshold should filter to findings below a value.
        """
        low_value = sample_targets.below_threshold(20)

        # The complexity finding (15) is below 20
        assert len(low_value) == 1

    # ===== Category Shortcuts =====

    def test_complexity_issues(self, sample_targets: AnalysisTargetList):
        """
        complexity_issues should filter to complexity-related types.
        """
        complexity = sample_targets.complexity_issues()

        # Only HIGH_CYCLOMATIC_COMPLEXITY in our sample
        assert len(complexity) == 1
        assert complexity[0].type == AnalysisType.HIGH_CYCLOMATIC_COMPLEXITY

    def test_dead_code(self, sample_targets: AnalysisTargetList):
        """
        dead_code should filter to dead code types.
        """
        dead = sample_targets.dead_code()

        # Only UNUSED_FUNCTION in our sample
        assert len(dead) == 1
        assert dead[0].type == AnalysisType.UNUSED_FUNCTION

    def test_pattern_issues(self, sample_targets: AnalysisTargetList):
        """
        pattern_issues should filter to pattern-related types.
        """
        patterns = sample_targets.pattern_issues()

        # MISSING_TYPE_HINT and BARE_EXCEPT
        assert len(patterns) == 3

    # ===== Grouping =====

    def test_group_by_file(self, sample_targets: AnalysisTargetList):
        """
        group_by_file should group findings by file path.
        """
        grouped = sample_targets.group_by_file()

        assert len(grouped) == 3  # core.py, utils.py, legacy.py
        assert Path("app/core.py") in grouped
        assert len(grouped[Path("app/core.py")]) == 3

    def test_group_by_type(self, sample_targets: AnalysisTargetList):
        """
        group_by_type should group findings by AnalysisType.
        """
        grouped = sample_targets.group_by_type()

        assert AnalysisType.MISSING_TYPE_HINT in grouped
        assert len(grouped[AnalysisType.MISSING_TYPE_HINT]) == 2

    def test_count_by_type(self, sample_targets: AnalysisTargetList):
        """
        count_by_type should return counts per type.
        """
        counts = sample_targets.count_by_type()

        assert counts[AnalysisType.MISSING_TYPE_HINT] == 2
        assert counts[AnalysisType.HIGH_CYCLOMATIC_COMPLEXITY] == 1
        assert counts[AnalysisType.UNUSED_FUNCTION] == 1
        assert counts[AnalysisType.BARE_EXCEPT] == 1

    def test_count_by_severity(self, sample_targets: AnalysisTargetList):
        """
        count_by_severity should return counts per severity.
        """
        counts = sample_targets.count_by_severity()

        assert counts["warning"] == 3
        assert counts["info"] == 1
        assert counts["error"] == 1

    def test_count_by_file(self, sample_targets: AnalysisTargetList):
        """
        count_by_file should return counts per file.
        """
        counts = sample_targets.count_by_file()

        assert counts[Path("app/core.py")] == 3
        assert counts[Path("app/utils.py")] == 1
        assert counts[Path("app/legacy.py")] == 1

    # ===== Sorting =====

    def test_sorted_by_severity(self, sample_targets: AnalysisTargetList):
        """
        sorted_by_severity should sort errors first by default.
        """
        sorted_list = sample_targets.sorted_by_severity()

        # First item should be error
        assert sorted_list[0].severity == "error"

    def test_sorted_by_severity_ascending(self, sample_targets: AnalysisTargetList):
        """
        sorted_by_severity(descending=False) should sort info first.
        """
        sorted_list = sample_targets.sorted_by_severity(descending=False)

        # First item should be info
        assert sorted_list[0].severity == "info"

    def test_sorted_by_value(self, sample_targets: AnalysisTargetList):
        """
        sorted_by_value should sort by numeric value descending.
        """
        sorted_list = sample_targets.sorted_by_value()

        # First item with value should be the highest
        with_value = [t for t in sorted_list if t.value is not None]
        if with_value:
            assert with_value[0].value == 15

    def test_sorted_by_location(self, sample_targets: AnalysisTargetList):
        """
        sorted_by_location should sort by file then line number.
        """
        sorted_list = sample_targets.sorted_by_location()

        # Should be sorted alphabetically by file, then by line
        locations = [(str(t.file_path), t.line_number) for t in sorted_list]
        assert locations == sorted(locations)

    # ===== Output Methods =====

    def test_to_list_of_dicts(self, sample_targets: AnalysisTargetList):
        """
        to_list_of_dicts should export as serializable dictionaries.
        """
        data = sample_targets.to_list_of_dicts()

        assert len(data) == 5
        assert all(isinstance(d, dict) for d in data)
        # Check expected keys
        first = data[0]
        assert "type" in first
        assert "file" in first
        assert "line" in first
        assert "message" in first
        assert "severity" in first

    def test_summary(self, sample_targets: AnalysisTargetList):
        """
        summary should return a formatted string.
        """
        summary = sample_targets.summary()

        assert "Total: 5 findings" in summary
        assert "MISSING_TYPE_HINT" in summary

    def test_summary_empty(self, rejig: Rejig):
        """
        summary for empty list should indicate no findings.
        """
        empty = AnalysisTargetList(rejig, [])
        summary = empty.summary()

        assert "No findings" in summary


# =============================================================================
# Integration Tests
# =============================================================================

class TestAnalysisTargetIntegration:
    """Integration tests for analysis targets."""

    def test_chained_filtering(self, tmp_path: Path):
        """
        Filters can be chained together.
        """
        rj = Rejig(str(tmp_path))

        findings = [
            AnalysisFinding(
                type=AnalysisType.MISSING_TYPE_HINT,
                file_path=Path("app.py"),
                line_number=10,
                severity="warning",
            ),
            AnalysisFinding(
                type=AnalysisType.MISSING_TYPE_HINT,
                file_path=Path("app.py"),
                line_number=20,
                severity="info",
            ),
            AnalysisFinding(
                type=AnalysisType.BARE_EXCEPT,
                file_path=Path("app.py"),
                line_number=30,
                severity="warning",
            ),
        ]
        targets = AnalysisTargetList(
            rj, [AnalysisTarget(rj, f) for f in findings]
        )

        # Chain: pattern issues -> warnings only
        result = targets.pattern_issues().warnings()

        assert len(result) == 2
        for t in result:
            assert t.severity == "warning"

    def test_navigation_to_file_target(self, tmp_path: Path):
        """
        AnalysisTarget can navigate to the underlying FileTarget.
        """
        (tmp_path / "app.py").write_text("x = 1\n")
        rj = Rejig(str(tmp_path))

        finding = AnalysisFinding(
            type=AnalysisType.UNUSED_VARIABLE,
            file_path=tmp_path / "app.py",
            line_number=1,
            name="x",
        )
        target = AnalysisTarget(rj, finding)

        file_target = target.to_file_target()
        assert file_target.exists()
