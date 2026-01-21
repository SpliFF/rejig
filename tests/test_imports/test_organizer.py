"""
Tests for rejig.imports.organizer module.

This module tests import organization (isort-like functionality):
- ImportOrganizer class
- organize() method
- Import classification (future, stdlib, thirdparty, firstparty)
- Import sorting within groups
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig import Rejig
from rejig.imports.organizer import ImportOrganizer, _get_stdlib_modules


# =============================================================================
# Stdlib Detection Tests
# =============================================================================

class TestStdlibModules:
    """Tests for stdlib module detection."""

    def test_get_stdlib_modules_returns_set(self):
        """_get_stdlib_modules() should return a set or frozenset."""
        result = _get_stdlib_modules()
        assert isinstance(result, (set, frozenset))

    def test_common_stdlib_modules_included(self):
        """Common stdlib modules should be in the set."""
        stdlib = _get_stdlib_modules()
        assert "os" in stdlib
        assert "sys" in stdlib
        assert "typing" in stdlib
        assert "json" in stdlib
        assert "pathlib" in stdlib
        assert "collections" in stdlib

    def test_future_module_included(self):
        """__future__ should be in the stdlib set."""
        stdlib = _get_stdlib_modules()
        assert "__future__" in stdlib


# =============================================================================
# ImportOrganizer Initialization Tests
# =============================================================================

class TestImportOrganizerInit:
    """Tests for ImportOrganizer initialization."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_init_with_rejig(self, rejig: Rejig):
        """ImportOrganizer should initialize with Rejig instance."""
        organizer = ImportOrganizer(rejig)
        assert organizer._rejig is rejig

    def test_init_with_first_party_packages(self, rejig: Rejig):
        """ImportOrganizer should accept first-party packages."""
        organizer = ImportOrganizer(rejig, first_party_packages={"mypackage"})
        assert "mypackage" in organizer._first_party

    def test_auto_detects_first_party_from_src(self, tmp_path: Path):
        """ImportOrganizer should auto-detect first-party from src/ layout."""
        # Create src/mypackage structure
        src_dir = tmp_path / "src" / "mypackage"
        src_dir.mkdir(parents=True)
        (src_dir / "__init__.py").write_text("")

        rejig = Rejig(str(tmp_path))
        organizer = ImportOrganizer(rejig)

        assert "mypackage" in organizer._first_party

    def test_auto_detects_first_party_from_root(self, tmp_path: Path):
        """ImportOrganizer should auto-detect first-party from root packages."""
        # Create mypackage at root
        pkg_dir = tmp_path / "mypackage"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("")

        rejig = Rejig(str(tmp_path))
        organizer = ImportOrganizer(rejig)

        assert "mypackage" in organizer._first_party

    def test_auto_detects_first_party_from_pyproject(self, tmp_path: Path):
        """ImportOrganizer should auto-detect first-party from pyproject.toml."""
        # Create pyproject.toml with project name
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(textwrap.dedent('''\
            [project]
            name = "my-cool-package"
        '''))

        rejig = Rejig(str(tmp_path))
        organizer = ImportOrganizer(rejig)

        # Dashes should be converted to underscores
        assert "my_cool_package" in organizer._first_party


# =============================================================================
# Import Classification Tests
# =============================================================================

