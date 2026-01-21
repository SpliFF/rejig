"""
Tests for rejig.modules.merge module.

This module tests module merging utilities:
- MergedContent dataclass
- ModuleMerger class
- merge() method
- merge_modules() convenience function
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig import Rejig
from rejig.modules.merge import MergedContent, ModuleMerger, merge_modules


# =============================================================================
# MergedContent Tests
# =============================================================================

class TestMergedContent:
    """Tests for MergedContent dataclass."""

    def test_empty_merged_content(self):
        """MergedContent should have empty defaults."""
        content = MergedContent()
        assert content.imports == []
        assert content.future_imports == []
        assert content.docstrings == []
        assert content.definitions == []
        assert content.all_exports == []

    def test_merged_content_stores_data(self):
        """MergedContent should store provided data."""
        content = MergedContent(
            imports=["import os"],
            future_imports=["from __future__ import annotations"],
            docstrings=['"""Module docstring."""'],
            definitions=["def func(): pass"],
            all_exports=["func"],
        )
        assert len(content.imports) == 1
        assert len(content.future_imports) == 1
        assert len(content.docstrings) == 1
        assert len(content.definitions) == 1
        assert len(content.all_exports) == 1


# =============================================================================
# ModuleMerger Initialization Tests
# =============================================================================

class TestModuleMergerInit:
    """Tests for ModuleMerger initialization."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_init(self, rejig: Rejig):
        """ModuleMerger should initialize with Rejig instance."""
        merger = ModuleMerger(rejig)
        assert merger._rejig is rejig


# =============================================================================
# ModuleMerger.merge() Tests
# =============================================================================

