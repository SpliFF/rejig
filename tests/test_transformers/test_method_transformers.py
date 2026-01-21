"""
Tests for method-related CST transformers.

This module tests transformers that operate on methods and functions:
- RenameMethod: Rename a method
- AddMethodDecorator: Add decorator to method
- RemoveMethodDecorator: Remove decorator from method
- InsertAtMethodStart: Insert code at method start
- InsertAtMethodEnd: Insert code at method end
- AddFirstParameter: Add first parameter to method

All transformers inherit from libcst.CSTTransformer and are used
by the higher-level target classes.

Coverage targets:
- Basic transformation operations
- Edge cases (already exists, not found, etc.)
- Nested classes and methods
"""
from __future__ import annotations

import textwrap

import libcst as cst
import pytest

from rejig.transformers import (
    AddFirstParameter,
    AddMethodDecorator,
    InsertAtMethodEnd,
    InsertAtMethodStart,
    RemoveMethodDecorator,
    RenameMethod,
)


# =============================================================================
# RenameMethod Tests
# =============================================================================

class TestRenameMethod:
    """Tests for RenameMethod transformer."""

    def test_rename_method(self):
        """
        RenameMethod should rename a method within a class.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def old_method(self):
                    pass
        """)

        tree = cst.parse_module(code)
        transformer = RenameMethod("MyClass", "old_method", "new_method")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "def new_method(self):" in result
        assert "def old_method(self):" not in result
        assert transformer.renamed is True

    def test_rename_preserves_method_body(self):
        """
        RenameMethod should preserve the method body.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def old_method(self, x):
                    result = x * 2
                    return result
        """)

        tree = cst.parse_module(code)
        transformer = RenameMethod("MyClass", "old_method", "new_method")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "def new_method(self, x):" in result
        assert "result = x * 2" in result
        assert "return result" in result

    def test_rename_preserves_decorators(self):
        """
        RenameMethod should preserve method decorators.
        """
        code = textwrap.dedent("""\
            class MyClass:
                @staticmethod
                def old_method():
                    pass
        """)

        tree = cst.parse_module(code)
        transformer = RenameMethod("MyClass", "old_method", "new_method")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "@staticmethod" in result
        assert "def new_method():" in result

    def test_rename_method_not_found(self):
        """
        RenameMethod should not modify if method is not found.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def some_method(self):
                    pass
        """)

        tree = cst.parse_module(code)
        transformer = RenameMethod("MyClass", "old_method", "new_method")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "def some_method(self):" in result
        assert transformer.renamed is False

    def test_rename_only_in_target_class(self):
        """
        RenameMethod should only rename methods in the specified class.
        """
        code = textwrap.dedent("""\
            class ClassA:
                def method(self):
                    pass

            class ClassB:
                def method(self):
                    pass
        """)

        tree = cst.parse_module(code)
        transformer = RenameMethod("ClassA", "method", "new_method")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        # Should rename in ClassA
        assert "class ClassA:" in result
        # Should not rename in ClassB
        lines = result.split("\n")
        # Find ClassB and check it still has 'method'
        in_classb = False
        for line in lines:
            if "class ClassB:" in line:
                in_classb = True
            if in_classb and "def method(self):" in line:
                break
        else:
            pytest.fail("ClassB should still have 'def method'")


# =============================================================================
# AddMethodDecorator Tests
# =============================================================================

class TestAddMethodDecorator:
    """Tests for AddMethodDecorator transformer."""

    def test_add_decorator_to_method(self):
        """
        AddMethodDecorator should add a decorator to a method.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def my_method(self):
                    pass
        """)

        tree = cst.parse_module(code)
        transformer = AddMethodDecorator("MyClass", "my_method", "property")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "@property" in result
        assert transformer.added is True

    def test_add_decorator_simple_names_only(self):
        """
        AddMethodDecorator currently only supports simple decorator names.

        Note: The current implementation uses cst.Name() for the decorator,
        which only works for simple names like "property", not decorators
        with arguments like "lru_cache(maxsize=100)".

        For decorators with arguments, use AddClassDecorator which uses
        cst.parse_expression() instead.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def my_method(self):
                    pass
        """)

        tree = cst.parse_module(code)
        # Test that simple decorators work
        transformer = AddMethodDecorator("MyClass", "my_method", "cached_property")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "@cached_property" in result

    def test_no_duplicate_decorator(self):
        """
        AddMethodDecorator should not add duplicate decorators.
        """
        code = textwrap.dedent("""\
            class MyClass:
                @property
                def my_method(self):
                    pass
        """)

        tree = cst.parse_module(code)
        transformer = AddMethodDecorator("MyClass", "my_method", "property")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert result.count("@property") == 1


