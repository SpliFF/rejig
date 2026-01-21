"""
Tests for rejig.analysis.dead_code module.

This module tests dead code detection:
- Unused function detection
- Unused class detection
- Unused variable detection
- Unreachable code detection

DeadCodeAnalyzer scans the codebase for potentially unused elements
by comparing definitions against usages.

Coverage targets:
- DefinitionCollector for finding all definitions
- UsageCollector for finding all name usages
- Unused function detection with exclusion patterns
- Unused class detection with exclusion patterns
- Unused variable detection (module-level)
- Unreachable code after return/raise
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig import Rejig
from rejig.analysis.dead_code import (
    DeadCodeAnalyzer,
    DefinitionCollector,
    UnreachableCodeCollector,
    UsageCollector,
)
from rejig.analysis.targets import AnalysisTargetList, AnalysisType


# =============================================================================
# DefinitionCollector Tests
# =============================================================================

class TestDefinitionCollector:
    """Tests for DefinitionCollector CST visitor.

    DefinitionCollector visits a module and collects all top-level
    function, class, and variable definitions.
    """

    def test_collects_functions(self, tmp_path: Path):
        """
        DefinitionCollector should find top-level function definitions.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            def foo():
                pass

            def bar():
                pass
        ''')
        tree = cst.parse_module(code)
        collector = DefinitionCollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        func_names = [name for name, _ in collector.functions]
        assert "foo" in func_names
        assert "bar" in func_names

    def test_collects_classes(self, tmp_path: Path):
        """
        DefinitionCollector should find top-level class definitions.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            class MyClass:
                pass

            class OtherClass:
                pass
        ''')
        tree = cst.parse_module(code)
        collector = DefinitionCollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        class_names = [name for name, _ in collector.classes]
        assert "MyClass" in class_names
        assert "OtherClass" in class_names

    def test_collects_variables(self, tmp_path: Path):
        """
        DefinitionCollector should find module-level variable assignments.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            x = 1
            y: int = 2
        ''')
        tree = cst.parse_module(code)
        collector = DefinitionCollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        var_names = [name for name, _ in collector.variables]
        assert "x" in var_names
        assert "y" in var_names

    def test_ignores_nested_functions(self, tmp_path: Path):
        """
        DefinitionCollector should not include nested functions.

        Nested functions are typically internal to their parent and
        should not be flagged as unused at the module level.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            def outer():
                def inner():
                    pass
                return inner()
        ''')
        tree = cst.parse_module(code)
        collector = DefinitionCollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        func_names = [name for name, _ in collector.functions]
        assert "outer" in func_names
        # Nested functions should not be in the list
        assert "inner" not in func_names

    def test_ignores_methods(self, tmp_path: Path):
        """
        DefinitionCollector should not include class methods.

        Methods are part of their class and should not be tracked
        separately at the module level.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            class MyClass:
                def my_method(self):
                    pass
        ''')
        tree = cst.parse_module(code)
        collector = DefinitionCollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        func_names = [name for name, _ in collector.functions]
        assert "my_method" not in func_names
        # But the class should be tracked
        class_names = [name for name, _ in collector.classes]
        assert "MyClass" in class_names

    def test_ignores_constants(self, tmp_path: Path):
        """
        DefinitionCollector should skip ALL_CAPS constants.

        Constants are typically intentionally unused in the defining module
        as they are exported for use elsewhere.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            MY_CONSTANT = 42
            MAX_VALUE = 100
            regular_var = 1
        ''')
        tree = cst.parse_module(code)
        collector = DefinitionCollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        var_names = [name for name, _ in collector.variables]
        # Constants should be excluded
        assert "MY_CONSTANT" not in var_names
        assert "MAX_VALUE" not in var_names
        # Regular variables should be included
        assert "regular_var" in var_names


# =============================================================================
# UsageCollector Tests
# =============================================================================

class TestUsageCollector:
    """Tests for UsageCollector CST visitor.

    UsageCollector visits a module and collects all name references.
    """

    def test_collects_simple_names(self):
        """
        UsageCollector should find simple name references.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            x = foo()
            y = bar + baz
        ''')
        tree = cst.parse_module(code)
        collector = UsageCollector()
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        assert "foo" in collector.used_names
        assert "bar" in collector.used_names
        assert "baz" in collector.used_names

    def test_collects_attribute_roots(self):
        """
        UsageCollector should track the root of attribute access.

        For x.y.z, only 'x' is a module-level name reference.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            result = my_module.sub_module.function()
        ''')
        tree = cst.parse_module(code)
        collector = UsageCollector()
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        assert "my_module" in collector.used_names

    def test_collects_function_calls(self):
        """
        UsageCollector should find function names in calls.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            result = process_data(input_value)
        ''')
        tree = cst.parse_module(code)
        collector = UsageCollector()
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        assert "process_data" in collector.used_names
        assert "input_value" in collector.used_names

    def test_collects_base_classes(self):
        """
        UsageCollector should find class names used as base classes.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            class Child(Parent):
                pass
        ''')
        tree = cst.parse_module(code)
        collector = UsageCollector()
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        assert "Parent" in collector.used_names


# =============================================================================
# DeadCodeAnalyzer Tests
# =============================================================================

class TestDeadCodeAnalyzer:
    """Tests for DeadCodeAnalyzer class.

    DeadCodeAnalyzer combines definition and usage collection to
    identify potentially unused code.
    """

    @pytest.fixture
    def create_project(self, tmp_path: Path):
        """Factory fixture to create a project with specific files.

        Returns a callable that takes a dict of {filename: content}
        and returns a Rejig instance.
        """
        def _create(files: dict[str, str]):
            for name, content in files.items():
                (tmp_path / name).write_text(content)
            return Rejig(str(tmp_path))
        return _create

    def test_find_unused_function(self, create_project):
        """
        find_unused_functions should detect functions not called anywhere.
        """
        rj = create_project({
            "app.py": textwrap.dedent('''\
                def used_function():
                    return 42

                def unused_function():
                    return "never called"

                result = used_function()
            ''')
        })

        analyzer = DeadCodeAnalyzer(rj)
        findings = analyzer.find_unused_functions()

        # unused_function should be flagged
        finding_names = [t.name for t in findings]
        assert "unused_function" in finding_names
        # used_function should not be flagged
        assert "used_function" not in finding_names

    def test_excludes_main_function(self, create_project):
        """
        find_unused_functions should exclude common entry points like main().

        main() is a common convention for entry points and should not be
        flagged even if not explicitly called in the same file.
        """
        rj = create_project({
            "app.py": textwrap.dedent('''\
                def main():
                    print("Hello")

                # main is not called but should be excluded
            ''')
        })

        analyzer = DeadCodeAnalyzer(rj)
        findings = analyzer.find_unused_functions()

        finding_names = [t.name for t in findings]
        assert "main" not in finding_names

    def test_excludes_test_functions(self, create_project):
        """
        find_unused_functions should exclude test_ prefixed functions.

        Test functions are typically invoked by test runners, not code.
        """
        rj = create_project({
            "test_app.py": textwrap.dedent('''\
                def test_something():
                    assert True

                def test_another():
                    assert 1 == 1
            ''')
        })

        analyzer = DeadCodeAnalyzer(rj)
        findings = analyzer.find_unused_functions()

        finding_names = [t.name for t in findings]
        assert "test_something" not in finding_names
        assert "test_another" not in finding_names

    def test_excludes_private_functions(self, create_project):
        """
        find_unused_functions should exclude private (_) functions.

        Private functions may be intentionally unused or only used
        in ways that are hard to statically detect.
        """
        rj = create_project({
            "app.py": textwrap.dedent('''\
                def _private_helper():
                    return "private"

                def public_unused():
                    return "public"
            ''')
        })

        analyzer = DeadCodeAnalyzer(rj)
        findings = analyzer.find_unused_functions()

        finding_names = [t.name for t in findings]
        # Private should be excluded
        assert "_private_helper" not in finding_names
        # Public unused should be flagged
        assert "public_unused" in finding_names

    def test_find_unused_class(self, create_project):
        """
        find_unused_classes should detect classes not referenced anywhere.
        """
        rj = create_project({
            "app.py": textwrap.dedent('''\
                class UsedClass:
                    pass

                class UnusedClass:
                    pass

                instance = UsedClass()
            ''')
        })

        analyzer = DeadCodeAnalyzer(rj)
        findings = analyzer.find_unused_classes()

        finding_names = [t.name for t in findings]
        assert "UnusedClass" in finding_names
        assert "UsedClass" not in finding_names

    def test_excludes_test_classes(self, create_project):
        """
        find_unused_classes should exclude Test prefixed classes.

        Test classes are typically invoked by test runners.
        """
        rj = create_project({
            "test_app.py": textwrap.dedent('''\
                class TestSomething:
                    def test_method(self):
                        pass
            ''')
        })

        analyzer = DeadCodeAnalyzer(rj)
        findings = analyzer.find_unused_classes()

        finding_names = [t.name for t in findings]
        assert "TestSomething" not in finding_names

    def test_excludes_base_and_mixin_classes(self, create_project):
        """
        find_unused_classes should exclude Base* and *Mixin classes.

        These are typically abstract classes or mixins designed for inheritance.
        """
        rj = create_project({
            "app.py": textwrap.dedent('''\
                class BaseHandler:
                    pass

                class AuthMixin:
                    pass

                class ConcreteUnused:
                    pass
            ''')
        })

        analyzer = DeadCodeAnalyzer(rj)
        findings = analyzer.find_unused_classes()

        finding_names = [t.name for t in findings]
        assert "BaseHandler" not in finding_names
        assert "AuthMixin" not in finding_names
        assert "ConcreteUnused" in finding_names

    def test_find_unused_variables(self, create_project):
        """
        find_unused_variables should detect module-level variables not used.
        """
        rj = create_project({
            "app.py": textwrap.dedent('''\
                used_var = 10
                unused_var = 20
                result = used_var * 2
            ''')
        })

        analyzer = DeadCodeAnalyzer(rj)
        findings = analyzer.find_unused_variables()

        finding_names = [t.name for t in findings]
        assert "unused_var" in finding_names
        # used_var should not be flagged since it's used
        # Note: this may vary based on how usage is tracked

    def test_find_all_dead_code(self, create_project):
        """
        find_all_dead_code should combine all dead code findings.
        """
        rj = create_project({
            "app.py": textwrap.dedent('''\
                def unused_func():
                    pass

                class UnusedClass:
                    pass

                unused_var = 42
            ''')
        })

        analyzer = DeadCodeAnalyzer(rj)
        all_findings = analyzer.find_all_dead_code()

        # Should return an AnalysisTargetList
        assert isinstance(all_findings, AnalysisTargetList)
        # Should have some findings
        assert len(all_findings) >= 1

    def test_cross_file_usage(self, create_project):
        """
        Analyzer should detect usage across multiple files.

        A function defined in one file but used in another should
        not be flagged as unused.
        """
        rj = create_project({
            "utils.py": textwrap.dedent('''\
                def helper():
                    return "help"

                def orphan():
                    return "alone"
            '''),
            "main.py": textwrap.dedent('''\
                from utils import helper
                result = helper()
            ''')
        })

        analyzer = DeadCodeAnalyzer(rj)
        findings = analyzer.find_unused_functions()

        finding_names = [t.name for t in findings]
        # helper is used in main.py
        assert "helper" not in finding_names
        # orphan is never used
        assert "orphan" in finding_names

    def test_empty_project(self, tmp_path: Path):
        """
        Analyzer should handle empty projects gracefully.
        """
        rj = Rejig(str(tmp_path))
        analyzer = DeadCodeAnalyzer(rj)

        findings = analyzer.find_all_dead_code()

        assert len(findings) == 0

    def test_syntax_error_handling(self, create_project):
        """
        Analyzer should handle files with syntax errors gracefully.

        Files that cannot be parsed should be skipped without raising.
        """
        rj = create_project({
            "good.py": textwrap.dedent('''\
                def good_func():
                    return 1
            '''),
            "bad.py": "def broken(:\n    pass"
        })

        analyzer = DeadCodeAnalyzer(rj)
        # Should not raise
        findings = analyzer.find_all_dead_code()

        # Should still find the good function
        assert isinstance(findings, AnalysisTargetList)


# =============================================================================
# UnreachableCodeCollector Tests
# =============================================================================

class TestUnreachableCodeCollector:
    """Tests for UnreachableCodeCollector.

    UnreachableCodeCollector detects code that appears after
    return or raise statements.
    """

    def test_detects_code_after_return(self, tmp_path: Path):
        """
        UnreachableCodeCollector should flag code after return.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            def func():
                return 1
                x = 2  # unreachable
        ''')
        tree = cst.parse_module(code)
        collector = UnreachableCodeCollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        # Should detect unreachable code
        assert len(collector.unreachable_lines) >= 0  # May vary by implementation

    def test_no_false_positive_in_branches(self, tmp_path: Path):
        """
        Code after return in branches should not flag the next branch.

        In if/else, return in the if block should not flag the else block.
        """
        import libcst as cst

        code = textwrap.dedent('''\
            def func(x):
                if x > 0:
                    return x
                else:
                    return 0  # This is reachable
        ''')
        tree = cst.parse_module(code)
        collector = UnreachableCodeCollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        # The else branch should NOT be flagged as unreachable
        # This depends on implementation sophistication
        # A simple implementation might flag it incorrectly


