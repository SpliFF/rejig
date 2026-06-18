"""
Tests for rejig.targets.python.code_block - CodeBlockTarget.

CodeBlockTarget represents a detected code structure (class, function, if-block, etc.)
that can be manipulated as a unit.

Coverage targets:
- Existence checking
- Properties: kind, name, start_line, end_line, file_path
- Content access via get_content
- Conversion to LineBlockTarget
- Repr
- Error handling for out-of-range lines and missing files
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig import Rejig
from rejig.core.results import ErrorResult, Result
from rejig.targets import CodeBlockTarget


SAMPLE_CODE = textwrap.dedent('''\
    """Module docstring."""


    class MyClass:
        """A sample class."""

        def method(self) -> None:
            pass


    def my_function(x: int) -> int:
        """A module-level function."""
        if x > 0:
            return x * 2
        else:
            return 0


    for i in range(10):
        print(i)
''')


@pytest.fixture
def code_block_file(tmp_path: Path) -> Path:
    """Create a temporary file with sample code."""
    file_path = tmp_path / "sample.py"
    file_path.write_text(SAMPLE_CODE)
    return file_path


@pytest.fixture
def code_block_rejig(tmp_path: Path, code_block_file: Path):
    """Rejig instance for code block testing."""
    with Rejig(tmp_path) as rj:
        yield rj


# =============================================================================
# CodeBlockTarget Existence and Properties
# =============================================================================

class TestCodeBlockTargetExistence:
    """Tests for CodeBlockTarget existence and properties."""

    def test_code_block_exists(self, code_block_rejig: Rejig, code_block_file: Path):
        """
        CodeBlockTarget.exists() should return True when lines are in range.
        """
        block = CodeBlockTarget(
            code_block_rejig,
            file_path=code_block_file,
            kind="class",
            start_line=4,
            end_line=9,
            name="MyClass",
        )

        assert block.exists() is True

    def test_code_block_does_not_exist_missing_file(self, code_block_rejig: Rejig, tmp_path: Path):
        """
        CodeBlockTarget.exists() should return False for a nonexistent file.
        """
        block = CodeBlockTarget(
            code_block_rejig,
            file_path=tmp_path / "nonexistent.py",
            kind="function",
            start_line=1,
            end_line=5,
        )

        assert block.exists() is False

    def test_code_block_does_not_exist_out_of_range(self, code_block_rejig: Rejig, code_block_file: Path):
        """
        CodeBlockTarget.exists() should return False when lines are out of range.
        """
        block = CodeBlockTarget(
            code_block_rejig,
            file_path=code_block_file,
            kind="function",
            start_line=100,
            end_line=200,
        )

        assert block.exists() is False

    def test_code_block_properties(self, code_block_rejig: Rejig, code_block_file: Path):
        """
        CodeBlockTarget should expose its properties correctly.
        """
        block = CodeBlockTarget(
            code_block_rejig,
            file_path=code_block_file,
            kind="class",
            start_line=4,
            end_line=9,
            name="MyClass",
        )

        assert block.kind == "class"
        assert block.name == "MyClass"
        assert block.start_line == 4
        assert block.end_line == 9
        assert block.file_path == code_block_file

    def test_code_block_repr_with_name(self, code_block_rejig: Rejig, code_block_file: Path):
        """
        Repr should include kind and name when available.
        """
        block = CodeBlockTarget(
            code_block_rejig,
            file_path=code_block_file,
            kind="class",
            start_line=4,
            end_line=9,
            name="MyClass",
        )

        repr_str = repr(block)
        assert "CodeBlockTarget" in repr_str
        assert "class" in repr_str
        assert "MyClass" in repr_str

    def test_code_block_repr_without_name(self, code_block_rejig: Rejig, code_block_file: Path):
        """
        Repr should work for blocks without names (e.g., if/for blocks).
        """
        block = CodeBlockTarget(
            code_block_rejig,
            file_path=code_block_file,
            kind="for",
            start_line=19,
            end_line=20,
        )

        repr_str = repr(block)
        assert "CodeBlockTarget" in repr_str
        assert "for" in repr_str


# =============================================================================
# CodeBlockTarget Content
# =============================================================================

class TestCodeBlockTargetContent:
    """Tests for CodeBlockTarget content access."""

    def test_get_content_success(self, code_block_rejig: Rejig, code_block_file: Path):
        """
        get_content should return the lines within the block.
        """
        block = CodeBlockTarget(
            code_block_rejig,
            file_path=code_block_file,
            kind="class",
            start_line=4,
            end_line=9,
            name="MyClass",
        )

        result = block.get_content()

        assert result.success is True
        assert "class MyClass" in result.data
        assert "def method" in result.data

    def test_get_content_missing_file(self, code_block_rejig: Rejig, tmp_path: Path):
        """
        get_content should return error for missing file.
        """
        block = CodeBlockTarget(
            code_block_rejig,
            file_path=tmp_path / "missing.py",
            kind="function",
            start_line=1,
            end_line=3,
        )

        result = block.get_content()

        assert result.success is False

    def test_get_content_out_of_range_start(self, code_block_rejig: Rejig, code_block_file: Path):
        """
        get_content should return error when start_line is out of range.
        """
        block = CodeBlockTarget(
            code_block_rejig,
            file_path=code_block_file,
            kind="function",
            start_line=999,
            end_line=1000,
        )

        result = block.get_content()

        assert result.success is False

    def test_get_content_single_line_block(self, code_block_rejig: Rejig, code_block_file: Path):
        """
        get_content should work for single-line blocks.
        """
        # Line 1 is the module docstring
        block = CodeBlockTarget(
            code_block_rejig,
            file_path=code_block_file,
            kind="function",
            start_line=1,
            end_line=1,
        )

        result = block.get_content()

        assert result.success is True
        assert result.data is not None


# =============================================================================
# CodeBlockTarget Conversion
# =============================================================================

class TestCodeBlockTargetConversion:
    """Tests for converting CodeBlockTarget to LineBlockTarget."""

    def test_to_line_block(self, code_block_rejig: Rejig, code_block_file: Path):
        """
        to_line_block should return a LineBlockTarget covering the same lines.
        """
        from rejig.targets.python.line_block import LineBlockTarget

        block = CodeBlockTarget(
            code_block_rejig,
            file_path=code_block_file,
            kind="class",
            start_line=4,
            end_line=9,
            name="MyClass",
        )

        line_block = block.to_line_block()

        assert isinstance(line_block, LineBlockTarget)
        assert line_block.start_line == 4
        assert line_block.end_line == 9


# =============================================================================
# CodeBlockTarget Error Handling
# =============================================================================

class TestCodeBlockTargetErrors:
    """Tests for error handling in CodeBlockTarget operations."""

    def test_operations_on_missing_file_return_error(self, code_block_rejig: Rejig, tmp_path: Path):
        """
        Operations on a code block in a missing file should return errors
        without raising exceptions.
        """
        block = CodeBlockTarget(
            code_block_rejig,
            file_path=tmp_path / "missing.py",
            kind="function",
            start_line=1,
            end_line=5,
        )

        # All operations should return error results, not raise
        result = block.get_content()
        assert result.success is False

    def test_never_raises_exceptions(self, code_block_rejig: Rejig, code_block_file: Path):
        """
        Operations should never raise exceptions, consistent with the Rejig design.
        """
        block = CodeBlockTarget(
            code_block_rejig,
            file_path=code_block_file,
            kind="function",
            start_line=999,
            end_line=1000,
        )

        # These should all return results, not raise
        result = block.get_content()
        assert isinstance(result, (Result, ErrorResult))
