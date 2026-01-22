"""
Tests for rejig.patching.models module.

This module tests the core data classes for patch representation:
- Change: Individual line changes
- Hunk: Contiguous blocks of changes
- FilePatch: Changes to a single file
- Patch: Complete multi-file patches

Coverage targets:
- Change: type detection, diff line generation
- Hunk: line counting, content extraction, reversal
- FilePatch: status flags, diff generation, reversal
- Patch: aggregation, file lookup, reversal
"""
from __future__ import annotations

from pathlib import Path

import pytest

from rejig.patching.models import (
    Change,
    ChangeType,
    FilePatch,
    Hunk,
    Patch,
    PatchFormat,
)


# =============================================================================
# Change Tests
# =============================================================================

class TestChange:
    """Tests for the Change dataclass."""

    def test_addition_change(self):
        """Test creation of an addition change."""
        change = Change(
            type=ChangeType.ADD,
            content="new line",
            new_line=10,
        )

        assert change.is_addition
        assert not change.is_deletion
        assert not change.is_context
        assert change.content == "new line"
        assert change.old_line is None
        assert change.new_line == 10

    def test_deletion_change(self):
        """Test creation of a deletion change."""
        change = Change(
            type=ChangeType.DELETE,
            content="old line",
            old_line=5,
        )

        assert change.is_deletion
        assert not change.is_addition
        assert not change.is_context
        assert change.old_line == 5
        assert change.new_line is None

    def test_context_change(self):
        """Test creation of a context change."""
        change = Change(
            type=ChangeType.CONTEXT,
            content="unchanged",
            old_line=3,
            new_line=3,
        )

        assert change.is_context
        assert not change.is_addition
        assert not change.is_deletion

    def test_to_diff_line_addition(self):
        """Test diff line generation for addition."""
        change = Change(type=ChangeType.ADD, content="new content")
        assert change.to_diff_line() == "+new content"

    def test_to_diff_line_deletion(self):
        """Test diff line generation for deletion."""
        change = Change(type=ChangeType.DELETE, content="old content")
        assert change.to_diff_line() == "-old content"

    def test_to_diff_line_context(self):
        """Test diff line generation for context."""
        change = Change(type=ChangeType.CONTEXT, content="context")
        assert change.to_diff_line() == " context"


# =============================================================================
# Hunk Tests
# =============================================================================

class TestHunk:
    """Tests for the Hunk dataclass."""

    def test_empty_hunk(self):
        """Test empty hunk properties."""
        hunk = Hunk(old_start=1, old_count=0, new_start=1, new_count=0)

        assert hunk.additions_count == 0
        assert hunk.deletions_count == 0
        assert hunk.additions == []
        assert hunk.deletions == []

    def test_hunk_with_changes(self):
        """Test hunk with mixed changes."""
        hunk = Hunk(
            old_start=10,
            old_count=3,
            new_start=10,
            new_count=4,
            changes=[
                Change(type=ChangeType.CONTEXT, content="unchanged"),
                Change(type=ChangeType.DELETE, content="old line"),
                Change(type=ChangeType.ADD, content="new line 1"),
                Change(type=ChangeType.ADD, content="new line 2"),
                Change(type=ChangeType.CONTEXT, content="also unchanged"),
            ],
        )

        assert hunk.additions_count == 2
        assert hunk.deletions_count == 1
        assert len(hunk.additions) == 2
        assert len(hunk.deletions) == 1

    def test_hunk_header_generation(self):
        """Test @@ header generation."""
        hunk = Hunk(old_start=10, old_count=3, new_start=12, new_count=5)
        assert hunk.to_header() == "@@ -10,3 +12,5 @@"

    def test_hunk_header_with_context(self):
        """Test @@ header with function context."""
        hunk = Hunk(
            old_start=10,
            old_count=3,
            new_start=10,
            new_count=3,
            function_context="def my_function():",
        )
        assert hunk.to_header() == "@@ -10,3 +10,3 @@ def my_function():"

    def test_hunk_get_old_content(self):
        """Test extraction of original content."""
        hunk = Hunk(
            old_start=1,
            old_count=2,
            new_start=1,
            new_count=2,
            changes=[
                Change(type=ChangeType.DELETE, content="old1"),
                Change(type=ChangeType.CONTEXT, content="context"),
                Change(type=ChangeType.ADD, content="new1"),
            ],
        )

        old_content = hunk.get_old_content()
        assert "old1" in old_content
        assert "context" in old_content
        assert "new1" not in old_content

    def test_hunk_get_new_content(self):
        """Test extraction of new content."""
        hunk = Hunk(
            old_start=1,
            old_count=2,
            new_start=1,
            new_count=2,
            changes=[
                Change(type=ChangeType.DELETE, content="old1"),
                Change(type=ChangeType.CONTEXT, content="context"),
                Change(type=ChangeType.ADD, content="new1"),
            ],
        )

        new_content = hunk.get_new_content()
        assert "new1" in new_content
        assert "context" in new_content
        assert "old1" not in new_content

    def test_hunk_reverse(self):
        """Test hunk reversal."""
        hunk = Hunk(
            old_start=10,
            old_count=2,
            new_start=10,
            new_count=3,
            changes=[
                Change(type=ChangeType.DELETE, content="deleted", old_line=10),
                Change(type=ChangeType.ADD, content="added1", new_line=10),
                Change(type=ChangeType.ADD, content="added2", new_line=11),
                Change(type=ChangeType.CONTEXT, content="ctx", old_line=11, new_line=12),
            ],
        )

        reversed_hunk = hunk.reverse()

        # Line counts should swap
        assert reversed_hunk.old_start == 10  # was new_start
        assert reversed_hunk.old_count == 3   # was new_count
        assert reversed_hunk.new_start == 10  # was old_start
        assert reversed_hunk.new_count == 2   # was old_count

        # Additions become deletions and vice versa
        assert reversed_hunk.deletions_count == 2
        assert reversed_hunk.additions_count == 1


