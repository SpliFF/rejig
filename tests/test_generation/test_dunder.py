"""
Tests for rejig.generation.dunder module.

This module tests dunder method generation:
- ClassAttribute dataclass
- ClassAttributeExtractor CST visitor
- extract_class_attributes function
- DunderGenerator class
- GenerateInitTransformer
- GenerateReprTransformer
- GenerateEqTransformer
- GenerateHashTransformer
"""
from __future__ import annotations

import textwrap

import libcst as cst
import pytest

from rejig.generation.dunder import (
    ClassAttribute,
    ClassAttributeExtractor,
    DunderGenerator,
    GenerateEqTransformer,
    GenerateHashTransformer,
    GenerateInitTransformer,
    GenerateReprTransformer,
    extract_class_attributes,
)


# =============================================================================
# ClassAttribute Tests
# =============================================================================

class TestClassAttribute:
    """Tests for ClassAttribute dataclass."""

    def test_minimal_attribute(self):
        """ClassAttribute should work with just a name."""
        attr = ClassAttribute(name="x")

        assert attr.name == "x"
        assert attr.type_hint is None
        assert attr.default is None
        assert attr.has_default is False

    def test_typed_attribute(self):
        """ClassAttribute should store type hints."""
        attr = ClassAttribute(name="count", type_hint="int")

        assert attr.name == "count"
        assert attr.type_hint == "int"
        assert attr.has_default is False

    def test_attribute_with_default(self):
        """ClassAttribute should store defaults."""
        attr = ClassAttribute(name="name", type_hint="str", default='"default"', has_default=True)

        assert attr.name == "name"
        assert attr.type_hint == "str"
        assert attr.default == '"default"'
        assert attr.has_default is True

    def test_attribute_all_fields(self):
        """ClassAttribute should accept all fields."""
        attr = ClassAttribute(
            name="items",
            type_hint="list[str]",
            default="[]",
            has_default=True,
        )

        assert attr.name == "items"
        assert attr.type_hint == "list[str]"
        assert attr.default == "[]"
        assert attr.has_default is True


# =============================================================================
# ClassAttributeExtractor Tests
# =============================================================================

class TestClassAttributeExtractor:
    """Tests for ClassAttributeExtractor CST visitor."""

    def test_extracts_annotated_assignment(self):
        """ClassAttributeExtractor should extract annotated class attributes."""
        code = textwrap.dedent('''\
            class MyClass:
                name: str
                count: int = 0
        ''')

        tree = cst.parse_module(code)
        extractor = ClassAttributeExtractor()

        # Walk through class body
        for stmt in tree.body:
            if isinstance(stmt, cst.ClassDef):
                for s in stmt.body.body:
                    if isinstance(s, cst.SimpleStatementLine):
                        for item in s.body:
                            if isinstance(item, cst.AnnAssign):
                                extractor.visit_AnnAssign(item)

        assert len(extractor.attributes) == 2
        assert extractor.attributes[0].name == "name"
        assert extractor.attributes[0].type_hint == "str"
        assert extractor.attributes[1].name == "count"
        assert extractor.attributes[1].has_default is True

    def test_extracts_simple_assignment(self):
        """ClassAttributeExtractor should extract simple class attributes."""
        code = textwrap.dedent('''\
            class MyClass:
                value = 42
        ''')

        tree = cst.parse_module(code)
        extractor = ClassAttributeExtractor()

        for stmt in tree.body:
            if isinstance(stmt, cst.ClassDef):
                for s in stmt.body.body:
                    if isinstance(s, cst.SimpleStatementLine):
                        for item in s.body:
                            if isinstance(item, cst.Assign):
                                extractor.visit_Assign(item)

        assert len(extractor.attributes) == 1
        assert extractor.attributes[0].name == "value"
        assert extractor.attributes[0].default == "42"
        assert extractor.attributes[0].has_default is True


# =============================================================================
# extract_class_attributes Tests
# =============================================================================

