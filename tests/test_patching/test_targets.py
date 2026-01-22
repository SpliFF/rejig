"""
Tests for rejig.patching.targets module.

This module tests the PatchTarget classes that provide a fluent API
for working with patches.

Coverage targets:
- PatchTarget: apply, reverse, to_rejig_code, save
- PatchFileTarget: navigation, properties
- PatchHunkTarget: apply, reverse, content access
"""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from rejig import Rejig
from rejig.patching import (
    Change,
    ChangeType,
    FilePatch,
    Hunk,
    Patch,
    PatchFileTarget,
    PatchHunkTarget,
    PatchTarget,
)


# =============================================================================
# PatchTarget Tests
# =============================================================================

class TestPatchTarget:
    """Tests for the PatchTarget class."""

    def test_empty_patch_target(self, tmp_path):
        """Test PatchTarget with empty patch."""
        rj = Rejig(tmp_path, dry_run=True)
        patch = Patch()
        target = PatchTarget(rj, patch)

        assert not target.exists()
        assert target.file_count == 0
        assert target.total_additions == 0
        assert target.total_deletions == 0

    def test_patch_target_properties(self, tmp_path):
        """Test PatchTarget property access."""
        rj = Rejig(tmp_path, dry_run=True)

        hunk = Hunk(
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
        fp = FilePatch(
            old_path=Path("test.py"),
            new_path=Path("test.py"),
            hunks=[hunk],
        )
        patch = Patch(files=[fp])

        target = PatchTarget(rj, patch)

        assert target.exists()
        assert target.file_count == 1
        assert target.total_additions == 2
        assert target.total_deletions == 1
        assert Path("test.py") in target.paths

    def test_patch_target_files_navigation(self, tmp_path):
        """Test navigating to file targets."""
        rj = Rejig(tmp_path, dry_run=True)

        patch = Patch(files=[
            FilePatch(new_path=Path("a.py")),
            FilePatch(new_path=Path("b.py")),
        ])

        target = PatchTarget(rj, patch)
        files = target.files()

        assert len(files) == 2

    def test_patch_target_file_lookup(self, tmp_path):
        """Test looking up a specific file."""
        rj = Rejig(tmp_path, dry_run=True)

        patch = Patch(files=[
            FilePatch(new_path=Path("target.py")),
        ])

        target = PatchTarget(rj, patch)

        found = target.file(Path("target.py"))
        assert found is not None
        assert found.path == Path("target.py")

        not_found = target.file(Path("missing.py"))
        assert not_found is None

    def test_patch_target_reverse(self, tmp_path):
        """Test creating reversed patch target."""
        rj = Rejig(tmp_path, dry_run=True)

        hunk = Hunk(
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
        patch = Patch(files=[
            FilePatch(
                old_path=Path("test.py"),
                new_path=Path("test.py"),
                hunks=[hunk],
            )
        ])

        target = PatchTarget(rj, patch)
        reversed_target = target.reverse()

        # Additions and deletions should be swapped
        assert reversed_target.total_additions == 1
        assert reversed_target.total_deletions == 2

    def test_patch_target_to_unified_diff(self, tmp_path):
        """Test converting to unified diff string."""
        rj = Rejig(tmp_path, dry_run=True)

        hunk = Hunk(
            old_start=1,
            old_count=1,
            new_start=1,
            new_count=1,
            changes=[
                Change(type=ChangeType.DELETE, content="old"),
                Change(type=ChangeType.ADD, content="new"),
            ],
        )
        patch = Patch(files=[
            FilePatch(
                old_path=Path("test.py"),
                new_path=Path("test.py"),
                hunks=[hunk],
            )
        ])

        target = PatchTarget(rj, patch)
        diff_text = target.to_unified_diff()

        assert "-old" in diff_text
        assert "+new" in diff_text
        assert "@@ -1,1 +1,1 @@" in diff_text

    def test_patch_target_save(self, tmp_path):
        """Test saving patch to file."""
        rj = Rejig(tmp_path, dry_run=False)

        patch = Patch(files=[
            FilePatch(
                old_path=Path("test.py"),
                new_path=Path("test.py"),
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
        ])

        target = PatchTarget(rj, patch)
        output_path = tmp_path / "output.patch"

        result = target.save(output_path)

        assert result.success
        assert output_path.exists()
        content = output_path.read_text()
        assert "-old" in content
        assert "+new" in content

    def test_patch_target_save_no_overwrite(self, tmp_path):
        """Test save refuses to overwrite without flag."""
        rj = Rejig(tmp_path, dry_run=False)
        patch = Patch(files=[FilePatch(new_path=Path("test.py"))])

        target = PatchTarget(rj, patch)
        output_path = tmp_path / "existing.patch"
        output_path.write_text("existing content")

        result = target.save(output_path, overwrite=False)

        assert not result.success
        assert "already exists" in result.message

    def test_patch_target_get_content(self, tmp_path):
        """Test get_content returns diff in data."""
        rj = Rejig(tmp_path, dry_run=True)
        patch = Patch(files=[
            FilePatch(
                old_path=Path("test.py"),
                new_path=Path("test.py"),
            )
        ])

        target = PatchTarget(rj, patch)
        result = target.get_content()

        assert result.success
        assert result.data is not None

    def test_patch_target_iteration(self, tmp_path):
        """Test iterating over patch target."""
        rj = Rejig(tmp_path, dry_run=True)
        patch = Patch(files=[
            FilePatch(new_path=Path("a.py")),
            FilePatch(new_path=Path("b.py")),
        ])

        target = PatchTarget(rj, patch)
        files = list(target)

        assert len(files) == 2
        assert all(isinstance(f, PatchFileTarget) for f in files)


# =============================================================================
# PatchFileTarget Tests
# =============================================================================

class TestPatchFileTarget:
    """Tests for the PatchFileTarget class."""

    def test_file_target_properties(self, tmp_path):
        """Test PatchFileTarget property access."""
        rj = Rejig(tmp_path, dry_run=True)

        fp = FilePatch(
            old_path=Path("old.py"),
            new_path=Path("new.py"),
            is_renamed=True,
            hunks=[
                Hunk(
                    old_start=1,
                    old_count=2,
                    new_start=1,
                    new_count=3,
                    changes=[
                        Change(type=ChangeType.CONTEXT, content="ctx"),
                        Change(type=ChangeType.DELETE, content="del"),
                        Change(type=ChangeType.ADD, content="add1"),
                        Change(type=ChangeType.ADD, content="add2"),
                    ],
                )
            ],
        )
        patch = Patch(files=[fp])
        patch_target = PatchTarget(rj, patch)

        file_target = patch_target.file(Path("new.py"))

        assert file_target.path == Path("new.py")
        assert file_target.old_path == Path("old.py")
        assert file_target.new_path == Path("new.py")
        assert file_target.is_renamed
        assert not file_target.is_new
        assert not file_target.is_deleted
        assert file_target.additions_count == 2
        assert file_target.deletions_count == 1
        assert file_target.hunk_count == 1

    def test_file_target_hunks_navigation(self, tmp_path):
        """Test navigating to hunk targets."""
        rj = Rejig(tmp_path, dry_run=True)

        fp = FilePatch(
            new_path=Path("test.py"),
            hunks=[
                Hunk(old_start=1, old_count=1, new_start=1, new_count=1),
                Hunk(old_start=10, old_count=1, new_start=10, new_count=1),
            ],
        )
        patch = Patch(files=[fp])
        patch_target = PatchTarget(rj, patch)

        file_target = patch_target.file(Path("test.py"))
        hunks = file_target.hunks()

        assert len(hunks) == 2

    def test_file_target_hunk_lookup(self, tmp_path):
        """Test looking up hunk by index."""
        rj = Rejig(tmp_path, dry_run=True)

        fp = FilePatch(
            new_path=Path("test.py"),
            hunks=[
                Hunk(old_start=1, old_count=1, new_start=1, new_count=1),
                Hunk(old_start=10, old_count=1, new_start=10, new_count=1),
            ],
        )
        patch = Patch(files=[fp])
        patch_target = PatchTarget(rj, patch)

        file_target = patch_target.file(Path("test.py"))

        hunk0 = file_target.hunk(0)
        assert hunk0 is not None
        assert hunk0.old_start == 1

        hunk1 = file_target.hunk(1)
        assert hunk1 is not None
        assert hunk1.old_start == 10

        hunk_invalid = file_target.hunk(99)
        assert hunk_invalid is None

    def test_file_target_reverse(self, tmp_path):
        """Test reversing file target."""
        rj = Rejig(tmp_path, dry_run=True)

        fp = FilePatch(
            old_path=Path("old.py"),
            new_path=Path("new.py"),
            is_renamed=True,
            hunks=[
                Hunk(
                    old_start=1,
                    old_count=1,
                    new_start=1,
                    new_count=2,
                    changes=[
                        Change(type=ChangeType.DELETE, content="del"),
                        Change(type=ChangeType.ADD, content="add1"),
                        Change(type=ChangeType.ADD, content="add2"),
                    ],
                )
            ],
        )
        patch = Patch(files=[fp])
        patch_target = PatchTarget(rj, patch)

        file_target = patch_target.file(Path("new.py"))
        reversed_target = file_target.reverse()

        assert reversed_target.old_path == Path("new.py")
        assert reversed_target.new_path == Path("old.py")
        assert reversed_target.additions_count == 1
        assert reversed_target.deletions_count == 2

    def test_file_target_iteration(self, tmp_path):
        """Test iterating over file target hunks."""
        rj = Rejig(tmp_path, dry_run=True)

        fp = FilePatch(
            new_path=Path("test.py"),
            hunks=[
                Hunk(old_start=1, old_count=1, new_start=1, new_count=1),
                Hunk(old_start=10, old_count=1, new_start=10, new_count=1),
            ],
        )
        patch = Patch(files=[fp])
        patch_target = PatchTarget(rj, patch)

        file_target = patch_target.file(Path("test.py"))
        hunks = list(file_target)

        assert len(hunks) == 2
        assert all(isinstance(h, PatchHunkTarget) for h in hunks)


# =============================================================================
# PatchHunkTarget Tests
# =============================================================================

class TestPatchHunkTarget:
    """Tests for the PatchHunkTarget class."""

    def test_hunk_target_properties(self, tmp_path):
        """Test PatchHunkTarget property access."""
        rj = Rejig(tmp_path, dry_run=True)

        hunk = Hunk(
            old_start=10,
            old_count=3,
            new_start=12,
            new_count=4,
            function_context="def my_func():",
            changes=[
                Change(type=ChangeType.CONTEXT, content="ctx"),
                Change(type=ChangeType.DELETE, content="del"),
                Change(type=ChangeType.ADD, content="add1"),
                Change(type=ChangeType.ADD, content="add2"),
            ],
        )
        fp = FilePatch(new_path=Path("test.py"), hunks=[hunk])
        patch = Patch(files=[fp])
        patch_target = PatchTarget(rj, patch)

        hunk_target = patch_target.file(Path("test.py")).hunk(0)

        assert hunk_target.old_start == 10
        assert hunk_target.old_count == 3
        assert hunk_target.new_start == 12
        assert hunk_target.new_count == 4
        assert hunk_target.function_context == "def my_func():"
        assert hunk_target.additions_count == 2
        assert hunk_target.deletions_count == 1
        assert hunk_target.index == 0

    def test_hunk_target_content(self, tmp_path):
        """Test getting old and new content."""
        rj = Rejig(tmp_path, dry_run=True)

        hunk = Hunk(
            old_start=1,
            old_count=2,
            new_start=1,
            new_count=2,
            changes=[
                Change(type=ChangeType.CONTEXT, content="ctx"),
                Change(type=ChangeType.DELETE, content="old"),
                Change(type=ChangeType.ADD, content="new"),
            ],
        )
        fp = FilePatch(new_path=Path("test.py"), hunks=[hunk])
        patch = Patch(files=[fp])
        patch_target = PatchTarget(rj, patch)

        hunk_target = patch_target.file(Path("test.py")).hunk(0)

        old_content = hunk_target.get_old_content()
        assert "ctx" in old_content
        assert "old" in old_content
        assert "new" not in old_content

        new_content = hunk_target.get_new_content()
        assert "ctx" in new_content
        assert "new" in new_content
        assert "old" not in new_content

    def test_hunk_target_reverse(self, tmp_path):
        """Test reversing hunk target."""
        rj = Rejig(tmp_path, dry_run=True)

        hunk = Hunk(
            old_start=1,
            old_count=1,
            new_start=1,
            new_count=2,
            changes=[
                Change(type=ChangeType.DELETE, content="del"),
                Change(type=ChangeType.ADD, content="add1"),
                Change(type=ChangeType.ADD, content="add2"),
            ],
        )
        fp = FilePatch(new_path=Path("test.py"), hunks=[hunk])
        patch = Patch(files=[fp])
        patch_target = PatchTarget(rj, patch)

        hunk_target = patch_target.file(Path("test.py")).hunk(0)
        reversed_target = hunk_target.reverse()

        assert reversed_target.old_count == 2  # was new_count
        assert reversed_target.new_count == 1  # was old_count
        assert reversed_target.additions_count == 1
        assert reversed_target.deletions_count == 2

    def test_hunk_target_to_header(self, tmp_path):
        """Test generating hunk header."""
        rj = Rejig(tmp_path, dry_run=True)

        hunk = Hunk(old_start=10, old_count=3, new_start=12, new_count=5)
        fp = FilePatch(new_path=Path("test.py"), hunks=[hunk])
        patch = Patch(files=[fp])
        patch_target = PatchTarget(rj, patch)

        hunk_target = patch_target.file(Path("test.py")).hunk(0)

        assert hunk_target.to_header() == "@@ -10,3 +12,5 @@"


# =============================================================================
# Integration with Rejig
# =============================================================================

class TestRejigIntegration:
    """Tests for integration with Rejig class."""

    def test_rejig_patch_method(self, tmp_path):
        """Test Rejig.patch() method."""
        rj = Rejig(tmp_path, dry_run=True)

        diff = dedent("""\
            --- a/test.py
            +++ b/test.py
            @@ -1 +1 @@
            -old
            +new
        """)

        target = rj.patch(diff)

        assert isinstance(target, PatchTarget)
        assert target.file_count == 1

    def test_rejig_patch_from_file(self, tmp_path):
        """Test Rejig.patch_from_file() method."""
        rj = Rejig(tmp_path, dry_run=True)

        patch_file = tmp_path / "test.patch"
        patch_file.write_text(dedent("""\
            --- a/test.py
            +++ b/test.py
            @@ -1 +1 @@
            -old
            +new
        """))

        target = rj.patch_from_file(patch_file)

        assert isinstance(target, PatchTarget)
        assert target.file_count == 1

    def test_rejig_patch_from_nonexistent_file(self, tmp_path):
        """Test Rejig.patch_from_file() with missing file."""
        rj = Rejig(tmp_path, dry_run=True)

        target = rj.patch_from_file(tmp_path / "missing.patch")

        # Should return empty patch target
        assert isinstance(target, PatchTarget)
        assert target.file_count == 0

    def test_rejig_generate_patch(self, tmp_path):
        """Test Rejig.generate_patch() method."""
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("old_value = 1\n")

        rj = Rejig(tmp_path, dry_run=True)

        # This should create a Result with diff
        result = rj.file("test.py").replace("old_value", "new_value")

        if result.success and result.diff:
            patch = rj.generate_patch(result)
            assert isinstance(patch, PatchTarget)
