"""
Tests for class-related CST transformers.

This module tests transformers that operate on class definitions:
- RenameClass: Rename a class
- AddClassDecorator: Add decorator to class
- RemoveDecorator: Remove decorator from class
- AddClassAttribute: Add class attribute
- RemoveClassAttribute: Remove class attribute

All transformers inherit from libcst.CSTTransformer and are used
by the higher-level target classes.

Coverage targets:
- Basic transformation operations
- Edge cases (already exists, not found, etc.)
- Complex class structures
"""
from __future__ import annotations

import textwrap

import libcst as cst
import pytest

from rejig.transformers import (
    AddClassAttribute,
    AddClassDecorator,
    RemoveClassAttribute,
    RemoveDecorator,
    RenameClass,
)


# =============================================================================
# RenameClass Tests
# =============================================================================

class TestRenameClass:
    """Tests for RenameClass transformer."""

    def test_rename_simple_class(self):
        """
        RenameClass should rename a class with the given name.
        """
        code = textwrap.dedent("""\
            class OldName:
                pass
        """)

        tree = cst.parse_module(code)
        transformer = RenameClass("OldName", "NewName")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "class NewName:" in result
        assert "class OldName:" not in result
        assert transformer.renamed is True

    def test_rename_class_not_found(self):
        """
        RenameClass should not modify code if class is not found.
        """
        code = textwrap.dedent("""\
            class SomeClass:
                pass
        """)

        tree = cst.parse_module(code)
        transformer = RenameClass("OldName", "NewName")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "class SomeClass:" in result
        assert transformer.renamed is False

    def test_rename_preserves_class_body(self):
        """
        RenameClass should preserve the class body.
        """
        code = textwrap.dedent("""\
            class OldName:
                x = 1

                def method(self):
                    return self.x
        """)

        tree = cst.parse_module(code)
        transformer = RenameClass("OldName", "NewName")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "class NewName:" in result
        assert "x = 1" in result
        assert "def method(self):" in result

    def test_rename_preserves_decorators(self):
        """
        RenameClass should preserve class decorators.
        """
        code = textwrap.dedent("""\
            @dataclass
            @frozen
            class OldName:
                pass
        """)

        tree = cst.parse_module(code)
        transformer = RenameClass("OldName", "NewName")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "class NewName:" in result
        assert "@dataclass" in result
        assert "@frozen" in result

    def test_rename_preserves_bases(self):
        """
        RenameClass should preserve base classes.
        """
        code = textwrap.dedent("""\
            class OldName(BaseClass, Mixin):
                pass
        """)

        tree = cst.parse_module(code)
        transformer = RenameClass("OldName", "NewName")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "class NewName(BaseClass, Mixin):" in result

    def test_rename_only_target_class(self):
        """
        RenameClass should only rename the specified class.

        Other classes with different names should be unchanged.
        """
        code = textwrap.dedent("""\
            class ClassA:
                pass

            class ClassB:
                pass
        """)

        tree = cst.parse_module(code)
        transformer = RenameClass("ClassA", "NewClassA")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "class NewClassA:" in result
        assert "class ClassB:" in result


# =============================================================================
# AddClassDecorator Tests
# =============================================================================

class TestAddClassDecorator:
    """Tests for AddClassDecorator transformer."""

    def test_add_simple_decorator(self):
        """
        AddClassDecorator should add a simple decorator to a class.
        """
        code = textwrap.dedent("""\
            class MyClass:
                pass
        """)

        tree = cst.parse_module(code)
        transformer = AddClassDecorator("MyClass", "dataclass")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "@dataclass" in result
        assert "class MyClass:" in result
        assert transformer.added is True

    def test_add_decorator_with_arguments(self):
        """
        AddClassDecorator should add decorators with arguments.
        """
        code = textwrap.dedent("""\
            class MyClass:
                pass
        """)

        tree = cst.parse_module(code)
        transformer = AddClassDecorator("MyClass", "dataclass(frozen=True)")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "@dataclass(frozen=True)" in result

    def test_add_decorator_to_existing(self):
        """
        AddClassDecorator should add to classes that already have decorators.
        """
        code = textwrap.dedent("""\
            @existing_decorator
            class MyClass:
                pass
        """)

        tree = cst.parse_module(code)
        transformer = AddClassDecorator("MyClass", "new_decorator")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "@new_decorator" in result
        assert "@existing_decorator" in result

    def test_no_duplicate_decorator(self):
        """
        AddClassDecorator should not add duplicate decorators.
        """
        code = textwrap.dedent("""\
            @dataclass
            class MyClass:
                pass
        """)

        tree = cst.parse_module(code)
        transformer = AddClassDecorator("MyClass", "dataclass")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        # Should only have one @dataclass
        assert result.count("@dataclass") == 1

    def test_add_decorator_class_not_found(self):
        """
        AddClassDecorator should not modify if class is not found.
        """
        code = textwrap.dedent("""\
            class OtherClass:
                pass
        """)

        tree = cst.parse_module(code)
        transformer = AddClassDecorator("MyClass", "dataclass")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "@dataclass" not in result
        assert transformer.added is False


# =============================================================================
# RemoveDecorator Tests
# =============================================================================

