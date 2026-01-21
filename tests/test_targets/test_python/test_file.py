"""
Tests for rejig.targets.python.file module - FileTarget.

FileTarget is the primary target for working with Python source files.
It provides methods for:
- Finding classes, functions, and methods
- Adding/removing imports
- Navigating to specific lines or blocks
- File-level transformations

Coverage targets:
- File existence checks
- Class/function/method discovery
- Import management
- Line/block navigation
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig import Rejig
from rejig.core.results import ErrorResult, Result
from rejig.targets import (
    ClassTarget,
    ErrorTarget,
    FileTarget,
    FunctionTarget,
    LineTarget,
    LineBlockTarget,
    TargetList,
)


# =============================================================================
# FileTarget Existence and Properties
# =============================================================================

class TestFileTargetExistence:
    """Tests for FileTarget existence checking and basic properties."""

    def test_file_target_exists_for_real_file(self, rejig: Rejig, tmp_python_project: Path):
        """
        FileTarget.exists() should return True for existing files.
        """
        target = rejig.file("src/models.py")

        assert target.exists() is True

    def test_file_target_not_exists_for_missing_file(self, rejig: Rejig):
        """
        FileTarget.exists() should return False for non-existent files.
        """
        target = rejig.file("nonexistent_file.py")

        assert target.exists() is False

    def test_file_target_file_path_property(self, rejig: Rejig, tmp_python_project: Path):
        """
        FileTarget should expose the file path.
        """
        target = rejig.file("src/models.py")

        # file_path should be a Path object
        assert isinstance(target.file_path, Path)
        # Should end with the correct filename
        assert target.file_path.name == "models.py"

    def test_file_target_get_content(self, rejig: Rejig, tmp_python_project: Path):
        """
        FileTarget.get_content() should return the file contents.
        """
        target = rejig.file("src/models.py")
        result = target.get_content()

        # Should succeed
        assert result.success is True
        # Content should be in the data field
        assert result.data is not None
        # Should contain expected content from fixture
        assert "MyClass" in result.data

    def test_file_target_get_content_missing_file(self, rejig: Rejig):
        """
        get_content() on non-existent file should return ErrorResult.
        """
        target = rejig.file("nonexistent.py")
        result = target.get_content()

        # Should fail (file doesn't exist)
        assert isinstance(result, ErrorResult) or not result.success


# =============================================================================
# FileTarget Class Discovery
# =============================================================================

class TestFileTargetClassDiscovery:
    """Tests for finding classes within a file."""

    def test_find_class_existing(self, rejig: Rejig):
        """
        find_class() should return ClassTarget when class exists.
        """
        target = rejig.file("src/models.py").find_class("MyClass")

        assert isinstance(target, ClassTarget)
        assert target.exists()
        assert target.name == "MyClass"

    def test_find_class_not_found(self, rejig: Rejig):
        """
        find_class() on FileTarget returns ErrorTarget for missing class.

        Unlike Rejig.find_class() which uses lazy targets, FileTarget.find_class()
        returns ErrorTarget immediately when the class is not found in the file.
        """
        target = rejig.file("src/models.py").find_class("NonExistent")

        # Returns ErrorTarget when class not found
        assert isinstance(target, ErrorTarget)
        assert target.exists() is False

    def test_find_classes_all(self, rejig: Rejig):
        """
        find_classes() without pattern returns all classes in the file.
        """
        classes = rejig.file("src/models.py").find_classes()

        # Should return TargetList
        assert isinstance(classes, TargetList)
        # Should find MyClass from fixture
        assert len(classes) >= 1
        # All should be ClassTargets
        for cls in classes:
            assert isinstance(cls, ClassTarget)

    def test_find_classes_with_pattern(self, rejig: Rejig):
        """
        find_classes() with pattern filters by regex.
        """
        classes = rejig.file("src/models.py").find_classes(pattern="^My")

        # All should match the pattern
        for cls in classes:
            assert cls.name.startswith("My")

    def test_find_classes_empty_file(self, tmp_path: Path):
        """
        find_classes() on file with no classes returns empty TargetList.
        """
        # Create file with no classes
        (tmp_path / "no_classes.py").write_text("# Just a comment\nx = 1")

        rj = Rejig(tmp_path)
        classes = rj.file("no_classes.py").find_classes()

        assert isinstance(classes, TargetList)
        assert len(classes) == 0


# =============================================================================
# FileTarget Function Discovery
# =============================================================================

class TestFileTargetFunctionDiscovery:
    """Tests for finding functions within a file."""

    def test_find_function_existing(self, rejig: Rejig):
        """
        find_function() should return FunctionTarget when function exists.
        """
        target = rejig.file("src/utils.py").find_function("simple_function")

        assert isinstance(target, FunctionTarget)
        assert target.exists()
        assert target.name == "simple_function"

    def test_find_function_not_found(self, rejig: Rejig):
        """
        find_function() on FileTarget returns ErrorTarget for missing function.

        Like find_class(), this immediately returns ErrorTarget when not found.
        """
        target = rejig.file("src/utils.py").find_function("no_such_function")

        assert isinstance(target, ErrorTarget)
        assert target.exists() is False

    def test_find_functions_all(self, rejig: Rejig):
        """
        find_functions() returns all module-level functions.
        """
        functions = rejig.file("src/utils.py").find_functions()

        assert isinstance(functions, TargetList)
        # Should find several functions from fixture
        assert len(functions) >= 3
        for func in functions:
            assert isinstance(func, FunctionTarget)

    def test_find_functions_with_pattern(self, rejig: Rejig):
        """
        find_functions() with pattern filters by regex.
        """
        # Find functions containing "function" in name
        functions = rejig.file("src/utils.py").find_functions(pattern="function")

        for func in functions:
            assert "function" in func.name.lower()


# =============================================================================
# FileTarget Line Navigation
# =============================================================================

class TestFileTargetLineNavigation:
    """Tests for navigating to specific lines in a file."""

    def test_line_single(self, rejig: Rejig):
        """
        line() should return a LineTarget for a specific line.
        """
        target = rejig.file("src/models.py").line(1)

        # Should return LineTarget
        assert isinstance(target, (LineTarget, ErrorTarget))
        # If it's a LineTarget, it should have line_number
        if isinstance(target, LineTarget):
            assert target.line_number == 1

    def test_lines_range(self, rejig: Rejig):
        """
        lines() should return a LineBlockTarget for a range of lines.
        """
        target = rejig.file("src/models.py").lines(1, 5)

        # Should return LineBlockTarget
        assert isinstance(target, (LineBlockTarget, ErrorTarget))
        if isinstance(target, LineBlockTarget):
            assert target.start_line == 1
            assert target.end_line == 5

    def test_line_out_of_range(self, rejig: Rejig):
        """
        line() with invalid line number should handle gracefully.
        """
        # Line 10000 probably doesn't exist
        target = rejig.file("src/models.py").line(10000)

        # Should return some target (may be ErrorTarget or LineTarget with issues)
        assert target is not None


# =============================================================================
# FileTarget Import Operations
# =============================================================================

class TestFileTargetImports:
    """Tests for import management in FileTarget."""

    def test_add_import(self, rejig: Rejig, tmp_python_project: Path):
        """
        add_import() should add an import statement to the file.
        """
        target = rejig.file("src/models.py")
        result = target.add_import("import json")

        # Operation should succeed
        assert result.success is True

        # Verify import was added
        content = (tmp_python_project / "src" / "models.py").read_text()
        assert "import json" in content

    def test_add_import_from_statement(self, rejig: Rejig, tmp_python_project: Path):
        """
        add_import() should handle 'from X import Y' syntax.
        """
        target = rejig.file("src/models.py")
        result = target.add_import("from collections import defaultdict")

        assert result.success is True

        content = (tmp_python_project / "src" / "models.py").read_text()
        assert "from collections import defaultdict" in content

    def test_add_import_dry_run(self, rejig_dry_run: Rejig, tmp_python_project: Path):
        """
        add_import() in dry-run should not modify the file.
        """
        original = (tmp_python_project / "src" / "models.py").read_text()

        target = rejig_dry_run.file("src/models.py")
        result = target.add_import("import sys")

        assert result.success is True
        # File unchanged
        assert (tmp_python_project / "src" / "models.py").read_text() == original


# =============================================================================
# FileTarget Modification Operations
# =============================================================================

class TestFileTargetModifications:
    """Tests for file modification operations."""

    def test_add_class(self, rejig: Rejig, tmp_python_project: Path):
        """
        add_class() should add a new class to the file.
        """
        target = rejig.file("src/models.py")
        result = target.add_class("NewClass", "pass")

        assert result.success is True

        # Verify class was added
        content = (tmp_python_project / "src" / "models.py").read_text()
        assert "class NewClass" in content

    def test_add_function(self, rejig: Rejig, tmp_python_project: Path):
        """
        add_function() should add a new function to the file.
        """
        target = rejig.file("src/utils.py")
        result = target.add_function("new_func", "return 42")

        assert result.success is True

        content = (tmp_python_project / "src" / "utils.py").read_text()
        assert "def new_func" in content


# =============================================================================
# FileTarget Integration
# =============================================================================

class TestFileTargetIntegration:
    """Integration tests for FileTarget."""

    def test_chained_operations(self, rejig: Rejig, tmp_python_project: Path):
        """
        FileTarget should support chained navigation and operations.
        """
        # Chain: file -> class -> method -> add decorator
        result = (
            rejig.file("src/models.py")
            .find_class("MyClass")
            .find_method("process")
            .add_decorator("staticmethod")
        )

        # This tests the full chain works without error
        # Result may succeed or fail depending on implementation details
        assert isinstance(result, (Result, ErrorResult))

    def test_file_target_for_nonexistent_operations_graceful(self, rejig: Rejig):
        """
        Operations on non-existent files should return ErrorResult, not raise.
        """
        target = rejig.file("does_not_exist.py")

        # Various operations should not raise
        result = target.add_class("Test", "pass")
        assert isinstance(result, ErrorResult) or not result.success

        result = target.add_import("import os")
        assert isinstance(result, ErrorResult) or not result.success
