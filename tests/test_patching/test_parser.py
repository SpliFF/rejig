"""
Tests for rejig.patching.parser module.

This module tests the PatchParser class for parsing unified and git diffs
into structured Patch objects.

Coverage targets:
- Unified diff parsing (diff -u format)
- Git diff parsing (git diff format)
- File headers, hunks, and change lines
- Edge cases (empty patches, binary files, renames)
"""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from rejig.patching.models import ChangeType, PatchFormat
from rejig.patching.parser import PatchParser, parse_patch, parse_patch_file


# =============================================================================
# Basic Parsing Tests
# =============================================================================

class TestBasicParsing:
    """Tests for basic diff parsing functionality."""

    def test_empty_patch(self):
        """Test parsing empty input."""
        parser = PatchParser()
        patch = parser.parse("")

        assert len(patch) == 0

    def test_whitespace_only_patch(self):
        """Test parsing whitespace-only input."""
        parser = PatchParser()
        patch = parser.parse("   \n\n   \t\n")

        assert len(patch) == 0

    def test_simple_unified_diff(self):
        """Test parsing a simple unified diff."""
        diff = dedent("""\
            --- a/test.py
            +++ b/test.py
            @@ -1,3 +1,3 @@
             line1
            -old line
            +new line
             line3
        """)

        parser = PatchParser()
        patch = parser.parse(diff)

        assert len(patch) == 1
        assert patch.files[0].old_path == Path("test.py")
        assert patch.files[0].new_path == Path("test.py")
        assert len(patch.files[0].hunks) == 1

        hunk = patch.files[0].hunks[0]
        assert hunk.old_start == 1
        assert hunk.old_count == 3
        assert hunk.new_start == 1
        assert hunk.new_count == 3
        assert hunk.additions_count == 1
        assert hunk.deletions_count == 1

    def test_multiple_hunks(self):
        """Test parsing a file with multiple hunks."""
        diff = dedent("""\
            --- a/test.py
            +++ b/test.py
            @@ -1,3 +1,4 @@
             first
            +inserted
             second
             third
            @@ -10,2 +11,1 @@
            -removed
             kept
        """)

        parser = PatchParser()
        patch = parser.parse(diff)

        assert len(patch.files[0].hunks) == 2
        assert patch.files[0].hunks[0].additions_count == 1
        assert patch.files[0].hunks[1].deletions_count == 1

    def test_multiple_files(self):
        """Test parsing a patch with multiple files."""
        diff = dedent("""\
            --- a/file1.py
            +++ b/file1.py
            @@ -1 +1 @@
            -old1
            +new1
            --- a/file2.py
            +++ b/file2.py
            @@ -1 +1 @@
            -old2
            +new2
        """)

        parser = PatchParser()
        patch = parser.parse(diff)

        assert len(patch) == 2
        assert patch.files[0].new_path == Path("file1.py")
        assert patch.files[1].new_path == Path("file2.py")


# =============================================================================
# Git Format Tests
# =============================================================================

class TestGitFormat:
    """Tests for git diff format parsing."""

    def test_git_diff_detection(self):
        """Test detection of git diff format."""
        diff = dedent("""\
            diff --git a/test.py b/test.py
            --- a/test.py
            +++ b/test.py
            @@ -1 +1 @@
            -old
            +new
        """)

        parser = PatchParser()
        patch = parser.parse(diff)

        assert patch.format == PatchFormat.GIT

    def test_git_new_file(self):
        """Test parsing git new file mode."""
        diff = dedent("""\
            diff --git a/new.py b/new.py
            new file mode 100644
            --- /dev/null
            +++ b/new.py
            @@ -0,0 +1,2 @@
            +line1
            +line2
        """)

        parser = PatchParser()
        patch = parser.parse(diff)

        fp = patch.files[0]
        assert fp.is_new
        assert fp.new_path == Path("new.py")
        assert fp.old_path is None

    def test_git_deleted_file(self):
        """Test parsing git deleted file mode."""
        diff = dedent("""\
            diff --git a/deleted.py b/deleted.py
            deleted file mode 100644
            --- a/deleted.py
            +++ /dev/null
            @@ -1,2 +0,0 @@
            -line1
            -line2
        """)

        parser = PatchParser()
        patch = parser.parse(diff)

        fp = patch.files[0]
        assert fp.is_deleted
        assert fp.old_path == Path("deleted.py")
        assert fp.new_path is None

    def test_git_renamed_file(self):
        """Test parsing git rename."""
        diff = dedent("""\
            diff --git a/old_name.py b/new_name.py
            similarity index 95%
            rename from old_name.py
            rename to new_name.py
        """)

        parser = PatchParser()
        patch = parser.parse(diff)

        fp = patch.files[0]
        assert fp.is_renamed
        assert fp.old_path == Path("old_name.py")
        assert fp.new_path == Path("new_name.py")
        assert fp.similarity_index == 95

    def test_git_mode_change(self):
        """Test parsing git mode changes."""
        diff = dedent("""\
            diff --git a/script.sh b/script.sh
            old mode 100644
            new mode 100755
            --- a/script.sh
            +++ b/script.sh
            @@ -1 +1 @@
            -old
            +new
        """)

        parser = PatchParser()
        patch = parser.parse(diff)

        fp = patch.files[0]
        assert fp.old_mode == "100644"
        assert fp.new_mode == "100755"


# =============================================================================
# Hunk Header Tests
# =============================================================================

