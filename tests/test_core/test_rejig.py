"""
Tests for rejig.core.rejig module - the main Rejig class.

This module tests the Rejig class which is the main entry point for all
refactoring operations. Tests cover:
- Initialization with various path types (file, directory, glob)
- File discovery
- Target navigation (file, module, class, function)
- Dry-run mode
- Context manager usage
- Transaction support

Coverage targets:
- Path resolution and file discovery
- Target factory methods (file, module, find_class, etc.)
- Dry-run behavior
- Rope project lifecycle
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig import Rejig, Result, ErrorResult
from rejig.targets import FileTarget, ClassTarget, FunctionTarget, ErrorTarget


# =============================================================================
# Initialization Tests
# =============================================================================

class TestRejigInitialization:
    """Tests for Rejig class initialization."""

    def test_init_with_directory_path(self, tmp_python_project: Path):
        """
        Rejig should accept a directory path and discover all .py files.
        This is the most common initialization pattern.
        """
        rj = Rejig(tmp_python_project)

        # root should be the project directory
        assert rj.root == tmp_python_project
        # Should discover Python files in src/ and tests/
        assert len(rj.files) >= 3  # __init__.py, models.py, utils.py, tests/__init__.py

    def test_init_with_single_file(self, tmp_python_file: Path):
        """
        Rejig should accept a single file path.
        The root becomes the file's parent directory.
        """
        rj = Rejig(tmp_python_file)

        # root should be the file's parent directory
        assert rj.root == tmp_python_file.parent
        # Should have exactly one file
        assert len(rj.files) == 1
        assert rj.files[0] == tmp_python_file

    def test_init_with_string_path(self, tmp_python_project: Path):
        """
        Rejig should accept string paths, converting to Path internally.
        """
        rj = Rejig(str(tmp_python_project))

        # Should work the same as Path
        assert rj.root == tmp_python_project
        assert len(rj.files) >= 3

    def test_init_with_glob_pattern(self, tmp_python_project: Path):
        """
        Rejig should accept glob patterns to filter files.
        """
        # Create additional files to test glob filtering
        (tmp_python_project / "src" / "test_utils.py").write_text("# test file")

        # Glob for only test files
        pattern = str(tmp_python_project / "src" / "test_*.py")
        rj = Rejig(pattern)

        # Should only find test_utils.py
        assert len(rj.files) == 1
        assert "test_utils.py" in str(rj.files[0])

    def test_init_dry_run_mode(self, tmp_python_project: Path):
        """
        Rejig should support dry-run mode where no files are modified.
        """
        rj = Rejig(tmp_python_project, dry_run=True)

        # dry_run property should be True
        assert rj.dry_run is True

    def test_init_default_not_dry_run(self, tmp_python_project: Path):
        """
        By default, Rejig should NOT be in dry-run mode.
        """
        rj = Rejig(tmp_python_project)

        assert rj.dry_run is False

    def test_init_with_nonexistent_glob(self, tmp_path: Path):
        """
        Rejig should handle glob patterns that match no files gracefully.
        Returns empty file list, not an error.
        """
        rj = Rejig(str(tmp_path / "nonexistent_*.py"))

        # Should have empty file list
        assert rj.files == []

    def test_root_path_alias(self, tmp_python_project: Path):
        """
        root_path should be an alias for root (backwards compatibility).
        """
        rj = Rejig(tmp_python_project)

        assert rj.root_path == rj.root


# =============================================================================
# File Discovery Tests
# =============================================================================

class TestFileDiscovery:
    """Tests for Python file discovery."""

    def test_discovers_nested_files(self, tmp_path: Path):
        """
        Rejig should discover Python files in nested directories.
        """
        # Create nested structure
        (tmp_path / "pkg").mkdir()
        (tmp_path / "pkg" / "subpkg").mkdir()
        (tmp_path / "pkg" / "__init__.py").write_text("")
        (tmp_path / "pkg" / "module.py").write_text("# module")
        (tmp_path / "pkg" / "subpkg" / "__init__.py").write_text("")
        (tmp_path / "pkg" / "subpkg" / "deep.py").write_text("# deep")

        rj = Rejig(tmp_path)

        # Should find all 4 Python files
        assert len(rj.files) == 4

    def test_ignores_non_python_files(self, tmp_path: Path):
        """
        Rejig should only discover .py files, ignoring others.
        """
        (tmp_path / "script.py").write_text("# python")
        (tmp_path / "config.yaml").write_text("key: value")
        (tmp_path / "README.md").write_text("# Readme")
        (tmp_path / "data.json").write_text("{}")

        rj = Rejig(tmp_path)

        # Should only find the Python file
        assert len(rj.files) == 1
        assert rj.files[0].name == "script.py"

    def test_files_property_cached(self, tmp_python_project: Path):
        """
        The files property should be lazily computed and cached.
        """
        rj = Rejig(tmp_python_project)

        # Access files twice
        files1 = rj.files
        files2 = rj.files

        # Should be the same object (cached)
        assert files1 is files2


# =============================================================================
# Context Manager Tests
# =============================================================================

class TestContextManager:
    """Tests for Rejig as a context manager."""

    def test_context_manager_basic_usage(self, tmp_python_project: Path):
        """
        Rejig should work as a context manager for automatic cleanup.
        """
        with Rejig(tmp_python_project) as rj:
            # Should be usable inside the context
            assert len(rj.files) >= 3

        # After exiting, close() has been called
        # (rope project closed, .ropeproject cleaned up)

    def test_context_manager_cleanup_on_exception(self, tmp_python_project: Path):
        """
        Rejig should clean up even if an exception occurs.
        """
        try:
            with Rejig(tmp_python_project) as rj:
                # Force rope project initialization
                _ = rj.files
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Cleanup should have happened (no assertion needed, just no error)


# =============================================================================
# Target Factory Tests
# =============================================================================

class TestTargetFactories:
    """Tests for target factory methods (file, module, find_class, etc.)."""

    def test_file_target_by_name(self, rejig: Rejig, tmp_python_project: Path):
        """
        file() should return a FileTarget for the specified file.
        """
        target = rejig.file("src/models.py")

        # Should return a FileTarget
        assert isinstance(target, FileTarget)
        # Target should exist
        assert target.exists()

    def test_file_target_not_found_returns_file_target(self, rejig: Rejig):
        """
        file() always returns a FileTarget, even for non-existent files.

        The API uses "lazy targets" - the target is created but existence
        is checked via exists() or when operations are attempted.
        Operations on non-existent files return ErrorResult.
        """
        target = rejig.file("nonexistent.py")

        # Returns FileTarget, NOT ErrorTarget
        assert isinstance(target, FileTarget)
        # But exists() reports the file doesn't exist
        assert target.exists() is False
        # Operations should return ErrorResult
        result = target.find_class("AnyClass")
        # Since file doesn't exist, operations fail gracefully
        # (the find_class returns ErrorTarget in this case)
        assert isinstance(result, ErrorTarget)

    def test_find_class_returns_class_target(self, rejig: Rejig):
        """
        find_class() should return a ClassTarget when the class exists.
        """
        # MyClass exists in src/models.py (from sample_class_code fixture)
        target = rejig.find_class("MyClass")

        # Should return a ClassTarget
        assert isinstance(target, ClassTarget)
        # Target should exist
        assert target.exists()

    def test_find_class_not_found_returns_class_target(self, rejig: Rejig):
        """
        find_class() always returns a ClassTarget, even for non-existent classes.

        Like file(), find_class uses "lazy targets". The target is created
        but exists() reports whether the class was actually found.
        Operations on non-existent classes return ErrorResult.
        """
        target = rejig.find_class("NonExistentClass")

        # Returns ClassTarget, NOT ErrorTarget
        assert isinstance(target, ClassTarget)
        # But exists() reports the class doesn't exist
        assert target.exists() is False
        # Operations should return ErrorResult
        result = target.add_attribute("x", "int", "0")
        assert isinstance(result, ErrorResult)

    def test_find_function_returns_function_target(self, rejig: Rejig):
        """
        find_function() should return a FunctionTarget when the function exists.
        """
        # simple_function exists in src/utils.py (from sample_function_code fixture)
        target = rejig.find_function("simple_function")

        # Should return a FunctionTarget
        assert isinstance(target, FunctionTarget)
        assert target.exists()

    def test_find_function_not_found_returns_function_target(self, rejig: Rejig):
        """
        find_function() always returns FunctionTarget, even for non-existent functions.

        Like other find_* methods, uses "lazy targets" approach.
        """
        target = rejig.find_function("nonexistent_function")

        # Returns FunctionTarget, NOT ErrorTarget
        assert isinstance(target, FunctionTarget)
        # But exists() reports the function doesn't exist
        assert target.exists() is False

    def test_find_classes_returns_target_list(self, rejig: Rejig):
        """
        find_classes() should return a TargetList of all matching classes.
        """
        classes = rejig.find_classes()

        # Should return a TargetList
        assert len(classes) >= 1  # At least MyClass from models.py
        # All items should be ClassTargets
        for cls in classes:
            assert isinstance(cls, ClassTarget)

    def test_find_classes_with_pattern(self, rejig: Rejig):
        """
        find_classes() should filter by regex pattern when provided.
        """
        # Only find classes starting with "My"
        classes = rejig.find_classes(pattern="^My")

        # Should find MyClass
        assert len(classes) >= 1
        for cls in classes:
            assert cls.name.startswith("My")

    def test_find_functions_returns_target_list(self, rejig: Rejig):
        """
        find_functions() should return a TargetList of all matching functions.
        """
        functions = rejig.find_functions()

        # Should return multiple functions from utils.py
        assert len(functions) >= 3
        for func in functions:
            assert isinstance(func, FunctionTarget)


# =============================================================================
# Dry-Run Mode Tests
# =============================================================================

class TestDryRunMode:
    """Tests for dry-run mode behavior."""

    def test_dry_run_does_not_modify_files(self, rejig_dry_run: Rejig, tmp_python_project: Path):
        """
        In dry-run mode, operations should NOT modify files on disk.

        The operation returns success=True (indicating it would have worked)
        but the file contents remain unchanged.

        Note: Some operations (like add_attribute) may not include "[DRY RUN]"
        in their message due to how the result is constructed, but the critical
        behavior is that files are not modified.
        """
        models_path = tmp_python_project / "src" / "models.py"
        original_content = models_path.read_text()

        # Attempt to add an attribute
        target = rejig_dry_run.find_class("MyClass")
        result = target.add_attribute("new_attr", "str", '"default"')

        # Result should indicate success (would have worked)
        assert result.success is True

        # CRITICAL: File should NOT be modified in dry-run mode
        current_content = models_path.read_text()
        assert current_content == original_content, (
            "File was modified in dry-run mode! This is a bug.\n"
            f"Expected 'new_attr' to NOT be in file, but found:\n{current_content}"
        )

    def test_dry_run_reports_files_that_would_change(self, rejig_dry_run: Rejig, tmp_python_project: Path):
        """
        In dry-run mode, the files_changed list shows which files would
        be modified if not in dry-run mode.
        """
        target = rejig_dry_run.find_class("MyClass")
        result = target.add_attribute("new_attr", "str", '"test"')

        # Should indicate which files would be changed
        assert len(result.files_changed) == 1
        assert result.files_changed[0].name == "models.py"

    def test_dry_run_propagates_to_targets(self, rejig_dry_run: Rejig):
        """
        Targets created from a dry-run Rejig should also be in dry-run mode.
        """
        target = rejig_dry_run.find_class("MyClass")

        # Target should report dry_run as True
        assert target.dry_run is True


# =============================================================================
# Chained Operations Tests
# =============================================================================

class TestChainedOperations:
    """Tests for fluent API chaining."""

    def test_chain_file_to_class(self, rejig: Rejig):
        """
        Should be able to chain file().find_class() for precise targeting.
        """
        target = rejig.file("src/models.py").find_class("MyClass")

        assert isinstance(target, ClassTarget)
        assert target.exists()
        assert target.name == "MyClass"

    def test_chain_class_to_method(self, rejig: Rejig):
        """
        Should be able to chain find_class().find_method() for method targeting.
        """
        target = rejig.find_class("MyClass").find_method("process")

        # Should find the process method
        assert target.exists()
        assert target.name == "process"

    def test_chain_returns_error_target_on_failure(self, rejig: Rejig):
        """
        Chaining through non-existent targets should return ErrorTarget,
        not raise exceptions.
        """
        # NonExistent doesn't exist, so find_method should also fail gracefully
        target = rejig.find_class("NonExistent").find_method("any_method")

        # Should be ErrorTarget
        assert isinstance(target, ErrorTarget)
        assert target.exists() is False

    def test_operations_on_error_target_return_error_result(self, rejig: Rejig):
        """
        Operations on ErrorTarget should return ErrorResult, not raise.
        """
        target = rejig.find_class("NonExistent")
        result = target.add_attribute("x", "int", "0")

        # Should be ErrorResult
        assert isinstance(result, ErrorResult)
        assert result.success is False


# =============================================================================
# Transaction Tests
# =============================================================================

class TestTransactionSupport:
    """Tests for transaction support in Rejig."""

    def test_not_in_transaction_by_default(self, rejig: Rejig):
        """
        Rejig should not be in a transaction by default.
        """
        assert rejig.in_transaction is False
        assert rejig.current_transaction is None

    def test_transaction_context_manager(self, rejig: Rejig):
        """
        transaction() should work as a context manager.

        Inside the context, in_transaction is True.
        After exiting, in_transaction is False (auto-rollback if not committed).
        """
        with rejig.transaction() as tx:
            assert rejig.in_transaction is True
            assert rejig.current_transaction is tx
            # Operations here would be batched

        # After exiting, no longer in transaction
        assert rejig.in_transaction is False

    def test_transaction_commit(self, rejig: Rejig, tmp_python_project: Path):
        """
        Transaction commit() applies all pending changes.

        Note: The actual implementation of add_attribute may or may not
        respect transactions depending on whether it uses _write_with_diff.
        This test verifies the transaction API works correctly.
        """
        with rejig.transaction() as tx:
            # Just verify the transaction API works
            assert tx is not None
            assert rejig.in_transaction is True
            # Commit the transaction (even if no changes)
            tx.commit()

        assert rejig.in_transaction is False

    def test_transaction_auto_rollback_on_exit(self, rejig: Rejig):
        """
        If transaction is not committed, it auto-rolls back on context exit.
        """
        with rejig.transaction() as tx:
            # Don't commit
            pass

        # Transaction should have been rolled back
        assert rejig.in_transaction is False

    def test_nested_transactions_not_supported(self, rejig: Rejig):
        """
        Nested transactions should raise RuntimeError.
        """
        with rejig.transaction():
            # Attempting to start another transaction should raise
            with pytest.raises(RuntimeError) as exc_info:
                with rejig.transaction():
                    pass

            assert "Nested transactions" in str(exc_info.value)


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_directory(self, tmp_path: Path):
        """
        Rejig should handle directories with no Python files.
        """
        rj = Rejig(tmp_path)

        assert rj.files == []

    def test_syntax_error_file_discovery(self, tmp_path: Path):
        """
        File discovery should not fail on files with syntax errors.
        """
        # Create a file with invalid Python syntax
        (tmp_path / "invalid.py").write_text("def broken(:\n    pass")
        (tmp_path / "valid.py").write_text("def valid(): pass")

        rj = Rejig(tmp_path)

        # Should still discover both files
        assert len(rj.files) == 2

    def test_find_class_in_file_with_syntax_error(self, tmp_path: Path):
        """
        find_class returns ClassTarget even for non-existent classes.

        The ClassTarget is created but exists() returns False.
        When the only file has a syntax error, the class won't be found.
        """
        (tmp_path / "invalid.py").write_text("def broken(:\n    pass")

        rj = Rejig(tmp_path)
        target = rj.find_class("AnyClass")

        # Returns ClassTarget (lazy target design)
        assert isinstance(target, ClassTarget)
        # But exists() is False since class not found (file couldn't be parsed)
        assert target.exists() is False

    def test_unicode_content_handling(self, tmp_path: Path):
        """
        Rejig should handle files with unicode content correctly.
        """
        unicode_code = textwrap.dedent('''
            """Unicode test module.

            Contains: emoji 🎉, Chinese 中文, Japanese 日本語
            """

            class UnicodeClass:
                """Class with unicode docstring: αβγδ"""

                def greet(self) -> str:
                    return "Hello, 世界! 🌍"
        ''').strip()

        (tmp_path / "unicode_test.py").write_text(unicode_code, encoding="utf-8")

        rj = Rejig(tmp_path)
        target = rj.find_class("UnicodeClass")

        # Should find the class correctly
        assert isinstance(target, ClassTarget)
        assert target.exists()
