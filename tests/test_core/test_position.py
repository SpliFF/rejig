"""
Tests for rejig.core.position module.

This module tests position/line number tracking utilities built on LibCST metadata.
These are critical for accurate targeting of code elements.

Coverage targets:
- NodePosition dataclass
- PositionFinder visitor: classes, functions, methods
- get_node_positions: full source parsing
- find_class_line, find_function_line, find_method_line
- find_class_lines, find_function_lines, find_method_lines (range versions)
- find_all_classes, find_all_functions
- Edge cases: nested classes, decorated functions, empty source
"""
from __future__ import annotations

import textwrap

import pytest

from rejig.core.position import (
    NodePosition,
    find_all_classes,
    find_all_functions,
    find_class_line,
    find_class_lines,
    find_function_line,
    find_function_lines,
    find_method_line,
    find_method_lines,
    get_node_positions,
)


SAMPLE_CODE = textwrap.dedent('''\
    """Module docstring."""
    import os


    class MyClass:
        """A sample class."""

        count: int = 0

        def __init__(self, name: str) -> None:
            self.name = name

        def process(self, data: str) -> str:
            return f"{self.name}: {data}"

        @staticmethod
        def helper() -> str:
            return "helper"


    class AnotherClass:
        """Another class."""

        def do_something(self) -> None:
            pass


    def module_function(x: int) -> int:
        """A module-level function."""
        return x * 2


    def another_function() -> str:
        return "hello"
''')


# =============================================================================
# NodePosition Tests
# =============================================================================

class TestNodePosition:
    """Tests for NodePosition dataclass."""

    def test_node_position_creation(self):
        """
        NodePosition should store name, start_line, and end_line.
        """
        pos = NodePosition(name="MyClass", start_line=5, end_line=20)

        assert pos.name == "MyClass"
        assert pos.start_line == 5
        assert pos.end_line == 20


# =============================================================================
# get_node_positions Tests
# =============================================================================

class TestGetNodePositions:
    """Tests for get_node_positions function."""

    def test_finds_classes(self):
        """
        Should find all top-level classes with correct names.
        """
        finder = get_node_positions(SAMPLE_CODE)

        class_names = [c.name for c in finder.classes]
        assert "MyClass" in class_names
        assert "AnotherClass" in class_names

    def test_finds_functions(self):
        """
        Should find all module-level functions.
        """
        finder = get_node_positions(SAMPLE_CODE)

        func_names = [f.name for f in finder.functions]
        assert "module_function" in func_names
        assert "another_function" in func_names

    def test_finds_methods(self):
        """
        Should find methods within each class.
        """
        finder = get_node_positions(SAMPLE_CODE)

        assert "MyClass" in finder.methods
        method_names = [m.name for m in finder.methods["MyClass"]]
        assert "__init__" in method_names
        assert "process" in method_names
        assert "helper" in method_names

    def test_methods_not_in_functions(self):
        """
        Methods inside classes should NOT appear in the functions list.
        """
        finder = get_node_positions(SAMPLE_CODE)

        func_names = [f.name for f in finder.functions]
        assert "__init__" not in func_names
        assert "process" not in func_names
        assert "helper" not in func_names

    def test_class_line_numbers_ordered(self):
        """
        Class line numbers should increase (classes appear in source order).
        """
        finder = get_node_positions(SAMPLE_CODE)

        if len(finder.classes) >= 2:
            assert finder.classes[0].start_line < finder.classes[1].start_line

    def test_start_line_less_than_end_line(self):
        """
        For multiline definitions, start_line should be less than end_line.
        """
        finder = get_node_positions(SAMPLE_CODE)

        for cls in finder.classes:
            assert cls.start_line <= cls.end_line, f"{cls.name}: start > end"

        for func in finder.functions:
            assert func.start_line <= func.end_line, f"{func.name}: start > end"


# =============================================================================
# find_class_line Tests
# =============================================================================

class TestFindClassLine:
    """Tests for find_class_line function."""

    def test_find_existing_class(self):
        """
        Should return the line number of an existing class.
        """
        line = find_class_line(SAMPLE_CODE, "MyClass")

        assert line is not None
        assert line > 0
        # Verify the line actually contains the class definition
        lines = SAMPLE_CODE.splitlines()
        assert "class MyClass" in lines[line - 1]

    def test_find_second_class(self):
        """
        Should find the correct line for a class that isn't the first one.
        """
        line = find_class_line(SAMPLE_CODE, "AnotherClass")

        assert line is not None
        lines = SAMPLE_CODE.splitlines()
        assert "class AnotherClass" in lines[line - 1]

    def test_nonexistent_class_returns_none(self):
        """
        Should return None for a class that doesn't exist.
        """
        line = find_class_line(SAMPLE_CODE, "NonExistentClass")

        assert line is None

    def test_empty_source(self):
        """
        Should return None for empty source code.
        """
        line = find_class_line("", "AnyClass")

        assert line is None


# =============================================================================
# find_function_line Tests
# =============================================================================

class TestFindFunctionLine:
    """Tests for find_function_line function."""

    def test_find_existing_function(self):
        """
        Should return the line number of an existing module-level function.
        """
        line = find_function_line(SAMPLE_CODE, "module_function")

        assert line is not None
        lines = SAMPLE_CODE.splitlines()
        assert "def module_function" in lines[line - 1]

    def test_nonexistent_function_returns_none(self):
        """
        Should return None for a function that doesn't exist.
        """
        line = find_function_line(SAMPLE_CODE, "nonexistent_func")

        assert line is None

    def test_does_not_find_methods(self):
        """
        Should NOT find methods (they're inside classes, not module-level).
        """
        line = find_function_line(SAMPLE_CODE, "process")

        assert line is None