class TestModuleMergerMerge:
    """Tests for ModuleMerger.merge()."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    @pytest.fixture
    def two_modules(self, tmp_path: Path) -> tuple[Path, Path]:
        """Create two simple modules."""
        module1 = tmp_path / "module1.py"
        module1.write_text(textwrap.dedent('''\
            """First module."""
            import os

            def func1():
                """Function 1."""
                pass
        '''))

        module2 = tmp_path / "module2.py"
        module2.write_text(textwrap.dedent('''\
            """Second module."""
            import sys

            def func2():
                """Function 2."""
                pass
        '''))

        return module1, module2

    def test_merge_missing_file(self, rejig: Rejig, tmp_path: Path):
        """merge() should fail if any file is missing."""
        merger = ModuleMerger(rejig)
        result = merger.merge(
            [tmp_path / "missing.py"],
            tmp_path / "output.py",
        )

        assert result.success is False
        assert "not found" in result.message

    def test_merge_creates_output(self, rejig: Rejig, two_modules: tuple[Path, Path], tmp_path: Path):
        """merge() should create merged output file."""
        module1, module2 = two_modules
        output_path = tmp_path / "merged.py"

        merger = ModuleMerger(rejig)
        result = merger.merge([module1, module2], output_path)

        assert result.success is True
        assert output_path.exists()

    def test_merge_combines_imports(self, rejig: Rejig, two_modules: tuple[Path, Path], tmp_path: Path):
        """merge() should combine imports from all modules."""
        module1, module2 = two_modules
        output_path = tmp_path / "merged.py"

        merger = ModuleMerger(rejig)
        result = merger.merge([module1, module2], output_path)

        assert result.success is True
        content = output_path.read_text()
        assert "import os" in content
        assert "import sys" in content

    def test_merge_combines_definitions(self, rejig: Rejig, two_modules: tuple[Path, Path], tmp_path: Path):
        """merge() should combine definitions from all modules."""
        module1, module2 = two_modules
        output_path = tmp_path / "merged.py"

        merger = ModuleMerger(rejig)
        result = merger.merge([module1, module2], output_path)

        assert result.success is True
        content = output_path.read_text()
        assert "def func1()" in content
        assert "def func2()" in content

    def test_merge_generates_all(self, rejig: Rejig, two_modules: tuple[Path, Path], tmp_path: Path):
        """merge() should generate __all__ by default."""
        module1, module2 = two_modules
        output_path = tmp_path / "merged.py"

        merger = ModuleMerger(rejig)
        result = merger.merge([module1, module2], output_path)

        assert result.success is True
        content = output_path.read_text()
        assert "__all__" in content
        assert '"func1"' in content
        assert '"func2"' in content

    def test_merge_no_all(self, rejig: Rejig, two_modules: tuple[Path, Path], tmp_path: Path):
        """merge() should skip __all__ when requested."""
        module1, module2 = two_modules
        output_path = tmp_path / "merged.py"

        merger = ModuleMerger(rejig)
        result = merger.merge([module1, module2], output_path, generate_all=False)

        assert result.success is True
        content = output_path.read_text()
        assert "__all__" not in content

    def test_merge_deduplicates_imports(self, rejig: Rejig, tmp_path: Path):
        """merge() should deduplicate identical imports."""
        module1 = tmp_path / "module1.py"
        module1.write_text("import os\ndef func1(): pass")

        module2 = tmp_path / "module2.py"
        module2.write_text("import os\ndef func2(): pass")

        output_path = tmp_path / "merged.py"

        merger = ModuleMerger(rejig)
        result = merger.merge([module1, module2], output_path)

        assert result.success is True
        content = output_path.read_text()
        # Should only have one 'import os'
        assert content.count("import os") == 1

    def test_merge_preserves_future_imports(self, rejig: Rejig, tmp_path: Path):
        """merge() should preserve __future__ imports."""
        module1 = tmp_path / "module1.py"
        module1.write_text("from __future__ import annotations\ndef func(): pass")

        output_path = tmp_path / "merged.py"

        merger = ModuleMerger(rejig)
        result = merger.merge([module1], output_path)

        assert result.success is True
        content = output_path.read_text()
        assert "from __future__ import annotations" in content
        # __future__ should be at the top
        lines = content.strip().split("\n")
        future_line = next((i for i, l in enumerate(lines) if "__future__" in l), -1)
        import_line = next((i for i, l in enumerate(lines) if l.startswith("import ") or l.startswith("from ") and "__future__" not in l), -1)
        if future_line != -1 and import_line != -1:
            assert future_line < import_line

    def test_merge_delete_originals(self, rejig: Rejig, two_modules: tuple[Path, Path], tmp_path: Path):
        """merge() should delete originals when requested."""
        module1, module2 = two_modules
        output_path = tmp_path / "merged.py"

        merger = ModuleMerger(rejig)
        result = merger.merge([module1, module2], output_path, delete_originals=True)

        assert result.success is True
        assert not module1.exists()
        assert not module2.exists()

    def test_merge_dry_run(self, tmp_path: Path, two_modules: tuple[Path, Path]):
        """merge() should not create file in dry-run mode."""
        module1, module2 = two_modules
        output_path = tmp_path / "merged.py"

        rejig = Rejig(str(tmp_path), dry_run=True)
        merger = ModuleMerger(rejig)
        result = merger.merge([module1, module2], output_path)

        assert result.success is True
        assert "[DRY RUN]" in result.message
        assert not output_path.exists()


# =============================================================================
# Convenience Function Tests
# =============================================================================

class TestConvenienceFunction:
    """Tests for merge_modules convenience function."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_merge_modules_function(self, rejig: Rejig, tmp_path: Path):
        """merge_modules() convenience function should work."""
        module = tmp_path / "module.py"
        module.write_text("def func(): pass")
        output = tmp_path / "output.py"

        result = merge_modules(rejig, [module], output)
        assert result.success is True


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases in module merging."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_merge_with_classes(self, rejig: Rejig, tmp_path: Path):
        """merge() should handle classes."""
        module = tmp_path / "module.py"
        module.write_text(textwrap.dedent('''\
            class MyClass:
                pass

            class OtherClass:
                pass
        '''))
        output = tmp_path / "output.py"

        merger = ModuleMerger(rejig)
        result = merger.merge([module], output)

        assert result.success is True
        content = output.read_text()
        assert "MyClass" in content
        assert "OtherClass" in content

    def test_merge_invalid_python(self, rejig: Rejig, tmp_path: Path):
        """merge() should handle invalid Python gracefully."""
        module = tmp_path / "invalid.py"
        module.write_text("this is not { valid python")
        output = tmp_path / "output.py"

        merger = ModuleMerger(rejig)
        result = merger.merge([module], output)

        # Should either fail gracefully or include raw content
        # Based on implementation, it adds raw content to definitions
        assert result.success is True or "Failed to parse" in result.message

    def test_merge_empty_file(self, rejig: Rejig, tmp_path: Path):
        """merge() should handle empty files."""
        module = tmp_path / "empty.py"
        module.write_text("")
        output = tmp_path / "output.py"

        merger = ModuleMerger(rejig)
        result = merger.merge([module], output)

        assert result.success is True

    def test_merge_single_module(self, rejig: Rejig, tmp_path: Path):
        """merge() should handle single module."""
        module = tmp_path / "single.py"
        module.write_text("def func(): pass")
        output = tmp_path / "output.py"

        merger = ModuleMerger(rejig)
        result = merger.merge([module], output)

        assert result.success is True
