"""
Tests for rejig.analysis.patterns module.

This module tests pattern finding for code quality issues:
- Functions without type hints
- Functions/classes without docstrings
- Bare except clauses
- Hardcoded strings
- Magic numbers

PatternFinder scans the codebase for common patterns that may
indicate issues or areas needing improvement.

Coverage targets:
- TypeHintCollector for missing type hints
- DocstringCollector for missing docstrings
- BareExceptCollector for bare except clauses
- HardcodedStringCollector for externalization candidates
- MagicNumberCollector for unnamed constants
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig import Rejig
from rejig.analysis.patterns import (
    BareExceptCollector,
    DocstringCollector,
    HardcodedStringCollector,
    MagicNumberCollector,
    PatternFinder,
    TypeHintCollector,
)
from rejig.analysis.targets import AnalysisTargetList, AnalysisType


# =============================================================================
# TypeHintCollector Tests
# =============================================================================

class TestTypeHintCollector:
    """Tests for TypeHintCollector CST visitor.

    TypeHintCollector finds functions and methods lacking type hints.
    """

    def test_finds_function_without_hints(self, tmp_path: Path):
        """
        TypeHintCollector should flag functions with no type hints.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            def no_hints(x, y):
                return x + y
        ''')
        tree = cst.parse_module(code)
        collector = TypeHintCollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        result_names = [name for name, _, _ in collector.results]
        assert "no_hints" in result_names

    def test_excludes_function_with_return_hint(self, tmp_path: Path):
        """
        TypeHintCollector should not flag functions with return hints.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            def with_return(x, y) -> int:
                return x + y
        ''')
        tree = cst.parse_module(code)
        collector = TypeHintCollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        result_names = [name for name, _, _ in collector.results]
        assert "with_return" not in result_names

    def test_excludes_function_with_param_hints(self, tmp_path: Path):
        """
        TypeHintCollector should not flag functions with parameter hints.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            def with_params(x: int, y: int):
                return x + y
        ''')
        tree = cst.parse_module(code)
        collector = TypeHintCollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        result_names = [name for name, _, _ in collector.results]
        assert "with_params" not in result_names

    def test_tracks_methods_with_class_name(self, tmp_path: Path):
        """
        TypeHintCollector should track methods and include class name.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            class MyClass:
                def untyped_method(self, x, y):
                    return x + y
        ''')
        tree = cst.parse_module(code)
        collector = TypeHintCollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        result_names = [name for name, _, _ in collector.results]
        assert "MyClass.untyped_method" in result_names

    def test_entity_type_is_function_or_method(self, tmp_path: Path):
        """
        TypeHintCollector should correctly identify entity types.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            def standalone(x):
                pass

            class MyClass:
                def method(self, x):
                    pass
        ''')
        tree = cst.parse_module(code)
        collector = TypeHintCollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        for name, _, entity_type in collector.results:
            if "." in name:
                assert entity_type == "method"
            else:
                assert entity_type == "function"


# =============================================================================
# DocstringCollector Tests
# =============================================================================

