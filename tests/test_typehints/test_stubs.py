"""
Tests for rejig.typehints.stubs module.

This module tests stub file generation:
- StubGenerator class
- generate_stub() method
- generate_for_file() method
- generate_for_package() method
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig.core.rejig import Rejig
from rejig.typehints.stubs import StubGenerator


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def stub_generator(tmp_path: Path) -> StubGenerator:
    """Create a StubGenerator instance."""
    rejig = Rejig(str(tmp_path))
    return StubGenerator(rejig)


@pytest.fixture
def dry_run_stub_generator(tmp_path: Path) -> StubGenerator:
    """Create a StubGenerator instance in dry-run mode."""
    rejig = Rejig(str(tmp_path), dry_run=True)
    return StubGenerator(rejig)


@pytest.fixture
def simple_module(tmp_path: Path) -> Path:
    """Create a simple Python module."""
    module_file = tmp_path / "simple.py"
    module_file.write_text(textwrap.dedent('''\
        """A simple module."""

        def hello(name: str) -> str:
            """Say hello."""
            return f"Hello, {name}!"

        def add(x: int, y: int) -> int:
            """Add two numbers."""
            return x + y
    '''))
    return module_file


@pytest.fixture
def module_with_class(tmp_path: Path) -> Path:
    """Create a module with a class."""
    module_file = tmp_path / "with_class.py"
    module_file.write_text(textwrap.dedent('''\
        """Module with a class."""

        class Calculator:
            """A simple calculator."""

            value: int

            def __init__(self, initial: int = 0) -> None:
                self.value = initial

            def add(self, x: int) -> int:
                """Add x to the value."""
                self.value += x
                return self.value

            def reset(self) -> None:
                """Reset to zero."""
                self.value = 0
    '''))
    return module_file


@pytest.fixture
def module_with_imports(tmp_path: Path) -> Path:
    """Create a module with imports."""
    module_file = tmp_path / "with_imports.py"
    module_file.write_text(textwrap.dedent('''\
        """Module with imports."""
        from typing import List, Optional
        from pathlib import Path

        def process(items: List[str], output: Optional[Path] = None) -> int:
            """Process items."""
            return len(items)
    '''))
    return module_file


@pytest.fixture
def module_with_decorators(tmp_path: Path) -> Path:
    """Create a module with decorated functions."""
    module_file = tmp_path / "with_decorators.py"
    module_file.write_text(textwrap.dedent('''\
        """Module with decorators."""
        from functools import lru_cache

        @lru_cache
        def expensive_computation(n: int) -> int:
            """Expensive computation."""
            return n ** 2

        class Service:
            @classmethod
            def create(cls) -> "Service":
                return cls()

            @staticmethod
            def helper(x: int) -> int:
                return x + 1

            @property
            def name(self) -> str:
                return "service"
    '''))
    return module_file


@pytest.fixture
def sample_package(tmp_path: Path) -> Path:
    """Create a sample Python package."""
    pkg_dir = tmp_path / "mypackage"
    pkg_dir.mkdir()

    # __init__.py
    (pkg_dir / "__init__.py").write_text(textwrap.dedent('''\
        """My package."""
        from .core import process
    '''))

    # core.py
    (pkg_dir / "core.py").write_text(textwrap.dedent('''\
        """Core functionality."""

        def process(data: str) -> str:
            """Process data."""
            return data.upper()
    '''))

    # utils.py
    (pkg_dir / "utils.py").write_text(textwrap.dedent('''\
        """Utility functions."""

        def helper(x: int) -> int:
            """Help with things."""
            return x + 1
    '''))

    return pkg_dir


# =============================================================================
# StubGenerator.generate_stub Tests
# =============================================================================

class TestGenerateStub:
    """Tests for StubGenerator.generate_stub."""

    def test_simple_functions(self, stub_generator: StubGenerator, simple_module: Path):
        """Should generate stubs for simple functions."""
        stub = stub_generator.generate_stub(simple_module)

        assert "def hello(name: str) -> str: ..." in stub
        assert "def add(x: int, y: int) -> int: ..." in stub

    def test_class_definition(self, stub_generator: StubGenerator, module_with_class: Path):
        """Should generate stubs for classes."""
        stub = stub_generator.generate_stub(module_with_class)

        assert "class Calculator:" in stub
        assert "value: int" in stub
        assert "def __init__(self, initial: int = 0) -> None: ..." in stub
        assert "def add(self, x: int) -> int: ..." in stub
        assert "def reset(self) -> None: ..." in stub

    def test_preserves_imports(self, stub_generator: StubGenerator, module_with_imports: Path):
        """Should preserve imports in stub."""
        stub = stub_generator.generate_stub(module_with_imports)

        assert "from typing import List, Optional" in stub
        assert "from pathlib import Path" in stub

    def test_decorated_functions(self, stub_generator: StubGenerator, module_with_decorators: Path):
        """Should preserve decorators in stub."""
        stub = stub_generator.generate_stub(module_with_decorators)

        assert "@lru_cache" in stub
        assert "@classmethod" in stub
        assert "@staticmethod" in stub
        assert "@property" in stub

    def test_function_with_defaults(self, stub_generator: StubGenerator, tmp_path: Path):
        """Should handle default values."""
        module_file = tmp_path / "defaults.py"
        module_file.write_text(textwrap.dedent('''\
            def func(x: int = 0, name: str = "default") -> None:
                pass
        '''))

        stub = stub_generator.generate_stub(module_file)

        assert 'x: int = 0' in stub
        assert 'name: str = "default"' in stub

    def test_complex_defaults_use_ellipsis(self, stub_generator: StubGenerator, tmp_path: Path):
        """Should use ... for complex default values."""
        module_file = tmp_path / "complex_defaults.py"
        module_file.write_text(textwrap.dedent('''\
            def func(data: list = [1, 2, 3, 4, 5, 6]) -> None:
                pass
        '''))

        stub = stub_generator.generate_stub(module_file)

        # Complex defaults should be replaced with ...
        assert "= ..." in stub

    def test_star_args(self, stub_generator: StubGenerator, tmp_path: Path):
        """Should handle *args."""
        module_file = tmp_path / "star_args.py"
        module_file.write_text(textwrap.dedent('''\
            def func(*args: int) -> None:
                pass
        '''))

        stub = stub_generator.generate_stub(module_file)

        assert "*args: int" in stub

    def test_star_kwargs(self, stub_generator: StubGenerator, tmp_path: Path):
        """Should handle **kwargs."""
        module_file = tmp_path / "star_kwargs.py"
        module_file.write_text(textwrap.dedent('''\
            def func(**kwargs: str) -> None:
                pass
        '''))

        stub = stub_generator.generate_stub(module_file)

        assert "**kwargs: str" in stub

    def test_keyword_only_args(self, stub_generator: StubGenerator, tmp_path: Path):
        """Should handle keyword-only arguments."""
        module_file = tmp_path / "kwonly.py"
        module_file.write_text(textwrap.dedent('''\
            def func(*, name: str, value: int = 0) -> None:
                pass
        '''))

        stub = stub_generator.generate_stub(module_file)

        assert "*, name: str" in stub

    def test_empty_class(self, stub_generator: StubGenerator, tmp_path: Path):
        """Should add ... for empty classes."""
        module_file = tmp_path / "empty_class.py"
        module_file.write_text(textwrap.dedent('''\
            class Empty:
                pass
        '''))

        stub = stub_generator.generate_stub(module_file)

        assert "class Empty:" in stub
        assert "    ..." in stub

    def test_class_with_bases(self, stub_generator: StubGenerator, tmp_path: Path):
        """Should handle class inheritance."""
        module_file = tmp_path / "inheritance.py"
        module_file.write_text(textwrap.dedent('''\
            class Child(Parent, Mixin):
                def method(self) -> None:
                    pass
        '''))

        stub = stub_generator.generate_stub(module_file)

        assert "class Child(Parent, Mixin):" in stub

    def test_module_level_annotations(self, stub_generator: StubGenerator, tmp_path: Path):
        """Should preserve module-level type annotations."""
        module_file = tmp_path / "module_vars.py"
        module_file.write_text(textwrap.dedent('''\
            VERSION: str = "1.0.0"
            DEBUG: bool = False
        '''))

        stub = stub_generator.generate_stub(module_file)

        assert 'VERSION: str = "1.0.0"' in stub
        assert "DEBUG: bool = False" in stub


# =============================================================================
# StubGenerator.generate_for_file Tests
# =============================================================================

class TestGenerateForFile:
    """Tests for StubGenerator.generate_for_file."""

    def test_creates_stub_file(self, stub_generator: StubGenerator, simple_module: Path):
        """Should create a .pyi stub file."""
        result = stub_generator.generate_for_file(simple_module)

        assert result.success is True
        assert result.files_changed

        stub_path = simple_module.with_suffix(".pyi")
        assert stub_path.exists()

        content = stub_path.read_text()
        assert "def hello(name: str) -> str: ..." in content

    def test_creates_stub_in_output_dir(self, stub_generator: StubGenerator, simple_module: Path, tmp_path: Path):
        """Should create stub in specified output directory."""
        output_dir = tmp_path / "stubs"

        result = stub_generator.generate_for_file(simple_module, output_dir=output_dir)

        assert result.success is True
        assert output_dir.exists()

        stub_path = output_dir / "simple.pyi"
        assert stub_path.exists()

    def test_fails_for_missing_file(self, stub_generator: StubGenerator, tmp_path: Path):
        """Should fail for missing source file."""
        nonexistent = tmp_path / "nonexistent.py"

        result = stub_generator.generate_for_file(nonexistent)

        assert result.success is False
        assert "not found" in result.message

    def test_dry_run_mode(self, dry_run_stub_generator: StubGenerator, simple_module: Path):
        """Should not create file in dry-run mode."""
        result = dry_run_stub_generator.generate_for_file(simple_module)

        assert result.success is True
        assert "[DRY RUN]" in result.message
        assert result.files_changed

        stub_path = simple_module.with_suffix(".pyi")
        assert not stub_path.exists()


# =============================================================================
# StubGenerator.generate_for_package Tests
# =============================================================================

class TestGenerateForPackage:
    """Tests for StubGenerator.generate_for_package."""

    def test_generates_stubs_for_all_modules(self, stub_generator: StubGenerator, sample_package: Path):
        """Should generate stubs for all modules in package."""
        result = stub_generator.generate_for_package(sample_package)

        assert result.success is True
        assert len(result.files_changed) >= 3  # __init__.py, core.py, utils.py

    def test_uses_default_output_dir(self, stub_generator: StubGenerator, sample_package: Path):
        """Should use 'stubs/' directory next to package by default."""
        result = stub_generator.generate_for_package(sample_package)

        assert result.success is True

        stubs_dir = sample_package.parent / "stubs" / "mypackage"
        assert stubs_dir.exists()
        assert (stubs_dir / "__init__.pyi").exists()
        assert (stubs_dir / "core.pyi").exists()
        assert (stubs_dir / "utils.pyi").exists()

    def test_uses_custom_output_dir(self, stub_generator: StubGenerator, sample_package: Path, tmp_path: Path):
        """Should use specified output directory."""
        output_dir = tmp_path / "custom_stubs"

        result = stub_generator.generate_for_package(sample_package, output_dir=output_dir)

        assert result.success is True
        assert (output_dir / "mypackage" / "core.pyi").exists()

    def test_fails_for_missing_package(self, stub_generator: StubGenerator, tmp_path: Path):
        """Should fail for missing package directory."""
        nonexistent = tmp_path / "nonexistent"

        result = stub_generator.generate_for_package(nonexistent)

        assert result.success is False
        assert "not found" in result.message

    def test_dry_run_mode(self, dry_run_stub_generator: StubGenerator, sample_package: Path):
        """Should not create files in dry-run mode."""
        result = dry_run_stub_generator.generate_for_package(sample_package)

        assert result.success is True
        assert "[DRY RUN]" in result.message
        assert len(result.files_changed) >= 3

        stubs_dir = sample_package.parent / "stubs"
        assert not stubs_dir.exists()

    def test_handles_nested_packages(self, stub_generator: StubGenerator, tmp_path: Path):
        """Should handle nested package structure."""
        # Create nested package
        pkg_dir = tmp_path / "outer"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text('"""Outer package."""\n')

        inner_dir = pkg_dir / "inner"
        inner_dir.mkdir()
        (inner_dir / "__init__.py").write_text('"""Inner package."""\n')
        (inner_dir / "module.py").write_text(textwrap.dedent('''\
            def func(x: int) -> int:
                return x
        '''))

        result = stub_generator.generate_for_package(pkg_dir)

        assert result.success is True

        stubs_dir = tmp_path / "stubs" / "outer"
        assert (stubs_dir / "inner" / "module.pyi").exists()


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases in stub generation."""

    def test_module_with_no_functions_or_classes(self, stub_generator: StubGenerator, tmp_path: Path):
        """Should handle module with only imports."""
        module_file = tmp_path / "only_imports.py"
        module_file.write_text(textwrap.dedent('''\
            """Just imports."""
            import os
            from typing import List
        '''))

        stub = stub_generator.generate_stub(module_file)

        assert "import os" in stub
        assert "from typing import List" in stub

    def test_function_without_type_hints(self, stub_generator: StubGenerator, tmp_path: Path):
        """Should handle functions without type hints."""
        module_file = tmp_path / "no_hints.py"
        module_file.write_text(textwrap.dedent('''\
            def func(x, y):
                return x + y
        '''))

        stub = stub_generator.generate_stub(module_file)

        assert "def func(x, y): ..." in stub

    def test_async_function(self, stub_generator: StubGenerator, tmp_path: Path):
        """Should handle async functions."""
        module_file = tmp_path / "async_module.py"
        module_file.write_text(textwrap.dedent('''\
            async def fetch(url: str) -> str:
                return ""
        '''))

        stub = stub_generator.generate_stub(module_file)

        # async should be in the stub (if preserved by libcst)
        assert "def fetch(url: str) -> str: ..." in stub

    def test_class_with_class_variables(self, stub_generator: StubGenerator, tmp_path: Path):
        """Should preserve class variables with annotations."""
        module_file = tmp_path / "class_vars.py"
        module_file.write_text(textwrap.dedent('''\
            class Config:
                debug: bool = False
                version: str = "1.0"
        '''))

        stub = stub_generator.generate_stub(module_file)

        assert "class Config:" in stub
        assert "debug: bool = False" in stub
        assert 'version: str = "1.0"' in stub

    def test_overloaded_functions(self, stub_generator: StubGenerator, tmp_path: Path):
        """Should preserve @overload decorators."""
        module_file = tmp_path / "overloads.py"
        module_file.write_text(textwrap.dedent('''\
            from typing import overload

            @overload
            def process(x: int) -> int: ...
            @overload
            def process(x: str) -> str: ...
            def process(x):
                return x
        '''))

        stub = stub_generator.generate_stub(module_file)

        assert "@overload" in stub
        assert "def process(x: int) -> int: ..." in stub
        assert "def process(x: str) -> str: ..." in stub
