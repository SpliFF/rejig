"""
Tests for script generation from patches.

This module tests the to_script() and save_script() methods
that generate executable Python scripts from patches.

Coverage targets:
- PatchConverter.to_script(): Generate complete scripts
- PatchConverter.save_script(): Save scripts to files
- PatchTarget.to_script(): Fluent API for script generation
- PatchTarget.save_script(): Fluent API for saving scripts
- Convenience functions: generate_script_from_patch, save_script_from_patch
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
    PatchConverter,
    PatchTarget,
    generate_script_from_patch,
    save_script_from_patch,
)


# =============================================================================
# PatchConverter.to_script() Tests
# =============================================================================

class TestPatchConverterToScript:
    """Tests for PatchConverter.to_script()."""

    def test_basic_script_generation(self, tmp_path):
        """Test generating a basic script from a patch."""
        rj = Rejig(tmp_path, dry_run=True)
        converter = PatchConverter(rj, smart_mode=False)

        hunk = Hunk(
            old_start=1,
            old_count=1,
            new_start=1,
            new_count=1,
            changes=[
                Change(type=ChangeType.DELETE, content="old_line"),
                Change(type=ChangeType.ADD, content="new_line"),
            ],
        )
        fp = FilePatch(
            old_path=Path("test.py"),
            new_path=Path("test.py"),
            hunks=[hunk],
        )
        patch = Patch(files=[fp])

        script = converter.to_script(patch)

        # Check essential parts
        assert "#!/usr/bin/env python3" in script
        assert "from rejig import Rejig" in script
        assert "def main() -> None:" in script
        assert 'if __name__ == "__main__":' in script
        assert "main()" in script

    def test_script_with_description(self, tmp_path):
        """Test script generation with custom description."""
        rj = Rejig(tmp_path, dry_run=True)
        converter = PatchConverter(rj, smart_mode=False)

        patch = Patch(files=[FilePatch(new_path=Path("test.py"))])
        script = converter.to_script(patch, description="Custom refactoring description")

        assert "Custom refactoring description" in script

    def test_script_with_custom_variable_name(self, tmp_path):
        """Test script generation with custom variable name."""
        rj = Rejig(tmp_path, dry_run=True)
        converter = PatchConverter(rj, smart_mode=False)

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
        fp = FilePatch(
            old_path=Path("test.py"),
            new_path=Path("test.py"),
            hunks=[hunk],
        )
        patch = Patch(files=[fp])

        script = converter.to_script(patch, variable_name="rejig")

        assert 'rejig = Rejig("."' in script
        assert 'rejig.file("test.py")' in script

    def test_script_with_custom_root_path(self, tmp_path):
        """Test script generation with custom root path."""
        rj = Rejig(tmp_path, dry_run=True)
        converter = PatchConverter(rj, smart_mode=False)

        patch = Patch(files=[FilePatch(new_path=Path("test.py"))])
        script = converter.to_script(patch, root_path="src/")

        assert 'rj = Rejig("src/"' in script

    def test_script_with_dry_run(self, tmp_path):
        """Test script generation with dry_run enabled."""
        rj = Rejig(tmp_path, dry_run=True)
        converter = PatchConverter(rj, smart_mode=False)

        patch = Patch(files=[FilePatch(new_path=Path("test.py"))])
        script = converter.to_script(patch, dry_run=True)

        assert "dry_run=True" in script

    def test_script_with_summary(self, tmp_path):
        """Test script generation includes patch summary."""
        rj = Rejig(tmp_path, dry_run=True)
        converter = PatchConverter(rj, smart_mode=False)

        hunk = Hunk(
            old_start=1,
            old_count=2,
            new_start=1,
            new_count=3,
            changes=[
                Change(type=ChangeType.DELETE, content="old1"),
                Change(type=ChangeType.DELETE, content="old2"),
                Change(type=ChangeType.ADD, content="new1"),
                Change(type=ChangeType.ADD, content="new2"),
                Change(type=ChangeType.ADD, content="new3"),
            ],
        )
        fp = FilePatch(
            old_path=Path("models.py"),
            new_path=Path("models.py"),
            hunks=[hunk],
        )
        patch = Patch(files=[fp])

        script = converter.to_script(patch, include_summary=True)

        assert "# Patch Summary" in script
        assert "# Files: 1" in script
        assert "# Additions: +3" in script
        assert "# Deletions: -2" in script

    def test_script_without_summary(self, tmp_path):
        """Test script generation without summary."""
        rj = Rejig(tmp_path, dry_run=True)
        converter = PatchConverter(rj, smart_mode=False)

        patch = Patch(files=[FilePatch(new_path=Path("test.py"))])
        script = converter.to_script(patch, include_summary=False)

        assert "# Patch Summary" not in script

    def test_script_with_error_handling(self, tmp_path):
        """Test script generation includes error handling."""
        rj = Rejig(tmp_path, dry_run=True)
        converter = PatchConverter(rj, smart_mode=False)

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
        fp = FilePatch(
            old_path=Path("test.py"),
            new_path=Path("test.py"),
            hunks=[hunk],
        )
        patch = Patch(files=[fp])

        script = converter.to_script(patch, include_error_handling=True)

        assert "results = []" in script
        assert "result.success" in script
        assert "success_count" in script

    def test_script_without_error_handling(self, tmp_path):
        """Test script generation without error handling."""
        rj = Rejig(tmp_path, dry_run=True)
        converter = PatchConverter(rj, smart_mode=False)

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
        fp = FilePatch(
            old_path=Path("test.py"),
            new_path=Path("test.py"),
            hunks=[hunk],
        )
        patch = Patch(files=[fp])

        script = converter.to_script(patch, include_error_handling=False)

        assert "results = []" not in script
        assert "success_count" not in script


# =============================================================================
# PatchConverter.save_script() Tests
# =============================================================================

class TestPatchConverterSaveScript:
    """Tests for PatchConverter.save_script()."""

    def test_save_script_creates_file(self, tmp_path):
        """Test saving a script creates the file."""
        rj = Rejig(tmp_path, dry_run=True)
        converter = PatchConverter(rj, smart_mode=False)

        patch = Patch(files=[FilePatch(new_path=Path("test.py"))])
        script_path = tmp_path / "apply_patch.py"

        result = converter.save_script(patch, script_path)

        assert result.success
        assert script_path.exists()
        assert script_path in result.files_changed

    def test_save_script_makes_executable(self, tmp_path):
        """Test saved script is executable."""
        rj = Rejig(tmp_path, dry_run=True)
        converter = PatchConverter(rj, smart_mode=False)

        patch = Patch(files=[FilePatch(new_path=Path("test.py"))])
        script_path = tmp_path / "apply_patch.py"

        converter.save_script(patch, script_path)

        # Check executable bit
        mode = script_path.stat().st_mode
        assert mode & 0o111  # At least one execute bit set

    def test_save_script_refuses_overwrite_by_default(self, tmp_path):
        """Test saving refuses to overwrite existing file."""
        rj = Rejig(tmp_path, dry_run=True)
        converter = PatchConverter(rj, smart_mode=False)

        patch = Patch(files=[FilePatch(new_path=Path("test.py"))])
        script_path = tmp_path / "apply_patch.py"
        script_path.write_text("existing content")

        result = converter.save_script(patch, script_path)

        assert not result.success
        assert "already exists" in result.message

    def test_save_script_with_overwrite(self, tmp_path):
        """Test saving with overwrite=True replaces file."""
        rj = Rejig(tmp_path, dry_run=True)
        converter = PatchConverter(rj, smart_mode=False)

        patch = Patch(files=[FilePatch(new_path=Path("test.py"))])
        script_path = tmp_path / "apply_patch.py"
        script_path.write_text("existing content")

        result = converter.save_script(patch, script_path, overwrite=True)

        assert result.success
        content = script_path.read_text()
        assert "from rejig import Rejig" in content

    def test_save_script_passes_kwargs(self, tmp_path):
        """Test save_script passes keyword arguments to to_script."""
        rj = Rejig(tmp_path, dry_run=True)
        converter = PatchConverter(rj, smart_mode=False)

        patch = Patch(files=[FilePatch(new_path=Path("test.py"))])
        script_path = tmp_path / "apply_patch.py"

        converter.save_script(
            patch,
            script_path,
            description="Test description",
            dry_run=True,
        )

        content = script_path.read_text()
        assert "Test description" in content
        assert "dry_run=True" in content


# =============================================================================
# PatchTarget Script Methods Tests
# =============================================================================

class TestPatchTargetScriptMethods:
    """Tests for PatchTarget.to_script() and save_script()."""

    def test_patch_target_to_script(self, tmp_path):
        """Test PatchTarget.to_script() method."""
        rj = Rejig(tmp_path, dry_run=True)

        patch = Patch(files=[FilePatch(new_path=Path("test.py"))])
        target = PatchTarget(rj, patch)

        script = target.to_script()

        assert "#!/usr/bin/env python3" in script
        assert "from rejig import Rejig" in script

    def test_patch_target_to_script_with_options(self, tmp_path):
        """Test PatchTarget.to_script() with all options."""
        rj = Rejig(tmp_path, dry_run=True)

        patch = Patch(files=[FilePatch(new_path=Path("test.py"))])
        target = PatchTarget(rj, patch)

        script = target.to_script(
            variable_name="refactor",
            root_path="lib/",
            description="My refactoring script",
            dry_run=True,
            smart_mode=False,
            include_error_handling=False,
            include_summary=False,
        )

        assert 'refactor = Rejig("lib/", dry_run=True)' in script
        assert "My refactoring script" in script
        assert "# Patch Summary" not in script

    def test_patch_target_save_script(self, tmp_path):
        """Test PatchTarget.save_script() method."""
        rj = Rejig(tmp_path, dry_run=True)

        patch = Patch(files=[FilePatch(new_path=Path("test.py"))])
        target = PatchTarget(rj, patch)

        script_path = tmp_path / "apply.py"
        result = target.save_script(script_path)

        assert result.success
        assert script_path.exists()
        content = script_path.read_text()
        assert "from rejig import Rejig" in content

    def test_patch_target_save_script_with_kwargs(self, tmp_path):
        """Test PatchTarget.save_script() passes kwargs."""
        rj = Rejig(tmp_path, dry_run=True)

        patch = Patch(files=[FilePatch(new_path=Path("test.py"))])
        target = PatchTarget(rj, patch)

        script_path = tmp_path / "apply.py"
        target.save_script(
            script_path,
            description="Custom script",
            root_path="src/",
        )

        content = script_path.read_text()
        assert "Custom script" in content
        assert 'Rejig("src/"' in content


# =============================================================================
# Convenience Functions Tests
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_generate_script_from_patch(self, tmp_path):
        """Test generate_script_from_patch function."""
        rj = Rejig(tmp_path, dry_run=True)

        patch = Patch(files=[FilePatch(new_path=Path("test.py"))])
        script = generate_script_from_patch(patch, rj)

        assert "#!/usr/bin/env python3" in script
        assert "from rejig import Rejig" in script

    def test_generate_script_from_patch_with_options(self, tmp_path):
        """Test generate_script_from_patch with options."""
        rj = Rejig(tmp_path, dry_run=True)

        patch = Patch(files=[FilePatch(new_path=Path("test.py"))])
        script = generate_script_from_patch(
            patch,
            rj,
            smart_mode=False,
            description="Generated script",
        )

        assert "Generated script" in script

    def test_save_script_from_patch(self, tmp_path):
        """Test save_script_from_patch function."""
        rj = Rejig(tmp_path, dry_run=True)

        patch = Patch(files=[FilePatch(new_path=Path("test.py"))])
        script_path = tmp_path / "apply.py"

        result = save_script_from_patch(patch, rj, script_path)

        assert result.success
        assert script_path.exists()

    def test_save_script_from_patch_with_overwrite(self, tmp_path):
        """Test save_script_from_patch with overwrite."""
        rj = Rejig(tmp_path, dry_run=True)

        patch = Patch(files=[FilePatch(new_path=Path("test.py"))])
        script_path = tmp_path / "apply.py"
        script_path.write_text("old content")

        result = save_script_from_patch(
            patch,
            rj,
            script_path,
            overwrite=True,
        )

        assert result.success
        content = script_path.read_text()
        assert "from rejig import Rejig" in content


# =============================================================================
# Script Validity Tests
# =============================================================================

class TestScriptValidity:
    """Tests that generated scripts are valid Python."""

    def test_script_is_valid_python(self, tmp_path):
        """Test that generated script compiles as valid Python."""
        rj = Rejig(tmp_path, dry_run=True)

        hunk = Hunk(
            old_start=1,
            old_count=1,
            new_start=1,
            new_count=2,
            changes=[
                Change(type=ChangeType.DELETE, content="old_line"),
                Change(type=ChangeType.ADD, content="new_line1"),
                Change(type=ChangeType.ADD, content="new_line2"),
            ],
        )
        fp = FilePatch(
            old_path=Path("test.py"),
            new_path=Path("test.py"),
            hunks=[hunk],
        )
        patch = Patch(files=[fp])
        target = PatchTarget(rj, patch)

        script = target.to_script()

        # Should not raise SyntaxError
        compile(script, "<string>", "exec")

    def test_script_with_special_characters(self, tmp_path):
        """Test script generation handles special characters."""
        rj = Rejig(tmp_path, dry_run=True)

        hunk = Hunk(
            old_start=1,
            old_count=1,
            new_start=1,
            new_count=1,
            changes=[
                Change(type=ChangeType.DELETE, content='line with "quotes"'),
                Change(type=ChangeType.ADD, content="line with 'quotes' and \\backslash"),
            ],
        )
        fp = FilePatch(
            old_path=Path("test.py"),
            new_path=Path("test.py"),
            hunks=[hunk],
        )
        patch = Patch(files=[fp])
        target = PatchTarget(rj, patch)

        script = target.to_script(include_error_handling=False)

        # Should compile without syntax errors
        compile(script, "<string>", "exec")

    def test_multifile_script(self, tmp_path):
        """Test script generation with multiple files."""
        rj = Rejig(tmp_path, dry_run=True)

        patches = []
        for name in ["a.py", "b.py", "c.py"]:
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
            patches.append(FilePatch(
                old_path=Path(name),
                new_path=Path(name),
                hunks=[hunk],
            ))

        patch = Patch(files=patches)
        target = PatchTarget(rj, patch)

        script = target.to_script()

        assert "a.py" in script
        assert "b.py" in script
        assert "c.py" in script
        compile(script, "<string>", "exec")