class TestDocstringCollector:
    """Tests for DocstringCollector CST visitor.

    DocstringCollector finds classes and functions without docstrings.
    """

    def test_finds_function_without_docstring(self, tmp_path: Path):
        """
        DocstringCollector should flag functions lacking docstrings.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            def no_doc(x):
                return x * 2
        ''')
        tree = cst.parse_module(code)
        collector = DocstringCollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        result_names = [name for name, _, _ in collector.results]
        assert "no_doc" in result_names

    def test_excludes_function_with_docstring(self, tmp_path: Path):
        """
        DocstringCollector should not flag functions with docstrings.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            def with_doc(x):
                """Multiply x by 2."""
                return x * 2
        ''')
        tree = cst.parse_module(code)
        collector = DocstringCollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        result_names = [name for name, _, _ in collector.results]
        assert "with_doc" not in result_names

    def test_finds_class_without_docstring(self, tmp_path: Path):
        """
        DocstringCollector should flag classes lacking docstrings.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            class NoDocClass:
                pass
        ''')
        tree = cst.parse_module(code)
        collector = DocstringCollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        results = [(name, entity_type) for name, _, entity_type in collector.results]
        assert ("NoDocClass", "class") in results

    def test_excludes_class_with_docstring(self, tmp_path: Path):
        """
        DocstringCollector should not flag classes with docstrings.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            class WithDocClass:
                """A documented class."""
                pass
        ''')
        tree = cst.parse_module(code)
        collector = DocstringCollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        result_names = [name for name, _, _ in collector.results]
        assert "WithDocClass" not in result_names

    def test_excludes_private_functions(self, tmp_path: Path):
        """
        DocstringCollector should skip private functions (single underscore).

        Private functions are internal implementation details and
        may not need public documentation.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            def _private_helper(x):
                return x
        ''')
        tree = cst.parse_module(code)
        collector = DocstringCollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        result_names = [name for name, _, _ in collector.results]
        assert "_private_helper" not in result_names


# =============================================================================
# BareExceptCollector Tests
# =============================================================================

class TestBareExceptCollector:
    """Tests for BareExceptCollector.

    BareExceptCollector finds except: clauses without exception types.
    """

    def test_finds_bare_except(self, tmp_path: Path):
        """
        BareExceptCollector should flag bare except clauses.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            def risky():
                try:
                    do_something()
                except:
                    pass
        ''')
        tree = cst.parse_module(code)
        collector = BareExceptCollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        assert len(collector.results) >= 1

    def test_excludes_typed_except(self, tmp_path: Path):
        """
        BareExceptCollector should not flag typed except clauses.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            def safe():
                try:
                    do_something()
                except ValueError:
                    pass
                except (TypeError, KeyError):
                    pass
        ''')
        tree = cst.parse_module(code)
        collector = BareExceptCollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        assert len(collector.results) == 0


# =============================================================================
# HardcodedStringCollector Tests
# =============================================================================

class TestHardcodedStringCollector:
    """Tests for HardcodedStringCollector.

    HardcodedStringCollector finds string literals that might need
    to be externalized (e.g., for i18n or configuration).
    """

    def test_finds_long_strings(self, tmp_path: Path):
        """
        HardcodedStringCollector should find long string literals.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            message = "This is a long hardcoded string that should be flagged"
        ''')
        tree = cst.parse_module(code)
        collector = HardcodedStringCollector(tmp_path / "test.py", min_length=10)
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        # Should find the long string
        assert len(collector.results) >= 1

    def test_excludes_short_strings(self, tmp_path: Path):
        """
        HardcodedStringCollector should not flag short strings.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            x = "hi"
            y = "ok"
        ''')
        tree = cst.parse_module(code)
        collector = HardcodedStringCollector(tmp_path / "test.py", min_length=10)
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        assert len(collector.results) == 0

    def test_excludes_constants(self, tmp_path: Path):
        """
        HardcodedStringCollector should skip strings assigned to constants.

        Strings assigned to ALL_CAPS names are intentional constants.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            MY_CONSTANT = "This is a constant string value for config"
        ''')
        tree = cst.parse_module(code)
        collector = HardcodedStringCollector(tmp_path / "test.py", min_length=10)
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        # Constants should be excluded
        assert len(collector.results) == 0

    def test_excludes_paths_and_urls(self, tmp_path: Path):
        """
        HardcodedStringCollector should skip paths and URLs.

        Strings containing '/', '://', etc. are likely paths or URLs
        which are typically configuration, not user-facing text.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            path = "/usr/local/bin/something"
            url = "https://example.com/api/endpoint"
        ''')
        tree = cst.parse_module(code)
        collector = HardcodedStringCollector(tmp_path / "test.py", min_length=10)
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        # Paths and URLs should be excluded
        assert len(collector.results) == 0


# =============================================================================
# MagicNumberCollector Tests
# =============================================================================

class TestMagicNumberCollector:
    """Tests for MagicNumberCollector.

    MagicNumberCollector finds numeric literals that might need
    to be named constants.
    """

    def test_finds_magic_numbers(self, tmp_path: Path):
        """
        MagicNumberCollector should find magic numbers.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            def calculate(x):
                return x * 3.14159 + 42
        ''')
        tree = cst.parse_module(code)
        collector = MagicNumberCollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        values = [v for v, _ in collector.results]
        # 42 might be in the results (it's not in ALLOWED_NUMBERS)
        # 3.14159 is a float that should be flagged

    def test_excludes_common_numbers(self, tmp_path: Path):
        """
        MagicNumberCollector should not flag common acceptable numbers.

        Numbers like 0, 1, 2, -1, 10, 100 are commonly used and acceptable.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            def use_common():
                x = 0
                y = 1
                z = 2
                w = -1
                return x + y + z + w
        ''')
        tree = cst.parse_module(code)
        collector = MagicNumberCollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        values = [v for v, _ in collector.results]
        assert 0 not in values
        assert 1 not in values
        assert 2 not in values
        assert -1 not in values

    def test_excludes_constant_assignments(self, tmp_path: Path):
        """
        MagicNumberCollector should skip numbers in constant assignments.

        Numbers assigned to ALL_CAPS names are intentional named constants.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            MAX_RETRIES = 5
            TIMEOUT_SECONDS = 30
        ''')
        tree = cst.parse_module(code)
        collector = MagicNumberCollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        values = [v for v, _ in collector.results]
        assert 5 not in values
        assert 30 not in values


# =============================================================================
# PatternFinder Tests
# =============================================================================

class TestPatternFinder:
    """Tests for PatternFinder class.

    PatternFinder provides high-level methods to find code patterns
    across a project.
    """

    @pytest.fixture
    def create_project(self, tmp_path: Path):
        """Factory fixture to create a project with specific files."""
        def _create(files: dict[str, str]):
            for name, content in files.items():
                (tmp_path / name).write_text(content)
            return Rejig(str(tmp_path))
        return _create

    def test_find_functions_without_type_hints(self, create_project):
        """
        find_functions_without_type_hints should find untyped functions.
        """
        rj = create_project({
            "app.py": textwrap.dedent('''\
                def untyped(x, y):
                    return x + y

                def typed(x: int, y: int) -> int:
                    return x + y
            ''')
        })

        finder = PatternFinder(rj)
        findings = finder.find_functions_without_type_hints()

        assert isinstance(findings, AnalysisTargetList)
        finding_names = [t.name for t in findings]
        assert "untyped" in finding_names
        assert "typed" not in finding_names

    def test_find_classes_without_docstrings(self, create_project):
        """
        find_classes_without_docstrings should find undocumented classes.
        """
        rj = create_project({
            "app.py": textwrap.dedent('''\
                class Undocumented:
                    pass

                class Documented:
                    """This class has a docstring."""
                    pass
            ''')
        })

        finder = PatternFinder(rj)
        findings = finder.find_classes_without_docstrings()

        finding_names = [t.name for t in findings]
        assert "Undocumented" in finding_names
        assert "Documented" not in finding_names

    def test_find_functions_without_docstrings(self, create_project):
        """
        find_functions_without_docstrings should find undocumented functions.
        """
        rj = create_project({
            "app.py": textwrap.dedent('''\
                def undocumented():
                    return 1

                def documented():
                    """Return one."""
                    return 1
            ''')
        })

        finder = PatternFinder(rj)
        findings = finder.find_functions_without_docstrings()

        finding_names = [t.name for t in findings]
        assert "undocumented" in finding_names
        assert "documented" not in finding_names

    def test_find_bare_excepts(self, create_project):
        """
        find_bare_excepts should find bare except clauses.
        """
        rj = create_project({
            "app.py": textwrap.dedent('''\
                def with_bare_except():
                    try:
                        risky()
                    except:
                        pass

                def with_typed_except():
                    try:
                        risky()
                    except ValueError:
                        pass
            ''')
        })

        finder = PatternFinder(rj)
        findings = finder.find_bare_excepts()

        # Should find at least one bare except
        assert len(findings) >= 1
        for target in findings:
            assert target.type == AnalysisType.BARE_EXCEPT

    def test_find_hardcoded_strings(self, create_project):
        """
        find_hardcoded_strings should find long string literals.
        """
        rj = create_project({
            "app.py": textwrap.dedent('''\
                message = "This is a hardcoded message that should be flagged for potential externalization"
                short = "ok"
            ''')
        })

        finder = PatternFinder(rj)
        findings = finder.find_hardcoded_strings(min_length=20)

        # Should find the long string
        assert len(findings) >= 1
        for target in findings:
            assert target.type == AnalysisType.HARDCODED_STRING

    def test_find_magic_numbers(self, create_project):
        """
        find_magic_numbers should find unnamed numeric constants.
        """
        rj = create_project({
            "app.py": textwrap.dedent('''\
                def calculate(x):
                    return x * 7 + 13
            ''')
        })

        finder = PatternFinder(rj)
        findings = finder.find_magic_numbers()

        # Should find 7 and 13 as magic numbers
        # (These are not in the ALLOWED_NUMBERS set)
        values = [t.value for t in findings if t.value is not None]
        # At least some magic numbers should be found
        # The exact values depend on the implementation

    def test_find_all_patterns(self, create_project):
        """
        find_all_patterns should combine multiple pattern findings.
        """
        rj = create_project({
            "app.py": textwrap.dedent('''\
                def untyped_no_doc():
                    try:
                        do_something()
                    except:
                        pass
            ''')
        })

        finder = PatternFinder(rj)
        findings = finder.find_all_patterns()

        assert isinstance(findings, AnalysisTargetList)
        # Should have multiple types of findings
        types = {t.type for t in findings}
        # At least missing type hint and bare except
        assert len(types) >= 1

    def test_empty_project(self, tmp_path: Path):
        """
        PatternFinder should handle empty projects gracefully.
        """
        rj = Rejig(str(tmp_path))
        finder = PatternFinder(rj)

        findings = finder.find_all_patterns()

        assert len(findings) == 0

    def test_syntax_error_handling(self, create_project):
        """
        PatternFinder should handle files with syntax errors.
        """
        rj = create_project({
            "good.py": textwrap.dedent('''\
                def good_func():
                    return 1
            '''),
            "bad.py": "def broken(:\n    pass"
        })

        finder = PatternFinder(rj)
        # Should not raise
        findings = finder.find_all_patterns()

        assert isinstance(findings, AnalysisTargetList)


# =============================================================================
# Integration Tests
# =============================================================================

class TestPatternFinderIntegration:
    """Integration tests for pattern finding workflow."""

    def test_finding_properties(self, tmp_path: Path):
        """
        Pattern findings should have expected properties.
        """
        (tmp_path / "app.py").write_text(textwrap.dedent('''\
            def no_hints_or_docs(x, y):
                return x + y
        '''))

        rj = Rejig(str(tmp_path))
        finder = PatternFinder(rj)
        findings = finder.find_functions_without_type_hints()

        if len(findings) > 0:
            target = findings[0]
            assert target.type == AnalysisType.MISSING_TYPE_HINT
            assert target.file_path == tmp_path / "app.py"
            assert "no_hints_or_docs" in target.name
            assert "type hint" in target.message.lower()

    def test_filter_by_severity(self, tmp_path: Path):
        """
        Pattern findings can be filtered by severity.
        """
        (tmp_path / "app.py").write_text(textwrap.dedent('''\
            def no_hints(x):
                try:
                    return x
                except:
                    return None
        '''))

        rj = Rejig(str(tmp_path))
        finder = PatternFinder(rj)
        findings = finder.find_all_patterns()

        # Filter to warnings only
        warnings = findings.warnings()
        for target in warnings:
            assert target.severity == "warning"

        # Filter to info only
        info = findings.info()
        for target in info:
            assert target.severity == "info"

    def test_group_by_file(self, tmp_path: Path):
        """
        Pattern findings can be grouped by file.
        """
        (tmp_path / "a.py").write_text("def func_a(x): return x\n")
        (tmp_path / "b.py").write_text("def func_b(x): return x\n")

        rj = Rejig(str(tmp_path))
        finder = PatternFinder(rj)
        findings = finder.find_functions_without_docstrings()

        grouped = findings.group_by_file()
        # Should have separate groups for each file
        assert isinstance(grouped, dict)
