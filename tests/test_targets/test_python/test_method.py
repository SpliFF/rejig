"""
Tests for rejig.targets.python.method module.

This module tests MethodTarget for class methods:
- Finding and locating methods within classes
- Getting method content
- Modifying method parameters
- Adding/removing decorators
- Renaming and deleting methods
- Type hint operations
- Insert statement operations
- Pattern matching operations (insert_before_match, insert_after_match)
- Dry run mode

MethodTarget provides operations for methods within classes.
Module-level functions should use FunctionTarget instead.

Coverage targets:
- exists() for existing and non-existing methods
- get_content() retrieval
- Parameter operations (add, remove, rename, reorder)
- Decorator operations (add, remove)
- rename() and delete()
- Type hint operations
- insert_statement() at start and end
- Pattern matching insertions
- Dry run mode
- Error handling for missing methods
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig import Rejig


# =============================================================================
# MethodTarget Basic Tests
# =============================================================================

class TestMethodTargetBasic:
    """Tests for basic MethodTarget operations."""

    @pytest.fixture
    def python_file(self, tmp_path: Path) -> Path:
        """Create a sample Python file with classes and methods."""
        content = textwrap.dedent('''\
            """Sample module with classes."""

            class MyClass:
                """A sample class."""

                def __init__(self, value):
                    """Initialize with a value."""
                    self.value = value

                def simple_method(self):
                    """A simple method."""
                    return self.value

                def method_with_params(self, x, y, z=10):
                    """Method with parameters."""
                    return self.value + x + y + z

                @property
                def decorated_method(self):
                    """A decorated method."""
                    return self.value * 2

            class OtherClass:
                """Another class with same method name."""

                def simple_method(self):
                    """Different implementation."""
                    return "other"
        ''')
        file_path = tmp_path / "sample.py"
        file_path.write_text(content)
        return file_path

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_method_exists(self, rejig: Rejig, python_file: Path):
        """
        MethodTarget.exists() should return True for existing methods.

        This verifies that MethodTarget can locate methods within classes.
        """
        target = rejig.file(python_file).find_class("MyClass").find_method("simple_method")
        assert target.exists() is True

    def test_method_not_exists(self, rejig: Rejig, python_file: Path):
        """
        MethodTarget.exists() should return False for non-existing methods.

        The lazy target API creates targets even for non-existent methods,
        but exists() should correctly report False.
        """
        target = rejig.file(python_file).find_class("MyClass").find_method("nonexistent_method")
        assert target.exists() is False

    def test_method_in_different_class(self, rejig: Rejig, python_file: Path):
        """
        MethodTarget should correctly identify methods in specific classes.

        Methods with the same name in different classes should be distinct.
        """
        my_class_target = rejig.file(python_file).find_class("MyClass").find_method("simple_method")
        other_class_target = rejig.file(python_file).find_class("OtherClass").find_method("simple_method")

        assert my_class_target.exists() is True
        assert other_class_target.exists() is True

        # They should have different class names
        assert my_class_target.class_name == "MyClass"
        assert other_class_target.class_name == "OtherClass"

    def test_get_content(self, rejig: Rejig, python_file: Path):
        """
        get_content() should return the full source code of the method.

        The returned data should include the method definition, docstring,
        and body.
        """
        target = rejig.file(python_file).find_class("MyClass").find_method("method_with_params")
        result = target.get_content()

        assert result.success is True
        assert "def method_with_params" in result.data
        assert "return self.value + x + y + z" in result.data

    def test_get_content_missing_method(self, rejig: Rejig, python_file: Path):
        """
        get_content() should return failure for non-existing methods.

        When a method doesn't exist, find_method() returns an ErrorTarget
        which returns ErrorResult for all operations.
        """
        target = rejig.file(python_file).find_class("MyClass").find_method("nonexistent")
        result = target.get_content()

        assert result.success is False
        # Error could be "not found" or "ErrorTarget" depending on how target was created
        assert "not found" in result.message.lower() or "errortarget" in result.message.lower()

    def test_method_line_number(self, rejig: Rejig, python_file: Path):
        """
        MethodTarget should provide the line number of the method.

        Line numbers are 1-indexed.
        """
        target = rejig.file(python_file).find_class("MyClass").find_method("simple_method")

        # The method should be found with a valid line number
        assert target.exists() is True
        assert target.line_number is not None
        assert target.line_number > 0

    def test_method_repr(self, rejig: Rejig, python_file: Path):
        """
        MethodTarget should have a useful string representation.
        """
        target = rejig.file(python_file).find_class("MyClass").find_method("simple_method")
        target.exists()  # Ensure file_path is set

        repr_str = repr(target)
        assert "MethodTarget" in repr_str
        assert "MyClass" in repr_str
        assert "simple_method" in repr_str


# =============================================================================
# MethodTarget Parameter Operations
# =============================================================================

class TestMethodTargetParameters:
    """Tests for MethodTarget parameter operations."""

    @pytest.fixture
    def python_file(self, tmp_path: Path) -> Path:
        """Create a Python file for parameter tests."""
        content = textwrap.dedent('''\
            class MyClass:
                def my_method(self, x, y):
                    return x + y

                def method_with_self_only(self):
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
        add_parameter() should add a parameter to the method signature.

        By default, parameters are added at the end (after existing params).
        """
        target = rejig.file(python_file).find_class("MyClass").find_method("my_method")
        result = target.add_parameter("z")

        assert result.success is True

        # Verify the parameter was added
        content = python_file.read_text()
        assert "def my_method(self, x, y, z):" in content

    def test_add_parameter_with_type(self, rejig: Rejig, python_file: Path):
        """
        add_parameter() should support type annotations.
        """
        target = rejig.file(python_file).find_class("MyClass").find_method("my_method")
        result = target.add_parameter("count", type_annotation="int")

        assert result.success is True

        content = python_file.read_text()
        assert "count: int" in content

    def test_add_parameter_with_default(self, rejig: Rejig, python_file: Path):
        """
        add_parameter() should support default values.
        """
        target = rejig.file(python_file).find_class("MyClass").find_method("my_method")
        result = target.add_parameter("flag", default_value="False")

        assert result.success is True

        content = python_file.read_text()
        assert "flag" in content
        assert "False" in content

    def test_add_parameter_preserves_self(self, rejig: Rejig, python_file: Path):
        """
        add_parameter() should preserve the self parameter.

        When adding to a method, self should always remain first.
        """
        target = rejig.file(python_file).find_class("MyClass").find_method("method_with_self_only")
        result = target.add_parameter("value")

        assert result.success is True

        content = python_file.read_text()
        # self should come before value
        assert "def method_with_self_only(self, value):" in content

    def test_remove_parameter(self, rejig: Rejig, python_file: Path):
        """
        remove_parameter() should remove a parameter from the method signature.
        """
        target = rejig.file(python_file).find_class("MyClass").find_method("my_method")
        result = target.remove_parameter("y")

        assert result.success is True

        content = python_file.read_text()
        assert "def my_method(self, x):" in content

    def test_remove_parameter_not_found(self, rejig: Rejig, python_file: Path):
        """
        remove_parameter() should fail for non-existing parameters.
        """
        target = rejig.file(python_file).find_class("MyClass").find_method("my_method")
        result = target.remove_parameter("nonexistent")

        assert result.success is False
        assert "not found" in result.message.lower()


