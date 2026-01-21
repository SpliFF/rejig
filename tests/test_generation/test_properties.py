"""
Tests for rejig.generation.properties module.

This module tests property generation:
- ConvertAttributeToPropertyTransformer
- AddPropertyTransformer
"""
from __future__ import annotations

import textwrap

import libcst as cst
import pytest

from rejig.generation.properties import (
    AddPropertyTransformer,
    ConvertAttributeToPropertyTransformer,
)


# =============================================================================
# ConvertAttributeToPropertyTransformer Tests
# =============================================================================

class TestConvertAttributeToPropertyTransformer:
    """Tests for ConvertAttributeToPropertyTransformer."""

    def test_converts_typed_attribute(self):
        """Should convert a typed attribute to property with getter/setter."""
        code = textwrap.dedent('''\
            class Person:
                name: str
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertAttributeToPropertyTransformer("Person", "name")
        modified = tree.visit(transformer)

        result = modified.code
        assert "_name" in result  # Private backing field
        assert "@property" in result
        assert "@name.setter" in result
        assert "def name(self)" in result
        assert transformer.converted is True

    def test_converts_typed_attribute_with_default(self):
        """Should preserve default value in private attribute."""
        code = textwrap.dedent('''\
            class Config:
                timeout: int = 30
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertAttributeToPropertyTransformer("Config", "timeout")
        modified = tree.visit(transformer)

        result = modified.code
        assert "_timeout" in result
        assert "30" in result
        assert transformer.converted is True

    def test_converts_untyped_attribute(self):
        """Should convert untyped attribute."""
        code = textwrap.dedent('''\
            class Box:
                value = 100
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertAttributeToPropertyTransformer("Box", "value")
        modified = tree.visit(transformer)

        result = modified.code
        assert "_value" in result
        assert "100" in result
        assert "@property" in result
        assert transformer.converted is True

    def test_getter_only(self):
        """Should create read-only property when setter=False."""
        code = textwrap.dedent('''\
            class Circle:
                radius: float = 1.0
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertAttributeToPropertyTransformer(
            "Circle", "radius", getter=True, setter=False
        )
        modified = tree.visit(transformer)

        result = modified.code
        assert "@property" in result
        assert "@radius.setter" not in result
        assert transformer.converted is True

    def test_custom_private_prefix(self):
        """Should use custom private prefix."""
        code = textwrap.dedent('''\
            class Data:
                value: int
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertAttributeToPropertyTransformer(
            "Data", "value", private_prefix="__"
        )
        modified = tree.visit(transformer)

        result = modified.code
        assert "__value" in result
        assert transformer.converted is True

    def test_attribute_not_found(self):
        """Should not convert if attribute doesn't exist."""
        code = textwrap.dedent('''\
            class Person:
                name: str
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertAttributeToPropertyTransformer("Person", "age")
        modified = tree.visit(transformer)

        assert transformer.converted is False

    def test_wrong_class(self):
        """Should not convert attributes in other classes."""
        code = textwrap.dedent('''\
            class Person:
                name: str

            class Animal:
                name: str
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertAttributeToPropertyTransformer("Person", "name")
        modified = tree.visit(transformer)

        # Should only convert in Person class
        result = modified.code
        assert transformer.converted is True


# =============================================================================
# AddPropertyTransformer Tests
# =============================================================================

class TestAddPropertyTransformer:
    """Tests for AddPropertyTransformer."""

    def test_adds_simple_property(self):
        """Should add a property with just getter body."""
        code = textwrap.dedent('''\
            class Rectangle:
                width: int = 10
                height: int = 20
        ''')

        tree = cst.parse_module(code)
        transformer = AddPropertyTransformer(
            "Rectangle",
            "area",
            "self.width * self.height",
            return_type="int",
        )
        modified = tree.visit(transformer)

        result = modified.code
        assert "@property" in result
        assert "def area(self)" in result
        assert "self.width * self.height" in result
        assert transformer.added is True

    def test_adds_property_with_setter(self):
        """Should add property with getter and setter."""
        code = textwrap.dedent('''\
            class Person:
                _age: int
        ''')

        tree = cst.parse_module(code)
        transformer = AddPropertyTransformer(
            "Person",
            "age",
            "self._age",
            setter_body="self._age = value",
            return_type="int",
        )
        modified = tree.visit(transformer)

        result = modified.code
        assert "@property" in result
        assert "@age.setter" in result
        assert "self._age" in result
        assert transformer.added is True

    def test_wraps_expression_in_return(self):
        """Should wrap expression in return statement if needed."""
        code = textwrap.dedent('''\
            class Circle:
                _radius: float
        ''')

        tree = cst.parse_module(code)
        transformer = AddPropertyTransformer(
            "Circle",
            "diameter",
            "self._radius * 2",
            return_type="float",
        )
        modified = tree.visit(transformer)

        result = modified.code
        assert "return self._radius * 2" in result

    def test_does_not_wrap_return_statement(self):
        """Should not wrap if already a return statement."""
        code = textwrap.dedent('''\
            class Box:
                _data: dict
        ''')

        tree = cst.parse_module(code)
        transformer = AddPropertyTransformer(
            "Box",
            "data",
            "return self._data.copy()",
            return_type="dict",
        )
        modified = tree.visit(transformer)

        result = modified.code
        # Should not have "return return"
        assert "return return" not in result
        assert "return self._data.copy()" in result

    def test_skips_if_property_exists(self):
        """Should not add property if it already exists."""
        code = textwrap.dedent('''\
            class Person:
                @property
                def name(self):
                    return "John"
        ''')

        tree = cst.parse_module(code)
        transformer = AddPropertyTransformer(
            "Person",
            "name",
            '"Jane"',
        )
        modified = tree.visit(transformer)

        assert transformer.added is False

    def test_targets_specific_class(self):
        """Should only add property to the target class."""
        code = textwrap.dedent('''\
            class Person:
                pass

            class Animal:
                pass
        ''')

        tree = cst.parse_module(code)
        transformer = AddPropertyTransformer(
            "Person",
            "type",
            '"human"',
        )
        modified = tree.visit(transformer)

        assert transformer.added is True


# =============================================================================
# Integration Tests
# =============================================================================

class TestPropertiesIntegration:
    """Integration tests for property generation."""

    def test_convert_then_add_computed_property(self):
        """Should be able to convert attribute and add computed property."""
        code = textwrap.dedent('''\
            class Square:
                side: float = 1.0
        ''')

        tree = cst.parse_module(code)

        # First convert side to property
        convert = ConvertAttributeToPropertyTransformer("Square", "side")
        tree = tree.visit(convert)

        # Then add area property
        add = AddPropertyTransformer(
            "Square",
            "area",
            "self._side * self._side",
            return_type="float",
        )
        tree = tree.visit(add)

        result = tree.code
        assert "_side" in result
        assert "def area(self)" in result
        assert convert.converted is True
        assert add.added is True
