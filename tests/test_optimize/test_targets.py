"""
Tests for rejig.optimize.targets module.

This module tests optimization target classes:
- OptimizeType enum
- OptimizeFinding dataclass
- OptimizeTarget class
- OptimizeTargetList class with filtering and aggregation

Coverage targets:
- OptimizeType enum values for DRY and loop optimizations
- OptimizeFinding attributes and properties
- OptimizeTarget navigation and properties
- OptimizeTargetList filtering (by_type, by_severity, in_file, etc.)
- OptimizeTargetList aggregation (group_by, count_by, etc.)
- OptimizeTargetList sorting and output methods
"""
from __future__ import annotations

from pathlib import Path

import pytest

from rejig import Rejig
from rejig.optimize.targets import (
    OptimizeFinding,
    OptimizeTarget,
    OptimizeTargetList,
    OptimizeType,
)


# =============================================================================
# OptimizeType Tests
# =============================================================================

class TestOptimizeType:
    """Tests for OptimizeType enum.

    OptimizeType defines all types of optimization findings.
    """

    def test_dry_types_exist(self):
        """
        OptimizeType should have DRY-related types.
        """
        assert hasattr(OptimizeType, "DUPLICATE_CODE_BLOCK")
        assert hasattr(OptimizeType, "DUPLICATE_EXPRESSION")
        assert hasattr(OptimizeType, "DUPLICATE_LITERAL")
        assert hasattr(OptimizeType, "SIMILAR_FUNCTION")
        assert hasattr(OptimizeType, "REPEATED_PATTERN")

    def test_loop_types_exist(self):
        """
        OptimizeType should have loop optimization types.
        """
        assert hasattr(OptimizeType, "SLOW_LOOP_TO_COMPREHENSION")
        assert hasattr(OptimizeType, "SLOW_LOOP_TO_DICT_COMPREHENSION")
        assert hasattr(OptimizeType, "SLOW_LOOP_TO_SET_COMPREHENSION")
        assert hasattr(OptimizeType, "SLOW_LOOP_TO_MAP")
        assert hasattr(OptimizeType, "SLOW_LOOP_TO_FILTER")
        assert hasattr(OptimizeType, "SLOW_LOOP_TO_ANY_ALL")
        assert hasattr(OptimizeType, "SLOW_LOOP_TO_SUM")
        assert hasattr(OptimizeType, "SLOW_LOOP_TO_JOIN")
        assert hasattr(OptimizeType, "SLOW_LOOP_TO_ENUMERATE")
        assert hasattr(OptimizeType, "SLOW_LOOP_TO_ZIP")

    def test_efficiency_types_exist(self):
        """
        OptimizeType should have general efficiency types.
        """
        assert hasattr(OptimizeType, "INEFFICIENT_STRING_CONCAT")
        assert hasattr(OptimizeType, "INEFFICIENT_LIST_EXTEND")
        assert hasattr(OptimizeType, "UNNECESSARY_LIST_CONVERSION")


# =============================================================================
# OptimizeFinding Tests
# =============================================================================

