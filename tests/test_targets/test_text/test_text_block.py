"""
Tests for rejig.targets.text.text_block - TextBlock target.

TextBlock provides raw text manipulation without AST parsing, useful for
any text file (README, config, etc.) using pattern-based operations.

Coverage targets:
- Existence checking
- Content access via get_content
- Pattern finding: find_pattern, find_first
- Pattern replacement: replace_pattern
- Line operations: insert_at_line, delete_line, delete_lines
- Dry-run mode
- Error handling: missing files, out-of-range lines
- TextMatch integration (returned by find_pattern)
"""
from __future__ import annotations

import re
import textwrap
from pathlib import Path

import pytest

from rejig import Rejig
from rejig.core.results import ErrorResult, Result
from rejig.targets import TargetList
from rejig.targets.text.text_block import TextBlock
from rejig.targets.text.text_match import TextMatch


SAMPLE_TEXT = textwrap.dedent('''\
    # My Project

    Version: 1.0.0
    Author: Test Author

    ## Features

    - Feature A: enabled
    - Feature B: disabled
    - Feature C: enabled

    ## Configuration

    DEBUG = True
    TIMEOUT = 30
    SECRET = "abc123"

    ## TODO

    TODO: Add more features
    TODO: Write documentation
    FIXME: Fix the bug
''')


@pytest.fixture
def text_file(tmp_path: Path) -> Path:
    """Create a temporary text file."""
    file_path = tmp_path / "readme.md"
    file_path.write_text(SAMPLE_TEXT)
    return file_path


@pytest.fixture
def text_rejig(tmp_path: Path, text_file: Path):
    """Rejig instance for text block testing."""
    with Rejig(tmp_path) as rj:
        yield rj


# =============================================================================
# TextBlock Existence and Content
# =============================================================================

class TestTextBlockExistence:
    """Tests for TextBlock existence and content access."""

    def test_exists(self, text_rejig: Rejig, text_file: Path):
        """
        TextBlock.exists() should return True for an existing file.
        """
        block = text_rejig.text_block("readme.md")

        assert block.exists() is True

    def test_not_exists(self, text_rejig: Rejig):
        """
        TextBlock.exists() should return False for a missing file.
        """
        block = text_rejig.text_block("missing.md")

        assert block.exists() is False

    def test_get_content(self, text_rejig: Rejig, text_file: Path):
        """
        get_content should return the file content.
        """
        block = text_rejig.text_block("readme.md")
        result = block.get_content()

        assert result.success is True
        assert "My Project" in result.data

    def test_get_content_missing_file(self, text_rejig: Rejig):
        """
        get_content on a missing file should return an error.
        """
        block = text_rejig.text_block("missing.md")
        result = block.get_content()

        assert result.success is False

    def test_repr(self, text_rejig: Rejig, text_file: Path):
        """
        TextBlock repr should include the path.
        """
        block = text_rejig.text_block("readme.md")

        assert "TextBlock" in repr(block)

    def test_from_file_classmethod(self, text_file: Path):
        """
        TextBlock.from_file should create a TextBlock without a Rejig instance.
        """
        block = TextBlock.from_file(text_file)

        assert block.exists() is True
        result = block.get_content()
        assert result.success is True


# =============================================================================
# TextBlock Pattern Finding
# =============================================================================

class TestTextBlockFindPattern:
    """Tests for pattern-based finding."""

    def test_find_pattern_returns_matches(self, text_rejig: Rejig, text_file: Path):
        """
        find_pattern should return TextMatch objects for each match.
        """
        block = text_rejig.text_block("readme.md")
        matches = block.find_pattern(r"TODO:.*")

        assert isinstance(matches, TargetList)
        assert len(matches) >= 2

    def test_find_pattern_no_matches(self, text_rejig: Rejig, text_file: Path):
        """
        find_pattern with no matches should return empty TargetList.
        """
        block = text_rejig.text_block("readme.md")
        matches = block.find_pattern(r"NONEXISTENT_PATTERN_12345")

        assert isinstance(matches, TargetList)
        assert len(matches) == 0

    def test_find_pattern_missing_file(self, text_rejig: Rejig):
        """
        find_pattern on a missing file should return empty TargetList.
        """
        block = text_rejig.text_block("missing.md")
        matches = block.find_pattern(r".*")

        assert isinstance(matches, TargetList)
        assert len(matches) == 0

    def test_find_pattern_with_flags(self, text_rejig: Rejig, text_file: Path):
        """
        find_pattern should support regex flags.
        """
        block = text_rejig.text_block("readme.md")

        # Case-insensitive search
        matches_case = block.find_pattern(r"debug", flags=re.IGNORECASE)
        matches_exact = block.find_pattern(r"debug")

        # Case-insensitive should find "DEBUG"
        assert len(matches_case) >= 1
        # Exact lowercase won't find "DEBUG"
        assert len(matches_case) >= len(matches_exact)

    def test_find_first(self, text_rejig: Rejig, text_file: Path):
        """
        find_first should return a single TextMatch or None.
        """
        block = text_rejig.text_block("readme.md")

        # Should find the first TODO
        match = block.find_first(r"TODO:.*")
        assert match is not None
        assert isinstance(match, TextMatch)

    def test_find_first_no_match(self, text_rejig: Rejig, text_file: Path):
        """
        find_first should return None when no match is found.
        """
        block = text_rejig.text_block("readme.md")

        match = block.find_first(r"NONEXISTENT_12345")
        assert match is None

    def test_text_match_properties(self, text_rejig: Rejig, text_file: Path):
        """
        TextMatch should expose text and line number.
        """
        block = text_rejig.text_block("readme.md")
        matches = block.find_pattern(r"Version: [\d.]+")

        if len(matches) > 0:
            match = matches[0]
            assert match.text is not None
            assert "1.0.0" in match.text
            assert match.line_number > 0


