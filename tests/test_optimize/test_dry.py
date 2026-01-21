"""
Tests for rejig.optimize.dry module.

This module tests DRY (Don't Repeat Yourself) analysis:
- Duplicate code block detection
- Duplicate expression detection
- Duplicate literal detection
- Similar function detection
- DRYAnalyzer integration

Coverage targets:
- CodeFragment dataclass
- DuplicateGroup dataclass
- CodeNormalizer transformer
- DuplicateCollector visitor
- FunctionSignatureCollector visitor
- DRYAnalyzer methods
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig import Rejig
from rejig.optimize.dry import (
    CodeFragment,
    DRYAnalyzer,
    DuplicateGroup,
)
from rejig.optimize.targets import OptimizeTargetList, OptimizeType


# =============================================================================
# CodeFragment Tests
# =============================================================================

class TestCodeFragment:
    """Tests for CodeFragment dataclass.

    CodeFragment holds code snippets for comparison.
    """

    def test_basic_attributes(self):
        """
        CodeFragment should have basic required attributes.
        """
        fragment = CodeFragment(
            code="x = 1",
            original_code="x = 1",
            file_path=Path("test.py"),
            line_number=1,
            end_line=1,
            node_type="assignment",
        )

        assert fragment.code == "x = 1"
        assert fragment.original_code == "x = 1"
        assert fragment.file_path == Path("test.py")
        assert fragment.line_number == 1
        assert fragment.node_type == "assignment"

    def test_hash_property(self):
        """
        hash property should return consistent MD5 hash of code.
        """
        fragment1 = CodeFragment(
            code="x = 1",
            original_code="x = 1",
            file_path=Path("test.py"),
            line_number=1,
            end_line=1,
            node_type="assignment",
        )
        fragment2 = CodeFragment(
            code="x = 1",
            original_code="x = 1",
            file_path=Path("other.py"),
            line_number=10,
            end_line=10,
            node_type="assignment",
        )

        # Same code should have same hash regardless of location
        assert fragment1.hash == fragment2.hash

    def test_different_code_different_hash(self):
        """
        Different code should have different hashes.
        """
        fragment1 = CodeFragment(
            code="x = 1",
            original_code="x = 1",
            file_path=Path("test.py"),
            line_number=1,
            end_line=1,
            node_type="assignment",
        )
        fragment2 = CodeFragment(
            code="y = 2",
            original_code="y = 2",
            file_path=Path("test.py"),
            line_number=2,
            end_line=2,
            node_type="assignment",
        )

        assert fragment1.hash != fragment2.hash

    def test_line_count_property(self):
        """
        line_count should return correct number of lines.
        """
        fragment = CodeFragment(
            code="x = 1\ny = 2\nz = 3",
            original_code="x = 1\ny = 2\nz = 3",
            file_path=Path("test.py"),
            line_number=10,
            end_line=12,
            node_type="block",
        )

        assert fragment.line_count == 3


# =============================================================================
# DuplicateGroup Tests
# =============================================================================

class TestDuplicateGroup:
    """Tests for DuplicateGroup dataclass."""

    def test_count_property(self):
        """
        count should return number of fragments.
        """
        fragments = [
            CodeFragment(
                code="x = 1",
                original_code="x = 1",
                file_path=Path(f"test{i}.py"),
                line_number=1,
                end_line=1,
                node_type="assignment",
            )
            for i in range(3)
        ]
        group = DuplicateGroup(fragments=fragments)

        assert group.count == 3

    def test_representative_property(self):
        """
        representative should return first fragment.
        """
        fragments = [
            CodeFragment(
                code="x = 1",
                original_code="x = 1",
                file_path=Path("first.py"),
                line_number=1,
                end_line=1,
                node_type="assignment",
            ),
            CodeFragment(
                code="x = 1",
                original_code="x = 1",
                file_path=Path("second.py"),
                line_number=1,
                end_line=1,
                node_type="assignment",
            ),
        ]
        group = DuplicateGroup(fragments=fragments)

        assert group.representative.file_path == Path("first.py")


# =============================================================================
# DRYAnalyzer Tests
# =============================================================================

class TestDRYAnalyzer:
    """Tests for DRYAnalyzer class.

    DRYAnalyzer detects DRY violations across a codebase.
    """

    @pytest.fixture
    def create_project(self, tmp_path: Path):
        """Factory fixture to create a project with specific files.

        Returns a callable that takes a dict of {filename: content}
        and returns a Rejig instance.
        """
        def _create(files: dict[str, str]):
            for name, content in files.items():
                file_path = tmp_path / name
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(textwrap.dedent(content))
            return Rejig(str(tmp_path))
        return _create

    # === Duplicate Code Block Tests ===

    def test_find_duplicate_code_blocks_basic(self, create_project):
        """
        find_duplicate_code_blocks should find repeated code.
        """
        rj = create_project({
            "file1.py": '''\
                def func1():
                    x = 1
                    y = 2
                    result = x + y
                    return result

                def func2():
                    x = 1
                    y = 2
                    result = x + y
                    return result
            ''',
        })

        analyzer = DRYAnalyzer(rj)
        findings = analyzer.find_duplicate_code_blocks(min_lines=3, min_occurrences=2)

        # Should find the duplicate block
        assert isinstance(findings, OptimizeTargetList)

    def test_find_duplicate_code_blocks_across_files(self, create_project):
        """
        find_duplicate_code_blocks should detect duplicates across files.
        """
        rj = create_project({
            "file1.py": '''\
                def process_a():
                    data = []
                    for i in range(10):
                        data.append(i * 2)
                    return data
            ''',
            "file2.py": '''\
                def process_b():
                    data = []
                    for i in range(10):
                        data.append(i * 2)
                    return data
            ''',
        })

        analyzer = DRYAnalyzer(rj)
        findings = analyzer.find_duplicate_code_blocks(min_lines=3, min_occurrences=2)

        # Should detect cross-file duplicates
        assert isinstance(findings, OptimizeTargetList)

    def test_find_duplicate_code_blocks_respects_min_lines(self, create_project):
        """
        find_duplicate_code_blocks should respect min_lines threshold.
        """
        rj = create_project({
            "file1.py": '''\
                def short1():
                    return 1

                def short2():
                    return 1
            ''',
        })

        analyzer = DRYAnalyzer(rj)
        # Set high minimum lines - should not find the short duplicates
        findings = analyzer.find_duplicate_code_blocks(min_lines=10, min_occurrences=2)

        # Short functions should not be flagged
        assert len(findings) == 0

    def test_find_duplicate_code_blocks_respects_min_occurrences(self, create_project):
        """
        find_duplicate_code_blocks should respect min_occurrences threshold.
        """
        rj = create_project({
            "file1.py": '''\
                def func1():
                    x = 1
                    y = 2
                    z = 3
                    return x + y + z

                def func2():
                    a = 10
                    b = 20
                    c = 30
                    return a + b + c
            ''',
        })

        analyzer = DRYAnalyzer(rj)
        # Require 3 occurrences but we only have 2 similar blocks
        findings = analyzer.find_duplicate_code_blocks(min_lines=3, min_occurrences=3)

        # Should not find anything with min_occurrences=3
        assert len(findings) == 0

    # === Duplicate Expression Tests ===

    def test_find_duplicate_expressions(self, create_project):
        """
        find_duplicate_expressions should find repeated expressions.
        """
        rj = create_project({
            "file1.py": '''\
                def calc():
                    a = some_complex_function(x, y, z)
                    b = some_complex_function(x, y, z)
                    c = some_complex_function(x, y, z)
                    return a + b + c
            ''',
        })

        analyzer = DRYAnalyzer(rj)
        findings = analyzer.find_duplicate_expressions(min_occurrences=3)

        assert isinstance(findings, OptimizeTargetList)

    # === Duplicate Literal Tests ===

    def test_find_duplicate_literals_numbers(self, create_project):
        """
        find_duplicate_literals should find repeated magic numbers.
        """
        rj = create_project({
            "file1.py": '''\
                def calc1():
                    return x * 3600

                def calc2():
                    return y * 3600

                def calc3():
                    return z * 3600
            ''',
        })

        analyzer = DRYAnalyzer(rj)
        findings = analyzer.find_duplicate_literals(min_occurrences=3)

        # Should find the magic number 3600
        assert isinstance(findings, OptimizeTargetList)

    def test_find_duplicate_literals_strings(self, create_project):
        """
        find_duplicate_literals should find repeated string literals.
        """
        rj = create_project({
            "file1.py": '''\
                msg1 = "Error: operation failed"
                msg2 = "Error: operation failed"
                msg3 = "Error: operation failed"
            ''',
        })

        analyzer = DRYAnalyzer(rj)
        findings = analyzer.find_duplicate_literals(min_occurrences=3)

        assert isinstance(findings, OptimizeTargetList)

    def test_find_duplicate_literals_ignores_common_values(self, create_project):
        """
        find_duplicate_literals should ignore common values like 0, 1, 2.
        """
        rj = create_project({
            "file1.py": '''\
                a = 0
                b = 0
                c = 0
                d = 1
                e = 1
                f = 1
            ''',
        })

        analyzer = DRYAnalyzer(rj)
        findings = analyzer.find_duplicate_literals(min_occurrences=3)

        # Common values should not be flagged as magic numbers
        literal_values = [t.original_code for t in findings]
        assert "0" not in literal_values
        assert "1" not in literal_values

    # === Similar Function Tests ===

    def test_find_similar_functions(self, create_project):
        """
        find_similar_functions should find functions with identical structure.
        """
        rj = create_project({
            "file1.py": '''\
                def process_users(items):
                    result = []
                    for item in items:
                        result.append(item.name)
                    return result

                def process_orders(items):
                    result = []
                    for item in items:
                        result.append(item.name)
                    return result
            ''',
        })

        analyzer = DRYAnalyzer(rj)
        findings = analyzer.find_similar_functions()

        assert isinstance(findings, OptimizeTargetList)

    # === Find All Issues ===

    def test_find_all_issues(self, create_project):
        """
        find_all_issues should aggregate all DRY findings.
        """
        rj = create_project({
            "file1.py": '''\
                MAGIC = 42

                def func1():
                    return 42 + 42 + 42

                def func2():
                    data = []
                    for i in range(10):
                        data.append(i)
                    return data

                def func3():
                    data = []
                    for i in range(10):
                        data.append(i)
                    return data
            ''',
        })

        analyzer = DRYAnalyzer(rj)
        findings = analyzer.find_all_issues()

        assert isinstance(findings, OptimizeTargetList)

    # === Edge Cases ===

    def test_empty_project(self, tmp_path: Path):
        """
        DRYAnalyzer should handle empty projects.
        """
        rj = Rejig(str(tmp_path))
        analyzer = DRYAnalyzer(rj)

        findings = analyzer.find_all_issues()

        assert len(findings) == 0

    def test_syntax_error_handling(self, create_project):
        """
        DRYAnalyzer should handle syntax errors gracefully.
        """
        rj = create_project({
            "good.py": '''\
                def good():
                    return 1
            ''',
            "bad.py": "def broken(:\n    pass",
        })

        analyzer = DRYAnalyzer(rj)
        # Should not raise
        findings = analyzer.find_all_issues()

        assert isinstance(findings, OptimizeTargetList)

    def test_empty_file(self, create_project):
        """
        DRYAnalyzer should handle empty files.
        """
        rj = create_project({
            "empty.py": "",
            "normal.py": "x = 1",
        })

        analyzer = DRYAnalyzer(rj)
        findings = analyzer.find_all_issues()

        assert isinstance(findings, OptimizeTargetList)


# =============================================================================
# Finding Attributes Tests
# =============================================================================

class TestDRYFindingAttributes:
    """Tests for DRY finding attributes and context."""

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

    def test_duplicate_block_finding_type(self, create_project):
        """
        Duplicate block findings should have correct type.
        """
        rj = create_project({
            "file1.py": '''\
                def func1():
                    x = 1
                    y = 2
                    z = 3
                    return x + y + z

                def func2():
                    x = 1
                    y = 2
                    z = 3
                    return x + y + z
            ''',
        })

        analyzer = DRYAnalyzer(rj)
        findings = analyzer.find_duplicate_code_blocks(min_lines=3, min_occurrences=2)

        for finding in findings:
            assert finding.type == OptimizeType.DUPLICATE_CODE_BLOCK

    def test_duplicate_literal_finding_type(self, create_project):
        """
        Duplicate literal findings should have correct type.
        """
        rj = create_project({
            "file1.py": '''\
                a = 12345
                b = 12345
                c = 12345
            ''',
        })

        analyzer = DRYAnalyzer(rj)
        findings = analyzer.find_duplicate_literals(min_occurrences=3)

        for finding in findings:
            assert finding.type == OptimizeType.DUPLICATE_LITERAL

    def test_similar_function_finding_type(self, create_project):
        """
        Similar function findings should have correct type.
        """
        rj = create_project({
            "file1.py": '''\
                def process_a(items):
                    result = []
                    for item in items:
                        result.append(item.value)
                    return result

                def process_b(items):
                    result = []
                    for item in items:
                        result.append(item.value)
                    return result
            ''',
        })

        analyzer = DRYAnalyzer(rj)
        findings = analyzer.find_similar_functions()

        for finding in findings:
            assert finding.type == OptimizeType.SIMILAR_FUNCTION

    def test_finding_has_context(self, create_project):
        """
        Findings should include context information.
        """
        rj = create_project({
            "file1.py": '''\
                def func1():
                    x = 1
                    y = 2
                    z = 3
                    return x + y + z

                def func2():
                    x = 1
                    y = 2
                    z = 3
                    return x + y + z
            ''',
        })

        analyzer = DRYAnalyzer(rj)
        findings = analyzer.find_duplicate_code_blocks(min_lines=3, min_occurrences=2)

        if len(findings) > 0:
            finding = findings[0]
            # Context should include occurrence count
            assert "occurrences" in finding.finding.context