class TestHunkHeaders:
    """Tests for hunk header parsing."""

    def test_hunk_with_function_context(self):
        """Test parsing hunk with function context."""
        diff = dedent("""\
            --- a/test.py
            +++ b/test.py
            @@ -10,3 +10,4 @@ def my_function():
                 pass
            +    added
                 return
        """)

        parser = PatchParser()
        patch = parser.parse(diff)

        hunk = patch.files[0].hunks[0]
        assert hunk.function_context == "def my_function():"

    def test_hunk_single_line_old(self):
        """Test parsing hunk with single line (no count)."""
        diff = dedent("""\
            --- a/test.py
            +++ b/test.py
            @@ -1 +1,2 @@
            -old
            +new1
            +new2
        """)

        parser = PatchParser()
        patch = parser.parse(diff)

        hunk = patch.files[0].hunks[0]
        assert hunk.old_count == 1  # Default when count omitted
        assert hunk.new_count == 2


# =============================================================================
# Line Number Tests
# =============================================================================

class TestLineNumbers:
    """Tests for line number assignment."""

    def test_line_numbers_assigned(self):
        """Test that line numbers are assigned to changes."""
        diff = dedent("""\
            --- a/test.py
            +++ b/test.py
            @@ -1,3 +1,3 @@
             line1
            -old
            +new
             line3
        """)

        parser = PatchParser()
        patch = parser.parse(diff)

        hunk = patch.files[0].hunks[0]
        changes = hunk.changes

        # Context line at position 1
        assert changes[0].old_line == 1
        assert changes[0].new_line == 1

        # Deletion at position 2 (old file only)
        assert changes[1].old_line == 2
        assert changes[1].new_line is None

        # Addition at position 2 (new file only)
        assert changes[2].old_line is None
        assert changes[2].new_line == 2

        # Context line at position 3
        assert changes[3].old_line == 3
        assert changes[3].new_line == 3


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases in parsing."""

    def test_no_newline_at_end(self):
        """Test parsing patch with 'no newline at end of file' marker."""
        diff = dedent("""\
            --- a/test.py
            +++ b/test.py
            @@ -1 +1 @@
            -old
            \\ No newline at end of file
            +new
            \\ No newline at end of file
        """)

        parser = PatchParser()
        patch = parser.parse(diff)

        # Should still parse correctly, ignoring the marker
        assert patch.files[0].hunks[0].deletions_count == 1
        assert patch.files[0].hunks[0].additions_count == 1

    def test_empty_lines_in_context(self):
        """Test parsing with empty context lines."""
        diff = dedent("""\
            --- a/test.py
            +++ b/test.py
            @@ -1,4 +1,4 @@
             line1

            -old
            +new
             line4
        """)

        parser = PatchParser()
        patch = parser.parse(diff)

        # Empty line should be parsed as context
        hunk = patch.files[0].hunks[0]
        assert len(hunk.changes) == 5


# =============================================================================
# Result-based Parsing
# =============================================================================

class TestParseToResult:
    """Tests for parse_to_result method."""

    def test_successful_parse_result(self):
        """Test successful parse returns success Result."""
        diff = dedent("""\
            --- a/test.py
            +++ b/test.py
            @@ -1 +1 @@
            -old
            +new
        """)

        parser = PatchParser()
        result = parser.parse_to_result(diff)

        assert result.success
        assert "1 file" in result.message
        assert result.data is not None

    def test_empty_parse_result(self):
        """Test parsing empty string returns success with empty patch."""
        parser = PatchParser()
        result = parser.parse_to_result("")

        assert result.success
        assert result.data.file_count == 0


# =============================================================================
# Convenience Functions
# =============================================================================

class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_parse_patch_function(self):
        """Test parse_patch convenience function."""
        diff = dedent("""\
            --- a/test.py
            +++ b/test.py
            @@ -1 +1 @@
            -old
            +new
        """)

        patch = parse_patch(diff)

        assert len(patch) == 1

    def test_parse_patch_file_not_found(self, tmp_path):
        """Test parse_patch_file with non-existent file."""
        result = parse_patch_file(tmp_path / "nonexistent.patch")

        assert result is None

    def test_parse_patch_file_exists(self, tmp_path):
        """Test parse_patch_file with existing file."""
        patch_file = tmp_path / "test.patch"
        patch_file.write_text(dedent("""\
            --- a/test.py
            +++ b/test.py
            @@ -1 +1 @@
            -old
            +new
        """))

        patch = parse_patch_file(patch_file)

        assert patch is not None
        assert len(patch) == 1


# =============================================================================
# Integration Tests
# =============================================================================

class TestParserIntegration:
    """Integration tests for parser with real-world-like diffs."""

    def test_realistic_git_diff(self):
        """Test parsing a realistic git diff output."""
        diff = dedent("""\
            diff --git a/src/module.py b/src/module.py
            index abc1234..def5678 100644
            --- a/src/module.py
            +++ b/src/module.py
            @@ -10,6 +10,7 @@ class MyClass:
                 def __init__(self):
                     self.value = 0
            +        self.name = ""

                 def process(self):
                     return self.value
            @@ -25,4 +26,8 @@ class MyClass:
                 def helper(self):
            -        pass
            +        # Implementation
            +        result = self._compute()
            +        return result
            +
        """)

        parser = PatchParser()
        patch = parser.parse(diff)

        assert patch.format == PatchFormat.GIT
        assert len(patch) == 1
        assert len(patch.files[0].hunks) == 2

        # First hunk adds one line
        assert patch.files[0].hunks[0].additions_count == 1
        assert patch.files[0].hunks[0].deletions_count == 0

        # Second hunk removes 1, adds 4
        assert patch.files[0].hunks[1].additions_count == 4
        assert patch.files[0].hunks[1].deletions_count == 1
