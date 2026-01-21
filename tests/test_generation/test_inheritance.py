"""
Tests for rejig.generation.inheritance module.

This module tests inheritance operations:
- AddBaseClassTransformer
- RemoveBaseClassTransformer
- AddMixinTransformer
"""
from __future__ import annotations

import textwrap

import libcst as cst
import pytest

from rejig.generation.inheritance import (
    AddBaseClassTransformer,
    AddMixinTransformer,
    RemoveBaseClassTransformer,
)


# =============================================================================
# AddBaseClassTransformer Tests
# =============================================================================

class TestAddBaseClassTransformer:
    """Tests for AddBaseClassTransformer."""

    def test_adds_base_class_to_class_without_bases(self):
        """Should add base class to a class with no bases."""
        code = textwrap.dedent('''\
            class MyClass:
                pass
        ''')

        tree = cst.parse_module(code)
        transformer = AddBaseClassTransformer("MyClass", "BaseClass")
        modified = tree.visit(transformer)

        result = modified.code
        assert "class MyClass(BaseClass)" in result
        assert transformer.added is True

    def test_adds_base_class_to_existing_bases(self):
        """Should add base class to a class with existing bases."""
        code = textwrap.dedent('''\
            class MyClass(ExistingBase):
                pass
        ''')

        tree = cst.parse_module(code)
        transformer = AddBaseClassTransformer("MyClass", "NewBase")
        modified = tree.visit(transformer)

        result = modified.code
        assert "ExistingBase" in result
        assert "NewBase" in result
        assert transformer.added is True

    def test_adds_base_class_at_beginning(self):
        """Should add base class at the beginning when position='first'."""
        code = textwrap.dedent('''\
            class MyClass(ExistingBase):
                pass
        ''')

        tree = cst.parse_module(code)
        transformer = AddBaseClassTransformer("MyClass", "NewBase", position="first")
        modified = tree.visit(transformer)

        result = modified.code
        # NewBase should appear before ExistingBase
        new_pos = result.find("NewBase")
        existing_pos = result.find("ExistingBase")
        assert new_pos < existing_pos
        assert transformer.added is True

    def test_adds_base_class_at_end(self):
        """Should add base class at the end when position='last'."""
        code = textwrap.dedent('''\
            class MyClass(ExistingBase):
                pass
        ''')

        tree = cst.parse_module(code)
        transformer = AddBaseClassTransformer("MyClass", "NewBase", position="last")
        modified = tree.visit(transformer)

        result = modified.code
        # NewBase should appear after ExistingBase
        new_pos = result.find("NewBase")
        existing_pos = result.find("ExistingBase")
        assert new_pos > existing_pos
        assert transformer.added is True

    def test_handles_module_path_base(self):
        """Should handle base class with module path."""
        code = textwrap.dedent('''\
            class MyClass:
                pass
        ''')

        tree = cst.parse_module(code)
        transformer = AddBaseClassTransformer("MyClass", "abc.ABC")
        modified = tree.visit(transformer)

        result = modified.code
        assert "abc.ABC" in result
        assert transformer.added is True

    def test_skips_if_base_already_exists(self):
        """Should not add base class if it already exists."""
        code = textwrap.dedent('''\
            class MyClass(BaseClass):
                pass
        ''')

        tree = cst.parse_module(code)
        transformer = AddBaseClassTransformer("MyClass", "BaseClass")
        modified = tree.visit(transformer)

        assert transformer.added is False

    def test_targets_specific_class(self):
        """Should only modify the target class."""
        code = textwrap.dedent('''\
            class MyClass:
                pass

            class OtherClass:
                pass
        ''')

        tree = cst.parse_module(code)
        transformer = AddBaseClassTransformer("MyClass", "NewBase")
        modified = tree.visit(transformer)

        result = modified.code
        # Only MyClass should have NewBase
        assert "class MyClass(NewBase)" in result
        assert "class OtherClass:" in result  # OtherClass unchanged
        assert transformer.added is True