class TestOptimizeFinding:
    """Tests for OptimizeFinding dataclass.

    OptimizeFinding holds data about a single optimization opportunity.
    """

    def test_basic_attributes(self):
        """
        OptimizeFinding should have basic required attributes.
        """
        finding = OptimizeFinding(
            type=OptimizeType.SLOW_LOOP_TO_COMPREHENSION,
            file_path=Path("test.py"),
            line_number=10,
        )

        assert finding.type == OptimizeType.SLOW_LOOP_TO_COMPREHENSION
        assert finding.file_path == Path("test.py")
        assert finding.line_number == 10
        # Default values
        assert finding.end_line == 10  # defaults to line_number
        assert finding.severity == "suggestion"
        assert finding.message == ""
        assert finding.original_code == ""
        assert finding.suggested_code == ""
        assert finding.context == {}

    def test_end_line_defaults_to_line_number(self):
        """
        end_line should default to line_number if not specified.
        """
        finding = OptimizeFinding(
            type=OptimizeType.DUPLICATE_LITERAL,
            file_path=Path("test.py"),
            line_number=5,
        )

        assert finding.end_line == 5

    def test_end_line_can_be_specified(self):
        """
        end_line can be specified separately for multi-line findings.
        """
        finding = OptimizeFinding(
            type=OptimizeType.DUPLICATE_CODE_BLOCK,
            file_path=Path("test.py"),
            line_number=5,
            end_line=15,
        )

        assert finding.line_number == 5
        assert finding.end_line == 15

    def test_location_single_line(self):
        """
        location property should format file:line for single-line findings.
        """
        finding = OptimizeFinding(
            type=OptimizeType.DUPLICATE_LITERAL,
            file_path=Path("src/utils.py"),
            line_number=42,
        )

        assert finding.location == "src/utils.py:42"

    def test_location_multi_line(self):
        """
        location property should format file:start-end for multi-line findings.
        """
        finding = OptimizeFinding(
            type=OptimizeType.DUPLICATE_CODE_BLOCK,
            file_path=Path("src/utils.py"),
            line_number=10,
            end_line=20,
        )

        assert finding.location == "src/utils.py:10-20"

    def test_context_default_initialization(self):
        """
        context should be initialized to empty dict if None.
        """
        finding = OptimizeFinding(
            type=OptimizeType.DUPLICATE_LITERAL,
            file_path=Path("test.py"),
            line_number=1,
            context=None,
        )

        assert finding.context == {}

    def test_full_attributes(self):
        """
        OptimizeFinding should store all provided attributes.
        """
        finding = OptimizeFinding(
            type=OptimizeType.SLOW_LOOP_TO_COMPREHENSION,
            file_path=Path("app.py"),
            line_number=10,
            end_line=15,
            name="process_items",
            message="Loop can be replaced with list comprehension",
            severity="suggestion",
            original_code="for x in items:\n    result.append(x)",
            suggested_code="result = [x for x in items]",
            estimated_improvement="Better readability",
            context={"confidence": 0.95},
        )

        assert finding.name == "process_items"
        assert "comprehension" in finding.message.lower()
        assert finding.original_code != ""
        assert finding.suggested_code != ""
        assert finding.context["confidence"] == 0.95


# =============================================================================
# OptimizeTarget Tests
# =============================================================================

class TestOptimizeTarget:
    """Tests for OptimizeTarget class.

    OptimizeTarget wraps an OptimizeFinding and provides navigation.
    """

    @pytest.fixture
    def sample_finding(self, tmp_path: Path) -> OptimizeFinding:
        """Create a sample finding for testing."""
        file_path = tmp_path / "sample.py"
        file_path.write_text("def foo():\n    pass\n")
        return OptimizeFinding(
            type=OptimizeType.SLOW_LOOP_TO_COMPREHENSION,
            file_path=file_path,
            line_number=1,
            end_line=2,
            name="foo",
            message="Test message",
            severity="suggestion",
            original_code="for x in y: pass",
            suggested_code="[x for x in y]",
        )

    @pytest.fixture
    def sample_target(self, tmp_path: Path, sample_finding: OptimizeFinding) -> OptimizeTarget:
        """Create a sample target for testing."""
        rj = Rejig(str(tmp_path))
        return OptimizeTarget(rj, sample_finding)

    def test_properties_delegate_to_finding(self, sample_target: OptimizeTarget):
        """
        OptimizeTarget properties should delegate to the finding.
        """
        assert sample_target.type == OptimizeType.SLOW_LOOP_TO_COMPREHENSION
        assert sample_target.line_number == 1
        assert sample_target.end_line == 2
        assert sample_target.name == "foo"
        assert sample_target.message == "Test message"
        assert sample_target.severity == "suggestion"
        assert sample_target.original_code == "for x in y: pass"
        assert sample_target.suggested_code == "[x for x in y]"

    def test_finding_property(self, sample_target: OptimizeTarget, sample_finding: OptimizeFinding):
        """
        finding property should return the underlying OptimizeFinding.
        """
        assert sample_target.finding == sample_finding

    def test_exists_when_file_exists(self, sample_target: OptimizeTarget):
        """
        exists() should return True when the file exists.
        """
        assert sample_target.exists() is True

    def test_exists_when_file_missing(self, tmp_path: Path):
        """
        exists() should return False when the file doesn't exist.
        """
        finding = OptimizeFinding(
            type=OptimizeType.DUPLICATE_LITERAL,
            file_path=tmp_path / "nonexistent.py",
            line_number=1,
        )
        rj = Rejig(str(tmp_path))
        target = OptimizeTarget(rj, finding)

        assert target.exists() is False

    def test_repr(self, sample_target: OptimizeTarget):
        """
        __repr__ should return a descriptive string.
        """
        repr_str = repr(sample_target)
        assert "OptimizeTarget" in repr_str
        assert "SLOW_LOOP_TO_COMPREHENSION" in repr_str

    def test_to_file_target(self, sample_target: OptimizeTarget):
        """
        to_file_target() should return a FileTarget for the file.
        """
        file_target = sample_target.to_file_target()
        assert file_target.exists()

    def test_to_line_target(self, sample_target: OptimizeTarget):
        """
        to_line_target() should return a LineTarget for the line.
        """
        line_target = sample_target.to_line_target()
        # LineTarget should exist if file exists
        assert line_target is not None


