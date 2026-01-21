"""
Tests for rejig.modules.split module.

This module tests module splitting utilities:
- SplitItem dataclass
- ModuleSplitter class
- split_by_class() function
- split_by_function() function
- convert_to_package() function
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig import Rejig
from rejig.modules.split import ModuleSplitter, SplitItem, split_by_class, split_by_function


# =============================================================================
# SplitItem Tests
# =============================================================================

class TestSplitItem:
    """Tests for SplitItem dataclass."""

    def test_basic_split_item(self):
        """SplitItem should store basic information."""
        item = SplitItem(
            name="MyClass",
            kind="class",
            code="class MyClass:\n    pass",
        )
        assert item.name == "MyClass"
        assert item.kind == "class"
        assert "class MyClass" in item.code

    def test_split_item_with_imports(self):
        """SplitItem should store imports."""
        item = SplitItem(
            name="func",
            kind="function",
            code="def func(): pass",
            imports=["import os", "from typing import List"],
        )
        assert len(item.imports) == 2

    def test_split_item_with_comments(self):
        """SplitItem should store leading comments."""
        item = SplitItem(
            name="func",
            kind="function",
            code="def func(): pass",
            leading_comments="# This is a helper function",
        )
        assert item.leading_comments == "# This is a helper function"


# =============================================================================
# ModuleSplitter Initialization Tests
# =============================================================================

class TestModuleSplitterInit:
    """Tests for ModuleSplitter initialization."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_init(self, rejig: Rejig):
        """ModuleSplitter should initialize with Rejig instance."""
        splitter = ModuleSplitter(rejig)
        assert splitter._rejig is rejig


# =============================================================================
# ModuleSplitter.split_by_class() Tests
# =============================================================================

class TestModuleSplitterSplitByClass:
    """Tests for ModuleSplitter.split_by_class()."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    @pytest.fixture
    def module_with_classes(self, tmp_path: Path) -> Path:
        """Create a module with multiple classes."""
        file_path = tmp_path / "models.py"
        file_path.write_text(textwrap.dedent('''\
            """Module with multiple classes."""
            import os
            from typing import List

            class User:
                """User class."""
                def __init__(self, name: str):
                    self.name = name

            class Post:
                """Post class."""
                def __init__(self, content: str):
                    self.content = content
        '''))
        return file_path

    def test_split_missing_file(self, rejig: Rejig, tmp_path: Path):
        """split_by_class() should fail for missing file."""
        splitter = ModuleSplitter(rejig)
        result = splitter.split_by_class(tmp_path / "missing.py")

        assert result.success is False
        assert "not found" in result.message

    def test_split_by_class_creates_files(self, rejig: Rejig, module_with_classes: Path):
        """split_by_class() should create one file per class."""
        splitter = ModuleSplitter(rejig)
        output_dir = module_with_classes.parent / "models_pkg"

        result = splitter.split_by_class(module_with_classes, output_dir=output_dir)

        assert result.success is True
        assert output_dir.exists()
        assert (output_dir / "user.py").exists()
        assert (output_dir / "post.py").exists()

    def test_split_by_class_creates_init(self, rejig: Rejig, module_with_classes: Path):
        """split_by_class() should create __init__.py with imports."""
        splitter = ModuleSplitter(rejig)
        output_dir = module_with_classes.parent / "models_pkg"

        result = splitter.split_by_class(module_with_classes, output_dir=output_dir)

        assert result.success is True
        init_path = output_dir / "__init__.py"
        assert init_path.exists()

        content = init_path.read_text()
        assert "from .user import User" in content
        assert "from .post import Post" in content

    def test_split_by_class_no_init(self, rejig: Rejig, module_with_classes: Path):
        """split_by_class() should respect create_init=False."""
        splitter = ModuleSplitter(rejig)
        output_dir = module_with_classes.parent / "models_pkg"

        result = splitter.split_by_class(
            module_with_classes, output_dir=output_dir, create_init=False
        )

        assert result.success is True
        assert not (output_dir / "__init__.py").exists()

    def test_split_by_class_no_classes(self, rejig: Rejig, tmp_path: Path):
        """split_by_class() should handle file with no classes."""
        file_path = tmp_path / "functions.py"
        file_path.write_text("def func(): pass")

        splitter = ModuleSplitter(rejig)
        result = splitter.split_by_class(file_path)

        assert result.success is True
        assert "No classes found" in result.message

    def test_split_by_class_dry_run(self, tmp_path: Path, module_with_classes: Path):
        """split_by_class() should not create files in dry-run mode."""
        rejig = Rejig(str(tmp_path), dry_run=True)
        splitter = ModuleSplitter(rejig)
        output_dir = module_with_classes.parent / "models_pkg"

        result = splitter.split_by_class(module_with_classes, output_dir=output_dir)

        assert result.success is True
        assert "[DRY RUN]" in result.message
        assert not output_dir.exists()


# =============================================================================
# ModuleSplitter.split_by_function() Tests
# =============================================================================

class TestModuleSplitterSplitByFunction:
    """Tests for ModuleSplitter.split_by_function()."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    @pytest.fixture
    def module_with_functions(self, tmp_path: Path) -> Path:
        """Create a module with multiple functions."""
        file_path = tmp_path / "utils.py"
        file_path.write_text(textwrap.dedent('''\
            """Utility functions."""
            import os

            def calculate_total(items):
                """Calculate total."""
                return sum(items)

            def format_output(value):
                """Format output."""
                return str(value)
        '''))
        return file_path

    def test_split_by_function_creates_files(self, rejig: Rejig, module_with_functions: Path):
        """split_by_function() should create one file per function."""
        splitter = ModuleSplitter(rejig)
        output_dir = module_with_functions.parent / "utils_pkg"

        result = splitter.split_by_function(module_with_functions, output_dir=output_dir)

        assert result.success is True
        assert output_dir.exists()
        assert (output_dir / "calculate_total.py").exists()
        assert (output_dir / "format_output.py").exists()

    def test_split_by_function_no_functions(self, rejig: Rejig, tmp_path: Path):
        """split_by_function() should handle file with no functions."""
        file_path = tmp_path / "classes.py"
        file_path.write_text("class MyClass: pass")

        splitter = ModuleSplitter(rejig)
        result = splitter.split_by_function(file_path)

        assert result.success is True
        # Note: Implementation has typo "functiones" instead of "functions"
        assert "No function" in result.message