# =============================================================================
# RemoveBaseClassTransformer Tests
# =============================================================================

class TestRemoveBaseClassTransformer:
    """Tests for RemoveBaseClassTransformer."""

    def test_removes_base_class(self):
        """Should remove the specified base class."""
        code = textwrap.dedent('''\
            class MyClass(BaseToRemove):
                pass
        ''')

        tree = cst.parse_module(code)
        transformer = RemoveBaseClassTransformer("MyClass", "BaseToRemove")
        modified = tree.visit(transformer)

        result = modified.code
        assert "BaseToRemove" not in result
        assert transformer.removed is True

    def test_removes_one_of_multiple_bases(self):
        """Should remove only the specified base class."""
        code = textwrap.dedent('''\
            class MyClass(Base1, BaseToRemove, Base2):
                pass
        ''')

        tree = cst.parse_module(code)
        transformer = RemoveBaseClassTransformer("MyClass", "BaseToRemove")
        modified = tree.visit(transformer)

        result = modified.code
        assert "Base1" in result
        assert "Base2" in result
        assert "BaseToRemove" not in result
        assert transformer.removed is True

    def test_removes_module_path_base(self):
        """Should remove base class with module path."""
        code = textwrap.dedent('''\
            class MyClass(abc.ABC, OtherBase):
                pass
        ''')

        tree = cst.parse_module(code)
        transformer = RemoveBaseClassTransformer("MyClass", "abc.ABC")
        modified = tree.visit(transformer)

        result = modified.code
        assert "abc.ABC" not in result
        assert "OtherBase" in result
        assert transformer.removed is True

    def test_not_removed_when_not_present(self):
        """Should not modify if base class is not present."""
        code = textwrap.dedent('''\
            class MyClass(OtherBase):
                pass
        ''')

        tree = cst.parse_module(code)
        transformer = RemoveBaseClassTransformer("MyClass", "NonExistentBase")
        modified = tree.visit(transformer)

        assert transformer.removed is False

    def test_targets_specific_class(self):
        """Should only modify the target class."""
        code = textwrap.dedent('''\
            class MyClass(BaseClass):
                pass

            class OtherClass(BaseClass):
                pass
        ''')

        tree = cst.parse_module(code)
        transformer = RemoveBaseClassTransformer("MyClass", "BaseClass")
        modified = tree.visit(transformer)

        result = modified.code
        # BaseClass should be removed from MyClass but not OtherClass
        assert "class OtherClass(BaseClass)" in result
        assert transformer.removed is True


# =============================================================================
# AddMixinTransformer Tests
# =============================================================================