# =============================================================================
# RemoveMethodDecorator Tests
# =============================================================================

class TestRemoveMethodDecorator:
    """Tests for RemoveMethodDecorator transformer."""

    def test_remove_decorator_from_method(self):
        """
        RemoveMethodDecorator should remove a decorator from a method.
        """
        code = textwrap.dedent("""\
            class MyClass:
                @property
                def my_method(self):
                    pass
        """)

        tree = cst.parse_module(code)
        transformer = RemoveMethodDecorator("MyClass", "my_method", "property")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "@property" not in result
        assert "def my_method(self):" in result
        assert transformer.removed is True

    def test_remove_keeps_other_decorators(self):
        """
        RemoveMethodDecorator should keep other decorators.
        """
        code = textwrap.dedent("""\
            class MyClass:
                @decorator1
                @property
                @decorator2
                def my_method(self):
                    pass
        """)

        tree = cst.parse_module(code)
        transformer = RemoveMethodDecorator("MyClass", "my_method", "property")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "@property" not in result
        assert "@decorator1" in result
        assert "@decorator2" in result


# =============================================================================
# InsertAtMethodStart Tests
# =============================================================================

class TestInsertAtMethodStart:
    """Tests for InsertAtMethodStart transformer."""

    def test_insert_statement_at_start(self):
        """
        InsertAtMethodStart should insert a statement at the beginning.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def my_method(self):
                    return 42
        """)

        tree = cst.parse_module(code)
        transformer = InsertAtMethodStart("MyClass", "my_method", "print('entering')")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "print('entering')" in result
        # The new statement should come before the return
        assert result.index("print") < result.index("return")

    def test_insert_preserves_docstring(self):
        """
        InsertAtMethodStart should preserve method docstrings.

        The inserted statement should come after the docstring.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def my_method(self):
                    \"\"\"Method docstring.\"\"\"
                    return 42
        """)

        tree = cst.parse_module(code)
        transformer = InsertAtMethodStart("MyClass", "my_method", "x = 1")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        # Docstring should still be present
        assert '"""Method docstring."""' in result
        assert "x = 1" in result


# =============================================================================
# InsertAtMethodEnd Tests
# =============================================================================

class TestInsertAtMethodEnd:
    """Tests for InsertAtMethodEnd transformer."""

    def test_insert_statement_at_end(self):
        """
        InsertAtMethodEnd should insert a statement at the end.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def my_method(self):
                    x = 1
        """)

        tree = cst.parse_module(code)
        transformer = InsertAtMethodEnd("MyClass", "my_method", "print('exiting')")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "print('exiting')" in result
        # The new statement should come after x = 1
        assert result.index("x = 1") < result.index("print")


# =============================================================================
# AddFirstParameter Tests
# =============================================================================

class TestAddFirstParameter:
    """Tests for AddFirstParameter transformer."""

    def test_add_first_parameter(self):
        """
        AddFirstParameter should add a parameter at the start.

        This is useful for converting functions to methods (adding self).
        """
        code = textwrap.dedent("""\
            class MyClass:
                def my_method():
                    pass
        """)

        tree = cst.parse_module(code)
        transformer = AddFirstParameter("MyClass", "my_method", "self")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "def my_method(self):" in result

    def test_add_first_parameter_with_existing(self):
        """
        AddFirstParameter should work with existing parameters.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def my_method(x, y):
                    pass
        """)

        tree = cst.parse_module(code)
        transformer = AddFirstParameter("MyClass", "my_method", "self")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "def my_method(self, x, y):" in result
