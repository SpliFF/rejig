"""
Tests for rejig.targets.python.line module.

This module tests LineTarget for single-line operations:
- Line existence and content retrieval
- Adding directives (type: ignore, noqa, pragma: no cover, etc.)
- Removing directives
- Line modification (rewrite, insert before/after)
- Dry run mode

LineTarget provides operations for a single line in a Python file,
particularly useful for adding/removing linting directives.

Coverage targets:
- exists() for valid and invalid line numbers
- get_content() retrieval
- add_type_ignore() with codes and reasons
- add_noqa() with codes
- add_no_cover() for coverage
- add_fmt_skip() for formatter
- add_pylint_disable() for pylint
- Removal operations for all directives
- rewrite() for content replacement
- insert_before() and insert_after()
- Dry run mode
- Error handling
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig import Rejig


# =============================================================================
# LineTarget Basic Tests
# =============================================================================

class TestLineTargetBasic:
    """Tests for basic LineTarget operations."""

    @pytest.fixture
    def python_file(self, tmp_path: Path) -> Path:
        """Create a sample Python file."""
        content = textwrap.dedent('''\
            import os
            x = 1
            y = 2
            result = x + y
        ''')
        file_path = tmp_path / "sample.py"
        file_path.write_text(content)
        return file_path

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_line_exists(self, rejig: Rejig, python_file: Path):
        """
        LineTarget.exists() should return True for valid line numbers.
        """
        target = rejig.file(python_file).line(1)
        assert target.exists() is True

    def test_line_not_exists_zero(self, rejig: Rejig, python_file: Path):
        """
        LineTarget.exists() should return False for line 0 (invalid).
        """
        target = rejig.file(python_file).line(0)
        assert target.exists() is False

    def test_line_not_exists_beyond_file(self, rejig: Rejig, python_file: Path):
        """
        LineTarget.exists() should return False for lines beyond file length.
        """
        target = rejig.file(python_file).line(100)
        assert target.exists() is False

    def test_get_content(self, rejig: Rejig, python_file: Path):
        """
        get_content() should return the content of the specified line.
        """
        target = rejig.file(python_file).line(1)
        result = target.get_content()

        assert result.success is True
        assert "import os" in result.data

    def test_get_content_missing_file(self, rejig: Rejig, tmp_path: Path):
        """
        get_content() should fail for missing files.
        """
        target = rejig.file(tmp_path / "missing.py").line(1)
        result = target.get_content()

        assert result.success is False

    def test_repr(self, rejig: Rejig, python_file: Path):
        """
        LineTarget should have a useful string representation.
        """
        target = rejig.file(python_file).line(3)

        repr_str = repr(target)
        assert "LineTarget" in repr_str
        assert "3" in repr_str


# =============================================================================
# LineTarget Add Directive Tests
# =============================================================================

class TestLineTargetAddDirectives:
    """Tests for adding directives to lines."""

    @pytest.fixture
    def python_file(self, tmp_path: Path) -> Path:
        """Create a Python file for directive tests."""
        content = textwrap.dedent('''\
            import os
            x: int = "wrong type"
            long_line = "this is a very long line that might trigger line length warnings"
        ''')
        file_path = tmp_path / "directives.py"
        file_path.write_text(content)
        return file_path

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_add_type_ignore_simple(self, rejig: Rejig, python_file: Path):
        """
        add_type_ignore() should add a generic type: ignore comment.
        """
        target = rejig.file(python_file).line(2)
        result = target.add_type_ignore()

        assert result.success is True

        content = python_file.read_text()
        assert "# type: ignore" in content

    def test_add_type_ignore_with_code(self, rejig: Rejig, python_file: Path):
        """
        add_type_ignore() should add specific error code.
        """
        target = rejig.file(python_file).line(2)
        result = target.add_type_ignore("assignment")

        assert result.success is True

        content = python_file.read_text()
        assert "# type: ignore[assignment]" in content

    def test_add_type_ignore_with_reason(self, rejig: Rejig, python_file: Path):
        """
        add_type_ignore() should add reason comment.
        """
        target = rejig.file(python_file).line(2)
        result = target.add_type_ignore("assignment", reason="Legacy code")

        assert result.success is True

        content = python_file.read_text()
        assert "# type: ignore[assignment]" in content
        assert "Legacy code" in content

    def test_add_type_ignore_no_duplicate(self, rejig: Rejig, tmp_path: Path):
        """
        add_type_ignore() should not add duplicate if already present.
        """
        file_path = tmp_path / "dup.py"
        file_path.write_text("x = 1  # type: ignore\n")

        target = rejig.file(file_path).line(1)
        result = target.add_type_ignore()

        assert result.success is True

        content = file_path.read_text()
        assert content.count("# type: ignore") == 1

    def test_add_noqa_simple(self, rejig: Rejig, python_file: Path):
        """
        add_noqa() should add a generic noqa comment.
        """
        target = rejig.file(python_file).line(3)
        result = target.add_noqa()

        assert result.success is True

        content = python_file.read_text()
        assert "# noqa" in content

    def test_add_noqa_with_code(self, rejig: Rejig, python_file: Path):
        """
        add_noqa() should add specific error code.
        """
        target = rejig.file(python_file).line(3)
        result = target.add_noqa("E501")

        assert result.success is True

        content = python_file.read_text()
        assert "# noqa: E501" in content

    def test_add_noqa_with_multiple_codes(self, rejig: Rejig, python_file: Path):
        """
        add_noqa() should support multiple error codes.
        """
        target = rejig.file(python_file).line(3)
        result = target.add_noqa(["E501", "F401"])

        assert result.success is True

        content = python_file.read_text()
        assert "# noqa: E501, F401" in content

    def test_add_no_cover(self, rejig: Rejig, python_file: Path):
        """
        add_no_cover() should add pragma: no cover comment.
        """
        target = rejig.file(python_file).line(2)
        result = target.add_no_cover()

        assert result.success is True

        content = python_file.read_text()
        assert "# pragma: no cover" in content

    def test_add_fmt_skip(self, rejig: Rejig, python_file: Path):
        """
        add_fmt_skip() should add fmt: skip comment for black.
        """
        target = rejig.file(python_file).line(3)
        result = target.add_fmt_skip()

        assert result.success is True

        content = python_file.read_text()
        assert "# fmt: skip" in content

    def test_add_pylint_disable(self, rejig: Rejig, python_file: Path):
        """
        add_pylint_disable() should add pylint: disable comment.
        """
        target = rejig.file(python_file).line(3)
        result = target.add_pylint_disable("line-too-long")

        assert result.success is True

        content = python_file.read_text()
        assert "# pylint: disable=line-too-long" in content


# =============================================================================
# LineTarget Remove Directive Tests
# =============================================================================

class TestLineTargetRemoveDirectives:
    """Tests for removing directives from lines."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_remove_type_ignore(self, rejig: Rejig, tmp_path: Path):
        """
        remove_type_ignore() should remove type: ignore comments.
        """
        file_path = tmp_path / "remove.py"
        file_path.write_text('x = "test"  # type: ignore[assignment]\n')

        target = rejig.file(file_path).line(1)
        result = target.remove_type_ignore()

        assert result.success is True

        content = file_path.read_text()
        assert "# type: ignore" not in content

    def test_remove_noqa(self, rejig: Rejig, tmp_path: Path):
        """
        remove_noqa() should remove noqa comments.
        """
        file_path = tmp_path / "remove.py"
        file_path.write_text("long_line = 123  # noqa: E501\n")

        target = rejig.file(file_path).line(1)
        result = target.remove_noqa()

        assert result.success is True

        content = file_path.read_text()
        assert "# noqa" not in content

    def test_remove_no_cover(self, rejig: Rejig, tmp_path: Path):
        """
        remove_no_cover() should remove pragma: no cover comments.
        """
        file_path = tmp_path / "remove.py"
        file_path.write_text("debug_code()  # pragma: no cover\n")

        target = rejig.file(file_path).line(1)
        result = target.remove_no_cover()

        assert result.success is True

        content = file_path.read_text()
        assert "# pragma: no cover" not in content

    def test_remove_fmt_skip(self, rejig: Rejig, tmp_path: Path):
        """
        remove_fmt_skip() should remove fmt: skip comments.
        """
        file_path = tmp_path / "remove.py"
        file_path.write_text("ugly_code()  # fmt: skip\n")

        target = rejig.file(file_path).line(1)
        result = target.remove_fmt_skip()

        assert result.success is True

        content = file_path.read_text()
        assert "# fmt: skip" not in content

    def test_remove_pylint_disable(self, rejig: Rejig, tmp_path: Path):
        """
        remove_pylint_disable() should remove pylint: disable comments.
        """
        file_path = tmp_path / "remove.py"
        file_path.write_text("line = 123  # pylint: disable=line-too-long\n")

        target = rejig.file(file_path).line(1)
        result = target.remove_pylint_disable()

        assert result.success is True

        content = file_path.read_text()
        assert "# pylint: disable" not in content


