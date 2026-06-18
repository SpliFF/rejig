"""
Tests for rejig.targets.python.module - ModuleTarget.

ModuleTarget resolves dotted module paths (e.g., "src.models") to Python files
and delegates operations to FileTarget.

Coverage targets:
- Module path resolution (dotted path -> filesystem path)
- Existence checking for existing/nonexistent modules
- Navigation: find_class, find_function, find_classes, find_functions
- Content access via get_content
- Error handling for missing modules
- Repr
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig import Rejig
from rejig.core.results import ErrorResult, Result
from rejig.targets import ErrorTarget, ModuleTarget, TargetList


# =============================================================================
# ModuleTarget Existence and Properties
# =============================================================================

class TestModuleTargetExistence:
    """Tests for ModuleTarget existence and path resolution."""

    def test_module_exists_by_dotted_path(self, rejig: Rejig):
        """
        ModuleTarget should resolve a dotted path to a file and report exists=True.
        """
        # src/models.py should be resolvable as "src.models"
        module = rejig.module("src.models")

        assert module.exists() is True

    def test_module_file_path_resolved(self, rejig: Rejig):
        """
        After resolution, file_path should point to the actual .py file.
        """
        module = rejig.module("src.models")

        # file_path should be resolved
        assert module.file_path is not None
        assert module.file_path.name == "models.py"

    def test_nonexistent_module_exists_false(self, rejig: Rejig):
        """
        A module path that doesn't match any file should report exists=False.
        """
        module = rejig.module("nonexistent.module.path")

        assert module.exists() is False

    def test_module_repr(self, rejig: Rejig):
        """
        ModuleTarget repr should include the module path.
        """
        module = rejig.module("src.models")

        repr_str = repr(module)
        assert "ModuleTarget" in repr_str
        assert "src.models" in repr_str

    def test_module_path_attribute(self, rejig: Rejig):
        """
        module_path attribute should store the original dotted path.
        """
        module = rejig.module("src.models")

        assert module.module_path == "src.models"


# =============================================================================
# ModuleTarget Content Access
# =============================================================================

class TestModuleTargetContent:
    """Tests for ModuleTarget content access."""

    def test_get_content_success(self, rejig: Rejig):
        """
        get_content should return the file content for an existing module.
        """
        module = rejig.module("src.models")
        result = module.get_content()

        assert result.success is True
        assert "class MyClass" in result.data

    def test_get_content_nonexistent_module(self, rejig: Rejig):
        """
        get_content on a nonexistent module should return an error result.
        """
        module = rejig.module("nonexistent.module")
        result = module.get_content()

        assert result.success is False
        assert isinstance(result, ErrorResult)


# =============================================================================
# ModuleTarget Navigation
# =============================================================================

class TestModuleTargetNavigation:
    """Tests for ModuleTarget navigation methods."""

    def test_find_class_in_module(self, rejig: Rejig):
        """
        find_class should find a class within the resolved module.
        """
        target = rejig.module("src.models").find_class("MyClass")

        assert target.exists() is True
        assert target.name == "MyClass"

    def test_find_class_nonexistent_module(self, rejig: Rejig):
        """
        find_class on a nonexistent module should return ErrorTarget.
        """
        target = rejig.module("nonexistent").find_class("AnyClass")

        assert isinstance(target, ErrorTarget)
        assert target.exists() is False

    def test_find_function_in_module(self, rejig: Rejig):
        """
        find_function should find a module-level function in the resolved module.
        """
        target = rejig.module("src.utils").find_function("simple_function")

        assert target.exists() is True

    def test_find_function_nonexistent_module(self, rejig: Rejig):
        """
        find_function on a nonexistent module should return ErrorTarget.
        """
        target = rejig.module("nonexistent").find_function("any_func")

        assert isinstance(target, ErrorTarget)

    def test_find_classes_in_module(self, rejig: Rejig):
        """
        find_classes should return all classes in the module.
        """
        classes = rejig.module("src.models").find_classes()

        assert isinstance(classes, TargetList)
        assert len(classes) >= 1

    def test_find_classes_nonexistent_module(self, rejig: Rejig):
        """
        find_classes on a nonexistent module should return empty TargetList.
        """
        classes = rejig.module("nonexistent").find_classes()

        assert isinstance(classes, TargetList)
        assert len(classes) == 0

    def test_find_functions_in_module(self, rejig: Rejig):
        """
        find_functions should return all functions in the module.
        """
        functions = rejig.module("src.utils").find_functions()

        assert isinstance(functions, TargetList)
        assert len(functions) >= 1

    def test_find_functions_nonexistent_module(self, rejig: Rejig):
        """
        find_functions on a nonexistent module should return empty TargetList.
        """
        functions = rejig.module("nonexistent").find_functions()

        assert isinstance(functions, TargetList)
        assert len(functions) == 0

    def test_chained_navigation(self, rejig: Rejig):
        """
        Should be able to chain module -> class -> method.
        """
        method = rejig.module("src.models").find_class("MyClass").find_method("process")

        assert method.exists() is True
        assert method.name == "process"

    def test_chained_navigation_error_propagation(self, rejig: Rejig):
        """
        Errors should propagate through chained navigation.
        """
        result = (
            rejig.module("nonexistent")
            .find_class("AnyClass")
            .find_method("any_method")
            .add_decorator("property")
        )

        assert isinstance(result, ErrorResult)
        assert result.success is False


# =============================================================================
# Package Init Resolution
# =============================================================================

class TestModulePackageResolution:
    """Tests for resolving package paths (directories with __init__.py)."""

    def test_resolve_package_init(self, tmp_path: Path):
        """
        A dotted path pointing to a package (directory with __init__.py)
        should resolve to the __init__.py file.
        """
        # Create package structure
        pkg_dir = tmp_path / "mypkg"
        pkg_dir.mkdir()
        init_file = pkg_dir / "__init__.py"
        init_file.write_text('"""Package init."""\n\nclass InitClass:\n    pass\n')

        rj = Rejig(tmp_path)
        module = rj.module("mypkg")

        assert module.exists() is True
        assert module.file_path is not None
        assert module.file_path.name == "__init__.py"