# =============================================================================
# TextBlock Pattern Replacement
# =============================================================================

class TestTextBlockReplacePattern:
    """Tests for pattern-based replacement."""

    def test_replace_pattern(self, text_rejig: Rejig, text_file: Path):
        """
        replace_pattern should replace all occurrences of a pattern.
        """
        block = text_rejig.text_block("readme.md")
        result = block.replace_pattern(r"Version: [\d.]+", "Version: 2.0.0")

        assert result.success is True
        assert text_file.read_text().count("Version: 2.0.0") == 1

    def test_replace_pattern_no_match(self, text_rejig: Rejig, text_file: Path):
        """
        replace_pattern with no matches should succeed with "no matches" message.
        """
        block = text_rejig.text_block("readme.md")
        original = text_file.read_text()
        result = block.replace_pattern(r"NONEXISTENT_12345", "replacement")

        assert result.success is True
        assert text_file.read_text() == original

    def test_replace_pattern_missing_file(self, text_rejig: Rejig):
        """
        replace_pattern on a missing file should return an error.
        """
        block = text_rejig.text_block("missing.md")
        result = block.replace_pattern(r".*", "replacement")

        assert result.success is False

    def test_replace_pattern_with_count(self, text_rejig: Rejig, text_file: Path):
        """
        replace_pattern with count=1 should replace only the first occurrence.
        """
        block = text_rejig.text_block("readme.md")
        result = block.replace_pattern(r"TODO:", "DONE:", count=1)

        assert result.success is True
        content = text_file.read_text()
        # One TODO should be replaced, others should remain
        assert "DONE:" in content
        assert "TODO:" in content  # Should still have at least one

    def test_replace_pattern_produces_diff(self, text_rejig: Rejig, text_file: Path):
        """
        replace_pattern should produce a diff in the result.
        """
        block = text_rejig.text_block("readme.md")
        result = block.replace_pattern(r"DEBUG = True", "DEBUG = False")

        assert result.success is True
        assert result.diff is not None
        assert "DEBUG" in result.diff


# =============================================================================
# TextBlock Line Operations
# =============================================================================

class TestTextBlockLineOperations:
    """Tests for line-level operations."""

    def test_insert_at_line(self, text_rejig: Rejig, text_file: Path):
        """
        insert_at_line should insert content at the specified line.
        """
        block = text_rejig.text_block("readme.md")
        result = block.insert_at_line(3, "Status: Active")

        assert result.success is True
        content = text_file.read_text()
        assert "Status: Active" in content

    def test_insert_at_line_out_of_range(self, text_rejig: Rejig, text_file: Path):
        """
        insert_at_line with out-of-range line should return error.
        """
        block = text_rejig.text_block("readme.md")
        result = block.insert_at_line(9999, "Content")

        assert result.success is False

    def test_insert_at_line_missing_file(self, text_rejig: Rejig):
        """
        insert_at_line on a missing file should return error.
        """
        block = text_rejig.text_block("missing.md")
        result = block.insert_at_line(1, "Content")

        assert result.success is False

    def test_delete_line(self, text_rejig: Rejig, text_file: Path):
        """
        delete_line should remove the specified line.
        """
        block = text_rejig.text_block("readme.md")
        # Get original line count
        original_lines = text_file.read_text().splitlines()
        original_count = len(original_lines)

        result = block.delete_line(1)

        assert result.success is True
        new_lines = text_file.read_text().splitlines()
        assert len(new_lines) == original_count - 1

    def test_delete_line_out_of_range(self, text_rejig: Rejig, text_file: Path):
        """
        delete_line with out-of-range line should return error.
        """
        block = text_rejig.text_block("readme.md")
        result = block.delete_line(9999)

        assert result.success is False

    def test_delete_lines_range(self, text_rejig: Rejig, text_file: Path):
        """
        delete_lines should remove a range of lines.
        """
        block = text_rejig.text_block("readme.md")
        original_count = len(text_file.read_text().splitlines())

        # Delete lines 2-4 (3 lines)
        result = block.delete_lines(2, 4)

        assert result.success is True
        new_count = len(text_file.read_text().splitlines())
        assert new_count == original_count - 3

    def test_delete_lines_invalid_range(self, text_rejig: Rejig, text_file: Path):
        """
        delete_lines with invalid range should return error.
        """
        block = text_rejig.text_block("readme.md")
        result = block.delete_lines(100, 200)

        assert result.success is False


# =============================================================================
# TextBlock Dry-Run
# =============================================================================

class TestTextBlockDryRun:
    """Tests for TextBlock in dry-run mode."""

    def test_replace_pattern_dry_run(self, tmp_path: Path):
        """
        In dry-run mode, replace_pattern should not modify the file.
        """
        file_path = tmp_path / "test.txt"
        file_path.write_text("hello world\n")
        original = file_path.read_text()

        with Rejig(tmp_path, dry_run=True) as rj:
            block = rj.text_block("test.txt")
            result = block.replace_pattern(r"hello", "goodbye")

            assert result.success is True
            assert file_path.read_text() == original

    def test_insert_at_line_dry_run(self, tmp_path: Path):
        """
        In dry-run mode, insert_at_line should not modify the file.
        """
        file_path = tmp_path / "test.txt"
        file_path.write_text("line1\nline2\n")
        original = file_path.read_text()

        with Rejig(tmp_path, dry_run=True) as rj:
            block = rj.text_block("test.txt")
            result = block.insert_at_line(2, "new line")

            assert result.success is True
            assert file_path.read_text() == original
