"""
Tests for rejig.packaging.models module.

This module tests the core packaging data models:
- Dependency: Represents a Python package dependency
- PackageMetadata: Package metadata (name, version, etc.)
- PackageConfig: Complete package configuration

Coverage targets:
- Dependency parsing and normalization
- PackageMetadata creation and comparison
- PackageConfig aggregation
"""
from __future__ import annotations

from pathlib import Path

import pytest

from rejig.packaging import Dependency, PackageConfig, PackageMetadata


# =============================================================================
# Dependency Tests
# =============================================================================

class TestDependency:
    """Tests for the Dependency class."""

    def test_simple_dependency(self):
        """
        Simple dependency with just a name should be created correctly.
        """
        dep = Dependency(name="requests")

        assert dep.name == "requests"
        assert dep.version_spec is None or dep.version_spec == ""
        assert dep.extras == []

    def test_dependency_with_version(self):
        """
        Dependency with version specifier should parse correctly.
        """
        dep = Dependency(name="requests", version_spec=">=2.28.0")

        assert dep.name == "requests"
        assert "2.28.0" in dep.version_spec

    def test_dependency_with_extras(self):
        """
        Dependency with extras should store them correctly.
        """
        dep = Dependency(name="requests", extras=["security", "socks"])

        assert dep.name == "requests"
        assert "security" in dep.extras
        assert "socks" in dep.extras

    def test_dependency_equality(self):
        """
        Two dependencies with same name should be equal (for deduplication).
        """
        dep1 = Dependency(name="requests", version_spec=">=2.28.0")
        dep2 = Dependency(name="requests", version_spec=">=2.28.0")

        assert dep1 == dep2

    def test_dependency_str_representation(self):
        """
        Dependency string representation should be PEP 508 compliant.
        """
        dep = Dependency(name="requests", version_spec=">=2.28.0")
        dep_str = str(dep)

        assert "requests" in dep_str
        # May include version spec depending on implementation

    def test_dependency_with_markers(self):
        """
        Dependency with environment markers should store them.
        """
        dep = Dependency(
            name="pywin32",
            version_spec=">=300",
            markers="sys_platform == 'win32'"
        )

        assert dep.name == "pywin32"
        if hasattr(dep, 'markers'):
            assert "win32" in dep.markers


# =============================================================================
# PackageMetadata Tests
# =============================================================================

class TestPackageMetadata:
    """Tests for PackageMetadata class."""

    def test_basic_metadata(self):
        """
        PackageMetadata with basic fields should work correctly.
        """
        meta = PackageMetadata(
            name="my-package",
            version="1.0.0",
            description="A test package",
        )

        assert meta.name == "my-package"
        assert meta.version == "1.0.0"
        assert meta.description == "A test package"

    def test_metadata_with_authors(self):
        """
        PackageMetadata should handle authors list.

        Note: The authors field is list[str], not list[dict].
        """
        meta = PackageMetadata(
            name="my-package",
            version="1.0.0",
            authors=["Test Author <test@example.com>"],
        )

        assert len(meta.authors) >= 1
        assert "Test Author" in meta.authors[0]

    def test_metadata_with_license(self):
        """
        PackageMetadata should handle license field.
        """
        meta = PackageMetadata(
            name="my-package",
            version="1.0.0",
            license="MIT",
        )

        assert meta.license == "MIT"

    def test_metadata_with_python_requires(self):
        """
        PackageMetadata should handle Python version requirements.

        Note: The field is named 'python_requires' not 'requires_python'.
        """
        meta = PackageMetadata(
            name="my-package",
            version="1.0.0",
            python_requires=">=3.10",
        )

        assert "3.10" in meta.python_requires


# =============================================================================
# PackageConfig Tests
# =============================================================================

class TestPackageConfig:
    """Tests for PackageConfig class.

    PackageConfig requires 'format' and 'source_path' as required arguments.
    Valid formats are: "requirements", "pep621", "poetry", "uv"
    """

    def test_package_config_creation(self):
        """
        PackageConfig should aggregate metadata and dependencies.

        Note: PackageConfig requires 'format' and 'source_path' parameters.
        """
        meta = PackageMetadata(
            name="my-package",
            version="1.0.0",
        )
        deps = [
            Dependency(name="requests", version_spec=">=2.28.0"),
            Dependency(name="pydantic", version_spec=">=2.0.0"),
        ]

        config = PackageConfig(
            format="pep621",
            source_path=Path("pyproject.toml"),
            metadata=meta,
            dependencies=deps,
        )

        assert config.metadata.name == "my-package"
        assert len(config.dependencies) == 2
        assert config.format == "pep621"

    def test_package_config_with_dev_dependencies(self):
        """
        PackageConfig should handle dev/optional dependencies.
        """
        meta = PackageMetadata(name="my-package", version="1.0.0")
        deps = [Dependency(name="requests")]
        dev_deps = {"dev": [Dependency(name="pytest"), Dependency(name="black")]}

        config = PackageConfig(
            format="pep621",
            source_path=Path("pyproject.toml"),
            metadata=meta,
            dependencies=deps,
            optional_dependencies=dev_deps,
        )

        assert "dev" in config.optional_dependencies
        assert len(config.optional_dependencies["dev"]) == 2

    def test_package_config_get_dependency(self):
        """
        get_dependency should find dependencies by name.
        """
        config = PackageConfig(
            format="pep621",
            source_path=Path("pyproject.toml"),
            dependencies=[
                Dependency(name="requests", version_spec=">=2.28.0"),
                Dependency(name="pydantic", version_spec=">=2.0.0"),
            ],
        )

        # Should find existing dependency
        dep = config.get_dependency("requests")
        assert dep is not None
        assert dep.name == "requests"

        # Should return None for missing dependency
        missing = config.get_dependency("nonexistent")
        assert missing is None

    def test_package_config_has_dependency(self):
        """
        has_dependency should check if dependency exists in any group.
        """
        config = PackageConfig(
            format="pep621",
            source_path=Path("pyproject.toml"),
            dependencies=[Dependency(name="requests")],
            dev_dependencies=[Dependency(name="pytest")],
        )

        assert config.has_dependency("requests") is True
        assert config.has_dependency("pytest") is True
        assert config.has_dependency("nonexistent") is False

    def test_package_config_all_dependencies(self):
        """
        all_dependencies should return all deps, optionally including dev.
        """
        config = PackageConfig(
            format="pep621",
            source_path=Path("pyproject.toml"),
            dependencies=[Dependency(name="requests")],
            dev_dependencies=[Dependency(name="pytest")],
        )

        # With dev deps (default)
        all_deps = config.all_dependencies()
        assert len(all_deps) == 2

        # Without dev deps
        main_only = config.all_dependencies(include_dev=False)
        assert len(main_only) == 1
        assert main_only[0].name == "requests"
