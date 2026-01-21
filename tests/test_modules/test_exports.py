"""
Tests for rejig.modules.exports module.

This module tests __all__ exports management:
- ExportsManager class
- get_exports() method
- generate_exports() method
- add_export() / remove_export() methods
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig import Rejig
from rejig.modules.exports import (
    ExportsManager,
    add_to_all,
    generate_all_exports,
    get_all_exports,
    remove_from_all,
)


# =============================================================================
# ExportsManager Initialization Tests
# =============================================================================

class TestExportsManagerInit:
    """Tests for ExportsManager initialization."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_init(self, rejig: Rejig):
        """ExportsManager should initialize with Rejig instance."""
        manager = ExportsManager(rejig)
        assert manager._rejig is rejig


# =============================================================================
# ExportsManager.get_exports() Tests
# =============================================================================

class TestExportsManagerGetExports:
    """Tests for ExportsManager.get_exports()."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_get_exports_missing_file(self, rejig: Rejig, tmp_path: Path):
        """get_exports() should return empty list for missing file."""
        manager = ExportsManager(rejig)
        result = manager.get_exports(tmp_path / "missing.py")

        assert result == []

    def test_get_exports_no_all(self, rejig: Rejig, tmp_path: Path):
        """get_exports() should return empty list when no __all__."""
        file_path = tmp_path / "module.py"
        file_path.write_text("def func(): pass")

        manager = ExportsManager(rejig)
        result = manager.get_exports(file_path)

        assert result == []

    def test_get_exports_list_format(self, rejig: Rejig, tmp_path: Path):
        """get_exports() should parse __all__ list format."""
        file_path = tmp_path / "module.py"
        file_path.write_text(textwrap.dedent('''\
            __all__ = ["func1", "func2", "MyClass"]

            def func1(): pass
            def func2(): pass
            class MyClass: pass
        '''))

        manager = ExportsManager(rejig)
        result = manager.get_exports(file_path)

        assert len(result) == 3
        assert "func1" in result
        assert "func2" in result
        assert "MyClass" in result

    def test_get_exports_tuple_format(self, rejig: Rejig, tmp_path: Path):
        """get_exports() should parse __all__ tuple format."""
        file_path = tmp_path / "module.py"
        file_path.write_text('__all__ = ("func1", "func2")')

        manager = ExportsManager(rejig)
        result = manager.get_exports(file_path)

        assert "func1" in result
        assert "func2" in result

    def test_get_exports_single_quotes(self, rejig: Rejig, tmp_path: Path):
        """get_exports() should handle single-quoted strings."""
        file_path = tmp_path / "module.py"
        file_path.write_text("__all__ = ['func1', 'func2']")

        manager = ExportsManager(rejig)
        result = manager.get_exports(file_path)

        assert "func1" in result
        assert "func2" in result


# =============================================================================
# ExportsManager.generate_exports() Tests
# =============================================================================

class TestExportsManagerGenerateExports:
    """Tests for ExportsManager.generate_exports()."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_generate_missing_file(self, rejig: Rejig, tmp_path: Path):
        """generate_exports() should fail for missing file."""
        manager = ExportsManager(rejig)
        result = manager.generate_exports(tmp_path / "missing.py")

        assert result.success is False
        assert "not found" in result.message

    def test_generate_from_functions(self, rejig: Rejig, tmp_path: Path):
        """generate_exports() should include public functions."""
        file_path = tmp_path / "module.py"
        file_path.write_text(textwrap.dedent('''\
            def public_func():
                pass

            def _private_func():
                pass
        '''))

        manager = ExportsManager(rejig)
        result = manager.generate_exports(file_path)

        assert result.success is True
        content = file_path.read_text()
        assert "__all__" in content
        assert '"public_func"' in content
        assert '"_private_func"' not in content

    def test_generate_from_classes(self, rejig: Rejig, tmp_path: Path):
        """generate_exports() should include public classes."""
        file_path = tmp_path / "module.py"
        file_path.write_text(textwrap.dedent('''\
            class PublicClass:
                pass

            class _PrivateClass:
                pass
        '''))

        manager = ExportsManager(rejig)
        result = manager.generate_exports(file_path)

        assert result.success is True
        content = file_path.read_text()
        assert '"PublicClass"' in content
        assert '"_PrivateClass"' not in content

    def test_generate_includes_private_when_requested(self, rejig: Rejig, tmp_path: Path):
        """generate_exports() should include private names when requested."""
        file_path = tmp_path / "module.py"
        file_path.write_text(textwrap.dedent('''\
            def _private_func():
                pass
        '''))

        manager = ExportsManager(rejig)
        result = manager.generate_exports(file_path, include_private=True)

        assert result.success is True
        content = file_path.read_text()
        assert '"_private_func"' in content

    def test_generate_no_definitions(self, rejig: Rejig, tmp_path: Path):
        """generate_exports() should handle files with no definitions."""
        file_path = tmp_path / "empty.py"
        file_path.write_text("# Just a comment")

        manager = ExportsManager(rejig)
        result = manager.generate_exports(file_path)

        assert result.success is True
        assert "No public definitions" in result.message

    def test_generate_updates_existing(self, rejig: Rejig, tmp_path: Path):
        """generate_exports() should update existing __all__."""
        file_path = tmp_path / "module.py"
        file_path.write_text(textwrap.dedent('''\
            __all__ = ["old_func"]

            def new_func():
                pass
        '''))

        manager = ExportsManager(rejig)
        result = manager.generate_exports(file_path)

        assert result.success is True
        content = file_path.read_text()
        assert '"new_func"' in content

    def test_generate_dry_run(self, tmp_path: Path):
        """generate_exports() should not modify in dry-run mode."""
        file_path = tmp_path / "module.py"
        original = "def func(): pass"
        file_path.write_text(original)

        rejig = Rejig(str(tmp_path), dry_run=True)
        manager = ExportsManager(rejig)
        result = manager.generate_exports(file_path)

        assert result.success is True
        assert "[DRY RUN]" in result.message
        assert file_path.read_text() == original


