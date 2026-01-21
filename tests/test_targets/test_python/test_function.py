"""
Tests for rejig.targets.python.function module.

This module tests FunctionTarget for module-level Python functions:
- Finding and locating functions
- Getting function content
- Modifying function parameters
- Adding/removing decorators
- Renaming and deleting functions
- Type hint operations
- Dry run mode

FunctionTarget provides operations for module-level functions (not methods).
Methods should use MethodTarget instead.

Coverage targets:
- exists() for existing and non-existing functions
- get_content() retrieval
- Parameter operations (add, remove, rename)
- Decorator operations (add, remove)
- rename() and delete()
- Type hint operations
- Dry run mode
- Error handling for missing functions
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig import Rejig


# =============================================================================
# FunctionTarget Basic Tests
# =============================================================================

class TestFunctionTargetBasic:
    """Tests for basic FunctionTarget operations."""

    @pytest.fixture
    def python_file(self, tmp_path: Path) -> Path:
        """Create a sample Python file with module-level functions."""
        content = textwrap.dedent('''\
            """Sample module with functions."""

            def simple_function():
                """A simple function."""
                pass

            def function_with_params(x, y, z=10):
                """Function with parameters."""
                result = x + y + z
                return result

            def function_with_types(name: str, count: int = 0) -> list[str]:
                """Function with type hints."""
                return [name] * count

            @property
            def decorated_function():
                """A decorated function."""
                return 42

            class SomeClass:
                def method_not_function(self):
                    """This is a method, not a module-level function."""
                    pass
        ''')
        file_path = tmp_path / "sample.py"
        file_path.write_text(content)
        return file_path

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_function_exists(self, rejig: Rejig, python_file: Path):
        """
        FunctionTarget.exists() should return True for existing functions.

        This verifies that FunctionTarget can locate module-level functions
        defined in the file.
        """
        target = rejig.file(python_file).find_function("simple_function")
        assert target.exists() is True

    def test_function_not_exists(self, rejig: Rejig, python_file: Path):
        """
        FunctionTarget.exists() should return False for non-existing functions.

        The lazy target API creates targets even for non-existent functions,
        but exists() should correctly report False.
        """
        target = rejig.file(python_file).find_function("nonexistent_function")
        assert target.exists() is False

    def test_function_with_params_exists(self, rejig: Rejig, python_file: Path):
        """
        FunctionTarget should work with functions that have parameters.
        """
        target = rejig.file(python_file).find_function("function_with_params")
        assert target.exists() is True

    def test_get_content(self, rejig: Rejig, python_file: Path):
        """
        get_content() should return the full source code of the function.

        The returned data should include the function definition, docstring,
        and body.
        """
        target = rejig.file(python_file).find_function("function_with_params")
        result = target.get_content()

        assert result.success is True
        assert "def function_with_params" in result.data
        assert "result = x + y + z" in result.data
        assert "return result" in result.data

    def test_get_content_missing_function(self, rejig: Rejig, python_file: Path):
        """
        get_content() should return failure for non-existing functions.

        When a function doesn't exist, find_function() returns an ErrorTarget
        which returns ErrorResult for all operations.
        """
        target = rejig.file(python_file).find_function("nonexistent")
        result = target.get_content()

        assert result.success is False
        # Error could be "not found" or "ErrorTarget" depending on how target was created
        assert "not found" in result.message.lower() or "errortarget" in result.message.lower()

    def test_function_line_number(self, rejig: Rejig, python_file: Path):
        """
        FunctionTarget should provide the line number of the function.

        Line numbers are 1-indexed.
        """
        target = rejig.file(python_file).find_function("simple_function")

        # The function should be found with a valid line number
        assert target.exists() is True
        assert target.line_number is not None
        assert target.line_number > 0

    def test_function_repr(self, rejig: Rejig, python_file: Path):
        """
        FunctionTarget should have a useful string representation.
        """
        target = rejig.file(python_file).find_function("simple_function")
        target.exists()  # Ensure file_path is set

        repr_str = repr(target)
        assert "FunctionTarget" in repr_str
        assert "simple_function" in repr_str


# =============================================================================
# FunctionTarget Parameter Operations
# =============================================================================

class TestFunctionTargetParameters:
    """Tests for FunctionTarget parameter operations."""

    @pytest.fixture
    def python_file(self, tmp_path: Path) -> Path:
        """Create a Python file for parameter tests."""
        content = textwrap.dedent('''\
            def my_function(x, y):
                return x + y

            def no_params():
                return 42
        ''')
        file_path = tmp_path / "params.py"
        file_path.write_text(content)
        return file_path

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_add_parameter(self, rejig: Rejig, python_file: Path):
        """
        add_parameter() should add a parameter to the function signature.

        By default, parameters are added at the end.
        """
        target = rejig.file(python_file).find_function("my_function")
        result = target.add_parameter("z")

        assert result.success is True

        # Verify the parameter was added
        content = python_file.read_text()
        assert "def my_function(x, y, z):" in content

    def test_add_parameter_with_type(self, rejig: Rejig, python_file: Path):
        """
        add_parameter() should support type annotations.
        """
        target = rejig.file(python_file).find_function("my_function")
        result = target.add_parameter("count", type_annotation="int")

        assert result.success is True

        content = python_file.read_text()
        assert "count: int" in content

    def test_add_parameter_with_default(self, rejig: Rejig, python_file: Path):
        """
        add_parameter() should support default values.
        """
        target = rejig.file(python_file).find_function("my_function")
        result = target.add_parameter("flag", default_value="True")

        assert result.success is True

        content = python_file.read_text()
        # Check for flag with default (may or may not have spaces around =)
        assert "flag" in content
        assert "True" in content

    def test_add_parameter_to_empty_function(self, rejig: Rejig, python_file: Path):
        """
        add_parameter() should work with functions that have no parameters.
        """
        target = rejig.file(python_file).find_function("no_params")
        result = target.add_parameter("value")

        assert result.success is True

        content = python_file.read_text()
        assert "def no_params(value):" in content

    def test_remove_parameter(self, rejig: Rejig, python_file: Path):
        """
        remove_parameter() should remove a parameter from the function signature.
        """
        target = rejig.file(python_file).find_function("my_function")
        result = target.remove_parameter("y")

        assert result.success is True

        content = python_file.read_text()
        assert "def my_function(x):" in content

    def test_remove_parameter_not_found(self, rejig: Rejig, python_file: Path):
        """
        remove_parameter() should fail for non-existing parameters.
        """
        target = rejig.file(python_file).find_function("my_function")
        result = target.remove_parameter("nonexistent")

        assert result.success is False
        assert "not found" in result.message.lower()


# =============================================================================
# FunctionTarget Decorator Operations
# =============================================================================

class TestFunctionTargetDecorators:
    """Tests for FunctionTarget decorator operations."""

    @pytest.fixture
    def python_file(self, tmp_path: Path) -> Path:
        """Create a Python file for decorator tests."""
        content = textwrap.dedent('''\
            def plain_function():
                return 42

            @staticmethod
            def decorated_function():
                return 100
        ''')
        file_path = tmp_path / "decorators.py"
        file_path.write_text(content)
        return file_path

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_add_decorator(self, rejig: Rejig, python_file: Path):
        """
        add_decorator() should add a decorator to the function.

        The decorator is added without the @ prefix (it's added automatically).
        """
        target = rejig.file(python_file).find_function("plain_function")
        result = target.add_decorator("timing")

        assert result.success is True

        content = python_file.read_text()
        assert "@timing" in content

    def test_add_decorator_with_args(self, rejig: Rejig, python_file: Path):
        """
        add_decorator() should support decorators with arguments.
        """
        target = rejig.file(python_file).find_function("plain_function")
        result = target.add_decorator("lru_cache(maxsize=128)")

        assert result.success is True

        content = python_file.read_text()
        assert "@lru_cache(maxsize=128)" in content

    def test_remove_decorator(self, rejig: Rejig, python_file: Path):
        """
        remove_decorator() should remove a decorator from the function.
        """
        target = rejig.file(python_file).find_function("decorated_function")
        result = target.remove_decorator("staticmethod")

        assert result.success is True

        content = python_file.read_text()
        # staticmethod should be removed
        assert "@staticmethod" not in content
        # But the function should still exist
        assert "def decorated_function" in content

    def test_remove_decorator_not_found(self, rejig: Rejig, python_file: Path):
        """
        remove_decorator() should fail for non-existing decorators.
        """
        target = rejig.file(python_file).find_function("plain_function")
        result = target.remove_decorator("nonexistent")

        assert result.success is False


# =============================================================================
# FunctionTarget Rename and Delete
# =============================================================================

class TestFunctionTargetRenameDelete:
    """Tests for FunctionTarget rename and delete operations."""

    @pytest.fixture
    def python_file(self, tmp_path: Path) -> Path:
        """Create a Python file for rename/delete tests."""
        content = textwrap.dedent('''\
            def old_function():
                return "old"

            def other_function():
                return "other"
        ''')
        file_path = tmp_path / "rename.py"
        file_path.write_text(content)
        return file_path

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_rename_function(self, rejig: Rejig, python_file: Path):
        """
        rename() should rename the function definition.

        Note: This only renames the definition, not call sites.
        """
        target = rejig.file(python_file).find_function("old_function")
        result = target.rename("new_function")

        assert result.success is True

        content = python_file.read_text()
        assert "def new_function" in content
        assert "def old_function" not in content

    def test_rename_updates_target_name(self, rejig: Rejig, python_file: Path):
        """
        After rename(), the target's name attribute should be updated.
        """
        target = rejig.file(python_file).find_function("old_function")
        assert target.name == "old_function"

        target.rename("new_function")

        assert target.name == "new_function"

    def test_delete_function(self, rejig: Rejig, python_file: Path):
        """
        delete() should remove the function from the file entirely.
        """
        target = rejig.file(python_file).find_function("old_function")
        result = target.delete()

        assert result.success is True

        content = python_file.read_text()
        assert "def old_function" not in content
        # other_function should still exist
        assert "def other_function" in content

    def test_delete_nonexistent_function(self, rejig: Rejig, python_file: Path):
        """
        delete() should fail for non-existing functions.

        When a function doesn't exist, find_function() returns an ErrorTarget
        which returns ErrorResult for all operations.
        """
        target = rejig.file(python_file).find_function("nonexistent")
        result = target.delete()

        assert result.success is False
        # Error could be "not found" or "ErrorTarget" depending on how target was created
        assert "not found" in result.message.lower() or "errortarget" in result.message.lower()


# =============================================================================
# FunctionTarget Type Hint Operations
# =============================================================================

class TestFunctionTargetTypeHints:
    """Tests for FunctionTarget type hint operations."""

    @pytest.fixture
    def python_file(self, tmp_path: Path) -> Path:
        """Create a Python file for type hint tests."""
        content = textwrap.dedent('''\
            def no_types(x, y):
                return x + y

            def with_types(x: int, y: int) -> int:
                return x + y
        ''')
        file_path = tmp_path / "types.py"
        file_path.write_text(content)
        return file_path

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_set_return_type(self, rejig: Rejig, python_file: Path):
        """
        set_return_type() should add a return type annotation.
        """
        target = rejig.file(python_file).find_function("no_types")
        result = target.set_return_type("int")

        assert result.success is True

        content = python_file.read_text()
        assert "-> int:" in content

    def test_set_parameter_type(self, rejig: Rejig, python_file: Path):
        """
        set_parameter_type() should add a type annotation to a parameter.
        """
        target = rejig.file(python_file).find_function("no_types")
        result = target.set_parameter_type("x", "float")

        assert result.success is True

        content = python_file.read_text()
        assert "x: float" in content


# =============================================================================
# FunctionTarget Insert Statement
# =============================================================================

class TestFunctionTargetInsertStatement:
    """Tests for FunctionTarget insert_statement operation."""

    @pytest.fixture
    def python_file(self, tmp_path: Path) -> Path:
        """Create a Python file for insert tests."""
        content = textwrap.dedent('''\
            def my_function(x):
                result = x * 2
                return result
        ''')
        file_path = tmp_path / "insert.py"
        file_path.write_text(content)
        return file_path

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_insert_statement_at_start(self, rejig: Rejig, python_file: Path):
        """
        insert_statement() with position="start" should insert at the beginning.

        The statement is inserted after any docstring but before other code.
        """
        target = rejig.file(python_file).find_function("my_function")
        result = target.insert_statement("print('entering')")

        assert result.success is True

        content = python_file.read_text()
        assert "print('entering')" in content
        # Should be before result = x * 2
        assert content.index("print('entering')") < content.index("result = x * 2")

    def test_insert_statement_at_end(self, rejig: Rejig, python_file: Path):
        """
        insert_statement() with position="end" should insert at the end.
        """
        target = rejig.file(python_file).find_function("my_function")
        result = target.insert_statement("print('exiting')", position="end")

        assert result.success is True

        content = python_file.read_text()
        assert "print('exiting')" in content


# =============================================================================
# FunctionTarget Dry Run
# =============================================================================

class TestFunctionTargetDryRun:
    """Tests for FunctionTarget dry run mode."""

    @pytest.fixture
    def python_file(self, tmp_path: Path) -> Path:
        """Create a Python file for dry run tests."""
        content = textwrap.dedent('''\
            def my_function():
                pass
        ''')
        file_path = tmp_path / "dryrun.py"
        file_path.write_text(content)
        return file_path

    def test_dry_run_rename(self, tmp_path: Path, python_file: Path):
        """
        In dry run mode, rename() should not modify the file.
        """
        rejig = Rejig(str(tmp_path), dry_run=True)
        target = rejig.file(python_file).find_function("my_function")

        result = target.rename("new_function")

        assert result.success is True
        assert "DRY RUN" in result.message

        # File should be unchanged
        content = python_file.read_text()
        assert "def my_function" in content
        assert "def new_function" not in content

    def test_dry_run_delete(self, tmp_path: Path, python_file: Path):
        """
        In dry run mode, delete() should not modify the file.
        """
        rejig = Rejig(str(tmp_path), dry_run=True)
        target = rejig.file(python_file).find_function("my_function")

        result = target.delete()

        assert result.success is True
        assert "DRY RUN" in result.message

        # File should be unchanged
        content = python_file.read_text()
        assert "def my_function" in content


# =============================================================================
# FunctionTarget Error Handling
# =============================================================================

class TestFunctionTargetErrors:
    """Tests for FunctionTarget error handling."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_operations_on_missing_function(self, rejig: Rejig, tmp_path: Path):
        """
        Operations on non-existing functions should return error results.

        This tests that the library follows the "never raise" pattern.
        """
        file_path = tmp_path / "test.py"
        file_path.write_text("# Empty file\n")

        target = rejig.file(file_path).find_function("nonexistent")

        # All operations should return failure results, not raise exceptions
        result = target.add_parameter("x")
        assert result.success is False

        result = target.remove_parameter("x")
        assert result.success is False

        result = target.add_decorator("test")
        assert result.success is False

        result = target.rename("new_name")
        assert result.success is False

    def test_operations_on_missing_file(self, rejig: Rejig, tmp_path: Path):
        """
        Operations on functions in non-existing files should fail gracefully.
        """
        target = rejig.file(tmp_path / "missing.py").find_function("func")

        # Should return False, not raise
        assert target.exists() is False

        # Operations should return failure results
        result = target.get_content()
        assert result.success is False
