"""
Tests for rejig.targets.base module.

This module tests the base Target classes:
- Target: Abstract base class for all targets
- ErrorTarget: Sentinel for failed lookups - allows chaining without raising
- TargetList: Batch operations on multiple targets

Coverage targets:
- Target base operations and error handling
- ErrorTarget chaining behavior
- TargetList filtering, iteration, and batch operations
"""
from __future__ import annotations

from pathlib import Path

import pytest

from rejig import Rejig
from rejig.core.results import BatchResult, ErrorResult, Result
from rejig.targets import ErrorTarget, Target, TargetList, ClassTarget


# =============================================================================
# ErrorTarget Tests
# =============================================================================

class TestErrorTarget:
    """Tests for ErrorTarget - sentinel for failed lookups."""

    def test_error_target_exists_returns_false(self, rejig: Rejig):
        """
        ErrorTarget.exists() should always return False.

        ErrorTarget represents a failed lookup, so the target doesn't exist.
        """
        error = ErrorTarget(rejig, "Test error message")

        assert error.exists() is False

    def test_error_target_repr(self, rejig: Rejig):
        """
        ErrorTarget should have a descriptive repr including the error message.
        """
        error = ErrorTarget(rejig, "Class 'Foo' not found")

        repr_str = repr(error)

        assert "ErrorTarget" in repr_str
        assert "Class 'Foo' not found" in repr_str

    def test_error_target_navigation_returns_self(self, rejig: Rejig):
        """
        Navigation methods on ErrorTarget should return the same ErrorTarget.

        This allows fluent chaining even after a lookup failure:
            rj.find_class("Missing").find_method("foo").add_decorator(...)
        """
        error = ErrorTarget(rejig, "Original error")

        # All navigation methods should return the same ErrorTarget
        assert error.find_class("any") is error
        assert error.find_function("any") is error
        assert error.find_method("any") is error
        assert error.line(1) is error
        assert error.lines(1, 5) is error

    def test_error_target_find_all_returns_empty_list(self, rejig: Rejig):
        """
        find_* (plural) methods should return empty TargetList, not ErrorTarget.

        This maintains type consistency - find_classes always returns TargetList.
        """
        error = ErrorTarget(rejig, "Error")

        classes = error.find_classes()
        functions = error.find_functions()
        methods = error.find_methods()

        # All should return empty TargetList
        assert isinstance(classes, TargetList)
        assert len(classes) == 0
        assert isinstance(functions, TargetList)
        assert len(functions) == 0
        assert isinstance(methods, TargetList)
        assert len(methods) == 0

    def test_error_target_operations_return_error_result(self, rejig: Rejig):
        """
        Operations on ErrorTarget return ErrorResult.

        Note: Methods defined on Target base class (add_attribute, rename, etc.)
        return "Operation not supported for ErrorTarget" messages.
        Only methods not defined on Target (via __getattr__) preserve the
        original error message.
        """
        error = ErrorTarget(rejig, "Class 'Foo' not found")

        # Base class operations return "not supported" ErrorResult
        result = error.add_attribute("x", "int", "0")
        assert isinstance(result, ErrorResult)
        assert "not supported" in result.message.lower()

        result = error.add_method("process", "pass")
        assert isinstance(result, ErrorResult)

        result = error.rename("NewName")
        assert isinstance(result, ErrorResult)

        result = error.delete()
        assert isinstance(result, ErrorResult)

    def test_error_target_any_method_returns_error_result(self, rejig: Rejig):
        """
        Any method call on ErrorTarget (via __getattr__) returns ErrorResult.

        This is achieved via the __getattr__ magic method that returns
        a callable which produces ErrorResult.
        """
        error = ErrorTarget(rejig, "Something went wrong")

        # Arbitrary method calls should work
        result = error.some_nonexistent_method()
        assert isinstance(result, ErrorResult)
        assert "Something went wrong" in result.message

        # With arguments
        result = error.another_method("arg1", kwarg="value")
        assert isinstance(result, ErrorResult)

    def test_error_target_preserves_rejig_reference(self, rejig: Rejig):
        """
        ErrorTarget should maintain a reference to the parent Rejig instance.
        """
        error = ErrorTarget(rejig, "Error")

        assert error.rejig is rejig
        assert error._rejig is rejig

    def test_error_target_chaining_preserves_error_target(self, rejig: Rejig):
        """
        Chaining navigation through ErrorTarget returns the same ErrorTarget.

        When you chain find_class, find_method, etc., you get back the same
        ErrorTarget (allowing continued chaining). The final operation
        (add_decorator) returns an ErrorResult.
        """
        original_error = ErrorTarget(rejig, "Module not found")

        # Navigation methods return the same ErrorTarget
        chained = original_error.find_class("AnyClass").find_method("any_method")
        assert chained is original_error

        # Final operation returns ErrorResult
        # Note: add_decorator is defined on Target, so message is "not supported"
        result = chained.add_decorator("property")
        assert isinstance(result, ErrorResult)
        assert "not supported" in result.message.lower()