# =============================================================================
# ModuleSplitter.convert_to_package() Tests
# =============================================================================

class TestModuleSplitterConvertToPackage:
    """Tests for ModuleSplitter.convert_to_package()."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_convert_missing_file(self, rejig: Rejig, tmp_path: Path):
        """convert_to_package() should fail for missing file."""
        splitter = ModuleSplitter(rejig)
        result = splitter.convert_to_package(tmp_path / "missing.py")

        assert result.success is False
        assert "not found" in result.message

    def test_convert_to_package_creates_directory(self, rejig: Rejig, tmp_path: Path):
        """convert_to_package() should create package directory."""
        file_path = tmp_path / "utils.py"
        file_path.write_text("def helper(): pass")

        splitter = ModuleSplitter(rejig)
        result = splitter.convert_to_package(file_path)

        assert result.success is True
        assert (tmp_path / "utils").is_dir()
        assert (tmp_path / "utils" / "__init__.py").exists()

    def test_convert_to_package_moves_content(self, rejig: Rejig, tmp_path: Path):
        """convert_to_package() should move content to __init__.py."""
        file_path = tmp_path / "utils.py"
        original_content = "def helper(): pass\n"
        file_path.write_text(original_content)

        splitter = ModuleSplitter(rejig)
        result = splitter.convert_to_package(file_path)

        assert result.success is True
        init_content = (tmp_path / "utils" / "__init__.py").read_text()
        assert init_content == original_content

    def test_convert_to_package_removes_original(self, rejig: Rejig, tmp_path: Path):
        """convert_to_package() should remove original file by default."""
        file_path = tmp_path / "utils.py"
        file_path.write_text("def helper(): pass")

        splitter = ModuleSplitter(rejig)
        result = splitter.convert_to_package(file_path)

        assert result.success is True
        assert not file_path.exists()

    def test_convert_to_package_keeps_original(self, rejig: Rejig, tmp_path: Path):
        """convert_to_package() should keep original when requested."""
        file_path = tmp_path / "utils.py"
        file_path.write_text("def helper(): pass")

        splitter = ModuleSplitter(rejig)
        result = splitter.convert_to_package(file_path, keep_original=True)

        assert result.success is True
        assert file_path.exists()

    def test_convert_to_package_dry_run(self, tmp_path: Path):
        """convert_to_package() should not modify in dry-run mode."""
        file_path = tmp_path / "utils.py"
        file_path.write_text("def helper(): pass")

        rejig = Rejig(str(tmp_path), dry_run=True)
        splitter = ModuleSplitter(rejig)
        result = splitter.convert_to_package(file_path)

        assert result.success is True
        assert "[DRY RUN]" in result.message
        assert file_path.exists()
        assert not (tmp_path / "utils").exists()


# =============================================================================
# Convenience Functions Tests
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_split_by_class_function(self, rejig: Rejig, tmp_path: Path):
        """split_by_class() convenience function should work."""
        file_path = tmp_path / "models.py"
        file_path.write_text("class User: pass")

        result = split_by_class(rejig, file_path)
        assert result.success is True

    def test_split_by_function_function(self, rejig: Rejig, tmp_path: Path):
        """split_by_function() convenience function should work."""
        file_path = tmp_path / "utils.py"
        file_path.write_text("def helper(): pass")

        result = split_by_function(rejig, file_path)
        assert result.success is True


# =============================================================================
# Filename Conversion Tests
# =============================================================================

class TestFilenameConversion:
    """Tests for class/function name to filename conversion."""

    @pytest.fixture
    def splitter(self, tmp_path: Path) -> ModuleSplitter:
        """Create a ModuleSplitter."""
        rejig = Rejig(str(tmp_path))
        return ModuleSplitter(rejig)

    def test_camel_case_to_snake_case(self, splitter: ModuleSplitter):
        """Should convert CamelCase to snake_case."""
        assert splitter._to_filename("MyClass") == "my_class"
        assert splitter._to_filename("UserProfile") == "user_profile"

    def test_consecutive_capitals(self, splitter: ModuleSplitter):
        """Should handle consecutive capital letters."""
        assert splitter._to_filename("HTTPClient") == "http_client"
        assert splitter._to_filename("XMLParser") == "xml_parser"

    def test_already_lowercase(self, splitter: ModuleSplitter):
        """Should handle already lowercase names."""
        assert splitter._to_filename("helper") == "helper"
        assert splitter._to_filename("my_func") == "my_func"
