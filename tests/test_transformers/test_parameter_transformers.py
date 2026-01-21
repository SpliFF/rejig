"""
Tests for parameter-related CST transformers.

This module tests transformers that operate on function/method parameters:
- AddParameter: Add a parameter to function/method
- RemoveParameter: Remove a parameter from function/method
- SetReturnType: Set return type annotation
- SetParameterType: Set parameter type annotation

Coverage targets:
- Adding parameters at different positions
- Removing various parameter types
- Setting type annotations
- Edge cases (self/cls handling, default values)
"""
from __future__ import annotations

import textwrap

import libcst as cst
import pytest

from rejig.transformers import (
    AddParameter,
    RemoveParameter,
    SetReturnType,
    SetParameterType,
)


# =============================================================================
# AddParameter Tests
# =============================================================================

class TestAddParameter:
    """Tests for AddParameter transformer."""

    def test_add_parameter_at_end(self):
        """
        AddParameter should add a parameter at the end by default.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def my_method(self, x):
                    pass
        """)

        tree = cst.parse_module(code)
        transformer = AddParameter("MyClass", "my_method", "y")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "def my_method(self, x, y):" in result
        assert transformer.added is True

    def test_add_parameter_at_start(self):
        """
        AddParameter should add a parameter at the start (after self/cls).
        """
        code = textwrap.dedent("""\
            class MyClass:
                def my_method(self, x, y):
                    pass
        """)

        tree = cst.parse_module(code)
        transformer = AddParameter("MyClass", "my_method", "z", position="start")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        # z should come after self but before x
        assert "def my_method(self, z, x, y):" in result

    def test_add_parameter_with_type_annotation(self):
        """
        AddParameter should add type annotation when provided.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def my_method(self):
                    pass
        """)

        tree = cst.parse_module(code)
        transformer = AddParameter("MyClass", "my_method", "count", type_annotation="int")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "count: int" in result

    def test_add_parameter_with_default_value(self):
        """
        AddParameter should add default value when provided.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def my_method(self):
                    pass
        """)

        tree = cst.parse_module(code)
        transformer = AddParameter("MyClass", "my_method", "flag", default_value="False")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "flag=False" in result or "flag = False" in result

    def test_add_parameter_with_type_and_default(self):
        """
        AddParameter should handle both type annotation and default value.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def my_method(self):
                    pass
        """)

        tree = cst.parse_module(code)
        transformer = AddParameter(
            "MyClass", "my_method", "name",
            type_annotation="str",
            default_value='"default"'
        )
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "name: str" in result
        assert '"default"' in result

    def test_add_parameter_to_module_function(self):
        """
        AddParameter should work on module-level functions (class_name=None).
        """
        code = textwrap.dedent("""\
            def my_function(x):
                pass
        """)

        tree = cst.parse_module(code)
        transformer = AddParameter(None, "my_function", "y")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "def my_function(x, y):" in result

    def test_add_parameter_function_not_found(self):
        """
        AddParameter should not modify if function is not found.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def other_method(self):
                    pass
        """)

        tree = cst.parse_module(code)
        transformer = AddParameter("MyClass", "my_method", "x")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "def other_method(self):" in result
        assert transformer.added is False


# =============================================================================
# RemoveParameter Tests
# =============================================================================

class TestRemoveParameter:
    """Tests for RemoveParameter transformer."""

    def test_remove_parameter(self):
        """
        RemoveParameter should remove a parameter by name.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def my_method(self, x, y, z):
                    pass
        """)

        tree = cst.parse_module(code)
        transformer = RemoveParameter("MyClass", "my_method", "y")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "def my_method(self, x, z):" in result
        assert transformer.removed is True

    def test_remove_last_parameter(self):
        """
        RemoveParameter should correctly remove the last parameter.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def my_method(self, x, y):
                    pass
        """)

        tree = cst.parse_module(code)
        transformer = RemoveParameter("MyClass", "my_method", "y")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "def my_method(self, x):" in result

    def test_remove_first_parameter_after_self(self):
        """
        RemoveParameter should correctly remove the first parameter after self.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def my_method(self, x, y):
                    pass
        """)

        tree = cst.parse_module(code)
        transformer = RemoveParameter("MyClass", "my_method", "x")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "def my_method(self, y):" in result

    def test_remove_parameter_from_module_function(self):
        """
        RemoveParameter should work on module-level functions.
        """
        code = textwrap.dedent("""\
            def my_function(a, b, c):
                pass
        """)

        tree = cst.parse_module(code)
        transformer = RemoveParameter(None, "my_function", "b")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "def my_function(a, c):" in result

    def test_remove_parameter_not_found(self):
        """
        RemoveParameter should not modify if parameter is not found.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def my_method(self, x):
                    pass
        """)

        tree = cst.parse_module(code)
        transformer = RemoveParameter("MyClass", "my_method", "nonexistent")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "def my_method(self, x):" in result
        assert transformer.removed is False