# =============================================================================
# ExportsManager.add_export() Tests
# =============================================================================

class TestExportsManagerAddExport:
    """Tests for ExportsManager.add_export()."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_add_export_missing_file(self, rejig: Rejig, tmp_path: Path):
        """add_export() should fail for missing file."""
        manager = ExportsManager(rejig)
        result = manager.add_export(tmp_path / "missing.py", "func")

        assert result.success is False
        assert "not found" in result.message

    def test_add_export_new_name(self, rejig: Rejig, tmp_path: Path):
        """add_export() should add new name to __all__."""
        file_path = tmp_path / "module.py"
        file_path.write_text('__all__ = ["existing"]')

        manager = ExportsManager(rejig)
        result = manager.add_export(file_path, "new_func")

        assert result.success is True
        content = file_path.read_text()
        assert '"new_func"' in content
        assert '"existing"' in content

    def test_add_export_already_exists(self, rejig: Rejig, tmp_path: Path):
        """add_export() should handle name that already exists."""
        file_path = tmp_path / "module.py"
        file_path.write_text('__all__ = ["existing"]')

        manager = ExportsManager(rejig)
        result = manager.add_export(file_path, "existing")

        assert result.success is True
        assert "already in" in result.message

    def test_add_export_creates_all(self, rejig: Rejig, tmp_path: Path):
        """add_export() should create __all__ if missing."""
        file_path = tmp_path / "module.py"
        file_path.write_text("def func(): pass")

        manager = ExportsManager(rejig)
        result = manager.add_export(file_path, "func")

        assert result.success is True
        content = file_path.read_text()
        assert "__all__" in content
        assert '"func"' in content


# =============================================================================
# ExportsManager.remove_export() Tests
# =============================================================================

class TestExportsManagerRemoveExport:
    """Tests for ExportsManager.remove_export()."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_remove_export_missing_file(self, rejig: Rejig, tmp_path: Path):
        """remove_export() should fail for missing file."""
        manager = ExportsManager(rejig)
        result = manager.remove_export(tmp_path / "missing.py", "func")

        assert result.success is False
        assert "not found" in result.message

    def test_remove_export_existing_name(self, rejig: Rejig, tmp_path: Path):
        """remove_export() should remove existing name from __all__."""
        file_path = tmp_path / "module.py"
        file_path.write_text('__all__ = ["func1", "func2"]')

        manager = ExportsManager(rejig)
        result = manager.remove_export(file_path, "func1")

        assert result.success is True
        content = file_path.read_text()
        assert '"func1"' not in content
        assert '"func2"' in content

    def test_remove_export_not_found(self, rejig: Rejig, tmp_path: Path):
        """remove_export() should handle name not in __all__."""
        file_path = tmp_path / "module.py"
        file_path.write_text('__all__ = ["existing"]')

        manager = ExportsManager(rejig)
        result = manager.remove_export(file_path, "nonexistent")

        assert result.success is True
        assert "not in" in result.message


