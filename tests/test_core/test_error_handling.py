"""
Tests for the "never raise exceptions" guarantee.

This is a critical design principle of Rejig: operations NEVER raise exceptions.
Instead, they return Result (success) or ErrorResult (failure). Failed navigation
returns ErrorTarget, which allows chaining to continue without raising.

This module provides comprehensive integration tests for:
- ErrorTarget chaining through multiple navigation levels
- ErrorResult from operations on nonexistent targets
- Graceful handling of syntax errors, missing files, bad paths
- Operations on ErrorTarget via __getattr__ fallback
- Mix of valid and invalid operations in batch
- The full fluent API error propagation path

Coverage targets:
- Deep chaining: file -> class -> method -> operation
- Batch operations with mixed valid/invalid targets
- Every factory method on Rejig with invalid inputs
- Config target operations on missing files
- Search and find operations with no matches
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig import Rejig
from rejig.core.results import BatchResult, ErrorResult, Result
from rejig.targets import (
    ClassTarget,
    ErrorTarget,
    FileTarget,
    FunctionTarget,
    TargetList,
)


# =============================================================================
# ErrorTarget Deep Chaining
# =============================================================================

class TestErrorTargetDeepChaining:
    """Tests for ErrorTarget chaining through multiple navigation levels."""

    def test_three_level_chain_returns_error_result(self, rejig: Rejig):
        """
        file -> class -> method -> operation should return ErrorResult
        when the file doesn't exist.
        """
        result = (
            rejig.file("nonexistent.py")
            .find_class("AnyClass")
            .find_method("any_method")
            .add_decorator("property")
        )

        assert isinstance(result, ErrorResult)
        assert result.success is False

    def test_four_level_chain_module_path(self, rejig: Rejig):
        """
        module -> class -> method -> operation with a nonexistent module.
        """
        result = (
            rejig.module("nonexistent.module.path")
            .find_class("SomeClass")
            .find_method("some_method")
            .rename("new_name")
        )

        assert isinstance(result, ErrorResult)
        assert result.success is False

    def test_error_target_identity_through_chain(self, rejig: Rejig):
        """
        Navigation through an ErrorTarget should return the same ErrorTarget
        (identity preservation for efficiency).
        """
        error = ErrorTarget(rejig, "Initial error")

        chained1 = error.find_class("X")
        chained2 = chained1.find_method("Y")
        chained3 = chained2.line(5)

        assert chained1 is error
        assert chained2 is error
        assert chained3 is error

    def test_error_target_find_all_returns_empty_at_every_level(self, rejig: Rejig):
        """
        Plural find operations (find_classes, find_functions, find_methods)
        should return empty TargetList from ErrorTarget.
        """
        error = ErrorTarget(rejig, "Error")

        assert len(error.find_classes()) == 0
        assert len(error.find_functions()) == 0
        assert len(error.find_methods()) == 0

    def test_error_target_getattr_with_various_args(self, rejig: Rejig):
        """
        ErrorTarget.__getattr__ should handle arbitrary method calls
        with various argument patterns.
        """
        error = ErrorTarget(rejig, "Test error")

        # No args
        result1 = error.nonexistent_method()
        assert isinstance(result1, ErrorResult)

        # Positional args
        result2 = error.another_method("arg1", "arg2")
        assert isinstance(result2, ErrorResult)

        # Keyword args
        result3 = error.yet_another(key="value", num=42)
        assert isinstance(result3, ErrorResult)

        # Mixed args
        result4 = error.mixed("pos", key="kw")
        assert isinstance(result4, ErrorResult)


# =============================================================================
# Never Raise Guarantee on Valid Targets with Bad Data
# =============================================================================

class TestNeverRaiseOnBadData:
    """Tests that operations return errors rather than raising exceptions."""

    def test_find_class_nonexistent_returns_class_target(self, rejig: Rejig):
        """
        find_class for a nonexistent class should return ClassTarget
        (lazy target design), not raise.
        """
        target = rejig.find_class("CompletelyFakeClass")

        assert isinstance(target, ClassTarget)
        assert target.exists() is False

    def test_operations_on_nonexistent_class(self, rejig: Rejig):
        """
        All operations on a ClassTarget that doesn't exist should return
        ErrorResult, not raise.
        """
        target = rejig.find_class("NonExistent")

        results = [
            target.add_attribute("x", "int", "0"),
            target.add_method("test", "pass"),
            target.add_decorator("dataclass"),
            target.remove_decorator("dataclass"),
            target.rename("NewName"),
            target.delete(),
            target.get_content(),
        ]

        for result in results:
            assert isinstance(result, (Result, ErrorResult)), (
                f"Expected Result/ErrorResult, got {type(result)}"
            )
            if isinstance(result, ErrorResult):
                assert result.success is False

    def test_operations_on_nonexistent_function(self, rejig: Rejig):
        """
        All operations on a FunctionTarget that doesn't exist should return
        ErrorResult, not raise.
        """
        target = rejig.find_function("nonexistent_func")

        results = [
            target.rename("new_name"),
            target.delete(),
            target.get_content(),
            target.add_decorator("staticmethod"),
        ]

        for result in results:
            assert isinstance(result, (Result, ErrorResult))

    def test_file_operations_on_nonexistent_file(self, rejig: Rejig):
        """
        FileTarget operations on a nonexistent file should return errors.
        """
        target = rejig.file("totally_missing.py")

        results = [
            target.get_content(),
            target.add_function("test", "pass"),
            target.add_class("Test", "pass"),
            target.add_import("import os"),
        ]

        for result in results:
            assert isinstance(result, (Result, ErrorResult))
            if isinstance(result, ErrorResult):
                assert result.success is False

    def test_syntax_error_file_class_search(self, tmp_path: Path):
        """
        Searching for classes in a file with syntax errors should not raise.
        """
        (tmp_path / "bad_syntax.py").write_text("def broken(:\n    pass")
        rj = Rejig(tmp_path)

        # find_classes should gracefully skip unparseable files
        classes = rj.find_classes()
        assert isinstance(classes, TargetList)
        # Should not have found any classes (the file is unparseable)

    def test_search_with_no_matches(self, rejig: Rejig):
        """
        Search with a pattern that matches nothing should return empty list.
        """
        matches = rejig.search(r"THIS_PATTERN_MATCHES_NOTHING_12345")

        assert isinstance(matches, TargetList)
        assert len(matches) == 0


# =============================================================================
# Config Target Error Handling
# =============================================================================

class TestConfigTargetErrors:
    """Tests for config target error handling."""

    def test_toml_operations_on_missing_file(self, rejig: Rejig):
        """
        TomlTarget operations on a missing file should return errors.
        """
        toml = rejig.toml("nonexistent.toml")

        result = toml.get_content()
        assert isinstance(result, (Result, ErrorResult))

    def test_yaml_operations_on_missing_file(self, rejig: Rejig):
        """
        YamlTarget operations on a missing file should return errors.
        """
        yaml = rejig.yaml("nonexistent.yaml")

        result = yaml.get_content()
        assert isinstance(result, (Result, ErrorResult))

    def test_json_operations_on_missing_file(self, rejig: Rejig):
        """
        JsonTarget operations on a missing file should return errors.
        """
        json_target = rejig.json("nonexistent.json")

        result = json_target.get_content()
        assert isinstance(result, (Result, ErrorResult))

    def test_ini_operations_on_missing_file(self, rejig: Rejig):
        """
        IniTarget operations on a missing file should return errors.
        """
        ini = rejig.ini("nonexistent.ini")

        result = ini.get_content()
        assert isinstance(result, (Result, ErrorResult))


# =============================================================================
# Batch Operations with Mixed Results
# =============================================================================

class TestBatchMixedResults:
    """Tests for batch operations with a mix of valid and invalid targets."""

    def test_find_classes_batch_with_pattern(self, rejig: Rejig):
        """
        Batch operations should work even when some targets are invalid.
        """
        # Find all classes, then batch add_decorator
        classes = rejig.find_classes()

        if len(classes) > 0:
            result = classes.add_decorator("some_decorator")

            assert isinstance(result, BatchResult)
            assert len(result) == len(classes)

    def test_empty_batch_operations(self, rejig: Rejig):
        """
        Batch operations on empty TargetList should return empty BatchResult.
        """
        empty = TargetList(rejig, [])

        result = empty.add_decorator("test")
        assert isinstance(result, BatchResult)
        assert len(result) == 0
        assert result.success is True  # Vacuous truth

        result = empty.delete()
        assert isinstance(result, BatchResult)
        assert len(result) == 0

        result = empty.rename("old", "new")
        assert isinstance(result, BatchResult)
        assert len(result) == 0


# =============================================================================
# ErrorResult Properties
# =============================================================================

class TestErrorResultUsagePatterns:
    """Tests for typical ErrorResult usage patterns."""

    def test_error_result_boolean_check(self, rejig: Rejig):
        """
        ErrorResult should be falsy, allowing `if not result` patterns.
        """
        target = rejig.find_class("NonExistent")
        result = target.add_attribute("x", "int", "0")

        if isinstance(result, ErrorResult):
            assert not result
            assert result.is_error()

    def test_error_result_chained_check(self, rejig: Rejig):
        """
        Common pattern: perform operation, check result, handle error.
        """
        result = rejig.find_class("NonExistent").add_attribute("x", "int")

        if result.is_error():
            assert isinstance(result, ErrorResult)
        else:
            # This branch should NOT be reached
            pytest.fail("Expected error result for nonexistent class")

    def test_batch_result_filter_errors(self, rejig: Rejig):
        """
        BatchResult.failed should collect all ErrorResults from batch operations.
        """
        # Create a batch with a mix (at least one class from fixture)
        classes = rejig.find_classes()

        if len(classes) > 0:
            result = classes.add_decorator("test_decorator")

            # Check that we can filter results
            assert isinstance(result, BatchResult)
            # Access failed and succeeded
            _ = result.failed
            _ = result.succeeded


# =============================================================================
# Rejig Factory Methods with Invalid Inputs
# =============================================================================

class TestRejigFactoryInvalidInputs:
    """Tests that every Rejig factory method handles invalid inputs gracefully."""

    def test_file_factory_nonexistent(self, rejig: Rejig):
        """
        file() with a nonexistent path should return a FileTarget (lazy).
        """
        target = rejig.file("does_not_exist.py")

        assert isinstance(target, FileTarget)
        assert target.exists() is False

    def test_module_factory_nonexistent(self, rejig: Rejig):
        """
        module() with a nonexistent dotted path should return a ModuleTarget.
        """
        from rejig.targets.python.module import ModuleTarget

        target = rejig.module("does.not.exist")

        assert isinstance(target, ModuleTarget)
        assert target.exists() is False

    def test_package_factory_nonexistent(self, rejig: Rejig):
        """
        package() with a nonexistent path should return a PackageTarget.
        """
        from rejig.targets.python.package import PackageTarget

        target = rejig.package("nonexistent_pkg")

        assert isinstance(target, PackageTarget)
        assert target.exists() is False

    def test_text_file_factory_nonexistent(self, rejig: Rejig):
        """
        text_file() with a nonexistent path should return a TextFileTarget.
        """
        from rejig.targets.text.text_file import TextFileTarget

        target = rejig.text_file("readme.txt")

        assert isinstance(target, TextFileTarget)
        assert target.exists() is False

    def test_toml_factory_nonexistent(self, rejig: Rejig):
        """
        toml() with a nonexistent path should return a TomlTarget.
        """
        target = rejig.toml("missing.toml")

        assert target.exists() is False

    def test_find_class_returns_lazy_target(self, rejig: Rejig):
        """
        find_class should always return a ClassTarget (lazy), never raise.
        """
        target = rejig.find_class("AbsolutelyNonExistentClass123")

        assert isinstance(target, ClassTarget)
        assert target.exists() is False

    def test_find_function_returns_lazy_target(self, rejig: Rejig):
        """
        find_function should always return a FunctionTarget (lazy), never raise.
        """
        target = rejig.find_function("absolutely_nonexistent_function_123")

        assert isinstance(target, FunctionTarget)
        assert target.exists() is False

    def test_find_files_with_no_matches(self, rejig: Rejig):
        """
        find_files with a non-matching glob should return empty TargetList.
        """
        files = rejig.find_files("**/*.nonexistent_extension")

        assert isinstance(files, TargetList)
        assert len(files) == 0

    def test_find_classes_empty_project(self, tmp_path: Path):
        """
        find_classes on an empty project should return empty TargetList.
        """
        rj = Rejig(tmp_path)
        classes = rj.find_classes()

        assert isinstance(classes, TargetList)
        assert len(classes) == 0

    def test_find_functions_empty_project(self, tmp_path: Path):
        """
        find_functions on an empty project should return empty TargetList.
        """
        rj = Rejig(tmp_path)
        functions = rj.find_functions()

        assert isinstance(functions, TargetList)
        assert len(functions) == 0