class TestRemoveDecorator:
    """Tests for RemoveDecorator transformer."""

    def test_remove_simple_decorator(self):
        """
        RemoveDecorator should remove a simple decorator.
        """
        code = textwrap.dedent("""\
            @dataclass
            class MyClass:
                pass
        """)

        tree = cst.parse_module(code)
        transformer = RemoveDecorator("MyClass", "dataclass")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "@dataclass" not in result
        assert "class MyClass:" in result
        assert transformer.removed is True

    def test_remove_decorator_with_arguments(self):
        """
        RemoveDecorator currently only removes simple Name decorators.

        Note: The current implementation does NOT handle decorators with
        arguments (Call nodes). This is a known limitation.
        Decorators like @dataclass(frozen=True) will NOT be removed
        when searching for "dataclass".
        """
        code = textwrap.dedent("""\
            @dataclass(frozen=True)
            class MyClass:
                pass
        """)

        tree = cst.parse_module(code)
        transformer = RemoveDecorator("MyClass", "dataclass")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        # Known limitation: decorator with arguments is NOT removed
        # because the implementation only checks cst.Name, not cst.Call
        assert "@dataclass(frozen=True)" in result
        assert transformer.removed is False

    def test_remove_keeps_other_decorators(self):
        """
        RemoveDecorator should keep other decorators.
        """
        code = textwrap.dedent("""\
            @decorator1
            @dataclass
            @decorator2
            class MyClass:
                pass
        """)

        tree = cst.parse_module(code)
        transformer = RemoveDecorator("MyClass", "dataclass")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "@dataclass" not in result
        assert "@decorator1" in result
        assert "@decorator2" in result

    def test_remove_decorator_not_found(self):
        """
        RemoveDecorator should not modify if decorator is not found.
        """
        code = textwrap.dedent("""\
            @other_decorator
            class MyClass:
                pass
        """)

        tree = cst.parse_module(code)
        transformer = RemoveDecorator("MyClass", "dataclass")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "@other_decorator" in result
        assert transformer.removed is False


# =============================================================================
# AddClassAttribute Tests
# =============================================================================

class TestAddClassAttribute:
    """Tests for AddClassAttribute transformer.

    Note: AddClassAttribute always creates type-annotated attributes.
    The signature is: AddClassAttribute(class_name, attr_name, type_annotation, default_value="None")

    It creates: attr_name: type_annotation = default_value
    """

    def test_add_simple_attribute(self):
        """
        AddClassAttribute should add a class attribute with type annotation.
        """
        code = textwrap.dedent("""\
            class MyClass:
                pass
        """)

        tree = cst.parse_module(code)
        # Signature: class_name, attr_name, type_annotation, default_value
        transformer = AddClassAttribute("MyClass", "x", "int", "42")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        # The attribute has type annotation
        assert "x: int = 42" in result
        assert transformer.added is True

    def test_add_string_attribute(self):
        """
        AddClassAttribute should handle string type annotations.
        """
        code = textwrap.dedent("""\
            class MyClass:
                pass
        """)

        tree = cst.parse_module(code)
        transformer = AddClassAttribute("MyClass", "name", "str", '"test"')
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert 'name: str = "test"' in result

    def test_add_attribute_default_value(self):
        """
        AddClassAttribute uses None as default value if not specified.
        """
        code = textwrap.dedent("""\
            class MyClass:
                pass
        """)

        tree = cst.parse_module(code)
        # Only providing class_name, attr_name, type_annotation
        transformer = AddClassAttribute("MyClass", "x", "int")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        # Default value is None
        assert "x: int = None" in result

    def test_add_attribute_class_not_found(self):
        """
        AddClassAttribute should not modify if class is not found.
        """
        code = textwrap.dedent("""\
            class OtherClass:
                pass
        """)

        tree = cst.parse_module(code)
        transformer = AddClassAttribute("MyClass", "x", "int", "42")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "x: int" not in result
        assert transformer.added is False


# =============================================================================
# RemoveClassAttribute Tests
# =============================================================================

class TestRemoveClassAttribute:
    """Tests for RemoveClassAttribute transformer."""

    def test_remove_simple_attribute(self):
        """
        RemoveClassAttribute should remove a class attribute.
        """
        code = textwrap.dedent("""\
            class MyClass:
                x = 42
        """)

        tree = cst.parse_module(code)
        transformer = RemoveClassAttribute("MyClass", "x")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "x = 42" not in result
        assert transformer.removed is True

    def test_remove_keeps_other_attributes(self):
        """
        RemoveClassAttribute should keep other attributes.
        """
        code = textwrap.dedent("""\
            class MyClass:
                x = 1
                y = 2
                z = 3
        """)

        tree = cst.parse_module(code)
        transformer = RemoveClassAttribute("MyClass", "y")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "x = 1" in result
        assert "y = 2" not in result
        assert "z = 3" in result

    def test_remove_attribute_not_found(self):
        """
        RemoveClassAttribute should not modify if attribute is not found.
        """
        code = textwrap.dedent("""\
            class MyClass:
                x = 42
        """)

        tree = cst.parse_module(code)
        transformer = RemoveClassAttribute("MyClass", "nonexistent")
        new_tree = tree.visit(transformer)

        result = new_tree.code
        assert "x = 42" in result
        assert transformer.removed is False