# =============================================================================
# Convenience Functions Tests
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_get_all_exports_function(self, rejig: Rejig, tmp_path: Path):
        """get_all_exports() should work."""
        file_path = tmp_path / "module.py"
        file_path.write_text('__all__ = ["func"]')

        result = get_all_exports(rejig, file_path)
        assert "func" in result

    def test_generate_all_exports_function(self, rejig: Rejig, tmp_path: Path):
        """generate_all_exports() should work."""
        file_path = tmp_path / "module.py"
        file_path.write_text("def func(): pass")

        result = generate_all_exports(rejig, file_path)
        assert result.success is True

    def test_add_to_all_function(self, rejig: Rejig, tmp_path: Path):
        """add_to_all() should work."""
        file_path = tmp_path / "module.py"
        file_path.write_text('__all__ = []')

        result = add_to_all(rejig, file_path, "func")
        assert result.success is True

    def test_remove_from_all_function(self, rejig: Rejig, tmp_path: Path):
        """remove_from_all() should work."""
        file_path = tmp_path / "module.py"
        file_path.write_text('__all__ = ["func"]')

        result = remove_from_all(rejig, file_path, "func")
        assert result.success is True


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases in exports management."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_generate_with_module_level_variables(self, rejig: Rejig, tmp_path: Path):
        """generate_exports() should include module-level variables."""
        file_path = tmp_path / "module.py"
        file_path.write_text(textwrap.dedent('''\
            VERSION = "1.0.0"
            _INTERNAL = "private"

            def func():
                pass
        '''))

        manager = ExportsManager(rejig)
        result = manager.generate_exports(file_path)

        assert result.success is True
        content = file_path.read_text()
        assert '"VERSION"' in content
        assert '"_INTERNAL"' not in content

    def test_generate_with_annotated_variables(self, rejig: Rejig, tmp_path: Path):
        """generate_exports() should handle annotated variables."""
        file_path = tmp_path / "module.py"
        file_path.write_text(textwrap.dedent('''\
            VERSION: str = "1.0.0"
            DEBUG: bool = False
        '''))

        manager = ExportsManager(rejig)
        result = manager.generate_exports(file_path)

        assert result.success is True
        content = file_path.read_text()
        assert '"VERSION"' in content
        assert '"DEBUG"' in content

    def test_invalid_python(self, rejig: Rejig, tmp_path: Path):
        """Should handle invalid Python gracefully."""
        file_path = tmp_path / "invalid.py"
        file_path.write_text("this is not { valid")

        manager = ExportsManager(rejig)

        # get_exports should return empty list
        exports = manager.get_exports(file_path)
        assert exports == []

        # generate_exports should fail
        result = manager.generate_exports(file_path)
        assert result.success is False