class TestImportClassification:
    """Tests for import classification."""

    @pytest.fixture
    def organizer(self, tmp_path: Path) -> ImportOrganizer:
        """Create an ImportOrganizer."""
        rejig = Rejig(str(tmp_path))
        return ImportOrganizer(rejig, first_party_packages={"mypackage"})

    def test_classify_future_import(self, organizer: ImportOrganizer):
        """Should classify __future__ imports as 'future'."""
        from rejig.imports.analyzer import ImportInfo

        imp = ImportInfo(
            module="__future__",
            names=["annotations"],
            is_from_import=True,
            is_future=True,
        )
        assert organizer._classify_import(imp) == "future"

    def test_classify_type_checking_import(self, organizer: ImportOrganizer):
        """Should classify TYPE_CHECKING imports as 'type_checking'."""
        from rejig.imports.analyzer import ImportInfo

        imp = ImportInfo(
            module="typing",
            names=["List"],
            is_from_import=True,
            is_type_checking=True,
        )
        assert organizer._classify_import(imp) == "type_checking"

    def test_classify_relative_import(self, organizer: ImportOrganizer):
        """Should classify relative imports as 'firstparty'."""
        from rejig.imports.analyzer import ImportInfo

        imp = ImportInfo(
            module="utils",
            names=["helper"],
            is_from_import=True,
            is_relative=True,
            relative_level=1,
        )
        assert organizer._classify_import(imp) == "firstparty"

    def test_classify_stdlib_import(self, organizer: ImportOrganizer):
        """Should classify stdlib imports as 'stdlib'."""
        from rejig.imports.analyzer import ImportInfo

        imp = ImportInfo(
            module=None,
            names=["os"],
            is_from_import=False,
        )
        assert organizer._classify_import(imp) == "stdlib"

    def test_classify_stdlib_from_import(self, organizer: ImportOrganizer):
        """Should classify stdlib from imports as 'stdlib'."""
        from rejig.imports.analyzer import ImportInfo

        imp = ImportInfo(
            module="os.path",
            names=["join"],
            is_from_import=True,
        )
        assert organizer._classify_import(imp) == "stdlib"

    def test_classify_first_party_import(self, organizer: ImportOrganizer):
        """Should classify first-party imports as 'firstparty'."""
        from rejig.imports.analyzer import ImportInfo

        imp = ImportInfo(
            module="mypackage.utils",
            names=["helper"],
            is_from_import=True,
        )
        assert organizer._classify_import(imp) == "firstparty"

    def test_classify_third_party_import(self, organizer: ImportOrganizer):
        """Should classify unknown imports as 'thirdparty'."""
        from rejig.imports.analyzer import ImportInfo

        imp = ImportInfo(
            module=None,
            names=["numpy"],
            is_from_import=False,
        )
        assert organizer._classify_import(imp) == "thirdparty"


# =============================================================================
# Import Sorting Tests
# =============================================================================

class TestImportSorting:
    """Tests for import sorting within groups."""

    @pytest.fixture
    def organizer(self, tmp_path: Path) -> ImportOrganizer:
        """Create an ImportOrganizer."""
        rejig = Rejig(str(tmp_path))
        return ImportOrganizer(rejig)

    def test_regular_imports_before_from_imports(self, organizer: ImportOrganizer):
        """Regular imports should come before from imports."""
        from rejig.imports.analyzer import ImportInfo

        imports = [
            ImportInfo(module="os", names=["getcwd"], is_from_import=True),
            ImportInfo(module=None, names=["os"], is_from_import=False),
        ]

        sorted_imports = organizer._sort_imports(imports)

        # Regular import should be first
        assert sorted_imports[0].is_from_import is False
        assert sorted_imports[1].is_from_import is True

    def test_alphabetical_sorting(self, organizer: ImportOrganizer):
        """Imports should be sorted alphabetically by module name."""
        from rejig.imports.analyzer import ImportInfo

        imports = [
            ImportInfo(module=None, names=["sys"], is_from_import=False),
            ImportInfo(module=None, names=["os"], is_from_import=False),
            ImportInfo(module=None, names=["abc"], is_from_import=False),
        ]

        sorted_imports = organizer._sort_imports(imports)

        assert sorted_imports[0].names == ["abc"]
        assert sorted_imports[1].names == ["os"]
        assert sorted_imports[2].names == ["sys"]


# =============================================================================
# ImportOrganizer.organize() Tests
# =============================================================================