# =============================================================================
# SetReturnType Tests
# =============================================================================

class TestSetReturnType:
    """Tests for SetReturnType transformer."""

    def test_set_return_type(self):
        """
        SetReturnType should add return type annotation.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def my_method(self):
                    return 42
        """)

        tree = cst.parse_module(code)
        transformer = SetReturnType("MyClass", "my_method", "int")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "def my_method(self) -> int:" in result
        assert transformer.changed is True

    def test_set_return_type_complex(self):
        """
        SetReturnType should handle complex type annotations.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def get_items(self):
                    return []
        """)

        tree = cst.parse_module(code)
        transformer = SetReturnType("MyClass", "get_items", "list[str]")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "-> list[str]:" in result

    def test_set_return_type_none(self):
        """
        SetReturnType should handle None return type.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def do_something(self):
                    print("done")
        """)

        tree = cst.parse_module(code)
        transformer = SetReturnType("MyClass", "do_something", "None")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "-> None:" in result

    def test_set_return_type_replaces_existing(self):
        """
        SetReturnType should replace existing return type.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def my_method(self) -> str:
                    return "hello"
        """)

        tree = cst.parse_module(code)
        transformer = SetReturnType("MyClass", "my_method", "int")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "-> int:" in result
        assert "-> str:" not in result

    def test_set_return_type_module_function(self):
        """
        SetReturnType should work on module-level functions.
        """
        code = textwrap.dedent("""\
            def my_function():
                return True
        """)

        tree = cst.parse_module(code)
        transformer = SetReturnType(None, "my_function", "bool")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "-> bool:" in result

    def test_set_return_type_function_not_found(self):
        """
        SetReturnType should not modify if function is not found.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def other_method(self):
                    pass
        """)

        tree = cst.parse_module(code)
        transformer = SetReturnType("MyClass", "my_method", "int")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "-> int:" not in result
        assert transformer.changed is False


# =============================================================================
# SetParameterType Tests
# =============================================================================

class TestSetParameterType:
    """Tests for SetParameterType transformer."""

    def test_set_parameter_type(self):
        """
        SetParameterType should add type annotation to parameter.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def my_method(self, x):
                    pass
        """)

        tree = cst.parse_module(code)
        transformer = SetParameterType("MyClass", "my_method", "x", "int")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "x: int" in result
        assert transformer.changed is True

    def test_set_parameter_type_complex(self):
        """
        SetParameterType should handle complex type annotations.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def process(self, items):
                    pass
        """)

        tree = cst.parse_module(code)
        transformer = SetParameterType("MyClass", "process", "items", "list[dict[str, Any]]")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "items: list[dict[str, Any]]" in result

    def test_set_parameter_type_replaces_existing(self):
        """
        SetParameterType should replace existing type annotation.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def my_method(self, x: str):
                    pass
        """)

        tree = cst.parse_module(code)
        transformer = SetParameterType("MyClass", "my_method", "x", "int")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "x: int" in result
        assert "x: str" not in result

    def test_set_parameter_type_module_function(self):
        """
        SetParameterType should work on module-level functions.
        """
        code = textwrap.dedent("""\
            def my_function(x):
                pass
        """)

        tree = cst.parse_module(code)
        transformer = SetParameterType(None, "my_function", "x", "float")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "x: float" in result

    def test_set_parameter_type_not_found(self):
        """
        SetParameterType should not modify if parameter is not found.
        """
        code = textwrap.dedent("""\
            class MyClass:
                def my_method(self, x):
                    pass
        """)

        tree = cst.parse_module(code)
        transformer = SetParameterType("MyClass", "my_method", "y", "int")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "y: int" not in result
        assert transformer.changed is False