# =============================================================================
# LineTarget Modification Tests
# =============================================================================

class TestLineTargetModification:
    """Tests for line modification operations."""

    @pytest.fixture
    def python_file(self, tmp_path: Path) -> Path:
        """Create a Python file for modification tests."""
        content = textwrap.dedent('''\
            line 1
            line 2
            line 3
        ''')
        file_path = tmp_path / "modify.py"
        file_path.write_text(content)
        return file_path

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_rewrite(self, rejig: Rejig, python_file: Path):
        """
        rewrite() should replace the line content.
        """
        target = rejig.file(python_file).line(2)
        result = target.rewrite("replaced content")

        assert result.success is True

        content = python_file.read_text()
        lines = content.splitlines()
        assert lines[1] == "replaced content"
        # Original line 2 content should be gone
        assert lines[1] != "line 2"

    def test_insert_before(self, rejig: Rejig, python_file: Path):
        """
        insert_before() should insert content before the line.
        """
        target = rejig.file(python_file).line(2)
        result = target.insert_before("inserted before")

        assert result.success is True

        content = python_file.read_text()
        lines = content.splitlines()
        assert "inserted before" in lines
        # Should be at index 1 (before original line 2)
        assert lines[1] == "inserted before"

    def test_insert_after(self, rejig: Rejig, python_file: Path):
        """
        insert_after() should insert content after the line.
        """
        target = rejig.file(python_file).line(2)
        result = target.insert_after("inserted after")

        assert result.success is True

        content = python_file.read_text()
        lines = content.splitlines()
        assert "inserted after" in lines
        # Should be at index 2 (after original line 2)
        assert lines[2] == "inserted after"

    def test_delete(self, rejig: Rejig, python_file: Path):
        """
        delete() should remove the line from the file.
        """
        target = rejig.file(python_file).line(2)
        result = target.delete()

        assert result.success is True

        content = python_file.read_text()
        lines = content.splitlines()
        assert len(lines) == 2
        assert "line 2" not in lines


