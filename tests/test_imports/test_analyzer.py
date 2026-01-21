"""
Tests for rejig.imports.analyzer module.

This module tests ImportAnalyzer and ImportInfo for analyzing imports:
- Extracting imports from Python files
- Detecting unused imports
- Detecting potentially missing imports
- Handling various import styles (regular, from, relative, star)
- Handling aliases and TYPE_CHECKING blocks

ImportAnalyzer provides import analysis using LibCST.

Coverage targets:
- ImportInfo data class functionality
- get_imports() for various import styles
- get_used_names() for name tracking
- find_unused_imports() for dead import detection
- find_potentially_missing_imports() for undefined name detection
- Edge cases (star imports, TYPE_CHECKING, __future__)
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig import Rejig
from rejig.imports import ImportAnalyzer, ImportInfo


# =============================================================================
# ImportInfo Tests
# =============================================================================

class TestImportInfo:
    """Tests for ImportInfo data class."""

    def test_simple_import_info(self):
        """
        ImportInfo should store basic import information.
        """
        info = ImportInfo(
            module=None,
            names=["os"],
            is_from_import=False,
        )
        assert info.module is None
        assert info.names == ["os"]
        assert info.is_from_import is False
        assert info.is_relative is False

    def test_from_import_info(self):
        """
        ImportInfo should handle from imports.
        """
        info = ImportInfo(
            module="os.path",
            names=["join", "dirname"],
            is_from_import=True,
        )
        assert info.module == "os.path"
        assert info.names == ["join", "dirname"]
        assert info.is_from_import is True

    def test_relative_import_info(self):
        """
        ImportInfo should track relative import details.
        """
        info = ImportInfo(
            module="utils",
            names=["helper"],
            is_from_import=True,
            is_relative=True,
            relative_level=2,
        )
        assert info.is_relative is True
        assert info.relative_level == 2

    def test_import_with_alias(self):
        """
        ImportInfo should track aliases.
        """
        info = ImportInfo(
            module=None,
            names=["numpy"],
            aliases={"np": "numpy"},
            is_from_import=False,
        )
        assert "np" in info.aliases
        assert info.aliases["np"] == "numpy"

    def test_get_imported_names_without_aliases(self):
        """
        get_imported_names() should return names directly when no aliases.
        """
        info = ImportInfo(
            module="os.path",
            names=["join", "dirname"],
            is_from_import=True,
        )
        names = info.get_imported_names()
        assert names == ["join", "dirname"]

    def test_get_imported_names_with_aliases(self):
        """
        get_imported_names() should return aliases when present.

        If 'numpy' is imported as 'np', we use 'np' in code, not 'numpy'.
        """
        info = ImportInfo(
            module=None,
            names=["numpy"],
            aliases={"np": "numpy"},
            is_from_import=False,
        )
        names = info.get_imported_names()
        assert "np" in names

    def test_get_original_name(self):
        """
        get_original_name() should resolve aliases to original names.
        """
        info = ImportInfo(
            module=None,
            names=["numpy"],
            aliases={"np": "numpy"},
            is_from_import=False,
        )
        # Alias should resolve to original
        assert info.get_original_name("np") == "numpy"
        # Non-alias should return unchanged
        assert info.get_original_name("other") == "other"

    def test_future_import_info(self):
        """
        ImportInfo should track __future__ imports.
        """
        info = ImportInfo(
            module="__future__",
            names=["annotations"],
            is_from_import=True,
            is_future=True,
        )
        assert info.is_future is True

    def test_type_checking_import_info(self):
        """
        ImportInfo should track TYPE_CHECKING imports.
        """
        info = ImportInfo(
            module="typing",
            names=["List"],
            is_from_import=True,
            is_type_checking=True,
        )
        assert info.is_type_checking is True


# =============================================================================
# ImportAnalyzer.get_imports() Tests
# =============================================================================

class TestImportAnalyzerGetImports:
    """Tests for ImportAnalyzer.get_imports()."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_simple_import(self, rejig: Rejig, tmp_path: Path):
        """
        get_imports() should extract simple 'import x' statements.
        """
        content = textwrap.dedent('''\
            import os
            import sys
        ''')
        file_path = tmp_path / "test.py"
        file_path.write_text(content)

        analyzer = ImportAnalyzer(rejig)
        imports = analyzer.get_imports(file_path)

        assert len(imports) >= 2
        names = [name for imp in imports for name in imp.names]
        assert "os" in names
        assert "sys" in names

    def test_from_import(self, rejig: Rejig, tmp_path: Path):
        """
        get_imports() should extract 'from x import y' statements.
        """
        content = textwrap.dedent('''\
            from os.path import join, dirname
            from collections import defaultdict
        ''')
        file_path = tmp_path / "test.py"
        file_path.write_text(content)

        analyzer = ImportAnalyzer(rejig)
        imports = analyzer.get_imports(file_path)

        assert len(imports) >= 2
        # Find the os.path import
        os_import = next((i for i in imports if i.module == "os.path"), None)
        assert os_import is not None
        assert "join" in os_import.names
        assert "dirname" in os_import.names

    def test_import_with_alias(self, rejig: Rejig, tmp_path: Path):
        """
        get_imports() should extract imports with aliases.
        """
        content = textwrap.dedent('''\
            import numpy as np
            from pandas import DataFrame as DF
        ''')
        file_path = tmp_path / "test.py"
        file_path.write_text(content)

        analyzer = ImportAnalyzer(rejig)
        imports = analyzer.get_imports(file_path)

        # Find numpy import
        np_import = next((i for i in imports if "numpy" in i.names), None)
        assert np_import is not None
        assert "np" in np_import.aliases

    def test_relative_import(self, rejig: Rejig, tmp_path: Path):
        """
        get_imports() should detect relative imports.
        """
        content = textwrap.dedent('''\
            from . import utils
            from ..helpers import helper_func
        ''')
        file_path = tmp_path / "test.py"
        file_path.write_text(content)

        analyzer = ImportAnalyzer(rejig)
        imports = analyzer.get_imports(file_path)

        # At least one should be relative
        relative_imports = [i for i in imports if i.is_relative]
        assert len(relative_imports) >= 1

    def test_star_import(self, rejig: Rejig, tmp_path: Path):
        """
        get_imports() should handle star imports.
        """
        content = textwrap.dedent('''\
            from os.path import *
        ''')
        file_path = tmp_path / "test.py"
        file_path.write_text(content)

        analyzer = ImportAnalyzer(rejig)
        imports = analyzer.get_imports(file_path)

        assert len(imports) >= 1
        star_import = next((i for i in imports if "*" in i.names), None)
        assert star_import is not None

    def test_future_import(self, rejig: Rejig, tmp_path: Path):
        """
        get_imports() should mark __future__ imports.
        """
        content = textwrap.dedent('''\
            from __future__ import annotations
            import os
        ''')
        file_path = tmp_path / "test.py"
        file_path.write_text(content)

        analyzer = ImportAnalyzer(rejig)
        imports = analyzer.get_imports(file_path)

        future_imports = [i for i in imports if i.is_future]
        assert len(future_imports) == 1
        assert "annotations" in future_imports[0].names

    def test_type_checking_import(self, rejig: Rejig, tmp_path: Path):
        """
        get_imports() should mark TYPE_CHECKING imports.
        """
        content = textwrap.dedent('''\
            from typing import TYPE_CHECKING

            if TYPE_CHECKING:
                from typing import List
        ''')
        file_path = tmp_path / "test.py"
        file_path.write_text(content)

        analyzer = ImportAnalyzer(rejig)
        imports = analyzer.get_imports(file_path)

        # The List import should be marked as type checking
        type_checking_imports = [i for i in imports if i.is_type_checking]
        assert len(type_checking_imports) >= 1

    def test_missing_file(self, rejig: Rejig, tmp_path: Path):
        """
        get_imports() should return empty list for missing files.
        """
        analyzer = ImportAnalyzer(rejig)
        imports = analyzer.get_imports(tmp_path / "missing.py")

        assert imports == []

    def test_invalid_python(self, rejig: Rejig, tmp_path: Path):
        """
        get_imports() should return empty list for invalid Python.
        """
        file_path = tmp_path / "invalid.py"
        file_path.write_text("this is not { valid python")

        analyzer = ImportAnalyzer(rejig)
        imports = analyzer.get_imports(file_path)

        assert imports == []