class TestExtractClassAttributes:
    """Tests for extract_class_attributes function."""

    def test_extracts_class_level_attributes(self):
        """extract_class_attributes should extract class-level attributes."""
        code = textwrap.dedent('''\
            class MyClass:
                name: str
                value: int = 10
        ''')

        tree = cst.parse_module(code)
        class_node = tree.body[0]
        attributes = extract_class_attributes(class_node)

        assert len(attributes) == 2
        names = [a.name for a in attributes]
        assert "name" in names
        assert "value" in names

    def test_extracts_init_assignments(self):
        """extract_class_attributes should extract self.x assignments from __init__."""
        code = textwrap.dedent('''\
            class MyClass:
                def __init__(self):
                    self.x = 1
                    self.y = 2
        ''')

        tree = cst.parse_module(code)
        class_node = tree.body[0]
        attributes = extract_class_attributes(class_node)

        assert len(attributes) == 2
        names = [a.name for a in attributes]
        assert "x" in names
        assert "y" in names

    def test_class_level_takes_precedence(self):
        """Class-level attributes should take precedence over __init__ assignments."""
        code = textwrap.dedent('''\
            class MyClass:
                x: int = 5

                def __init__(self):
                    self.x = 10
        ''')

        tree = cst.parse_module(code)
        class_node = tree.body[0]
        attributes = extract_class_attributes(class_node)

        # Should have only one 'x' from class level
        x_attrs = [a for a in attributes if a.name == "x"]
        assert len(x_attrs) == 1
        assert x_attrs[0].type_hint == "int"
        assert x_attrs[0].default == "5"

    def test_empty_class(self):
        """extract_class_attributes should handle empty classes."""
        code = textwrap.dedent('''\
            class Empty:
                pass
        ''')

        tree = cst.parse_module(code)
        class_node = tree.body[0]
        attributes = extract_class_attributes(class_node)

        assert attributes == []


# =============================================================================
# DunderGenerator Tests
# =============================================================================

class TestDunderGenerator:
    """Tests for DunderGenerator class."""

    def test_generate_init_empty(self):
        """generate_init should handle classes with no attributes."""
        gen = DunderGenerator([])
        code = gen.generate_init()

        assert "def __init__(self)" in code
        assert "pass" in code

    def test_generate_init_with_attributes(self):
        """generate_init should create proper __init__ with attributes."""
        attrs = [
            ClassAttribute(name="name", type_hint="str"),
            ClassAttribute(name="age", type_hint="int", default="0", has_default=True),
        ]
        gen = DunderGenerator(attrs)
        code = gen.generate_init()

        assert "def __init__(self, name: str, age: int = 0)" in code
        assert "self.name = name" in code
        assert "self.age = age" in code

    def test_generate_init_untyped(self):
        """generate_init should handle untyped attributes."""
        attrs = [
            ClassAttribute(name="value"),
            ClassAttribute(name="default", default="None", has_default=True),
        ]
        gen = DunderGenerator(attrs)
        code = gen.generate_init()

        assert "value" in code
        assert "default=None" in code

    def test_generate_repr_empty(self):
        """generate_repr should handle classes with no attributes."""
        gen = DunderGenerator([])
        code = gen.generate_repr()

        assert "def __repr__(self)" in code
        assert "__class__.__name__" in code

    def test_generate_repr_with_attributes(self):
        """generate_repr should include all attributes."""
        attrs = [
            ClassAttribute(name="name", type_hint="str"),
            ClassAttribute(name="value", type_hint="int"),
        ]
        gen = DunderGenerator(attrs)
        code = gen.generate_repr()

        assert "def __repr__(self)" in code
        assert "name=" in code
        assert "value=" in code
        assert "!r" in code  # Should use repr formatting

    def test_generate_eq_empty(self):
        """generate_eq should handle classes with no attributes."""
        gen = DunderGenerator([])
        code = gen.generate_eq()

        assert "def __eq__(self, other: object)" in code
        assert "isinstance" in code

    def test_generate_eq_with_attributes(self):
        """generate_eq should compare all attributes."""
        attrs = [
            ClassAttribute(name="x", type_hint="int"),
            ClassAttribute(name="y", type_hint="int"),
        ]
        gen = DunderGenerator(attrs)
        code = gen.generate_eq()

        assert "def __eq__(self, other: object)" in code
        assert "NotImplemented" in code
        assert "self.x == other.x" in code
        assert "self.y == other.y" in code

    def test_generate_hash_empty(self):
        """generate_hash should handle classes with no attributes."""
        gen = DunderGenerator([])
        code = gen.generate_hash()

        assert "def __hash__(self)" in code
        assert "hash(())" in code

    def test_generate_hash_with_attributes(self):
        """generate_hash should hash all attributes."""
        attrs = [
            ClassAttribute(name="x", type_hint="int"),
            ClassAttribute(name="y", type_hint="int"),
        ]
        gen = DunderGenerator(attrs)
        code = gen.generate_hash()

        assert "def __hash__(self)" in code
        assert "self.x" in code
        assert "self.y" in code
        assert "hash(" in code


# =============================================================================
# GenerateInitTransformer Tests
# =============================================================================