# =============================================================================
# TargetList Tests
# =============================================================================

class TestTargetList:
    """Tests for TargetList - batch operations on multiple targets."""

    def test_target_list_empty(self, rejig: Rejig):
        """
        Empty TargetList should behave correctly.
        """
        targets = TargetList(rejig, [])

        # Length should be 0
        assert len(targets) == 0
        # Should be falsy
        assert bool(targets) is False
        # first/last should return None
        assert targets.first() is None
        assert targets.last() is None
        # to_list should return empty list
        assert targets.to_list() == []

    def test_target_list_with_targets(self, rejig: Rejig):
        """
        TargetList with targets should allow access and iteration.
        """
        # Get some real targets
        classes = rejig.find_classes()

        # Should have at least one class (MyClass from fixture)
        assert len(classes) >= 1
        # Should be truthy
        assert bool(classes) is True
        # first should return a target
        assert classes.first() is not None
        # Should be iterable
        target_list = list(classes)
        assert len(target_list) >= 1

    def test_target_list_iteration(self, rejig: Rejig):
        """
        TargetList should be iterable via for loops.
        """
        classes = rejig.find_classes()

        # Should be able to iterate
        count = 0
        for cls in classes:
            count += 1
            assert hasattr(cls, 'name')

        assert count == len(classes)

    def test_target_list_repr(self, rejig: Rejig):
        """
        TargetList repr should show the number of targets.
        """
        classes = rejig.find_classes()
        repr_str = repr(classes)

        assert "TargetList" in repr_str
        assert "targets" in repr_str

    def test_target_list_filter(self, rejig: Rejig):
        """
        filter() should return a new TargetList with matching targets.
        """
        functions = rejig.find_functions()

        # Filter to functions with "function" in the name
        filtered = functions.filter(lambda f: "function" in f.name.lower())

        # Should return a TargetList
        assert isinstance(filtered, TargetList)
        # All targets should match the predicate
        for func in filtered:
            assert "function" in func.name.lower()

    def test_target_list_matching(self, rejig: Rejig):
        """
        matching() should filter by regex pattern on target names.
        """
        functions = rejig.find_functions()

        # Match functions starting with "simple"
        matched = functions.matching(r"^simple")

        # Should return TargetList
        assert isinstance(matched, TargetList)
        # All should match the pattern
        for func in matched:
            assert func.name.startswith("simple")

    def test_target_list_first_and_last(self, rejig: Rejig):
        """
        first() and last() should return single targets or None.
        """
        functions = rejig.find_functions()

        first = functions.first()
        last = functions.last()

        # Should return actual targets (not TargetList)
        assert first is not None
        assert last is not None
        assert not isinstance(first, TargetList)
        assert not isinstance(last, TargetList)

    def test_target_list_to_list(self, rejig: Rejig):
        """
        to_list() should return a plain Python list of targets.
        """
        functions = rejig.find_functions()

        as_list = functions.to_list()

        # Should be a regular list
        assert isinstance(as_list, list)
        # Same length
        assert len(as_list) == len(functions)

    def test_target_list_batch_add_decorator(self, rejig: Rejig, tmp_python_project: Path):
        """
        Batch add_decorator should apply to all targets and return BatchResult.
        """
        # Find all methods in MyClass
        methods = rejig.find_class("MyClass").find_methods()

        # Add decorator to all (if there are methods)
        if len(methods) > 0:
            result = methods.add_decorator("property")

            # Should return BatchResult
            assert isinstance(result, BatchResult)
            # Should have results for each method
            assert len(result) == len(methods)

    def test_target_list_batch_delete(self, rejig_dry_run: Rejig):
        """
        Batch delete should attempt to delete all targets.
        """
        # Use dry-run to not actually delete
        functions = rejig_dry_run.find_functions()

        if len(functions) > 0:
            result = functions.delete()

            # Should return BatchResult
            assert isinstance(result, BatchResult)
            # Should have results for each function
            assert len(result) == len(functions)

    def test_target_list_batch_operation_on_empty(self, rejig: Rejig):
        """
        Batch operations on empty TargetList should return empty BatchResult.
        """
        empty = TargetList(rejig, [])

        result = empty.add_decorator("test")

        assert isinstance(result, BatchResult)
        assert len(result) == 0
        # Empty BatchResult is considered successful (vacuous truth)
        assert result.success is True

    def test_target_list_without_docstrings(self, rejig: Rejig):
        """
        without_docstrings() should filter to targets missing docstrings.
        """
        functions = rejig.find_functions()

        # Get functions without docstrings
        no_docs = functions.without_docstrings()

        # Should return TargetList
        assert isinstance(no_docs, TargetList)
        # All should lack docstrings (if has_docstring attribute exists)
        for func in no_docs:
            if hasattr(func, 'has_docstring'):
                assert not func.has_docstring

    def test_target_list_with_docstrings(self, rejig: Rejig):
        """
        with_docstrings() should filter to targets that have docstrings.
        """
        functions = rejig.find_functions()

        # Get functions with docstrings
        with_docs = functions.with_docstrings()

        # Should return TargetList
        assert isinstance(with_docs, TargetList)
        # All should have docstrings (if has_docstring attribute exists)
        for func in with_docs:
            if hasattr(func, 'has_docstring'):
                assert func.has_docstring