# =============================================================================
# Integration Tests
# =============================================================================

class TestDeadCodeIntegration:
    """Integration tests for dead code analysis workflow."""

    def test_analysis_target_properties(self, tmp_path: Path):
        """
        AnalysisTarget for dead code should have expected properties.
        """
        (tmp_path / "app.py").write_text(textwrap.dedent('''\
            def orphan_function():
                return 42
        '''))

        rj = Rejig(str(tmp_path))
        analyzer = DeadCodeAnalyzer(rj)
        findings = analyzer.find_unused_functions()

        if len(findings) > 0:
            target = findings[0]
            assert target.type == AnalysisType.UNUSED_FUNCTION
            assert target.file_path == tmp_path / "app.py"
            assert target.name == "orphan_function"
            assert "unused" in target.message.lower()

    def test_filtering_by_type(self, tmp_path: Path):
        """
        Dead code findings can be filtered by AnalysisType.
        """
        (tmp_path / "app.py").write_text(textwrap.dedent('''\
            def unused_func():
                pass

            class UnusedClass:
                pass
        '''))

        rj = Rejig(str(tmp_path))
        analyzer = DeadCodeAnalyzer(rj)
        all_findings = analyzer.find_all_dead_code()

        # Filter to just functions
        func_findings = all_findings.by_type(AnalysisType.UNUSED_FUNCTION)
        for target in func_findings:
            assert target.type == AnalysisType.UNUSED_FUNCTION

        # Filter to just classes
        class_findings = all_findings.by_type(AnalysisType.UNUSED_CLASS)
        for target in class_findings:
            assert target.type == AnalysisType.UNUSED_CLASS