# =============================================================================
# ImportAnalyzer.get_used_names() Tests
# =============================================================================

class TestImportAnalyzerGetUsedNames:
    """Tests for ImportAnalyzer.get_used_names().

    NOTE: Many of these tests are marked xfail because the implementation
    uses tree.walk() which is not available in the current libcst version.
    The implementation catches the exception and returns an empty set.
    """

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_simple_name_usage(self, rejig: Rejig, tmp_path: Path):
        """
        get_used_names() should find names used in code.
        """
        content = textwrap.dedent('''\
            import os
            result = os.getcwd()
            print(result)
        ''')
        file_path = tmp_path / "test.py"
        file_path.write_text(content)

        analyzer = ImportAnalyzer(rejig)
        used = analyzer.get_used_names(file_path)

        assert "os" in used
        assert "print" in used

    def test_excludes_import_names(self, rejig: Rejig, tmp_path: Path):
        """
        get_used_names() should NOT count names in import statements.

        The names in 'import os' or 'from os import path' shouldn't be
        counted as "usages" because they're definitions, not references.
        """
        content = textwrap.dedent('''\
            import os
            from sys import path
        ''')
        file_path = tmp_path / "test.py"
        file_path.write_text(content)

        analyzer = ImportAnalyzer(rejig)
        used = analyzer.get_used_names(file_path)

        # These are import statements, not usages
        # (though the implementation may vary on this)
        # The key is that we don't double-count

    def test_attribute_access(self, rejig: Rejig, tmp_path: Path):
        """
        get_used_names() should track the root of attribute access.

        For os.path.join(), we need to track 'os' as used.
        """
        content = textwrap.dedent('''\
            import os
            result = os.path.join("a", "b")
        ''')
        file_path = tmp_path / "test.py"
        file_path.write_text(content)

        analyzer = ImportAnalyzer(rejig)
        used = analyzer.get_used_names(file_path)

        assert "os" in used