# =============================================================================
# FilePatch Tests
# =============================================================================

class TestFilePatch:
    """Tests for the FilePatch dataclass."""

    def test_empty_file_patch(self):
        """Test empty file patch."""
        fp = FilePatch()

        assert fp.path is None
        assert not fp.is_new
        assert not fp.is_deleted
        assert not fp.is_renamed
        assert fp.additions_count == 0
        assert fp.deletions_count == 0

    def test_new_file_patch(self):
        """Test new file patch."""
        fp = FilePatch(
            new_path=Path("new_file.py"),
            is_new=True,
        )

        assert fp.is_new
        assert fp.path == Path("new_file.py")

    def test_deleted_file_patch(self):
        """Test deleted file patch."""
        fp = FilePatch(
            old_path=Path("old_file.py"),
            is_deleted=True,
        )

        assert fp.is_deleted
        assert fp.path == Path("old_file.py")  # Falls back to old_path

    def test_renamed_file_patch(self):
        """Test renamed file patch."""
        fp = FilePatch(
            old_path=Path("old_name.py"),
            new_path=Path("new_name.py"),
            is_renamed=True,
            similarity_index=95,
        )

        assert fp.is_renamed
        assert fp.similarity_index == 95
        assert fp.path == Path("new_name.py")

    def test_file_patch_with_hunks(self):
        """Test file patch with hunks."""
        hunk1 = Hunk(
            old_start=1,
            old_count=1,
            new_start=1,
            new_count=2,
            changes=[
                Change(type=ChangeType.DELETE, content="old"),
                Change(type=ChangeType.ADD, content="new1"),
                Change(type=ChangeType.ADD, content="new2"),
            ],
        )
        hunk2 = Hunk(
            old_start=10,
            old_count=1,
            new_start=11,
            new_count=0,
            changes=[
                Change(type=ChangeType.DELETE, content="removed"),
            ],
        )

        fp = FilePatch(
            old_path=Path("test.py"),
            new_path=Path("test.py"),
            hunks=[hunk1, hunk2],
        )

        assert fp.additions_count == 2
        assert fp.deletions_count == 2
        assert fp.has_changes

    def test_file_patch_reverse(self):
        """Test file patch reversal."""
        fp = FilePatch(
            old_path=Path("old.py"),
            new_path=Path("new.py"),
            is_renamed=True,
            hunks=[
                Hunk(
                    old_start=1,
                    old_count=1,
                    new_start=1,
                    new_count=1,
                    changes=[
                        Change(type=ChangeType.DELETE, content="old"),
                        Change(type=ChangeType.ADD, content="new"),
                    ],
                )
            ],
        )

        reversed_fp = fp.reverse()

        assert reversed_fp.old_path == Path("new.py")
        assert reversed_fp.new_path == Path("old.py")
        assert reversed_fp.is_renamed  # Still a rename
        # Hunk changes should be reversed
        assert reversed_fp.hunks[0].deletions_count == 1
        assert reversed_fp.hunks[0].additions_count == 1


# =============================================================================
# Patch Tests
# =============================================================================

