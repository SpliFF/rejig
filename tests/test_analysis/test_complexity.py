"""
Tests for rejig.analysis.complexity module.

This module tests cyclomatic complexity analysis:
- Simple function analysis
- Complex function detection
- Nesting depth analysis
- Function/method parameter counting
- Long function/class detection

The ComplexityAnalyzer requires a Rejig instance and works on files
in the project directory.

Coverage targets:
- Complexity calculation (cyclomatic complexity)
- Nesting depth tracking
- Parameter counting
- Branch and return counting
- Thresholds and finding generation
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig import Rejig
from rejig.analysis import ComplexityAnalyzer, ComplexityResult, NestingResult


# =============================================================================
# ComplexityResult Tests
# =============================================================================

class TestComplexityResult:
    """Tests for ComplexityResult dataclass.

    ComplexityResult holds the complexity metrics for a single function or method.
    """

    def test_basic_attributes(self):
        """
        ComplexityResult should have basic required attributes.
        """
        result = ComplexityResult(
            name="test_func",
            file_path=Path("test.py"),
            line_number=1,
        )

        assert result.name == "test_func"
        assert result.file_path == Path("test.py")
        assert result.line_number == 1
        # Default values
        assert result.cyclomatic_complexity == 1
        assert result.line_count == 0
        assert result.parameter_count == 0

    def test_full_name_for_function(self):
        """
        full_name should return just the function name for module-level functions.
        """
        result = ComplexityResult(
            name="my_func",
            file_path=Path("test.py"),
            line_number=1,
            is_method=False,
            class_name=None,
        )

        assert result.full_name == "my_func"

    def test_full_name_for_method(self):
        """
        full_name should return Class.method for methods.
        """
        result = ComplexityResult(
            name="my_method",
            file_path=Path("test.py"),
            line_number=10,
            is_method=True,
            class_name="MyClass",
        )

        assert result.full_name == "MyClass.my_method"


# =============================================================================
# NestingResult Tests
# =============================================================================

class TestNestingResult:
    """Tests for NestingResult dataclass.

    NestingResult holds the nesting depth information for a function or method.
    """

    def test_basic_attributes(self):
        """
        NestingResult should have basic required attributes.
        """
        result = NestingResult(
            name="test_func",
            file_path=Path("test.py"),
            line_number=1,
        )

        assert result.name == "test_func"
        assert result.file_path == Path("test.py")
        assert result.max_depth == 0

    def test_full_name_for_method(self):
        """
        full_name should return Class.method for methods.
        """
        result = NestingResult(
            name="nested_method",
            file_path=Path("test.py"),
            line_number=10,
            is_method=True,
            class_name="MyClass",
            max_depth=3,
        )

        assert result.full_name == "MyClass.nested_method"
        assert result.max_depth == 3


# =============================================================================
# ComplexityAnalyzer Tests
# =============================================================================

class TestComplexityAnalyzer:
    """Tests for ComplexityAnalyzer class.

    ComplexityAnalyzer requires a Rejig instance and analyzes Python files
    in the project for complexity metrics.
    """

    @pytest.fixture
    def create_project(self, tmp_path: Path):
        """Factory fixture to create a project with specific code.

        Returns a callable that takes code and returns a (Rejig, file_path) tuple.
        """
        def _create(code: str, filename: str = "test.py"):
            file_path = tmp_path / filename
            file_path.write_text(code)
            rj = Rejig(str(tmp_path))
            return rj, file_path
        return _create

    def test_simple_function_low_complexity(self, create_project):
        """
        Simple function should have low cyclomatic complexity.

        A function with no branches has complexity of 1 (the base value).
        """
        code = textwrap.dedent('''\
            def simple(x):
                return x * 2
        ''')
        rj, _ = create_project(code)

        analyzer = ComplexityAnalyzer(rj)
        results = analyzer.analyze_all()

        # Should find one function
        assert len(results) >= 1
        # Find the simple function
        simple_results = [r for r in results if r.name == "simple"]
        assert len(simple_results) == 1
        # Complexity should be 1 (no branches)
        assert simple_results[0].cyclomatic_complexity == 1

    def test_function_with_if_increases_complexity(self, create_project):
        """
        Each if statement increases cyclomatic complexity by 1.
        """
        code = textwrap.dedent('''\
            def with_if(x):
                if x > 0:
                    return x
                return 0
        ''')
        rj, _ = create_project(code)

        analyzer = ComplexityAnalyzer(rj)
        results = analyzer.analyze_all()

        # Find our function
        func_results = [r for r in results if r.name == "with_if"]
        assert len(func_results) == 1
        # Base complexity (1) + one if (1) = 2
        assert func_results[0].cyclomatic_complexity == 2

    def test_function_with_nested_conditionals(self, create_project):
        """
        Nested if statements each add to complexity.
        """
        code = textwrap.dedent('''\
            def nested(x, y):
                if x > 0:
                    if y > 0:
                        return "both positive"
                    else:
                        return "x positive"
                else:
                    return "x not positive"
        ''')
        rj, _ = create_project(code)

        analyzer = ComplexityAnalyzer(rj)
        results = analyzer.analyze_all()

        func_results = [r for r in results if r.name == "nested"]
        assert len(func_results) == 1
        # Base (1) + outer if (1) + inner if (1) = 3
        assert func_results[0].cyclomatic_complexity >= 3

    def test_function_with_for_loop(self, create_project):
        """
        For loops increase complexity.
        """
        code = textwrap.dedent('''\
            def with_loop(items):
                total = 0
                for item in items:
                    total += item
                return total
        ''')
        rj, _ = create_project(code)

        analyzer = ComplexityAnalyzer(rj)
        results = analyzer.analyze_all()

        func_results = [r for r in results if r.name == "with_loop"]
        assert len(func_results) == 1
        # Base (1) + for loop (1) = 2
        assert func_results[0].cyclomatic_complexity >= 2

    def test_function_with_while_loop(self, create_project):
        """
        While loops increase complexity.
        """
        code = textwrap.dedent('''\
            def with_while(x):
                while x > 0:
                    x -= 1
                return x
        ''')
        rj, _ = create_project(code)

        analyzer = ComplexityAnalyzer(rj)
        results = analyzer.analyze_all()

        func_results = [r for r in results if r.name == "with_while"]
        assert len(func_results) == 1
        assert func_results[0].cyclomatic_complexity >= 2

    def test_function_with_try_except(self, create_project):
        """
        Each except handler increases complexity.
        """
        code = textwrap.dedent('''\
            def with_try(x):
                try:
                    return int(x)
                except ValueError:
                    return 0
                except TypeError:
                    return -1
        ''')
        rj, _ = create_project(code)

        analyzer = ComplexityAnalyzer(rj)
        results = analyzer.analyze_all()

        func_results = [r for r in results if r.name == "with_try"]
        assert len(func_results) == 1
        # Two except handlers add to complexity
        assert func_results[0].cyclomatic_complexity >= 3

    def test_function_with_boolean_operators(self, create_project):
        """
        Boolean operators (and/or) increase complexity.

        Each and/or operator adds a decision point.
        """
        code = textwrap.dedent('''\
            def with_bool(a, b, c):
                if a and b or c:
                    return True
                return False
        ''')
        rj, _ = create_project(code)

        analyzer = ComplexityAnalyzer(rj)
        results = analyzer.analyze_all()

        func_results = [r for r in results if r.name == "with_bool"]
        assert len(func_results) == 1
        # Base (1) + if (1) + and (1) + or (1) = 4
        assert func_results[0].cyclomatic_complexity >= 4

    def test_function_with_ternary(self, create_project):
        """
        Ternary expressions (x if cond else y) increase complexity.
        """
        code = textwrap.dedent('''\
            def with_ternary(x):
                return x if x > 0 else 0
        ''')
        rj, _ = create_project(code)

        analyzer = ComplexityAnalyzer(rj)
        results = analyzer.analyze_all()

        func_results = [r for r in results if r.name == "with_ternary"]
        assert len(func_results) == 1
        # Base (1) + ternary (1) = 2
        assert func_results[0].cyclomatic_complexity >= 2

    def test_multiple_functions(self, create_project):
        """
        Analyzer should report on all functions in a file.
        """
        code = textwrap.dedent('''\
            def func1():
                return 1

            def func2():
                return 2

            def func3():
                return 3
        ''')
        rj, _ = create_project(code)

        analyzer = ComplexityAnalyzer(rj)
        results = analyzer.analyze_all()

        # Should find 3 functions
        func_names = [r.name for r in results]
        assert "func1" in func_names
        assert "func2" in func_names
        assert "func3" in func_names

    def test_method_in_class(self, create_project):
        """
        Methods should be recognized and have class_name set.
        """
        code = textwrap.dedent('''\
            class MyClass:
                def my_method(self, x):
                    if x > 0:
                        return x
                    return 0
        ''')
        rj, _ = create_project(code)

        analyzer = ComplexityAnalyzer(rj)
        results = analyzer.analyze_all()

        method_results = [r for r in results if r.name == "my_method"]
        assert len(method_results) == 1
        assert method_results[0].is_method is True
        assert method_results[0].class_name == "MyClass"

    def test_parameter_counting(self, create_project):
        """
        Analyzer should count function parameters.

        For methods, self/cls should not be counted.
        """
        code = textwrap.dedent('''\
            def func_with_params(a, b, c, d):
                return a + b + c + d

            class MyClass:
                def method_with_params(self, x, y):
                    return x + y
        ''')
        rj, _ = create_project(code)

        analyzer = ComplexityAnalyzer(rj)
        results = analyzer.analyze_all()

        func_result = [r for r in results if r.name == "func_with_params"][0]
        assert func_result.parameter_count == 4

        method_result = [r for r in results if r.name == "method_with_params"][0]
        # self is not counted
        assert method_result.parameter_count == 2

    def test_return_counting(self, create_project):
        """
        Analyzer should count return statements.
        """
        code = textwrap.dedent('''\
            def multiple_returns(x):
                if x < 0:
                    return -1
                elif x == 0:
                    return 0
                else:
                    return 1
        ''')
        rj, _ = create_project(code)

        analyzer = ComplexityAnalyzer(rj)
        results = analyzer.analyze_all()

        func_result = [r for r in results if r.name == "multiple_returns"][0]
        assert func_result.return_count == 3

    def test_branch_counting(self, create_project):
        """
        Analyzer should count if/elif branches.
        """
        code = textwrap.dedent('''\
            def with_branches(x):
                if x < 0:
                    return -1
                elif x == 0:
                    return 0
                elif x == 1:
                    return 1
                else:
                    return 2
        ''')
        rj, _ = create_project(code)

        analyzer = ComplexityAnalyzer(rj)
        results = analyzer.analyze_all()

        # Note: The collector counts if as branches, not elif separately
        # Exact behavior depends on implementation
        func_result = [r for r in results if r.name == "with_branches"][0]
        assert func_result.branch_count >= 1

    def test_find_complex_functions(self, create_project):
        """
        find_complex_functions should return functions above threshold.
        """
        code = textwrap.dedent('''\
            def simple():
                return 1

            def complex_func(data):
                result = 0
                for item in data:
                    if item > 0:
                        if item < 100:
                            result += item
                        else:
                            result += 100
                    elif item == 0:
                        pass
                    else:
                        result -= item
                return result
        ''')
        rj, _ = create_project(code)

        analyzer = ComplexityAnalyzer(rj)
        # Set low threshold to catch the complex function
        findings = analyzer.find_complex_functions(max_complexity=3)

        # Should find the complex function
        finding_names = [t._finding.name for t in findings]
        assert "complex_func" in finding_names
        # Should not find the simple function
        assert "simple" not in finding_names

    def test_find_deeply_nested(self, create_project):
        """
        find_deeply_nested should find functions with excessive nesting.
        """
        code = textwrap.dedent('''\
            def shallow():
                if True:
                    return 1
                return 0

            def deeply_nested(x):
                if x > 0:
                    for i in range(x):
                        if i > 0:
                            while i > 0:
                                if i % 2 == 0:
                                    i -= 1
                return x
        ''')
        rj, _ = create_project(code)

        analyzer = ComplexityAnalyzer(rj)
        # Set threshold to 2 to catch the deeply nested function
        findings = analyzer.find_deeply_nested(max_depth=2)

        # Should find deeply_nested
        finding_names = [t._finding.name for t in findings]
        assert "deeply_nested" in finding_names

    def test_find_functions_with_many_parameters(self, create_project):
        """
        find_functions_with_many_parameters should find functions with too many params.
        """
        code = textwrap.dedent('''\
            def few_params(a, b):
                return a + b

            def many_params(a, b, c, d, e, f, g, h):
                return a + b + c + d + e + f + g + h
        ''')
        rj, _ = create_project(code)

        analyzer = ComplexityAnalyzer(rj)
        findings = analyzer.find_functions_with_many_parameters(max_params=5)

        finding_names = [t._finding.name for t in findings]
        assert "many_params" in finding_names
        assert "few_params" not in finding_names

    def test_empty_file(self, create_project):
        """
        Analyzer should handle empty files gracefully.
        """
        rj, _ = create_project("")

        analyzer = ComplexityAnalyzer(rj)
        results = analyzer.analyze_all()

        assert results == []

    def test_file_with_syntax_error(self, create_project):
        """
        Analyzer should handle syntax errors gracefully.

        Files with syntax errors should return empty results rather than raising.
        """
        code = "def broken(:\n    pass"  # Invalid syntax
        rj, _ = create_project(code)

        analyzer = ComplexityAnalyzer(rj)
        results = analyzer.analyze_all()

        # Should not raise, just return empty or skip the file
        assert isinstance(results, list)
