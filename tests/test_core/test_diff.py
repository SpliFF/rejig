"""
Tests for rejig.core.diff module.

This module tests the diff generation and combination utilities that underpin
all file modification reporting in Rejig.

Coverage targets:
- generate_diff: identical content, simple changes, multi-line changes,
  empty content, trailing newline handling
- combine_diffs: empty dict, single diff, multiple diffs, ordering, empty diff filtering
"""
from __future__ import annotations

from pathlib import Path

import pytest

from rejig.core.diff import combine_diffs, generate_diff


# =============================================================================
# generate_diff Tests
# =============================================================================

class TestGenerateDiff:
    """Tests for generate_diff function."""

    def test_identical_content_returns_empty_string(self):
        """
        When original and modified are identical, generate_diff should return
        an empty string (no changes).
        """
        content = "def hello():\n    pass\n"
        result = generate_diff(content, content, Path("test.py"))

        assert result == ""

    def test_simple_line_change(self):
        """
        A single-line change should produce a unified diff with correct
        --- and +++ headers and the changed lines.
        """
        original = "hello\n"
        modified = "hello world\n"
        path = Path("test.py")

        result = generate_diff(original, modified, path)

        assert "--- a/test.py" in result
        assert "+++ b/test.py" in result
        assert "-hello" in result
        assert "+hello world" in result

    def test_multiline_addition(self):
        """
        Adding lines should produce a diff showing the new lines with +.
        """
        original = "line1\nline2\n"
        modified = "line1\nline_new\nline2\n"
        path = Path("module.py")

        result = generate_diff(original, modified, path)

        assert "+line_new" in result
        assert "--- a/module.py" in result
        assert "+++ b/module.py" in result

    def test_multiline_deletion(self):
        """
        Removing lines should produce a diff showing the removed lines with -.
        """
        original = "line1\nline2\nline3\n"
        modified = "line1\nline3\n"
        path = Path("module.py")

        result = generate_diff(original, modified, path)

        assert "-line2" in result

    def test_empty_original(self):
        """
        Diff from empty content to non-empty should show all lines as additions.
        """
        original = ""
        modified = "new content\n"
        path = Path("new_file.py")

        result = generate_diff(original, modified, path)

        assert "+new content" in result

    def test_empty_modified(self):
        """
        Diff from non-empty to empty should show all lines as deletions.
        """
        original = "old content\n"
        modified = ""
        path = Path("deleted_file.py")

        result = generate_diff(original, modified, path)

        assert "-old content" in result

    def test_trailing_newline_handling(self):
        """
        Content without trailing newlines should still produce valid diffs.
        The function should normalize newlines for proper diff formatting.
        """
        original = "no trailing newline"
        modified = "changed no trailing newline"
        path = Path("test.py")

        result = generate_diff(original, modified, path)

        # Should still produce a valid diff
        assert "---" in result
        assert "+++" in result

    def test_context_lines_parameter(self):
        """
        The context_lines parameter should control how many unchanged lines
        appear around changes.
        """
        lines = [f"line{i}\n" for i in range(20)]
        original = "".join(lines)
        # Change line 10
        modified_lines = lines.copy()
        modified_lines[10] = "changed_line10\n"
        modified = "".join(modified_lines)
        path = Path("test.py")

        # With 0 context lines
        result_0 = generate_diff(original, modified, path, context_lines=0)
        # With 5 context lines
        result_5 = generate_diff(original, modified, path, context_lines=5)

        # More context should produce a longer diff
        assert len(result_5) > len(result_0)

    def test_path_appears_in_header(self):
        """
        The file path should appear in the diff header in git-style format.
        """
        original = "old\n"
        modified = "new\n"
        path = Path("src/mymodule/utils.py")

        result = generate_diff(original, modified, path)

        assert "a/src/mymodule/utils.py" in result
        assert "b/src/mymodule/utils.py" in result

    def test_both_empty_returns_empty(self):
        """
        When both original and modified are empty, should return empty string.
        """
        result = generate_diff("", "", Path("test.py"))

        assert result == ""

    def test_unicode_content(self):
        """
        Diff should handle unicode content correctly.
        """
        original = "hello = '\u4e16\u754c'\n"
        modified = "hello = '\u4e16\u754c!'\n"
        path = Path("unicode.py")

        result = generate_diff(original, modified, path)

        assert "-hello = '\u4e16\u754c'" in result
        assert "+hello = '\u4e16\u754c!'" in result


# =============================================================================
# combine_diffs Tests
# =============================================================================

class TestCombineDiffs:
    """Tests for combine_diffs function."""

    def test_empty_dict_returns_empty_string(self):
        """
        An empty dict should produce an empty combined diff.
        """
        result = combine_diffs({})

        assert result == ""

    def test_single_diff(self):
        """
        A single diff entry should be returned as-is.
        """
        diff = "--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new\n"
        diffs = {Path("file.py"): diff}

        result = combine_diffs(diffs)

        assert result == diff

    def test_multiple_diffs_combined(self):
        """
        Multiple diff entries should be combined with newlines between them.
        """
        diff1 = "--- a/file1.py\n+++ b/file1.py\n@@ -1 +1 @@\n-old1\n+new1\n"
        diff2 = "--- a/file2.py\n+++ b/file2.py\n@@ -1 +1 @@\n-old2\n+new2\n"

        diffs = {
            Path("file1.py"): diff1,
            Path("file2.py"): diff2,
        }

        result = combine_diffs(diffs)

        assert "file1.py" in result
        assert "file2.py" in result
        assert "-old1" in result
        assert "+new1" in result
        assert "-old2" in result
        assert "+new2" in result

    def test_diffs_sorted_by_path(self):
        """
        Combined diffs should be sorted by file path for deterministic output.
        """
        diff_z = "--- a/z.py\n+++ b/z.py\n@@ -1 +1 @@\n-z\n+Z\n"
        diff_a = "--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-a\n+A\n"

        diffs = {
            Path("z.py"): diff_z,
            Path("a.py"): diff_a,
        }

        result = combine_diffs(diffs)

        # a.py should come before z.py
        a_pos = result.index("a.py")
        z_pos = result.index("z.py")
        assert a_pos < z_pos

    def test_empty_diffs_filtered_out(self):
        """
        Empty diff entries should be filtered out from the combined result.
        """
        diff1 = "--- a/file1.py\n+++ b/file1.py\n@@ -1 +1 @@\n-old\n+new\n"

        diffs = {
            Path("file1.py"): diff1,
            Path("unchanged.py"): "",  # Empty diff
        }

        result = combine_diffs(diffs)

        assert "file1.py" in result
        assert "unchanged.py" not in result

    def test_all_empty_diffs_returns_empty(self):
        """
        If all diffs are empty, should return empty string.
        """
        diffs = {
            Path("file1.py"): "",
            Path("file2.py"): "",
        }

        result = combine_diffs(diffs)

        assert result == ""