class TestGenerateInitTransformer:
    """Tests for GenerateInitTransformer."""

    def test_adds_init_to_class(self):
        """GenerateInitTransformer should add __init__ to a class."""
        code = textwrap.dedent('''\
            class Person:
                name: str
                age: int
        ''')

        tree = cst.parse_module(code)
        transformer = GenerateInitTransformer("Person")
        modified = tree.visit(transformer)

        result = modified.code
        assert "def __init__" in result
        assert "self.name = name" in result
        assert "self.age = age" in result
        assert transformer.added is True

    def test_skips_existing_init(self):
        """GenerateInitTransformer should skip if __init__ already exists."""
        code = textwrap.dedent('''\
            class Person:
                name: str

                def __init__(self, name: str):
                    self.name = name
        ''')

        tree = cst.parse_module(code)
        transformer = GenerateInitTransformer("Person", overwrite=False)
        modified = tree.visit(transformer)

        # Should be unchanged
        assert transformer.added is False

    def test_overwrites_existing_init(self):
        """GenerateInitTransformer with overwrite=True should replace __init__."""
        code = textwrap.dedent('''\
            class Person:
                name: str
                age: int

                def __init__(self):
                    pass
        ''')

        tree = cst.parse_module(code)
        transformer = GenerateInitTransformer("Person", overwrite=True)
        modified = tree.visit(transformer)

        result = modified.code
        assert "self.name = name" in result
        assert "self.age = age" in result
        assert transformer.added is True

    def test_targets_specific_class(self):
        """GenerateInitTransformer should only modify the target class."""
        code = textwrap.dedent('''\
            class Person:
                name: str

            class Animal:
                species: str
        ''')

        tree = cst.parse_module(code)
        transformer = GenerateInitTransformer("Person")
        modified = tree.visit(transformer)

        result = modified.code
        # Should have __init__ in Person but not necessarily in Animal
        assert "def __init__" in result


# =============================================================================
# GenerateReprTransformer Tests
# =============================================================================

class TestGenerateReprTransformer:
    """Tests for GenerateReprTransformer."""

    def test_adds_repr_to_class(self):
        """GenerateReprTransformer should add __repr__ to a class."""
        code = textwrap.dedent('''\
            class Person:
                name: str
        ''')

        tree = cst.parse_module(code)
        transformer = GenerateReprTransformer("Person")
        modified = tree.visit(transformer)

        result = modified.code
        assert "def __repr__" in result
        assert "name=" in result
        assert transformer.added is True

    def test_skips_existing_repr(self):
        """GenerateReprTransformer should skip if __repr__ already exists."""
        code = textwrap.dedent('''\
            class Person:
                name: str

                def __repr__(self):
                    return "Person"
        ''')

        tree = cst.parse_module(code)
        transformer = GenerateReprTransformer("Person", overwrite=False)
        modified = tree.visit(transformer)

        assert transformer.added is False


# =============================================================================
# GenerateEqTransformer Tests
# =============================================================================

class TestGenerateEqTransformer:
    """Tests for GenerateEqTransformer."""

    def test_adds_eq_to_class(self):
        """GenerateEqTransformer should add __eq__ to a class."""
        code = textwrap.dedent('''\
            class Point:
                x: int
                y: int
        ''')

        tree = cst.parse_module(code)
        transformer = GenerateEqTransformer("Point")
        modified = tree.visit(transformer)

        result = modified.code
        assert "def __eq__" in result
        assert "NotImplemented" in result
        assert transformer.added is True

    def test_skips_existing_eq(self):
        """GenerateEqTransformer should skip if __eq__ already exists."""
        code = textwrap.dedent('''\
            class Point:
                x: int

                def __eq__(self, other):
                    return True
        ''')

        tree = cst.parse_module(code)
        transformer = GenerateEqTransformer("Point", overwrite=False)
        modified = tree.visit(transformer)

        assert transformer.added is False


# =============================================================================
# GenerateHashTransformer Tests
# =============================================================================

class TestGenerateHashTransformer:
    """Tests for GenerateHashTransformer."""

    def test_adds_hash_to_class(self):
        """GenerateHashTransformer should add __hash__ to a class."""
        code = textwrap.dedent('''\
            class Point:
                x: int
                y: int
        ''')

        tree = cst.parse_module(code)
        transformer = GenerateHashTransformer("Point")
        modified = tree.visit(transformer)

        result = modified.code
        assert "def __hash__" in result
        assert "hash(" in result
        assert transformer.added is True

    def test_skips_existing_hash(self):
        """GenerateHashTransformer should skip if __hash__ already exists."""
        code = textwrap.dedent('''\
            class Point:
                x: int

                def __hash__(self):
                    return 0
        ''')

        tree = cst.parse_module(code)
        transformer = GenerateHashTransformer("Point", overwrite=False)
        modified = tree.visit(transformer)

        assert transformer.added is False

    def test_overwrites_existing_hash(self):
        """GenerateHashTransformer with overwrite=True should replace __hash__."""
        code = textwrap.dedent('''\
            class Point:
                x: int
                y: int

                def __hash__(self):
                    return 0
        ''')

        tree = cst.parse_module(code)
        transformer = GenerateHashTransformer("Point", overwrite=True)
        modified = tree.visit(transformer)

        result = modified.code
        assert "self.x" in result
        assert "self.y" in result
        assert transformer.added is True