# =============================================================================
# MethodTarget Decorator Operations
# =============================================================================

class TestMethodTargetDecorators:
    """Tests for MethodTarget decorator operations."""

    @pytest.fixture
    def python_file(self, tmp_path: Path) -> Path:
        """Create a Python file for decorator tests."""
        content = textwrap.dedent('''\
            class MyClass:
                def plain_method(self):
                    return 42

                @property
                def decorated_method(self):
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
        add_decorator() should add a decorator to the method.

        The decorator is added without the @ prefix (it's added automatically).
        """
        target = rejig.file(python_file).find_class("MyClass").find_method("plain_method")
        result = target.add_decorator("staticmethod")

        assert result.success is True

        content = python_file.read_text()
        assert "@staticmethod" in content

    def test_remove_decorator(self, rejig: Rejig, python_file: Path):
        """
        remove_decorator() should remove a decorator from the method.
        """
        target = rejig.file(python_file).find_class("MyClass").find_method("decorated_method")
        result = target.remove_decorator("property")

        assert result.success is True

        content = python_file.read_text()
        assert "@property" not in content
        # But the method should still exist
        assert "def decorated_method" in content


# =============================================================================
# MethodTarget Rename and Delete
# =============================================================================

class TestMethodTargetRenameDelete:
    """Tests for MethodTarget rename and delete operations."""

    @pytest.fixture
    def python_file(self, tmp_path: Path) -> Path:
        """Create a Python file for rename/delete tests."""
        content = textwrap.dedent('''\
            class MyClass:
                def old_method(self):
                    return "old"

                def other_method(self):
                    return "other"
        ''')
        file_path = tmp_path / "rename.py"
        file_path.write_text(content)
        return file_path

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_rename_method(self, rejig: Rejig, python_file: Path):
        """
        rename() should rename the method definition.

        Note: This only renames the definition, not call sites.
        """
        target = rejig.file(python_file).find_class("MyClass").find_method("old_method")
        result = target.rename("new_method")

        assert result.success is True

        content = python_file.read_text()
        assert "def new_method" in content
        assert "def old_method" not in content

    def test_rename_updates_target_name(self, rejig: Rejig, python_file: Path):
        """
        After rename(), the target's name attribute should be updated.
        """
        target = rejig.file(python_file).find_class("MyClass").find_method("old_method")
        assert target.name == "old_method"

        target.rename("new_method")

        assert target.name == "new_method"

    def test_delete_method(self, rejig: Rejig, python_file: Path):
        """
        delete() should remove the method from the class entirely.
        """
        target = rejig.file(python_file).find_class("MyClass").find_method("old_method")
        result = target.delete()

        assert result.success is True

        content = python_file.read_text()
        assert "def old_method" not in content
        # other_method should still exist
        assert "def other_method" in content

    def test_delete_nonexistent_method(self, rejig: Rejig, python_file: Path):
        """
        delete() should fail for non-existing methods.

        When a method doesn't exist, find_method() returns an ErrorTarget
        which returns ErrorResult for all operations.
        """
        target = rejig.file(python_file).find_class("MyClass").find_method("nonexistent")
        result = target.delete()

        assert result.success is False
        # Error could be "not found" or "ErrorTarget" depending on how target was created
        assert "not found" in result.message.lower() or "errortarget" in result.message.lower()


# =============================================================================
# MethodTarget Type Hint Operations
# =============================================================================

class TestMethodTargetTypeHints:
    """Tests for MethodTarget type hint operations."""

    @pytest.fixture
    def python_file(self, tmp_path: Path) -> Path:
        """Create a Python file for type hint tests."""
        content = textwrap.dedent('''\
            class MyClass:
                def no_types(self, x, y):
                    return x + y

                def with_types(self, x: int, y: int) -> int:
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
        target = rejig.file(python_file).find_class("MyClass").find_method("no_types")
        result = target.set_return_type("int")

        assert result.success is True

        content = python_file.read_text()
        assert "-> int:" in content

    def test_set_parameter_type(self, rejig: Rejig, python_file: Path):
        """
        set_parameter_type() should add a type annotation to a parameter.
        """
        target = rejig.file(python_file).find_class("MyClass").find_method("no_types")
        result = target.set_parameter_type("x", "float")

        assert result.success is True

        content = python_file.read_text()
        assert "x: float" in content


# =============================================================================
# MethodTarget Insert Statement
# =============================================================================

class TestMethodTargetInsertStatement:
    """Tests for MethodTarget insert_statement operation."""

    @pytest.fixture
    def python_file(self, tmp_path: Path) -> Path:
        """Create a Python file for insert tests."""
        content = textwrap.dedent('''\
            class MyClass:
                def my_method(self, x):
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
        target = rejig.file(python_file).find_class("MyClass").find_method("my_method")
        result = target.insert_statement("self.log('entering')")

        assert result.success is True

        content = python_file.read_text()
        assert "self.log('entering')" in content
        # Should be before result = x * 2
        assert content.index("self.log('entering')") < content.index("result = x * 2")

    def test_insert_statement_at_end(self, rejig: Rejig, python_file: Path):
        """
        insert_statement() with position="end" should insert at the end.
        """
        target = rejig.file(python_file).find_class("MyClass").find_method("my_method")
        result = target.insert_statement("self.log('exiting')", position="end")

        assert result.success is True

        content = python_file.read_text()
        assert "self.log('exiting')" in content


# =============================================================================
# MethodTarget Dry Run
# =============================================================================

class TestMethodTargetDryRun:
    """Tests for MethodTarget dry run mode."""

    @pytest.fixture
    def python_file(self, tmp_path: Path) -> Path:
        """Create a Python file for dry run tests."""
        content = textwrap.dedent('''\
            class MyClass:
                def my_method(self):
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
        target = rejig.file(python_file).find_class("MyClass").find_method("my_method")

        result = target.rename("new_method")

        assert result.success is True
        assert "DRY RUN" in result.message

        # File should be unchanged
        content = python_file.read_text()
        assert "def my_method" in content
        assert "def new_method" not in content

    def test_dry_run_delete(self, tmp_path: Path, python_file: Path):
        """
        In dry run mode, delete() should not modify the file.
        """
        rejig = Rejig(str(tmp_path), dry_run=True)
        target = rejig.file(python_file).find_class("MyClass").find_method("my_method")

        result = target.delete()

        assert result.success is True
        assert "DRY RUN" in result.message

        # File should be unchanged
        content = python_file.read_text()
        assert "def my_method" in content


# =============================================================================
# MethodTarget Error Handling
# =============================================================================

class TestMethodTargetErrors:
    """Tests for MethodTarget error handling."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_operations_on_missing_method(self, rejig: Rejig, tmp_path: Path):
        """
        Operations on non-existing methods should return error results.

        This tests that the library follows the "never raise" pattern.
        """
        file_path = tmp_path / "test.py"
        file_path.write_text("class MyClass:\n    pass\n")

        target = rejig.file(file_path).find_class("MyClass").find_method("nonexistent")

        # All operations should return failure results, not raise exceptions
        result = target.add_parameter("x")
        assert result.success is False

        result = target.remove_parameter("x")
        assert result.success is False

        result = target.add_decorator("test")
        assert result.success is False

        result = target.rename("new_name")
        assert result.success is False

    def test_operations_on_missing_class(self, rejig: Rejig, tmp_path: Path):
        """
        Operations on methods in non-existing classes should fail gracefully.
        """
        file_path = tmp_path / "test.py"
        file_path.write_text("# Empty file\n")

        target = rejig.file(file_path).find_class("NonexistentClass").find_method("method")

        # Should return False, not raise
        assert target.exists() is False

        # Operations should return failure results
        result = target.get_content()
        assert result.success is False

    def test_operations_on_missing_file(self, rejig: Rejig, tmp_path: Path):
        """
        Operations on methods in non-existing files should fail gracefully.
        """
        target = rejig.file(tmp_path / "missing.py").find_class("MyClass").find_method("method")

        # Should return False, not raise
        assert target.exists() is False

        # Operations should return failure results
        result = target.get_content()
        assert result.success is False


# =============================================================================
# MethodTarget Convert Operations
# =============================================================================

class TestMethodTargetConvert:
    """Tests for MethodTarget convert operations."""

    @pytest.fixture
    def python_file(self, tmp_path: Path) -> Path:
        """Create a Python file for convert tests."""
        content = textwrap.dedent('''\
            class MyClass:
                @staticmethod
                def static_method():
                    return 42

                def regular_method(self):
                    return self.value

                async def async_method(self):
                    await self.fetch()
                    return "done"
        ''')
        file_path = tmp_path / "convert.py"
        file_path.write_text(content)
        return file_path

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_convert_to_async(self, rejig: Rejig, python_file: Path):
        """
        convert_to_async() should add async keyword to the method.
        """
        target = rejig.file(python_file).find_class("MyClass").find_method("regular_method")
        result = target.convert_to_async()

        assert result.success is True

        content = python_file.read_text()
        assert "async def regular_method" in content

    def test_convert_to_sync(self, rejig: Rejig, python_file: Path):
        """
        convert_to_sync() should remove async keyword from the method.
        """
        target = rejig.file(python_file).find_class("MyClass").find_method("async_method")
        result = target.convert_to_sync()

        assert result.success is True

        content = python_file.read_text()
        # Should no longer have async
        assert "async def async_method" not in content
        assert "def async_method" in content