# =============================================================================
# OptimizeTargetList Tests
# =============================================================================

class TestOptimizeTargetList:
    """Tests for OptimizeTargetList class.

    OptimizeTargetList provides filtering and aggregation over findings.
    """

    @pytest.fixture
    def sample_findings(self, tmp_path: Path) -> list[OptimizeFinding]:
        """Create sample findings for testing."""
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file1.write_text("x = 1")
        file2.write_text("y = 2")

        return [
            OptimizeFinding(
                type=OptimizeType.SLOW_LOOP_TO_COMPREHENSION,
                file_path=file1,
                line_number=1,
                severity="suggestion",
            ),
            OptimizeFinding(
                type=OptimizeType.SLOW_LOOP_TO_COMPREHENSION,
                file_path=file2,
                line_number=5,
                severity="warning",
            ),
            OptimizeFinding(
                type=OptimizeType.DUPLICATE_LITERAL,
                file_path=file1,
                line_number=10,
                severity="suggestion",
            ),
            OptimizeFinding(
                type=OptimizeType.DUPLICATE_CODE_BLOCK,
                file_path=file1,
                line_number=20,
                severity="warning",
            ),
            OptimizeFinding(
                type=OptimizeType.SLOW_LOOP_TO_SUM,
                file_path=file2,
                line_number=15,
                severity="info",
            ),
        ]

    @pytest.fixture
    def sample_target_list(
        self, tmp_path: Path, sample_findings: list[OptimizeFinding]
    ) -> OptimizeTargetList:
        """Create a sample target list for testing."""
        rj = Rejig(str(tmp_path))
        targets = [OptimizeTarget(rj, f) for f in sample_findings]
        return OptimizeTargetList(rj, targets)

    def test_len(self, sample_target_list: OptimizeTargetList):
        """
        len() should return the number of targets.
        """
        assert len(sample_target_list) == 5

    def test_iteration(self, sample_target_list: OptimizeTargetList):
        """
        OptimizeTargetList should be iterable.
        """
        items = list(sample_target_list)
        assert len(items) == 5
        for item in items:
            assert isinstance(item, OptimizeTarget)

    def test_repr(self, sample_target_list: OptimizeTargetList):
        """
        __repr__ should show count.
        """
        assert "5 findings" in repr(sample_target_list)

    # === Type filtering ===

    def test_by_type(self, sample_target_list: OptimizeTargetList):
        """
        by_type() should filter to a specific type.
        """
        comprehensions = sample_target_list.by_type(OptimizeType.SLOW_LOOP_TO_COMPREHENSION)
        assert len(comprehensions) == 2
        for t in comprehensions:
            assert t.type == OptimizeType.SLOW_LOOP_TO_COMPREHENSION

    def test_by_types(self, sample_target_list: OptimizeTargetList):
        """
        by_types() should filter to multiple types.
        """
        loop_types = sample_target_list.by_types(
            OptimizeType.SLOW_LOOP_TO_COMPREHENSION,
            OptimizeType.SLOW_LOOP_TO_SUM,
        )
        assert len(loop_types) == 3

    # === Severity filtering ===

    def test_by_severity(self, sample_target_list: OptimizeTargetList):
        """
        by_severity() should filter to a specific severity.
        """
        warnings = sample_target_list.by_severity("warning")
        assert len(warnings) == 2
        for t in warnings:
            assert t.severity == "warning"

    def test_suggestions(self, sample_target_list: OptimizeTargetList):
        """
        suggestions() should filter to suggestion severity.
        """
        suggestions = sample_target_list.suggestions()
        assert len(suggestions) == 2
        for t in suggestions:
            assert t.severity == "suggestion"

    def test_warnings(self, sample_target_list: OptimizeTargetList):
        """
        warnings() should filter to warning severity.
        """
        warnings = sample_target_list.warnings()
        assert len(warnings) == 2

    def test_info(self, sample_target_list: OptimizeTargetList):
        """
        info() should filter to info severity.
        """
        info_items = sample_target_list.info()
        assert len(info_items) == 1

    # === Location filtering ===

    def test_in_file(self, sample_target_list: OptimizeTargetList, tmp_path: Path):
        """
        in_file() should filter to a specific file.
        """
        file1 = tmp_path / "file1.py"
        in_file1 = sample_target_list.in_file(file1)
        assert len(in_file1) == 3
        for t in in_file1:
            assert t.file_path == file1

    def test_in_file_with_string(self, sample_target_list: OptimizeTargetList, tmp_path: Path):
        """
        in_file() should accept string paths.
        """
        in_file = sample_target_list.in_file(str(tmp_path / "file1.py"))
        assert len(in_file) == 3

    def test_in_directory(self, sample_target_list: OptimizeTargetList, tmp_path: Path):
        """
        in_directory() should filter to files in a directory.
        """
        in_dir = sample_target_list.in_directory(tmp_path)
        assert len(in_dir) == 5  # All files are in tmp_path

    # === Category shortcuts ===

    def test_dry_issues(self, sample_target_list: OptimizeTargetList):
        """
        dry_issues() should filter to DRY-related findings.
        """
        dry = sample_target_list.dry_issues()
        assert len(dry) == 2
        for t in dry:
            assert t.type in {
                OptimizeType.DUPLICATE_CODE_BLOCK,
                OptimizeType.DUPLICATE_EXPRESSION,
                OptimizeType.DUPLICATE_LITERAL,
                OptimizeType.SIMILAR_FUNCTION,
                OptimizeType.REPEATED_PATTERN,
            }

    def test_loop_issues(self, sample_target_list: OptimizeTargetList):
        """
        loop_issues() should filter to loop optimization findings.
        """
        loops = sample_target_list.loop_issues()
        assert len(loops) == 3

    # === Aggregation ===

    def test_group_by_file(self, sample_target_list: OptimizeTargetList, tmp_path: Path):
        """
        group_by_file() should group findings by file path.
        """
        groups = sample_target_list.group_by_file()
        assert len(groups) == 2
        assert tmp_path / "file1.py" in groups
        assert tmp_path / "file2.py" in groups
        assert len(groups[tmp_path / "file1.py"]) == 3
        assert len(groups[tmp_path / "file2.py"]) == 2

    def test_group_by_type(self, sample_target_list: OptimizeTargetList):
        """
        group_by_type() should group findings by type.
        """
        groups = sample_target_list.group_by_type()
        assert OptimizeType.SLOW_LOOP_TO_COMPREHENSION in groups
        assert len(groups[OptimizeType.SLOW_LOOP_TO_COMPREHENSION]) == 2

    def test_count_by_type(self, sample_target_list: OptimizeTargetList):
        """
        count_by_type() should return counts per type.
        """
        counts = sample_target_list.count_by_type()
        assert counts[OptimizeType.SLOW_LOOP_TO_COMPREHENSION] == 2
        assert counts[OptimizeType.DUPLICATE_LITERAL] == 1
        assert counts[OptimizeType.DUPLICATE_CODE_BLOCK] == 1
        assert counts[OptimizeType.SLOW_LOOP_TO_SUM] == 1

    def test_count_by_severity(self, sample_target_list: OptimizeTargetList):
        """
        count_by_severity() should return counts per severity.
        """
        counts = sample_target_list.count_by_severity()
        assert counts["suggestion"] == 2
        assert counts["warning"] == 2
        assert counts["info"] == 1

    def test_count_by_file(self, sample_target_list: OptimizeTargetList, tmp_path: Path):
        """
        count_by_file() should return counts per file.
        """
        counts = sample_target_list.count_by_file()
        assert counts[tmp_path / "file1.py"] == 3
        assert counts[tmp_path / "file2.py"] == 2

    # === Sorting ===

    def test_sorted_by_severity(self, sample_target_list: OptimizeTargetList):
        """
        sorted_by_severity() should sort with warnings first by default.
        """
        sorted_list = sample_target_list.sorted_by_severity()
        severities = [t.severity for t in sorted_list]
        # Warnings should come before suggestions, which come before info
        warning_indices = [i for i, s in enumerate(severities) if s == "warning"]
        suggestion_indices = [i for i, s in enumerate(severities) if s == "suggestion"]
        info_indices = [i for i, s in enumerate(severities) if s == "info"]

        if warning_indices and suggestion_indices:
            assert max(warning_indices) < min(suggestion_indices)
        if suggestion_indices and info_indices:
            assert max(suggestion_indices) < min(info_indices)

    def test_sorted_by_location(self, sample_target_list: OptimizeTargetList):
        """
        sorted_by_location() should sort by file then line number.
        """
        sorted_list = sample_target_list.sorted_by_location()
        locations = [(str(t.file_path), t.line_number) for t in sorted_list]
        assert locations == sorted(locations)

    # === Output methods ===

    def test_to_list_of_dicts(self, sample_target_list: OptimizeTargetList):
        """
        to_list_of_dicts() should return serializable dictionaries.
        """
        dicts = sample_target_list.to_list_of_dicts()
        assert len(dicts) == 5
        for d in dicts:
            assert "type" in d
            assert "file" in d
            assert "line" in d
            assert "severity" in d

    def test_summary(self, sample_target_list: OptimizeTargetList):
        """
        summary() should return a human-readable summary.
        """
        summary = sample_target_list.summary()
        assert "5" in summary  # Total count
        assert "optimization" in summary.lower()

    def test_summary_empty_list(self, tmp_path: Path):
        """
        summary() should handle empty list.
        """
        rj = Rejig(str(tmp_path))
        empty_list = OptimizeTargetList(rj, [])
        summary = empty_list.summary()
        assert "No" in summary or "0" in summary


