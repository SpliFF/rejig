"""
Tests for rejig.targets.python.package - PackageTarget.

PackageTarget provides operations on Python packages (directories with __init__.py).

Coverage targets:
- Package existence checking
- Properties: name, file_path, init_file
- Module/subpackage discovery
- Navigation: find_module, find_subpackage, find_class, find_function
- Content access via get_content (__init__.py)
- Error handling for missing packages
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig import Rejig
from rejig.core.results import ErrorResult, Result
from rejig.targets import ErrorTarget, FileTarget, PackageTarget, TargetList


# =============================================================================
# Helper to create package structures
# =============================================================================

@pytest.fixture
def package_project(tmp_path: Path) -> Path:
    """
    Create a temporary project with packages for testing.

    Structure:
    tmp_path/
      mypkg/
        __init__.py
        models.py       (contains MyModel class)
        utils.py         (contains helper function)
        subpkg/
          __init__.py
          core.py        (contains CoreClass)
      empty_dir/         (no __init__.py)
    """
    # Main package
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text('"""My package."""\n')
    (pkg / "models.py").write_text(textwrap.dedent('''\
        """Models module."""

        class MyModel:
            """A model class."""

            def save(self) -> None:
                pass
    '''))
    (pkg / "utils.py").write_text(textwrap.dedent('''\
        """Utilities module."""

        def helper(x: int) -> int:
            return x * 2

        def format_name(name: str) -> str:
            return name.strip().title()
    '''))

    # Subpackage
    subpkg = pkg / "subpkg"
    subpkg.mkdir()
    (subpkg / "__init__.py").write_text('"""Sub-package."""\n')
    (subpkg / "core.py").write_text(textwrap.dedent('''\
        """Core module."""

        class CoreClass:
            """Core class."""

            def run(self) -> None:
                pass
    '''))

    # Non-package directory
    (tmp_path / "empty_dir").mkdir()

    return tmp_path


@pytest.fixture
def pkg_rejig(package_project: Path):
    """Rejig instance for the package project."""
    with Rejig(package_project) as rj:
        yield rj


# =============================================================================
# PackageTarget Existence and Properties
# =============================================================================

class TestPackageTargetExistence:
    """Tests for PackageTarget existence and basic properties."""

    def test_package_exists(self, pkg_rejig: Rejig, package_project: Path):
        """
        PackageTarget.exists() should return True for a directory with __init__.py.
        """
        pkg = pkg_rejig.package("mypkg")

        assert pkg.exists() is True

    def test_package_does_not_exist_no_init(self, pkg_rejig: Rejig, package_project: Path):
        """
        PackageTarget.exists() should return False for a directory without __init__.py.
        """
        pkg = pkg_rejig.package("empty_dir")

        assert pkg.exists() is False

    def test_package_does_not_exist_missing_dir(self, pkg_rejig: Rejig):
        """
        PackageTarget.exists() should return False for a nonexistent directory.
        """
        pkg = pkg_rejig.package("nonexistent_pkg")

        assert pkg.exists() is False

    def test_package_name_property(self, pkg_rejig: Rejig):
        """
        PackageTarget.name should return the directory name.
        """
        pkg = pkg_rejig.package("mypkg")

        assert pkg.name == "mypkg"

    def test_package_repr(self, pkg_rejig: Rejig):
        """
        PackageTarget repr should include the path.
        """
        pkg = pkg_rejig.package("mypkg")

        assert "PackageTarget" in repr(pkg)
        assert "mypkg" in repr(pkg)

    def test_init_file_property(self, pkg_rejig: Rejig, package_project: Path):
        """
        init_file property should return a FileTarget for __init__.py.
        """
        pkg = pkg_rejig.package("mypkg")
        init = pkg.init_file

        assert isinstance(init, FileTarget)
        assert init.exists() is True

    def test_init_file_missing_returns_error_target(self, pkg_rejig: Rejig):
        """
        init_file property should return ErrorTarget when __init__.py is missing.
        """
        pkg = pkg_rejig.package("empty_dir")
        init = pkg.init_file

        assert isinstance(init, ErrorTarget)


# =============================================================================
# PackageTarget Content
# =============================================================================

class TestPackageTargetContent:
    """Tests for PackageTarget content access."""

    def test_get_content_returns_init_content(self, pkg_rejig: Rejig):
        """
        get_content should return the __init__.py content.
        """
        pkg = pkg_rejig.package("mypkg")
        result = pkg.get_content()

        assert result.success is True
        assert "My package" in result.data

    def test_get_content_nonexistent_package(self, pkg_rejig: Rejig):
        """
        get_content on nonexistent package should return error.
        """
        pkg = pkg_rejig.package("nonexistent_pkg")
        result = pkg.get_content()

        assert result.success is False


# =============================================================================
# PackageTarget Module/Subpackage Discovery
# =============================================================================

class TestPackageTargetDiscovery:
    """Tests for module and subpackage discovery."""

    def test_get_modules(self, pkg_rejig: Rejig, package_project: Path):
        """
        get_modules should return all .py files in the package directory.
        """
        pkg = pkg_rejig.package("mypkg")
        modules = pkg.get_modules()

        names = [m.name for m in modules]
        assert "__init__.py" in names
        assert "models.py" in names
        assert "utils.py" in names

    def test_get_modules_nonexistent(self, pkg_rejig: Rejig):
        """
        get_modules on nonexistent package should return empty list.
        """
        pkg = pkg_rejig.package("nonexistent_pkg")
        modules = pkg.get_modules()

        assert modules == []

    def test_get_subpackages(self, pkg_rejig: Rejig, package_project: Path):
        """
        get_subpackages should return directories with __init__.py.
        """
        pkg = pkg_rejig.package("mypkg")
        subpackages = pkg.get_subpackages()

        names = [s.name for s in subpackages]
        assert "subpkg" in names

    def test_get_subpackages_nonexistent(self, pkg_rejig: Rejig):
        """
        get_subpackages on nonexistent package should return empty list.
        """
        pkg = pkg_rejig.package("nonexistent_pkg")
        subpackages = pkg.get_subpackages()

        assert subpackages == []


# =============================================================================
# PackageTarget Navigation
# =============================================================================

class TestPackageTargetNavigation:
    """Tests for PackageTarget navigation methods."""

    def test_find_module(self, pkg_rejig: Rejig, package_project: Path):
        """
        find_module should return a FileTarget for an existing module.
        """
        pkg = pkg_rejig.package("mypkg")
        module = pkg.find_module("models")

        assert isinstance(module, FileTarget)
        assert module.exists() is True

    def test_find_module_not_found(self, pkg_rejig: Rejig):
        """
        find_module for a missing module should return ErrorTarget.
        """
        pkg = pkg_rejig.package("mypkg")
        module = pkg.find_module("nonexistent")

        assert isinstance(module, ErrorTarget)

    def test_find_subpackage(self, pkg_rejig: Rejig, package_project: Path):
        """
        find_subpackage should return a PackageTarget for an existing subpackage.
        """
        pkg = pkg_rejig.package("mypkg")
        subpkg = pkg.find_subpackage("subpkg")

        assert isinstance(subpkg, PackageTarget)
        assert subpkg.exists() is True

    def test_find_subpackage_not_found(self, pkg_rejig: Rejig):
        """
        find_subpackage for a missing subpackage should return ErrorTarget.
        """
        pkg = pkg_rejig.package("mypkg")
        subpkg = pkg.find_subpackage("nonexistent")

        assert isinstance(subpkg, ErrorTarget)

    def test_find_class_in_package(self, pkg_rejig: Rejig):
        """
        find_class should search across all modules in the package.
        """
        pkg = pkg_rejig.package("mypkg")
        target = pkg.find_class("MyModel")

        assert target.exists() is True
        assert target.name == "MyModel"

    def test_find_class_not_in_package(self, pkg_rejig: Rejig):
        """
        find_class for a missing class should return ErrorTarget.
        """
        pkg = pkg_rejig.package("mypkg")
        target = pkg.find_class("NonExistentClass")

        assert isinstance(target, ErrorTarget)

    def test_find_function_in_package(self, pkg_rejig: Rejig):
        """
        find_function should search across all modules in the package.
        """
        pkg = pkg_rejig.package("mypkg")
        target = pkg.find_function("helper")

        assert target.exists() is True

    def test_find_function_not_in_package(self, pkg_rejig: Rejig):
        """
        find_function for a missing function should return ErrorTarget.
        """
        pkg = pkg_rejig.package("mypkg")
        target = pkg.find_function("nonexistent_func")

        assert isinstance(target, ErrorTarget)


# =============================================================================
# PackageTarget Chaining
# =============================================================================

class TestPackageTargetChaining:
    """Tests for chaining through PackageTarget."""

    def test_package_to_class_to_method(self, pkg_rejig: Rejig):
        """
        Should be able to chain package -> class -> method.
        """
        method = pkg_rejig.package("mypkg").find_class("MyModel").find_method("save")

        assert method.exists() is True

    def test_package_to_module_to_class(self, pkg_rejig: Rejig):
        """
        Should be able to chain package -> module -> class.
        """
        target = pkg_rejig.package("mypkg").find_module("models").find_class("MyModel")

        assert target.exists() is True

    def test_error_propagation_through_chain(self, pkg_rejig: Rejig):
        """
        Errors should propagate through chained operations without raising.
        """
        result = (
            pkg_rejig.package("nonexistent_pkg")
            .find_class("AnyClass")
            .add_attribute("x", "int", "0")
        )

        assert isinstance(result, ErrorResult)
        assert result.success is False