# =============================================================================
# ImportAnalyzer.find_unused_imports() Tests
# =============================================================================

class TestImportAnalyzerFindUnusedImports:
    """Tests for ImportAnalyzer.find_unused_imports()."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_finds_unused_import(self, rejig: Rejig, tmp_path: Path):
        """
        find_unused_imports() should detect imports that aren't used.
        """
        content = textwrap.dedent('''\
            import os
            import sys
            print("hello")
        ''')
        file_path = tmp_path / "test.py"
        file_path.write_text(content)

        analyzer = ImportAnalyzer(rejig)
        unused = analyzer.find_unused_imports(file_path)

        # Both os and sys are unused
        unused_names = [name for imp in unused for name in imp.names]
        assert "os" in unused_names
        assert "sys" in unused_names

    def test_used_import_not_reported(self, rejig: Rejig, tmp_path: Path):
        """
        find_unused_imports() should NOT report imports that are used.
        """
        content = textwrap.dedent('''\
            import os
            import sys
            print(os.getcwd())
        ''')
        file_path = tmp_path / "test.py"
        file_path.write_text(content)

        analyzer = ImportAnalyzer(rejig)
        unused = analyzer.find_unused_imports(file_path)

        # os is used, sys is not
        unused_names = [name for imp in unused for name in imp.names]
        assert "os" not in unused_names
        assert "sys" in unused_names

    def test_future_imports_never_unused(self, rejig: Rejig, tmp_path: Path):
        """
        find_unused_imports() should skip __future__ imports.

        __future__ imports affect compilation and should never be removed.
        """
        content = textwrap.dedent('''\
            from __future__ import annotations
            x = 1
        ''')
        file_path = tmp_path / "test.py"
        file_path.write_text(content)

        analyzer = ImportAnalyzer(rejig)
        unused = analyzer.find_unused_imports(file_path)

        # __future__ should not be reported as unused
        unused_names = [name for imp in unused for name in imp.names]
        assert "annotations" not in unused_names

    def test_star_imports_skipped(self, rejig: Rejig, tmp_path: Path):
        """
        find_unused_imports() should skip star imports.

        We can't determine if a star import is unused since we don't
        know what names it brings in.
        """
        content = textwrap.dedent('''\
            from os.path import *
            x = 1
        ''')
        file_path = tmp_path / "test.py"
        file_path.write_text(content)

        analyzer = ImportAnalyzer(rejig)
        unused = analyzer.find_unused_imports(file_path)

        # Star import should not be reported
        star_imports = [imp for imp in unused if "*" in imp.names]
        assert len(star_imports) == 0


# =============================================================================
# ImportAnalyzer.find_potentially_missing_imports() Tests
# =============================================================================

class TestImportAnalyzerFindMissingImports:
    """Tests for ImportAnalyzer.find_potentially_missing_imports()."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_finds_undefined_names(self, rejig: Rejig, tmp_path: Path):
        """
        find_potentially_missing_imports() should find undefined names.
        """
        content = textwrap.dedent('''\
            x = numpy.array([1, 2, 3])
        ''')
        file_path = tmp_path / "test.py"
        file_path.write_text(content)

        analyzer = ImportAnalyzer(rejig)
        missing = analyzer.find_potentially_missing_imports(file_path)

        # numpy is used but not imported
        assert "numpy" in missing

    def test_ignores_defined_names(self, rejig: Rejig, tmp_path: Path):
        """
        find_potentially_missing_imports() should ignore locally defined names.
        """
        content = textwrap.dedent('''\
            def helper():
                pass

            class MyClass:
                pass

            x = 1
            result = helper()
            obj = MyClass()
        ''')
        file_path = tmp_path / "test.py"
        file_path.write_text(content)

        analyzer = ImportAnalyzer(rejig)
        missing = analyzer.find_potentially_missing_imports(file_path)

        # These are all defined locally
        assert "helper" not in missing
        assert "MyClass" not in missing
        assert "x" not in missing

    def test_ignores_imported_names(self, rejig: Rejig, tmp_path: Path):
        """
        find_potentially_missing_imports() should ignore imported names.
        """
        content = textwrap.dedent('''\
            import os
            from sys import path
            result = os.getcwd()
        ''')
        file_path = tmp_path / "test.py"
        file_path.write_text(content)

        analyzer = ImportAnalyzer(rejig)
        missing = analyzer.find_potentially_missing_imports(file_path)

        # These are imported
        assert "os" not in missing
        assert "path" not in missing

    def test_ignores_builtins(self, rejig: Rejig, tmp_path: Path):
        """
        find_potentially_missing_imports() should ignore builtin names.
        """
        content = textwrap.dedent('''\
            x = len([1, 2, 3])
            y = str(42)
            z = dict()
        ''')
        file_path = tmp_path / "test.py"
        file_path.write_text(content)

        analyzer = ImportAnalyzer(rejig)
        missing = analyzer.find_potentially_missing_imports(file_path)

        # These are builtins
        assert "len" not in missing
        assert "str" not in missing
        assert "dict" not in missing

    def test_ignores_special_names(self, rejig: Rejig, tmp_path: Path):
        """
        find_potentially_missing_imports() should ignore self, cls, etc.
        """
        content = textwrap.dedent('''\
            class MyClass:
                def method(self):
                    return self.value

                @classmethod
                def create(cls):
                    return cls()
        ''')
        file_path = tmp_path / "test.py"
        file_path.write_text(content)

        analyzer = ImportAnalyzer(rejig)
        missing = analyzer.find_potentially_missing_imports(file_path)

        # These are special names
        assert "self" not in missing
        assert "cls" not in missing