class TestAddMixinTransformer:
    """Tests for AddMixinTransformer."""

    def test_adds_mixin_to_class(self):
        """Should add mixin to a class."""
        code = textwrap.dedent('''\
            class MyClass:
                pass
        ''')

        tree = cst.parse_module(code)
        transformer = AddMixinTransformer("MyClass", "LoggingMixin")
        modified = tree.visit(transformer)

        result = modified.code
        assert "LoggingMixin" in result
        assert transformer.added is True

    def test_adds_mixin_at_beginning(self):
        """Mixin should be added at the beginning of bases (MRO convention)."""
        code = textwrap.dedent('''\
            class MyClass(BaseClass):
                pass
        ''')

        tree = cst.parse_module(code)
        transformer = AddMixinTransformer("MyClass", "LoggingMixin")
        modified = tree.visit(transformer)

        result = modified.code
        # Mixin should come before BaseClass
        mixin_pos = result.find("LoggingMixin")
        base_pos = result.find("BaseClass")
        assert mixin_pos < base_pos
        assert transformer.added is True

    def test_adds_multiple_mixins_in_order(self):
        """Multiple mixins should be added in correct order."""
        code = textwrap.dedent('''\
            class MyClass(BaseClass):
                pass
        ''')

        tree = cst.parse_module(code)

        # Add first mixin
        transformer1 = AddMixinTransformer("MyClass", "Mixin1")
        tree = tree.visit(transformer1)

        # Add second mixin (should go before Mixin1)
        transformer2 = AddMixinTransformer("MyClass", "Mixin2")
        tree = tree.visit(transformer2)

        result = tree.code
        # Order should be: Mixin2, Mixin1, BaseClass
        mixin2_pos = result.find("Mixin2")
        mixin1_pos = result.find("Mixin1")
        base_pos = result.find("BaseClass")
        assert mixin2_pos < mixin1_pos < base_pos

    def test_skips_if_mixin_already_exists(self):
        """Should not add mixin if it already exists."""
        code = textwrap.dedent('''\
            class MyClass(LoggingMixin, BaseClass):
                pass
        ''')

        tree = cst.parse_module(code)
        transformer = AddMixinTransformer("MyClass", "LoggingMixin")
        modified = tree.visit(transformer)

        assert transformer.added is False

    def test_targets_specific_class(self):
        """Should only add mixin to the target class."""
        code = textwrap.dedent('''\
            class MyClass:
                pass

            class OtherClass:
                pass
        ''')

        tree = cst.parse_module(code)
        transformer = AddMixinTransformer("MyClass", "LoggingMixin")
        modified = tree.visit(transformer)

        result = modified.code
        assert "class MyClass(LoggingMixin)" in result
        assert "class OtherClass:" in result  # OtherClass unchanged
        assert transformer.added is True


# =============================================================================
# Integration Tests
# =============================================================================

class TestInheritanceIntegration:
    """Integration tests for inheritance operations."""

    def test_add_and_remove_base(self):
        """Should be able to add and then remove a base class."""
        code = textwrap.dedent('''\
            class MyClass:
                pass
        ''')

        tree = cst.parse_module(code)

        # Add base class
        add = AddBaseClassTransformer("MyClass", "NewBase")
        tree = tree.visit(add)
        assert add.added is True

        # Remove it
        remove = RemoveBaseClassTransformer("MyClass", "NewBase")
        tree = tree.visit(remove)
        assert remove.removed is True

        result = tree.code
        assert "NewBase" not in result

    def test_build_inheritance_chain(self):
        """Should be able to build complex inheritance."""
        code = textwrap.dedent('''\
            class MyClass:
                pass
        ''')

        tree = cst.parse_module(code)

        # Add base class
        add_base = AddBaseClassTransformer("MyClass", "BaseClass")
        tree = tree.visit(add_base)

        # Add mixin
        add_mixin = AddMixinTransformer("MyClass", "LoggingMixin")
        tree = tree.visit(add_mixin)

        # Add another mixin
        add_mixin2 = AddMixinTransformer("MyClass", "CachingMixin")
        tree = tree.visit(add_mixin2)

        result = tree.code
        # Should have all bases in MRO order
        assert "CachingMixin" in result
        assert "LoggingMixin" in result
        assert "BaseClass" in result

    def test_replace_base_class(self):
        """Should be able to replace a base class."""
        code = textwrap.dedent('''\
            class MyClass(OldBase):
                pass
        ''')

        tree = cst.parse_module(code)

        # Remove old base
        remove = RemoveBaseClassTransformer("MyClass", "OldBase")
        tree = tree.visit(remove)

        # Add new base
        add = AddBaseClassTransformer("MyClass", "NewBase")
        tree = tree.visit(add)

        result = tree.code
        assert "OldBase" not in result
        assert "NewBase" in result

    def test_valid_python_after_operations(self):
        """All inheritance operations should produce valid Python."""
        code = textwrap.dedent('''\
            class Service:
                def run(self):
                    pass
        ''')

        tree = cst.parse_module(code)

        # Add multiple bases
        transformer1 = AddBaseClassTransformer("Service", "BaseService")
        tree = tree.visit(transformer1)

        transformer2 = AddMixinTransformer("Service", "LoggingMixin")
        tree = tree.visit(transformer2)

        result = tree.code
        # Should parse without error
        cst.parse_module(result)