# =============================================================================
# LineTarget Dry Run Tests
# =============================================================================

class TestLineTargetDryRun:
    """Tests for LineTarget dry run mode."""

    @pytest.fixture
    def python_file(self, tmp_path: Path) -> Path:
        """Create a Python file for dry run tests."""
        content = "original_line\n"
        file_path = tmp_path / "dryrun.py"
        file_path.write_text(content)
        return file_path

    def test_dry_run_add_type_ignore(self, tmp_path: Path, python_file: Path):
        """
        In dry run mode, add_type_ignore() should not modify the file.
        """
        rejig = Rejig(str(tmp_path), dry_run=True)
        target = rejig.file(python_file).line(1)

        result = target.add_type_ignore()

        assert result.success is True
        assert "DRY RUN" in result.message

        # File should be unchanged
        content = python_file.read_text()
        assert "type: ignore" not in content

    def test_dry_run_rewrite(self, tmp_path: Path, python_file: Path):
        """
        In dry run mode, rewrite() should not modify the file.
        """
        rejig = Rejig(str(tmp_path), dry_run=True)
        target = rejig.file(python_file).line(1)

        result = target.rewrite("new content")

        assert result.success is True
        assert "DRY RUN" in result.message

        # File should be unchanged
        content = python_file.read_text()
        assert "original_line" in content

    def test_dry_run_delete(self, tmp_path: Path, python_file: Path):
        """
        In dry run mode, delete() should not modify the file.
        """
        rejig = Rejig(str(tmp_path), dry_run=True)
        target = rejig.file(python_file).line(1)

        result = target.delete()

        assert result.success is True
        assert "DRY RUN" in result.message

        # File should be unchanged
        content = python_file.read_text()
        assert "original_line" in content


# =============================================================================
# LineTarget Error Handling Tests
# =============================================================================

class TestLineTargetErrors:
    """Tests for LineTarget error handling."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_modify_out_of_range(self, rejig: Rejig, tmp_path: Path):
        """
        Modification operations should fail for out-of-range lines.
        """
        file_path = tmp_path / "test.py"
        file_path.write_text("single line\n")

        target = rejig.file(file_path).line(100)
        result = target.add_type_ignore()

        assert result.success is False
        assert "out of range" in result.message.lower()

    def test_modify_missing_file(self, rejig: Rejig, tmp_path: Path):
        """
        Modification operations should fail for missing files.
        """
        target = rejig.file(tmp_path / "missing.py").line(1)
        result = target.add_type_ignore()

        assert result.success is False
        assert "not found" in result.message.lower()
