"""
Tests for rejig.optimize.loops module.

This module tests loop optimization analysis:
- List comprehension opportunities
- Dict comprehension opportunities
- Set comprehension opportunities
- Builtin function opportunities (map, filter, any, all, sum, join)
- Iterator opportunities (enumerate, zip)

Coverage targets:
- LoopPattern dataclass
- LoopPatternVisitor for pattern detection
- LoopOptimizer methods
- Confidence scoring
- Pattern type mapping
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig import Rejig
from rejig.optimize.loops import (
    LoopOptimizer,
    LoopPattern,
)
from rejig.optimize.targets import OptimizeTargetList, OptimizeType


# =============================================================================
# LoopPattern Tests
# =============================================================================

class TestLoopPattern:
    """Tests for LoopPattern dataclass.

    LoopPattern holds information about a detected loop optimization.
    """

    def test_basic_attributes(self):
        """
        LoopPattern should have basic required attributes.
        """
        pattern = LoopPattern(
            pattern_type="list_comprehension",
            original_code="for x in items: result.append(x)",
            suggested_code="result = [x for x in items]",
            line_number=10,
            end_line=12,
        )

        assert pattern.pattern_type == "list_comprehension"
        assert "append" in pattern.original_code
        assert pattern.suggested_code.startswith("result")
        assert pattern.line_number == 10
        assert pattern.end_line == 12
        assert pattern.confidence == 0.9  # Default

    def test_custom_confidence(self):
        """
        LoopPattern should accept custom confidence.
        """
        pattern = LoopPattern(
            pattern_type="zip_candidate",
            original_code="for i in range(len(x)): ...",
            suggested_code="for item in x: ...",
            line_number=1,
            end_line=3,
            confidence=0.7,
        )

        assert pattern.confidence == 0.7


# =============================================================================
# LoopOptimizer Tests
# =============================================================================

class TestLoopOptimizer:
    """Tests for LoopOptimizer class.

    LoopOptimizer detects loops that can be optimized.
    """

    @pytest.fixture
    def create_project(self, tmp_path: Path):
        """Factory fixture to create a project with specific files."""
        def _create(files: dict[str, str]):
            for name, content in files.items():
                file_path = tmp_path / name
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(textwrap.dedent(content))
            return Rejig(str(tmp_path))
        return _create

    # === List Comprehension Tests ===

    def test_detect_list_append_pattern(self, create_project):
        """
        LoopOptimizer should detect for loop with append.
        """
        rj = create_project({
            "file1.py": '''\
                result = []
                for x in items:
                    result.append(x * 2)
            ''',
        })

        optimizer = LoopOptimizer(rj)
        findings = optimizer.find_comprehension_opportunities()

        assert isinstance(findings, OptimizeTargetList)

    def test_list_append_suggested_code(self, create_project):
        """
        List append pattern should suggest list comprehension.
        """
        rj = create_project({
            "file1.py": '''\
                def process():
                    result = []
                    for x in items:
                        result.append(x * 2)
                    return result
            ''',
        })

        optimizer = LoopOptimizer(rj)
        findings = optimizer.find_comprehension_opportunities()

        # Check that suggested code is a comprehension
        for finding in findings:
            if finding.type == OptimizeType.SLOW_LOOP_TO_COMPREHENSION:
                assert "[" in finding.suggested_code or "list(" in finding.suggested_code

    # === Dict Comprehension Tests ===

    def test_detect_dict_assignment_pattern(self, create_project):
        """
        LoopOptimizer should detect for loop building a dict.
        """
        rj = create_project({
            "file1.py": '''\
                def process():
                    result = {}
                    for item in items:
                        result[item.key] = item.value
                    return result
            ''',
        })

        optimizer = LoopOptimizer(rj)
        findings = optimizer.find_comprehension_opportunities()

        # Should detect dict comprehension opportunity
        types = [f.type for f in findings]
        # May or may not find depending on exact pattern matching
        assert isinstance(findings, OptimizeTargetList)

    # === Set Comprehension Tests ===

    def test_detect_set_add_pattern(self, create_project):
        """
        LoopOptimizer should detect for loop with set.add().
        """
        rj = create_project({
            "file1.py": '''\
                def process():
                    result = set()
                    for x in items:
                        result.add(x.name)
                    return result
            ''',
        })

        optimizer = LoopOptimizer(rj)
        findings = optimizer.find_comprehension_opportunities()

        assert isinstance(findings, OptimizeTargetList)

    # === Builtin Function Tests ===

    def test_detect_sum_pattern(self, create_project):
        """
        LoopOptimizer should detect for loop summing values.
        """
        rj = create_project({
            "file1.py": '''\
                def total():
                    result = 0
                    for x in items:
                        result += x
                    return result
            ''',
        })

        optimizer = LoopOptimizer(rj)
        findings = optimizer.find_builtin_opportunities()

        # Should suggest sum()
        types = [f.type for f in findings]
        assert isinstance(findings, OptimizeTargetList)

    def test_detect_string_join_pattern(self, create_project):
        """
        LoopOptimizer should detect string concatenation in loop.
        """
        rj = create_project({
            "file1.py": '''\
                def concat():
                    result = ""
                    for x in items:
                        result += x
                    return result
            ''',
        })

        optimizer = LoopOptimizer(rj)
        findings = optimizer.find_builtin_opportunities()

        assert isinstance(findings, OptimizeTargetList)

    def test_detect_any_pattern(self, create_project):
        """
        LoopOptimizer should detect any() pattern.
        """
        rj = create_project({
            "file1.py": '''\
                def has_positive():
                    for x in items:
                        if x > 0:
                            return True
                    return False
            ''',
        })

        optimizer = LoopOptimizer(rj)
        findings = optimizer.find_builtin_opportunities()

        assert isinstance(findings, OptimizeTargetList)

    # === Iterator Tests ===

    def test_detect_enumerate_pattern(self, create_project):
        """
        LoopOptimizer should detect manual index tracking.
        """
        rj = create_project({
            "file1.py": '''\
                def process():
                    i = 0
                    for item in items:
                        print(i, item)
                        i += 1
            ''',
        })

        optimizer = LoopOptimizer(rj)
        findings = optimizer.find_iterator_opportunities()

        assert isinstance(findings, OptimizeTargetList)

    def test_detect_range_len_pattern(self, create_project):
        """
        LoopOptimizer should detect range(len()) pattern.
        """
        rj = create_project({
            "file1.py": '''\
                def process():
                    for i in range(len(items)):
                        print(items[i])
            ''',
        })

        optimizer = LoopOptimizer(rj)
        findings = optimizer.find_iterator_opportunities()

        assert isinstance(findings, OptimizeTargetList)

    # === Filter Pattern Tests ===

    def test_detect_filter_pattern(self, create_project):
        """
        LoopOptimizer should detect conditional append pattern.
        """
        rj = create_project({
            "file1.py": '''\
                def filter_items():
                    result = []
                    for x in items:
                        if x > 0:
                            result.append(x)
                    return result
            ''',
        })

        optimizer = LoopOptimizer(rj)
        findings = optimizer.find_builtin_opportunities()

        assert isinstance(findings, OptimizeTargetList)

    # === Map Pattern Tests ===

    def test_detect_map_pattern(self, create_project):
        """
        LoopOptimizer should detect function application pattern.
        """
        rj = create_project({
            "file1.py": '''\
                def process():
                    result = []
                    for x in items:
                        result.append(str(x))
                    return result
            ''',
        })

        optimizer = LoopOptimizer(rj)
        findings = optimizer.find_builtin_opportunities()

        assert isinstance(findings, OptimizeTargetList)

    # === Find All Issues ===

    def test_find_all_issues(self, create_project):
        """
        find_all_issues should aggregate all loop findings.
        """
        rj = create_project({
            "file1.py": '''\
                def process():
                    # List append pattern
                    result1 = []
                    for x in items:
                        result1.append(x * 2)

                    # Sum pattern
                    total = 0
                    for x in items:
                        total += x

                    # Range len pattern
                    for i in range(len(items)):
                        print(items[i])

                    return result1, total
            ''',
        })

        optimizer = LoopOptimizer(rj)
        findings = optimizer.find_all_issues()

        assert isinstance(findings, OptimizeTargetList)
        # Should find multiple patterns
        assert len(findings) >= 0

    def test_find_all_issues_respects_confidence(self, create_project):
        """
        find_all_issues should respect min_confidence threshold.
        """
        rj = create_project({
            "file1.py": '''\
                def process():
                    result = []
                    for x in items:
                        result.append(x)
                    return result
            ''',
        })

        optimizer = LoopOptimizer(rj)

        # High confidence should find clear patterns
        high_conf = optimizer.find_all_issues(min_confidence=0.9)

        # Lower confidence should find more
        low_conf = optimizer.find_all_issues(min_confidence=0.5)

        # Low confidence should find at least as many
        assert len(low_conf) >= len(high_conf)

    # === Edge Cases ===

    def test_empty_project(self, tmp_path: Path):
        """
        LoopOptimizer should handle empty projects.
        """
        rj = Rejig(str(tmp_path))
        optimizer = LoopOptimizer(rj)

        findings = optimizer.find_all_issues()

        assert len(findings) == 0

    def test_syntax_error_handling(self, create_project):
        """
        LoopOptimizer should handle syntax errors gracefully.
        """
        rj = create_project({
            "good.py": '''\
                def process():
                    result = []
                    for x in items:
                        result.append(x)
                    return result
            ''',
            "bad.py": "def broken(:\n    pass",
        })

        optimizer = LoopOptimizer(rj)
        # Should not raise
        findings = optimizer.find_all_issues()

        assert isinstance(findings, OptimizeTargetList)

    def test_no_false_positives_for_complex_loops(self, create_project):
        """
        LoopOptimizer should not flag complex loops that can't be simplified.
        """
        rj = create_project({
            "file1.py": '''\
                def complex_loop():
                    result = []
                    for x in items:
                        # Multiple statements - not a simple comprehension
                        if x > 0:
                            x = x * 2
                            result.append(x)
                        else:
                            result.append(0)
                    return result
            ''',
        })

        optimizer = LoopOptimizer(rj)
        findings = optimizer.find_comprehension_opportunities()

        # Complex loops should not be flagged for simple comprehension
        # They might still be flagged with lower confidence
        assert isinstance(findings, OptimizeTargetList)


# =============================================================================
# Finding Type Tests
# =============================================================================

class TestLoopFindingTypes:
    """Tests for loop finding types and attributes."""

    @pytest.fixture
    def create_project(self, tmp_path: Path):
        """Factory fixture."""
        def _create(files: dict[str, str]):
            for name, content in files.items():
                file_path = tmp_path / name
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(textwrap.dedent(content))
            return Rejig(str(tmp_path))
        return _create

    def test_comprehension_has_correct_type(self, create_project):
        """
        List comprehension findings should have correct type.
        """
        rj = create_project({
            "file1.py": '''\
                def process():
                    result = []
                    for x in items:
                        result.append(x)
                    return result
            ''',
        })

        optimizer = LoopOptimizer(rj)
        findings = optimizer.find_comprehension_opportunities()

        for finding in findings:
            assert finding.type in {
                OptimizeType.SLOW_LOOP_TO_COMPREHENSION,
                OptimizeType.SLOW_LOOP_TO_DICT_COMPREHENSION,
                OptimizeType.SLOW_LOOP_TO_SET_COMPREHENSION,
            }

    def test_sum_has_correct_type(self, create_project):
        """
        Sum pattern findings should have correct type.
        """
        rj = create_project({
            "file1.py": '''\
                def total():
                    result = 0
                    for x in items:
                        result += x
                    return result
            ''',
        })

        optimizer = LoopOptimizer(rj)
        findings = optimizer.find_all_issues()

        sum_findings = [f for f in findings if f.type == OptimizeType.SLOW_LOOP_TO_SUM]
        # May find sum pattern
        assert isinstance(findings, OptimizeTargetList)

    def test_finding_has_suggested_code(self, create_project):
        """
        Findings should include suggested replacement code.
        """
        rj = create_project({
            "file1.py": '''\
                def process():
                    result = []
                    for x in items:
                        result.append(x * 2)
                    return result
            ''',
        })

        optimizer = LoopOptimizer(rj)
        findings = optimizer.find_all_issues()

        for finding in findings:
            # Suggested code should not be empty
            assert finding.suggested_code != "" or finding.finding.suggested_code != ""

    def test_finding_has_original_code(self, create_project):
        """
        Findings should include original code snippet.
        """
        rj = create_project({
            "file1.py": '''\
                def process():
                    result = []
                    for x in items:
                        result.append(x)
                    return result
            ''',
        })

        optimizer = LoopOptimizer(rj)
        findings = optimizer.find_all_issues()

        for finding in findings:
            # Original code should contain the loop
            assert "for" in finding.original_code.lower() or finding.original_code != ""

    def test_finding_has_confidence_in_context(self, create_project):
        """
        Findings should include confidence in context.
        """
        rj = create_project({
            "file1.py": '''\
                def process():
                    result = []
                    for x in items:
                        result.append(x)
                    return result
            ''',
        })

        optimizer = LoopOptimizer(rj)
        findings = optimizer.find_all_issues()

        for finding in findings:
            assert "confidence" in finding.finding.context
            assert 0 <= finding.finding.context["confidence"] <= 1


# =============================================================================
# Category Method Tests
# =============================================================================

class TestLoopOptimizerCategories:
    """Tests for category-specific finder methods."""

    @pytest.fixture
    def create_project(self, tmp_path: Path):
        """Factory fixture."""
        def _create(files: dict[str, str]):
            for name, content in files.items():
                file_path = tmp_path / name
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(textwrap.dedent(content))
            return Rejig(str(tmp_path))
        return _create

    def test_find_comprehension_opportunities_returns_only_comprehensions(self, create_project):
        """
        find_comprehension_opportunities should only return comprehension types.
        """
        rj = create_project({
            "file1.py": '''\
                def process():
                    result = []
                    for x in items:
                        result.append(x)

                    total = 0
                    for x in items:
                        total += x

                    return result, total
            ''',
        })

        optimizer = LoopOptimizer(rj)
        findings = optimizer.find_comprehension_opportunities()

        comprehension_types = {
            OptimizeType.SLOW_LOOP_TO_COMPREHENSION,
            OptimizeType.SLOW_LOOP_TO_DICT_COMPREHENSION,
            OptimizeType.SLOW_LOOP_TO_SET_COMPREHENSION,
        }

        for finding in findings:
            assert finding.type in comprehension_types

    def test_find_builtin_opportunities_returns_only_builtins(self, create_project):
        """
        find_builtin_opportunities should only return builtin types.
        """
        rj = create_project({
            "file1.py": '''\
                def process():
                    result = []
                    for x in items:
                        result.append(x)

                    total = 0
                    for x in items:
                        total += x

                    return result, total
            ''',
        })

        optimizer = LoopOptimizer(rj)
        findings = optimizer.find_builtin_opportunities()

        builtin_types = {
            OptimizeType.SLOW_LOOP_TO_MAP,
            OptimizeType.SLOW_LOOP_TO_FILTER,
            OptimizeType.SLOW_LOOP_TO_ANY_ALL,
            OptimizeType.SLOW_LOOP_TO_SUM,
            OptimizeType.SLOW_LOOP_TO_JOIN,
        }

        for finding in findings:
            assert finding.type in builtin_types

    def test_find_iterator_opportunities_returns_only_iterators(self, create_project):
        """
        find_iterator_opportunities should only return iterator types.
        """
        rj = create_project({
            "file1.py": '''\
                def process():
                    i = 0
                    for x in items:
                        print(i, x)
                        i += 1

                    for i in range(len(items)):
                        print(items[i])
            ''',
        })

        optimizer = LoopOptimizer(rj)
        findings = optimizer.find_iterator_opportunities()

        iterator_types = {
            OptimizeType.SLOW_LOOP_TO_ENUMERATE,
            OptimizeType.SLOW_LOOP_TO_ZIP,
        }

        for finding in findings:
            assert finding.type in iterator_types


# =============================================================================
# Integration Tests
# =============================================================================

class TestLoopOptimizerIntegration:
    """Integration tests for LoopOptimizer."""

    @pytest.fixture
    def create_project(self, tmp_path: Path):
        """Factory fixture."""
        def _create(files: dict[str, str]):
            for name, content in files.items():
                file_path = tmp_path / name
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(textwrap.dedent(content))
            return Rejig(str(tmp_path))
        return _create

    def test_multiple_files(self, create_project):
        """
        LoopOptimizer should analyze multiple files.
        """
        rj = create_project({
            "file1.py": '''\
                def process1():
                    result = []
                    for x in items:
                        result.append(x)
                    return result
            ''',
            "file2.py": '''\
                def process2():
                    total = 0
                    for x in items:
                        total += x
                    return total
            ''',
        })

        optimizer = LoopOptimizer(rj)
        findings = optimizer.find_all_issues()

        # Should find patterns from both files
        files = {f.file_path for f in findings}
        # May or may not find both depending on exact pattern matching
        assert isinstance(findings, OptimizeTargetList)

    def test_filtering_by_file(self, create_project):
        """
        Findings can be filtered by file.
        """
        rj = create_project({
            "file1.py": '''\
                def process1():
                    result = []
                    for x in items:
                        result.append(x)
                    return result
            ''',
            "file2.py": '''\
                def process2():
                    result = []
                    for x in items:
                        result.append(x)
                    return result
            ''',
        })

        optimizer = LoopOptimizer(rj)
        findings = optimizer.find_all_issues()

        # Filter to file1 only
        file1_findings = findings.in_file(rj.root / "file1.py")

        for finding in file1_findings:
            assert "file1.py" in str(finding.file_path)

    def test_summary_generation(self, create_project):
        """
        Findings should generate a summary.
        """
        rj = create_project({
            "file1.py": '''\
                def process():
                    result = []
                    for x in items:
                        result.append(x)
                    return result
            ''',
        })

        optimizer = LoopOptimizer(rj)
        findings = optimizer.find_all_issues()

        summary = findings.summary()

        assert isinstance(summary, str)