# =============================================================================
# Edge Cases
# =============================================================================

class TestOptimizeTargetListEdgeCases:
    """Edge case tests for OptimizeTargetList."""

    def test_empty_list(self, tmp_path: Path):
        """
        Empty OptimizeTargetList should work correctly.
        """
        rj = Rejig(str(tmp_path))
        empty_list = OptimizeTargetList(rj, [])

        assert len(empty_list) == 0
        assert list(empty_list) == []
        assert empty_list.count_by_type() == {}
        assert empty_list.group_by_file() == {}

    def test_filter_returns_empty_when_no_match(self, tmp_path: Path):
        """
        Filtering with no matches should return empty list.
        """
        file1 = tmp_path / "file1.py"
        file1.write_text("x = 1")

        finding = OptimizeFinding(
            type=OptimizeType.DUPLICATE_LITERAL,
            file_path=file1,
            line_number=1,
            severity="suggestion",
        )
        rj = Rejig(str(tmp_path))
        target_list = OptimizeTargetList(rj, [OptimizeTarget(rj, finding)])

        # Filter to type that doesn't exist
        filtered = target_list.by_type(OptimizeType.SLOW_LOOP_TO_MAP)
        assert len(filtered) == 0

    def test_chained_filtering(self, tmp_path: Path):
        """
        Filters can be chained.
        """
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file1.write_text("x = 1")
        file2.write_text("y = 2")

        findings = [
            OptimizeFinding(
                type=OptimizeType.SLOW_LOOP_TO_COMPREHENSION,
                file_path=file1,
                line_number=1,
                severity="warning",
            ),
            OptimizeFinding(
                type=OptimizeType.SLOW_LOOP_TO_COMPREHENSION,
                file_path=file2,
                line_number=1,
                severity="suggestion",
            ),
        ]
        rj = Rejig(str(tmp_path))
        targets = [OptimizeTarget(rj, f) for f in findings]
        target_list = OptimizeTargetList(rj, targets)

        # Chain filters
        result = (
            target_list
            .by_type(OptimizeType.SLOW_LOOP_TO_COMPREHENSION)
            .by_severity("warning")
            .in_file(file1)
        )
        assert len(result) == 1