# =============================================================================
# find_method_line Tests
# =============================================================================

class TestFindMethodLine:
    """Tests for find_method_line function."""

    def test_find_existing_method(self):
        """
        Should return the line number of an existing method.
        """
        line = find_method_line(SAMPLE_CODE, "MyClass", "process")

        assert line is not None
        lines = SAMPLE_CODE.splitlines()
        assert "def process" in lines[line - 1]

    def test_nonexistent_method_returns_none(self):
        """
        Should return None for a method that doesn't exist.
        """
        line = find_method_line(SAMPLE_CODE, "MyClass", "nonexistent_method")

        assert line is None

    def test_nonexistent_class_returns_none(self):
        """
        Should return None when the class doesn't exist.
        """
        line = find_method_line(SAMPLE_CODE, "NonExistentClass", "process")

        assert line is None

    def test_method_in_correct_class(self):
        """
        Should only find methods in the specified class.
        """
        # do_something is in AnotherClass, not MyClass
        line_wrong = find_method_line(SAMPLE_CODE, "MyClass", "do_something")
        line_right = find_method_line(SAMPLE_CODE, "AnotherClass", "do_something")

        assert line_wrong is None
        assert line_right is not None


# =============================================================================
# find_class_lines (Range) Tests
# =============================================================================

class TestFindClassLines:
    """Tests for find_class_lines function (returns start, end tuple)."""

    def test_returns_start_and_end(self):
        """
        Should return a (start_line, end_line) tuple for an existing class.
        """
        result = find_class_lines(SAMPLE_CODE, "MyClass")

        assert result is not None
        start, end = result
        assert start > 0
        assert end > start  # Class spans multiple lines

    def test_nonexistent_returns_none(self):
        """
        Should return None for a class that doesn't exist.
        """
        result = find_class_lines(SAMPLE_CODE, "FakeClass")

        assert result is None


# =============================================================================
# find_function_lines (Range) Tests
# =============================================================================

class TestFindFunctionLines:
    """Tests for find_function_lines function (returns start, end tuple)."""

    def test_returns_start_and_end(self):
        """
        Should return a (start_line, end_line) tuple for an existing function.
        """
        result = find_function_lines(SAMPLE_CODE, "module_function")

        assert result is not None
        start, end = result
        assert start > 0
        assert end >= start

    def test_nonexistent_returns_none(self):
        """
        Should return None for a function that doesn't exist.
        """
        result = find_function_lines(SAMPLE_CODE, "fake_function")

        assert result is None


# =============================================================================
# find_method_lines (Range) Tests
# =============================================================================

class TestFindMethodLines:
    """Tests for find_method_lines function (returns start, end tuple)."""

    def test_returns_start_and_end(self):
        """
        Should return a (start_line, end_line) tuple for an existing method.
        """
        result = find_method_lines(SAMPLE_CODE, "MyClass", "process")

        assert result is not None
        start, end = result
        assert start > 0
        assert end >= start

    def test_nonexistent_method_returns_none(self):
        """
        Should return None when the method doesn't exist.
        """
        result = find_method_lines(SAMPLE_CODE, "MyClass", "fake_method")

        assert result is None

    def test_nonexistent_class_returns_none(self):
        """
        Should return None when the class doesn't exist.
        """
        result = find_method_lines(SAMPLE_CODE, "FakeClass", "process")

        assert result is None


# =============================================================================
# find_all_classes / find_all_functions Tests
# =============================================================================

class TestFindAll:
    """Tests for find_all_classes and find_all_functions."""

    def test_find_all_classes(self):
        """
        Should return all classes in the source.
        """
        classes = find_all_classes(SAMPLE_CODE)

        names = [c.name for c in classes]
        assert "MyClass" in names
        assert "AnotherClass" in names

    def test_find_all_functions(self):
        """
        Should return all module-level functions in the source.
        """
        functions = find_all_functions(SAMPLE_CODE)

        names = [f.name for f in functions]
        assert "module_function" in names
        assert "another_function" in names

    def test_no_classes_returns_empty(self):
        """
        Source without classes should return empty list.
        """
        source = "def hello(): pass\n"
        classes = find_all_classes(source)

        assert len(classes) == 0

    def test_no_functions_returns_empty(self):
        """
        Source without module-level functions should return empty list.
        """
        source = "class Foo:\n    def bar(self): pass\n"
        functions = find_all_functions(source)

        assert len(functions) == 0


# =============================================================================
# Edge Cases
# =============================================================================

class TestPositionEdgeCases:
    """Tests for edge cases in position tracking."""

    def test_decorated_class(self):
        """
        Decorated classes should still be found with correct line numbers.
        """
        source = textwrap.dedent('''\
            from dataclasses import dataclass

            @dataclass
            class MyData:
                name: str
                value: int
        ''')

        line = find_class_line(source, "MyData")
        assert line is not None

        # Class should span from the decorator to the last attribute
        result = find_class_lines(source, "MyData")
        assert result is not None
        start, end = result
        assert start <= 4  # Decorator or class line

    def test_decorated_function(self):
        """
        Decorated functions should still be found.
        """
        source = textwrap.dedent('''\
            import functools

            @functools.lru_cache
            def cached_func(n: int) -> int:
                return n * 2
        ''')

        line = find_function_line(source, "cached_func")
        assert line is not None

    def test_single_line_function(self):
        """
        Single-line functions should have start_line == end_line.
        """
        source = "def f(): pass\n"

        result = find_function_lines(source, "f")
        assert result is not None
        start, end = result
        assert start == end
