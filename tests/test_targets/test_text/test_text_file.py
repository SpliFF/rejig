"""
Tests for rejig.targets.text.text_file module.

This module tests TextFileTarget for generic text file operations:
- File existence and content retrieval
- Content modification (rewrite, replace)
- Appending and prepending content
- Line-based operations (insert, delete)
- Pattern matching and search
- Dry run mode

TextFileTarget provides operations for any text file that doesn't
have a specific format (like Python, TOML, etc.).

Coverage targets:
- exists() for existing and non-existing files
- get_content() retrieval
- rewrite() for full content replacement
- replace() for regex-based replacement
- append() and prepend() operations
- insert_at_line() and delete_line() operations
- find_lines() for pattern searching
- Dry run mode
- Error handling
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig import Rejig


# =============================================================================
# TextFileTarget Basic Tests
# =============================================================================

class TestTextFileTargetBasic:
    """Tests for basic TextFileTarget operations."""

    @pytest.fixture
    def text_file(self, tmp_path: Path) -> Path:
        """Create a sample text file."""
        content = textwrap.dedent('''\
            Line 1: Hello World
            Line 2: This is a test
            Line 3: More content here
            Line 4: Final line
        ''')
        file_path = tmp_path / "sample.txt"
        file_path.write_text(content)
        return file_path

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_text_file_exists(self, rejig: Rejig, text_file: Path):
        """
        TextFileTarget.exists() should return True for existing files.
        """
        target = rejig.text_file(text_file)
        assert target.exists() is True

    def test_text_file_not_exists(self, rejig: Rejig, tmp_path: Path):
        """
        TextFileTarget.exists() should return False for missing files.
        """
        target = rejig.text_file(tmp_path / "missing.txt")
        assert target.exists() is False

    def test_get_content(self, rejig: Rejig, text_file: Path):
        """
        get_content() should return the full file content.
        """
        target = rejig.text_file(text_file)
        result = target.get_content()

        assert result.success is True
        assert "Hello World" in result.data
        assert "Final line" in result.data

    def test_get_content_missing_file(self, rejig: Rejig, tmp_path: Path):
        """
        get_content() should return error for missing files.
        """
        target = rejig.text_file(tmp_path / "missing.txt")
        result = target.get_content()

        assert result.success is False
        assert "not found" in result.message.lower()

    def test_line_count(self, rejig: Rejig, text_file: Path):
        """
        line_count() should return the number of lines.
        """
        target = rejig.text_file(text_file)

        count = target.line_count()
        assert count == 4

    def test_get_line(self, rejig: Rejig, text_file: Path):
        """
        get_line() should return a specific line by number.

        Line numbers are 1-indexed.
        """
        target = rejig.text_file(text_file)

        line = target.get_line(1)
        assert "Hello World" in line

        line = target.get_line(4)
        assert "Final line" in line

    def test_get_line_out_of_range(self, rejig: Rejig, text_file: Path):
        """
        get_line() should return None for out-of-range line numbers.
        """
        target = rejig.text_file(text_file)

        line = target.get_line(0)  # Invalid
        assert line is None

        line = target.get_line(100)  # Beyond file
        assert line is None


# =============================================================================
# TextFileTarget Content Modification Tests
# =============================================================================

class TestTextFileTargetModification:
    """Tests for TextFileTarget content modification."""

    @pytest.fixture
    def text_file(self, tmp_path: Path) -> Path:
        """Create a sample text file."""
        content = "Old content here.\n"
        file_path = tmp_path / "modify.txt"
        file_path.write_text(content)
        return file_path

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_rewrite(self, rejig: Rejig, text_file: Path):
        """
        rewrite() should replace the entire file content.
        """
        target = rejig.text_file(text_file)
        result = target.rewrite("New content entirely.")

        assert result.success is True

        content = text_file.read_text()
        assert content == "New content entirely."
        assert "Old content" not in content

    def test_replace_simple(self, rejig: Rejig, text_file: Path):
        """
        replace() should perform regex replacement.
        """
        target = rejig.text_file(text_file)
        result = target.replace("Old", "New")

        assert result.success is True

        content = text_file.read_text()
        assert "New content" in content
        assert "Old content" not in content

    def test_replace_no_match(self, rejig: Rejig, text_file: Path):
        """
        replace() should succeed with no changes if pattern not found.
        """
        target = rejig.text_file(text_file)
        result = target.replace("nonexistent", "replacement")

        assert result.success is True
        assert "no match" in result.message.lower()

    def test_replace_with_count(self, rejig: Rejig, tmp_path: Path):
        """
        replace() with count should limit replacements.
        """
        file_path = tmp_path / "replace.txt"
        file_path.write_text("hello hello hello")

        target = rejig.text_file(file_path)
        result = target.replace("hello", "world", count=1)

        assert result.success is True

        content = file_path.read_text()
        assert "world" in content
        assert content.count("hello") == 2  # Only one replaced


# =============================================================================
# TextFileTarget Append/Prepend Tests
# =============================================================================

class TestTextFileTargetAppendPrepend:
    """Tests for TextFileTarget append and prepend operations."""

    @pytest.fixture
    def text_file(self, tmp_path: Path) -> Path:
        """Create a sample text file."""
        content = "Original content\n"
        file_path = tmp_path / "append.txt"
        file_path.write_text(content)
        return file_path

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_append(self, rejig: Rejig, text_file: Path):
        """
        append() should add content at the end of the file.
        """
        target = rejig.text_file(text_file)
        result = target.append("Added at end")

        assert result.success is True

        content = text_file.read_text()
        assert "Original content" in content
        assert "Added at end" in content
        assert content.endswith("Added at end") or content.endswith("Added at end\n")

    def test_prepend(self, rejig: Rejig, text_file: Path):
        """
        prepend() should add content at the beginning of the file.
        """
        target = rejig.text_file(text_file)
        result = target.prepend("Added at start")

        assert result.success is True

        content = text_file.read_text()
        assert "Added at start" in content
        assert "Original content" in content
        assert content.startswith("Added at start")


# =============================================================================
# TextFileTarget Line Operations Tests
# =============================================================================

class TestTextFileTargetLineOperations:
    """Tests for TextFileTarget line-based operations."""

    @pytest.fixture
    def text_file(self, tmp_path: Path) -> Path:
        """Create a sample text file with numbered lines."""
        content = textwrap.dedent('''\
            Line 1
            Line 2
            Line 3
            Line 4
        ''')
        file_path = tmp_path / "lines.txt"
        file_path.write_text(content)
        return file_path

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_insert_at_line(self, rejig: Rejig, text_file: Path):
        """
        insert_at_line() should insert content at a specific line number.

        Line numbers are 1-indexed.
        """
        target = rejig.text_file(text_file)
        result = target.insert_at_line(2, "Inserted line")

        assert result.success is True

        content = text_file.read_text()
        lines = content.splitlines()
        assert "Inserted line" in lines
        assert lines[1] == "Inserted line"

    def test_insert_at_line_out_of_range(self, rejig: Rejig, text_file: Path):
        """
        insert_at_line() should fail for out-of-range line numbers.
        """
        target = rejig.text_file(text_file)
        result = target.insert_at_line(100, "Content")

        assert result.success is False
        assert "out of range" in result.message.lower()

    def test_delete_line(self, rejig: Rejig, text_file: Path):
        """
        delete_line() should remove a specific line.
        """
        target = rejig.text_file(text_file)
        result = target.delete_line(2)

        assert result.success is True

        content = text_file.read_text()
        lines = content.splitlines()
        assert len(lines) == 3
        assert "Line 2" not in lines

    def test_delete_lines_range(self, rejig: Rejig, text_file: Path):
        """
        delete_lines() should remove a range of lines.
        """
        target = rejig.text_file(text_file)
        result = target.delete_lines(2, 3)

        assert result.success is True

        content = text_file.read_text()
        lines = content.splitlines()
        assert len(lines) == 2
        assert "Line 1" in lines
        assert "Line 4" in lines


# =============================================================================
# TextFileTarget Pattern Search Tests
# =============================================================================

class TestTextFileTargetSearch:
    """Tests for TextFileTarget search operations."""

    @pytest.fixture
    def text_file(self, tmp_path: Path) -> Path:
        """Create a sample text file with searchable content."""
        content = textwrap.dedent('''\
            # Comment line
            TODO: Fix this bug
            Regular code here
            TODO: Another task
            More code
        ''')
        file_path = tmp_path / "search.txt"
        file_path.write_text(content)
        return file_path

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_find_lines_simple(self, rejig: Rejig, text_file: Path):
        """
        find_lines() should return lines matching a pattern.

        Returns list of (line_number, line_content) tuples.
        """
        target = rejig.text_file(text_file)
        matches = target.find_lines("TODO")

        assert len(matches) == 2
        # First match
        assert matches[0][0] == 2  # Line number
        assert "TODO" in matches[0][1]  # Line content

    def test_find_lines_regex(self, rejig: Rejig, text_file: Path):
        """
        find_lines() should support regex patterns.
        """
        target = rejig.text_file(text_file)
        matches = target.find_lines(r"TODO:.*task")

        assert len(matches) == 1
        assert "Another task" in matches[0][1]

    def test_find_lines_no_match(self, rejig: Rejig, text_file: Path):
        """
        find_lines() should return empty list if no matches.
        """
        target = rejig.text_file(text_file)
        matches = target.find_lines("nonexistent")

        assert matches == []


# =============================================================================
# TextFileTarget Dry Run Tests
# =============================================================================

class TestTextFileTargetDryRun:
    """Tests for TextFileTarget dry run mode."""

    @pytest.fixture
    def text_file(self, tmp_path: Path) -> Path:
        """Create a sample text file."""
        content = "Original content\n"
        file_path = tmp_path / "dryrun.txt"
        file_path.write_text(content)
        return file_path

    def test_dry_run_rewrite(self, tmp_path: Path, text_file: Path):
        """
        In dry run mode, rewrite() should not modify the file.
        """
        rejig = Rejig(str(tmp_path), dry_run=True)
        target = rejig.text_file(text_file)

        result = target.rewrite("New content")

        assert result.success is True
        assert "DRY RUN" in result.message

        # File should be unchanged
        content = text_file.read_text()
        assert "Original content" in content

    def test_dry_run_delete(self, tmp_path: Path, text_file: Path):
        """
        In dry run mode, delete() should not remove the file.
        """
        rejig = Rejig(str(tmp_path), dry_run=True)
        target = rejig.text_file(text_file)

        result = target.delete()

        assert result.success is True
        assert "DRY RUN" in result.message

        # File should still exist
        assert text_file.exists()


# =============================================================================
# TextFileTarget Delete Tests
# =============================================================================

class TestTextFileTargetDelete:
    """Tests for TextFileTarget delete operation."""

    @pytest.fixture
    def text_file(self, tmp_path: Path) -> Path:
        """Create a sample text file."""
        file_path = tmp_path / "delete_me.txt"
        file_path.write_text("Content to delete")
        return file_path

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_delete(self, rejig: Rejig, text_file: Path):
        """
        delete() should remove the file.
        """
        target = rejig.text_file(text_file)

        assert text_file.exists()

        result = target.delete()

        assert result.success is True
        assert not text_file.exists()

    def test_delete_missing_file(self, rejig: Rejig, tmp_path: Path):
        """
        delete() should fail for non-existing files.
        """
        target = rejig.text_file(tmp_path / "missing.txt")
        result = target.delete()

        assert result.success is False
        assert "not found" in result.message.lower()