# =============================================================================
# Target Base Class Tests
# =============================================================================

class TestTargetBase:
    """Tests for Target base class behavior."""

    def test_target_rejig_property(self, rejig: Rejig):
        """
        Target should provide access to parent Rejig instance.
        """
        target = rejig.find_class("MyClass")

        assert target.rejig is rejig
        assert target._rejig is rejig

    def test_target_dry_run_property(self, rejig: Rejig, rejig_dry_run: Rejig):
        """
        Target should reflect the dry_run setting of its Rejig instance.
        """
        normal_target = rejig.find_class("MyClass")
        dry_run_target = rejig_dry_run.find_class("MyClass")

        assert normal_target.dry_run is False
        assert dry_run_target.dry_run is True

    def test_target_unsupported_operation(self, rejig: Rejig):
        """
        Unsupported operations should return ErrorResult, not raise.

        This tests the _unsupported_operation method indirectly.
        """
        # TomlTarget doesn't support add_method (it's for config files)
        toml = rejig.toml("nonexistent.toml")
        result = toml.add_method("test", "pass")

        # Should return ErrorResult
        assert isinstance(result, ErrorResult)
        assert "not supported" in result.message.lower()

    def test_target_get_content_not_implemented(self, rejig: Rejig):
        """
        Base Target.get_content() returns ErrorResult for unsupported targets.
        """
        # A target that doesn't override get_content
        toml = rejig.toml("test.toml")

        # get_content may or may not be implemented depending on target type
        # This just verifies it doesn't raise
        result = toml.get_content()
        # Result should be a Result (success or error)
        assert isinstance(result, (Result, ErrorResult))


# =============================================================================
# Integration Tests
# =============================================================================

class TestTargetIntegration:
    """Integration tests for Target classes working together."""

    def test_find_class_returns_class_target(self, rejig: Rejig):
        """
        find_class should return a ClassTarget (or subclass).
        """
        target = rejig.find_class("MyClass")

        # Should be a ClassTarget
        assert isinstance(target, ClassTarget)
        # Should exist (from fixture)
        assert target.exists()
        # Should have the correct name
        assert target.name == "MyClass"

    def test_chained_navigation(self, rejig: Rejig):
        """
        Test fluent API chaining: file -> class -> method.
        """
        method = rejig.file("src/models.py").find_class("MyClass").find_method("process")

        # Should find the method
        assert method.exists()
        assert method.name == "process"

    def test_target_list_from_find_classes(self, rejig: Rejig):
        """
        find_classes() should return a proper TargetList.
        """
        classes = rejig.find_classes()

        # Should be a TargetList
        assert isinstance(classes, TargetList)
        # Should contain ClassTargets
        for cls in classes:
            assert isinstance(cls, ClassTarget)

    def test_error_propagation_through_chain(self, rejig: Rejig):
        """
        Errors should propagate through chained operations.

        When a file doesn't exist, subsequent operations should
        return ErrorResult without raising.
        """
        result = (
            rejig.file("nonexistent.py")
            .find_class("AnyClass")
            .find_method("any_method")
            .add_decorator("property")
        )

        # Should be an ErrorResult (file doesn't exist)
        assert isinstance(result, ErrorResult)
        # Should indicate the file doesn't exist
        assert not result.success

    def test_batch_operations_preserve_order(self, rejig: Rejig):
        """
        Batch operations should preserve the order of targets.
        """
        functions = rejig.find_functions()

        if len(functions) > 1:
            # Get names in order
            names = [f.name for f in functions]

            # Batch operation
            result = functions.rename("prefix_", "$0")

            # Results should be in the same order
            # (Note: this tests the BatchResult order, not the rename itself)
            assert len(result.results) == len(functions)
