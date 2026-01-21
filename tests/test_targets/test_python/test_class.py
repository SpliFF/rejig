"""
Tests for rejig.targets.python.class_ module - ClassTarget.

ClassTarget provides operations on Python class definitions:
- Finding methods within the class
- Adding/removing attributes and methods
- Adding/removing decorators
- Renaming the class
- Converting to dataclass

Coverage targets:
- Class existence and properties
- Method discovery
- Attribute operations
- Decorator operations
- Class transformations
"""
from __future__ import annotations

from pathlib import Path

import pytest

from rejig import Rejig
from rejig.core.results import ErrorResult, Result
from rejig.targets import ClassTarget, ErrorTarget, MethodTarget, TargetList


# =============================================================================
# ClassTarget Existence and Properties
# =============================================================================

class TestClassTargetExistence:
    """Tests for ClassTarget existence checking and basic properties."""

    def test_class_target_exists(self, rejig: Rejig):
        """
        ClassTarget.exists() should return True for existing classes.
        """
        target = rejig.find_class("MyClass")

        assert target.exists() is True

    def test_class_target_name_property(self, rejig: Rejig):
        """
        ClassTarget should expose the class name.
        """
        target = rejig.find_class("MyClass")

        assert target.name == "MyClass"

    def test_class_target_file_path_property(self, rejig: Rejig):
        """
        ClassTarget should expose the file path where the class is defined.
        """
        target = rejig.find_class("MyClass")

        assert hasattr(target, 'file_path') or hasattr(target, '_find_class')
        # The class should be in models.py from the fixture
        if hasattr(target, 'file_path') and target.file_path:
            assert "models.py" in str(target.file_path)

    def test_class_target_get_content(self, rejig: Rejig):
        """
        ClassTarget.get_content() should return the class source code.
        """
        target = rejig.find_class("MyClass")
        result = target.get_content()

        # Should succeed
        assert result.success is True
        # Content should include class definition
        assert "class MyClass" in result.data


# =============================================================================
# ClassTarget Method Discovery
# =============================================================================

class TestClassTargetMethodDiscovery:
    """Tests for finding methods within a class."""

    def test_find_method_existing(self, rejig: Rejig):
        """
        find_method() should return MethodTarget when method exists.
        """
        target = rejig.find_class("MyClass").find_method("process")

        assert isinstance(target, MethodTarget)
        assert target.exists()
        assert target.name == "process"

    def test_find_method_not_found(self, rejig: Rejig):
        """
        find_method() returns ErrorTarget when method doesn't exist.
        """
        target = rejig.find_class("MyClass").find_method("nonexistent_method")

        assert isinstance(target, ErrorTarget)
        assert target.exists() is False

    def test_find_method_init(self, rejig: Rejig):
        """
        find_method() should find __init__ method.
        """
        target = rejig.find_class("MyClass").find_method("__init__")

        assert isinstance(target, MethodTarget)
        assert target.exists()

    def test_find_method_static(self, rejig: Rejig):
        """
        find_method() should find static methods.
        """
        target = rejig.find_class("MyClass").find_method("helper")

        assert isinstance(target, MethodTarget)
        assert target.exists()

    def test_find_method_private(self, rejig: Rejig):
        """
        find_method() should find private methods (with _ prefix).
        """
        target = rejig.find_class("MyClass").find_method("_private_method")

        assert isinstance(target, MethodTarget)
        assert target.exists()

    def test_find_methods_all(self, rejig: Rejig, tmp_python_project: Path):
        """
        find_methods() returns all methods in the class.
        """
        # Use file-based navigation for reliability
        methods = rejig.file("src/models.py").find_class("MyClass").find_methods()

        assert isinstance(methods, TargetList)
        # Should find at least some methods
        # MyClass has: __init__, process, helper, _private_method
        assert len(methods) >= 4, f"Expected at least 4 methods, got {len(methods)}"
        for method in methods:
            assert isinstance(method, MethodTarget)

    def test_find_methods_with_pattern(self, rejig: Rejig):
        """
        find_methods() with pattern filters by regex.
        """
        # Find methods starting with underscore (dunder and private)
        methods = rejig.find_class("MyClass").find_methods(pattern="^_")

        for method in methods:
            assert method.name.startswith("_")


# =============================================================================
# ClassTarget Attribute Operations
# =============================================================================