class TestImportOrganizerOrganize:
    """Tests for ImportOrganizer.organize()."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_organize_missing_file(self, rejig: Rejig, tmp_path: Path):
        """organize() should fail for missing file."""
        organizer = ImportOrganizer(rejig)
        result = organizer.organize(tmp_path / "missing.py")

        assert result.success is False
        assert "not found" in result.message

    def test_organize_invalid_python(self, rejig: Rejig, tmp_path: Path):
        """organize() should fail for invalid Python."""
        file_path = tmp_path / "invalid.py"
        file_path.write_text("this is not { valid python")

        organizer = ImportOrganizer(rejig)
        result = organizer.organize(file_path)

        assert result.success is False
        assert "Failed to parse" in result.message

    def test_organize_no_imports(self, rejig: Rejig, tmp_path: Path):
        """organize() should succeed when no imports."""
        file_path = tmp_path / "no_imports.py"
        file_path.write_text("x = 1\ny = 2\n")

        organizer = ImportOrganizer(rejig)
        result = organizer.organize(file_path)

        assert result.success is True
        assert "No imports" in result.message

    def test_organize_already_organized(self, rejig: Rejig, tmp_path: Path):
        """organize() should detect already organized imports."""
        content = textwrap.dedent('''\
            import os
            import sys
        ''')
        file_path = tmp_path / "organized.py"
        file_path.write_text(content)

        organizer = ImportOrganizer(rejig)
        result = organizer.organize(file_path)

        assert result.success is True

    def test_organize_groups_imports(self, rejig: Rejig, tmp_path: Path):
        """organize() should group imports by type."""
        content = textwrap.dedent('''\
            import numpy
            import os
            from __future__ import annotations
            import sys
        ''')
        file_path = tmp_path / "unorganized.py"
        file_path.write_text(content)

        organizer = ImportOrganizer(rejig)
        result = organizer.organize(file_path)

        assert result.success is True

        # Check the organized content
        new_content = file_path.read_text()
        lines = new_content.strip().split('\n')

        # __future__ should be first
        assert lines[0].startswith("from __future__")

    def test_organize_dry_run(self, tmp_path: Path):
        """organize() should not modify in dry-run mode."""
        content = textwrap.dedent('''\
            import numpy
            import os
        ''')
        file_path = tmp_path / "test.py"
        file_path.write_text(content)

        rejig = Rejig(str(tmp_path), dry_run=True)
        organizer = ImportOrganizer(rejig)
        result = organizer.organize(file_path)

        assert result.success is True
        assert "[DRY RUN]" in result.message
        # Content should be unchanged
        assert file_path.read_text() == content


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases in import organization."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_mixed_import_styles(self, rejig: Rejig, tmp_path: Path):
        """Should handle mixed import styles."""
        content = textwrap.dedent('''\
            from collections import defaultdict
            import sys, os
            from os.path import join
        ''')
        file_path = tmp_path / "mixed.py"
        file_path.write_text(content)

        organizer = ImportOrganizer(rejig)
        result = organizer.organize(file_path)

        assert result.success is True

    def test_import_with_comments(self, rejig: Rejig, tmp_path: Path):
        """Should handle imports with inline comments."""
        content = textwrap.dedent('''\
            import os  # for file operations
            import sys  # for system info
        ''')
        file_path = tmp_path / "comments.py"
        file_path.write_text(content)

        organizer = ImportOrganizer(rejig)
        result = organizer.organize(file_path)

        assert result.success is True

    def test_type_checking_imports_preserved(self, rejig: Rejig, tmp_path: Path):
        """TYPE_CHECKING imports should stay in place."""
        content = textwrap.dedent('''\
            from __future__ import annotations
            import os
            from typing import TYPE_CHECKING

            if TYPE_CHECKING:
                from typing import List, Dict
        ''')
        file_path = tmp_path / "type_checking.py"
        file_path.write_text(content)

        organizer = ImportOrganizer(rejig)
        result = organizer.organize(file_path)

        assert result.success is True
        new_content = file_path.read_text()
        # TYPE_CHECKING block should still be present
        assert "if TYPE_CHECKING:" in new_content
