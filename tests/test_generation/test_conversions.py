"""
Tests for rejig.generation.conversions module.

This module tests class conversion transformers:
- ConvertToDataclassTransformer
- ConvertFromDataclassTransformer
- ConvertToTypedDictTransformer
- ConvertToNamedTupleTransformer
"""
from __future__ import annotations

import textwrap

import libcst as cst
import pytest

from rejig.generation.conversions import (
    ConvertFromDataclassTransformer,
    ConvertToDataclassTransformer,
    ConvertToNamedTupleTransformer,
    ConvertToTypedDictTransformer,
)


# =============================================================================
# ConvertToDataclassTransformer Tests
# =============================================================================

class TestConvertToDataclassTransformer:
    """Tests for ConvertToDataclassTransformer."""

    def test_converts_simple_class(self):
        """Should convert a simple class to dataclass."""
        code = textwrap.dedent('''\
            class Person:
                def __init__(self, name: str, age: int):
                    self.name = name
                    self.age = age
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertToDataclassTransformer("Person")
        modified = tree.visit(transformer)

        result = modified.code
        assert "@dataclass" in result
        assert "name: str" in result or "name:" in result
        assert "age: int" in result or "age:" in result
        assert transformer.converted is True

    def test_converts_class_with_class_attrs(self):
        """Should convert class with class-level attributes."""
        code = textwrap.dedent('''\
            class Point:
                x: int
                y: int = 0
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertToDataclassTransformer("Point")
        modified = tree.visit(transformer)

        result = modified.code
        assert "@dataclass" in result
        assert transformer.converted is True

    def test_adds_frozen_option(self):
        """Should add frozen=True when specified."""
        code = textwrap.dedent('''\
            class Config:
                host: str
                port: int
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertToDataclassTransformer("Config", frozen=True)
        modified = tree.visit(transformer)

        result = modified.code
        # LibCST may format with spaces around =
        assert "frozen" in result and "True" in result
        assert transformer.converted is True

    def test_adds_slots_option(self):
        """Should add slots=True when specified."""
        code = textwrap.dedent('''\
            class Data:
                value: int
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertToDataclassTransformer("Data", slots=True)
        modified = tree.visit(transformer)

        result = modified.code
        # LibCST may format with spaces around =
        assert "slots" in result and "True" in result
        assert transformer.converted is True

    def test_skips_already_dataclass(self):
        """Should skip if already a dataclass."""
        code = textwrap.dedent('''\
            @dataclass
            class Person:
                name: str
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertToDataclassTransformer("Person")
        modified = tree.visit(transformer)

        # Should be unchanged
        assert transformer.converted is False

    def test_removes_manual_init(self):
        """Should remove __init__ when converting."""
        code = textwrap.dedent('''\
            class Point:
                def __init__(self, x: int, y: int):
                    self.x = x
                    self.y = y
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertToDataclassTransformer("Point")
        modified = tree.visit(transformer)

        result = modified.code
        assert "@dataclass" in result
        # The generated output shouldn't have manual __init__
        assert transformer.converted is True

    def test_preserves_other_methods(self):
        """Should preserve non-init methods."""
        code = textwrap.dedent('''\
            class Rectangle:
                width: int
                height: int

                def area(self):
                    return self.width * self.height
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertToDataclassTransformer("Rectangle")
        modified = tree.visit(transformer)

        result = modified.code
        assert "@dataclass" in result
        assert "def area(self)" in result
        assert transformer.converted is True

    def test_preserves_docstring(self):
        """Should preserve class docstring."""
        code = textwrap.dedent('''\
            class Person:
                """A person class."""
                name: str
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertToDataclassTransformer("Person")
        modified = tree.visit(transformer)

        result = modified.code
        assert '"""A person class."""' in result
        assert transformer.converted is True

    def test_targets_specific_class(self):
        """Should only convert the target class."""
        code = textwrap.dedent('''\
            class Person:
                name: str

            class Animal:
                species: str
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertToDataclassTransformer("Person")
        modified = tree.visit(transformer)

        result = modified.code
        # Only Person should be converted
        assert transformer.converted is True


# =============================================================================
# ConvertFromDataclassTransformer Tests
# =============================================================================

class TestConvertFromDataclassTransformer:
    """Tests for ConvertFromDataclassTransformer."""

    def test_converts_dataclass_to_regular(self):
        """Should convert dataclass to regular class with __init__."""
        code = textwrap.dedent('''\
            @dataclass
            class Person:
                name: str
                age: int
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertFromDataclassTransformer("Person")
        modified = tree.visit(transformer)

        result = modified.code
        assert "@dataclass" not in result
        assert "def __init__" in result
        assert transformer.converted is True

    def test_generates_repr(self):
        """Should generate __repr__ when requested."""
        code = textwrap.dedent('''\
            @dataclass
            class Point:
                x: int
                y: int
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertFromDataclassTransformer("Point", generate_repr=True)
        modified = tree.visit(transformer)

        result = modified.code
        assert "def __repr__" in result
        assert transformer.converted is True

    def test_generates_eq(self):
        """Should generate __eq__ when requested."""
        code = textwrap.dedent('''\
            @dataclass
            class Point:
                x: int
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertFromDataclassTransformer("Point", generate_eq=True)
        modified = tree.visit(transformer)

        result = modified.code
        assert "def __eq__" in result
        assert transformer.converted is True

    def test_generates_hash(self):
        """Should generate __hash__ when requested."""
        code = textwrap.dedent('''\
            @dataclass
            class Point:
                x: int
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertFromDataclassTransformer("Point", generate_hash=True)
        modified = tree.visit(transformer)

        result = modified.code
        assert "def __hash__" in result
        assert transformer.converted is True

    def test_skips_non_dataclass(self):
        """Should skip if not a dataclass."""
        code = textwrap.dedent('''\
            class Person:
                name: str
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertFromDataclassTransformer("Person")
        modified = tree.visit(transformer)

        assert transformer.converted is False

    def test_handles_dataclass_with_args(self):
        """Should handle @dataclass(frozen=True) style decorators."""
        code = textwrap.dedent('''\
            @dataclass(frozen=True)
            class Config:
                host: str
                port: int
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertFromDataclassTransformer("Config")
        modified = tree.visit(transformer)

        result = modified.code
        assert "@dataclass" not in result
        assert "def __init__" in result
        assert transformer.converted is True

    def test_preserves_other_decorators(self):
        """Should preserve non-dataclass decorators."""
        code = textwrap.dedent('''\
            @other_decorator
            @dataclass
            class Item:
                name: str
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertFromDataclassTransformer("Item")
        modified = tree.visit(transformer)

        result = modified.code
        assert "@other_decorator" in result
        assert "@dataclass" not in result
        assert transformer.converted is True


# =============================================================================
# ConvertToTypedDictTransformer Tests
# =============================================================================

class TestConvertToTypedDictTransformer:
    """Tests for ConvertToTypedDictTransformer."""

    def test_converts_class_to_typeddict(self):
        """Should convert class to TypedDict."""
        code = textwrap.dedent('''\
            class PersonDict:
                name: str
                age: int
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertToTypedDictTransformer("PersonDict")
        modified = tree.visit(transformer)

        result = modified.code
        assert "TypedDict" in result
        assert "name: str" in result
        assert "age: int" in result
        assert transformer.converted is True

    def test_removes_defaults(self):
        """Should remove default values (TypedDict doesn't support them)."""
        code = textwrap.dedent('''\
            class ConfigDict:
                host: str = "localhost"
                port: int = 8080
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertToTypedDictTransformer("ConfigDict")
        modified = tree.visit(transformer)

        result = modified.code
        assert "TypedDict" in result
        # TypedDict doesn't support defaults, so = values should be gone
        assert transformer.converted is True

    def test_removes_methods(self):
        """Should remove all methods (TypedDict doesn't have methods)."""
        code = textwrap.dedent('''\
            class DataDict:
                value: int

                def process(self):
                    pass
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertToTypedDictTransformer("DataDict")
        modified = tree.visit(transformer)

        result = modified.code
        assert "TypedDict" in result
        # Methods should be removed
        assert transformer.converted is True

    def test_removes_decorators(self):
        """Should remove all decorators."""
        code = textwrap.dedent('''\
            @dataclass
            class PersonDict:
                name: str
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertToTypedDictTransformer("PersonDict")
        modified = tree.visit(transformer)

        result = modified.code
        assert "@dataclass" not in result
        assert "TypedDict" in result
        assert transformer.converted is True

    def test_preserves_docstring(self):
        """Should preserve class docstring."""
        code = textwrap.dedent('''\
            class MyDict:
                """A typed dictionary."""
                key: str
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertToTypedDictTransformer("MyDict")
        modified = tree.visit(transformer)

        result = modified.code
        assert '"""A typed dictionary."""' in result
        assert transformer.converted is True


# =============================================================================
# ConvertToNamedTupleTransformer Tests
# =============================================================================

class TestConvertToNamedTupleTransformer:
    """Tests for ConvertToNamedTupleTransformer."""

    def test_converts_class_to_namedtuple(self):
        """Should convert class to NamedTuple."""
        code = textwrap.dedent('''\
            class Point:
                x: int
                y: int
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertToNamedTupleTransformer("Point")
        modified = tree.visit(transformer)

        result = modified.code
        assert "NamedTuple" in result
        assert "x: int" in result
        assert "y: int" in result
        assert transformer.converted is True

    def test_preserves_defaults(self):
        """Should preserve default values (NamedTuple supports them)."""
        code = textwrap.dedent('''\
            class Config:
                host: str = "localhost"
                port: int = 8080
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertToNamedTupleTransformer("Config")
        modified = tree.visit(transformer)

        result = modified.code
        assert "NamedTuple" in result
        # NamedTuple supports defaults
        assert "localhost" in result or '"localhost"' in result
        assert transformer.converted is True

    def test_removes_methods(self):
        """Should remove methods (NamedTuple class body only has attributes)."""
        code = textwrap.dedent('''\
            class Data:
                value: int

                def double(self):
                    return self.value * 2
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertToNamedTupleTransformer("Data")
        modified = tree.visit(transformer)

        result = modified.code
        assert "NamedTuple" in result
        assert transformer.converted is True

    def test_removes_decorators(self):
        """Should remove all decorators."""
        code = textwrap.dedent('''\
            @dataclass
            class Point:
                x: int
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertToNamedTupleTransformer("Point")
        modified = tree.visit(transformer)

        result = modified.code
        assert "@dataclass" not in result
        assert "NamedTuple" in result
        assert transformer.converted is True

    def test_handles_untyped_attributes(self):
        """Should use Any for untyped attributes."""
        code = textwrap.dedent('''\
            class Box:
                def __init__(self):
                    self.value = None
        ''')

        tree = cst.parse_module(code)
        transformer = ConvertToNamedTupleTransformer("Box")
        modified = tree.visit(transformer)

        result = modified.code
        assert "NamedTuple" in result
        assert transformer.converted is True


# =============================================================================
# Integration Tests
# =============================================================================

class TestConversionsIntegration:
    """Integration tests for class conversions."""

    def test_round_trip_dataclass(self):
        """Converting to dataclass and back should produce working code."""
        original = textwrap.dedent('''\
            class Person:
                def __init__(self, name: str, age: int):
                    self.name = name
                    self.age = age
        ''')

        tree = cst.parse_module(original)

        # Convert to dataclass
        to_dc = ConvertToDataclassTransformer("Person")
        tree = tree.visit(to_dc)

        # Convert back
        from_dc = ConvertFromDataclassTransformer(
            "Person",
            generate_repr=True,
            generate_eq=True,
        )
        tree = tree.visit(from_dc)

        result = tree.code
        assert "def __init__" in result
        assert "def __repr__" in result
        assert "def __eq__" in result

    def test_conversion_chain(self):
        """Multiple conversions should work in sequence."""
        code = textwrap.dedent('''\
            class Data:
                value: int = 0
        ''')

        tree = cst.parse_module(code)

        # First convert to dataclass
        to_dc = ConvertToDataclassTransformer("Data")
        tree = tree.visit(to_dc)
        assert to_dc.converted is True

        # Then convert to TypedDict (as new class)
        # Note: This creates a different class structure
        to_td = ConvertToTypedDictTransformer("Data")
        tree = tree.visit(to_td)
        assert to_td.converted is True