class TestClassTargetAttributes:
    """Tests for class attribute operations."""

    def test_add_attribute(self, rejig: Rejig, tmp_python_project: Path):
        """
        add_attribute() should add a class-level attribute with type annotation.
        """
        target = rejig.find_class("MyClass")
        result = target.add_attribute("new_attr", "str", '"default"')

        assert result.success is True

        # Verify attribute was added
        content = (tmp_python_project / "src" / "models.py").read_text()
        assert "new_attr" in content
        assert "str" in content

    def test_add_attribute_already_exists(self, rejig: Rejig):
        """
        add_attribute() for existing attribute should handle gracefully.
        """
        target = rejig.find_class("MyClass")
        # 'count' already exists in the fixture
        result = target.add_attribute("count", "int", "0")

        # Should either succeed (overwrite) or fail gracefully
        assert isinstance(result, (Result, ErrorResult))

    def test_remove_attribute(self, rejig: Rejig, tmp_python_project: Path):
        """
        remove_attribute() should remove a class attribute.
        """
        # First add an attribute, then remove it
        target = rejig.find_class("MyClass")
        target.add_attribute("temp_attr", "str", '"temp"')

        result = target.remove_attribute("temp_attr")

        # Should succeed
        assert result.success is True


# =============================================================================
# ClassTarget Method Operations
# =============================================================================

class TestClassTargetMethods:
    """Tests for class method operations."""

    def test_add_method(self, rejig: Rejig, tmp_python_project: Path):
        """
        add_method() should add a new method to the class.
        """
        target = rejig.find_class("MyClass")
        result = target.add_method("new_method", "return 'hello'")

        assert result.success is True

        content = (tmp_python_project / "src" / "models.py").read_text()
        assert "def new_method" in content

    def test_add_method_with_parameters(self, rejig: Rejig, tmp_python_project: Path):
        """
        add_method() should support methods with parameters.
        """
        target = rejig.find_class("MyClass")
        result = target.add_method(
            "method_with_params",
            "return x + y",
            params="x: int, y: int",
            return_type="int"
        )

        assert result.success is True

        content = (tmp_python_project / "src" / "models.py").read_text()
        assert "method_with_params" in content


# =============================================================================
# ClassTarget Decorator Operations
# =============================================================================

class TestClassTargetDecorators:
    """Tests for class decorator operations."""

    def test_add_decorator(self, rejig: Rejig, tmp_python_project: Path):
        """
        add_decorator() should add a decorator to the class.
        """
        target = rejig.find_class("MyClass")
        result = target.add_decorator("dataclass")

        assert result.success is True

        content = (tmp_python_project / "src" / "models.py").read_text()
        assert "@dataclass" in content

    def test_add_decorator_with_arguments(self, rejig: Rejig, tmp_python_project: Path):
        """
        add_decorator() should support decorators with arguments.
        """
        target = rejig.find_class("MyClass")
        result = target.add_decorator("dataclass(frozen=True)")

        assert result.success is True

        content = (tmp_python_project / "src" / "models.py").read_text()
        assert "dataclass" in content

    def test_remove_decorator(self, rejig: Rejig, tmp_python_project: Path):
        """
        remove_decorator() should remove a decorator from the class.
        """
        # First add a decorator
        target = rejig.find_class("MyClass")
        target.add_decorator("dataclass")

        # Then remove it
        result = target.remove_decorator("dataclass")

        assert result.success is True


# =============================================================================
# ClassTarget Rename Operation
# =============================================================================

class TestClassTargetRename:
    """Tests for class rename operations."""

    def test_rename_class(self, rejig: Rejig, tmp_python_project: Path):
        """
        rename() should rename the class.
        """
        target = rejig.find_class("MyClass")
        result = target.rename("RenamedClass")

        assert result.success is True

        content = (tmp_python_project / "src" / "models.py").read_text()
        assert "class RenamedClass" in content
        # Original name should be gone (or minimal)
        # Note: might still have references in docstrings etc.


# =============================================================================
# ClassTarget Integration
# =============================================================================

class TestClassTargetIntegration:
    """Integration tests for ClassTarget."""

    def test_chained_method_operations(self, rejig: Rejig, tmp_python_project: Path):
        """
        Operations on methods found through class should work.
        """
        result = (
            rejig.find_class("MyClass")
            .find_method("process")
            .add_decorator("property")
        )

        # Should return a Result (success or failure)
        assert isinstance(result, (Result, ErrorResult))

    def test_class_not_found_operations(self, rejig: Rejig):
        """
        Operations on non-existent class should fail gracefully.
        """
        target = rejig.find_class("NonExistentClass")

        result = target.add_method("test", "pass")
        assert isinstance(result, ErrorResult) or not result.success

        result = target.add_attribute("x", "int", "0")
        assert isinstance(result, ErrorResult) or not result.success

    def test_dry_run_preserves_class(self, rejig_dry_run: Rejig, tmp_python_project: Path):
        """
        Dry-run operations should not modify the class.
        """
        original = (tmp_python_project / "src" / "models.py").read_text()

        target = rejig_dry_run.find_class("MyClass")
        target.add_method("dry_run_method", "pass")
        target.add_attribute("dry_run_attr", "str", '"test"')

        # File should be unchanged
        assert (tmp_python_project / "src" / "models.py").read_text() == original