class TestPatch:
    """Tests for the Patch dataclass."""

    def test_empty_patch(self):
        """Test empty patch."""
        patch = Patch()

        assert len(patch) == 0
        assert patch.file_count == 0
        assert patch.total_additions == 0
        assert patch.total_deletions == 0
        assert not bool(patch)

    def test_patch_with_files(self):
        """Test patch with multiple files."""
        fp1 = FilePatch(
            new_path=Path("file1.py"),
            hunks=[
                Hunk(
                    old_start=1,
                    old_count=0,
                    new_start=1,
                    new_count=2,
                    changes=[
                        Change(type=ChangeType.ADD, content="line1"),
                        Change(type=ChangeType.ADD, content="line2"),
                    ],
                )
            ],
        )
        fp2 = FilePatch(
            new_path=Path("file2.py"),
            hunks=[
                Hunk(
                    old_start=5,
                    old_count=1,
                    new_start=5,
                    new_count=0,
                    changes=[
                        Change(type=ChangeType.DELETE, content="removed"),
                    ],
                )
            ],
        )

        patch = Patch(files=[fp1, fp2])

        assert len(patch) == 2
        assert patch.file_count == 2
        assert patch.total_additions == 2
        assert patch.total_deletions == 1
        assert bool(patch)

    def test_patch_file_lookup(self):
        """Test looking up a file by path."""
        fp = FilePatch(new_path=Path("target.py"))
        patch = Patch(files=[fp])

        found = patch.get_file(Path("target.py"))
        assert found is fp

        not_found = patch.get_file(Path("missing.py"))
        assert not_found is None

    def test_patch_paths(self):
        """Test getting all paths."""
        patch = Patch(files=[
            FilePatch(new_path=Path("a.py")),
            FilePatch(new_path=Path("b.py")),
        ])

        paths = patch.paths
        assert len(paths) == 2
        assert Path("a.py") in paths
        assert Path("b.py") in paths

    def test_patch_file_type_filters(self):
        """Test filtering by file type."""
        patch = Patch(files=[
            FilePatch(new_path=Path("new.py"), is_new=True),
            FilePatch(old_path=Path("deleted.py"), is_deleted=True),
            FilePatch(old_path=Path("old.py"), new_path=Path("renamed.py"), is_renamed=True),
            FilePatch(old_path=Path("modified.py"), new_path=Path("modified.py")),
        ])

        assert len(patch.new_files) == 1
        assert len(patch.deleted_files) == 1
        assert len(patch.renamed_files) == 1
        assert len(patch.modified_files) == 1

    def test_patch_reverse(self):
        """Test patch reversal."""
        patch = Patch(files=[
            FilePatch(
                old_path=Path("test.py"),
                new_path=Path("test.py"),
                hunks=[
                    Hunk(
                        old_start=1,
                        old_count=1,
                        new_start=1,
                        new_count=2,
                        changes=[
                            Change(type=ChangeType.DELETE, content="old"),
                            Change(type=ChangeType.ADD, content="new1"),
                            Change(type=ChangeType.ADD, content="new2"),
                        ],
                    )
                ],
            )
        ])

        reversed_patch = patch.reverse()

        # Should have same number of files
        assert len(reversed_patch) == 1
        # But changes should be reversed
        fp = reversed_patch.files[0]
        assert fp.additions_count == 1  # Was 2 deletions
        assert fp.deletions_count == 2  # Was 1 addition

    def test_patch_iteration(self):
        """Test iterating over patch files."""
        patch = Patch(files=[
            FilePatch(new_path=Path("a.py")),
            FilePatch(new_path=Path("b.py")),
        ])

        files = list(patch)
        assert len(files) == 2

    def test_patch_summary(self):
        """Test summary generation."""
        patch = Patch(files=[
            FilePatch(
                new_path=Path("test.py"),
                hunks=[
                    Hunk(
                        old_start=1,
                        old_count=1,
                        new_start=1,
                        new_count=3,
                        changes=[
                            Change(type=ChangeType.DELETE, content="old"),
                            Change(type=ChangeType.ADD, content="new1"),
                            Change(type=ChangeType.ADD, content="new2"),
                            Change(type=ChangeType.ADD, content="new3"),
                        ],
                    )
                ],
            )
        ])

        summary = patch.summary()
        assert "1 file(s)" in summary
        assert "+3/-1" in summary


# =============================================================================
# Format Tests
# =============================================================================

class TestPatchFormat:
    """Tests for PatchFormat enum."""

    def test_unified_format(self):
        """Test UNIFIED format value."""
        assert PatchFormat.UNIFIED.value == "unified"

    def test_git_format(self):
        """Test GIT format value."""
        assert PatchFormat.GIT.value == "git"
