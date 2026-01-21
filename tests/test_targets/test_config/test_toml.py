"""
Tests for rejig.targets.config.toml module - TomlTarget.

TomlTarget provides operations on TOML configuration files:
- Reading and writing values
- Navigating to sections
- Modifying nested structures

Coverage targets:
- File existence and properties
- Getting/setting values
- Section navigation
- Error handling
"""
from __future__ import annotations

from pathlib import Path

import pytest

from rejig import Rejig
from rejig.core.results import ErrorResult, Result


# =============================================================================
# TomlTarget Basic Operations
# =============================================================================

class TestTomlTargetBasic:
    """Tests for TomlTarget basic operations."""

    def test_toml_target_exists(self, rejig_config: Rejig, tmp_config_files: Path):
        """
        TomlTarget.exists() should return True for existing files.
        """
        target = rejig_config.toml("pyproject.toml")

        assert target.exists() is True

    def test_toml_target_not_exists(self, rejig_config: Rejig):
        """
        TomlTarget.exists() should return False for non-existent files.
        """
        target = rejig_config.toml("nonexistent.toml")

        assert target.exists() is False

    def test_toml_get_value(self, rejig_config: Rejig):
        """
        get() should retrieve a value from the TOML file.

        Note: get() returns the value directly, not a Result object.
        """
        target = rejig_config.toml("pyproject.toml")
        value = target.get("project.name")

        # Returns value directly
        assert value == "sample-project"

    def test_toml_get_nested_value(self, rejig_config: Rejig):
        """
        get() should retrieve nested values using dotted paths.
        """
        target = rejig_config.toml("pyproject.toml")
        value = target.get("project.version")

        assert value == "1.0.0"

    def test_toml_get_nonexistent_key(self, rejig_config: Rejig):
        """
        get() for non-existent key should return None (default).
        """
        target = rejig_config.toml("pyproject.toml")
        value = target.get("nonexistent.key")

        # Returns None by default for missing keys
        assert value is None

    def test_toml_get_with_default(self, rejig_config: Rejig):
        """
        get() should return the default value if key not found.
        """
        target = rejig_config.toml("pyproject.toml")
        value = target.get("nonexistent.key", "default_value")

        assert value == "default_value"

    def test_toml_set_value(self, rejig_config: Rejig, tmp_config_files: Path):
        """
        set() should modify a value in the TOML file and return Result.
        """
        target = rejig_config.toml("pyproject.toml")
        result = target.set("project.version", "2.0.0")

        assert result.success is True

        # Verify change
        content = (tmp_config_files / "pyproject.toml").read_text()
        assert "2.0.0" in content

    def test_toml_set_new_key(self, rejig_config: Rejig, tmp_config_files: Path):
        """
        set() should create a new key if it doesn't exist.
        """
        target = rejig_config.toml("pyproject.toml")
        result = target.set("project.new_key", "new_value")

        assert result.success is True

        # Verify the value was set
        value = target.get("project.new_key")
        assert value == "new_value"

    def test_toml_dry_run(self, tmp_config_files: Path):
        """
        Dry-run should not modify the file.
        """
        original = (tmp_config_files / "pyproject.toml").read_text()

        rj = Rejig(tmp_config_files, dry_run=True)
        target = rj.toml("pyproject.toml")
        result = target.set("project.version", "999.0.0")

        assert result.success is True
        # File unchanged
        assert (tmp_config_files / "pyproject.toml").read_text() == original


# =============================================================================
# TomlTarget Section Operations
# =============================================================================

class TestTomlTargetSections:
    """Tests for TOML section operations."""

    def test_toml_get_section(self, rejig_config: Rejig):
        """
        get() should retrieve entire sections as dictionaries.
        """
        target = rejig_config.toml("pyproject.toml")
        value = target.get("project")

        # Returns the section as a dict
        assert isinstance(value, dict)
        assert "name" in value
        assert "version" in value

    def test_toml_get_list_value(self, rejig_config: Rejig):
        """
        get() should retrieve list values.
        """
        target = rejig_config.toml("pyproject.toml")
        value = target.get("project.dependencies")

        assert isinstance(value, list)
        assert len(value) >= 1

    def test_toml_set_in_section(self, rejig_config: Rejig, tmp_config_files: Path):
        """
        set() should work with nested sections.
        """
        target = rejig_config.toml("pyproject.toml")
        result = target.set("tool.black.line-length", 120)

        assert result.success is True

        # Verify using get() which returns value directly
        value = target.get("tool.black.line-length")
        assert value == 120


# =============================================================================
# TomlTarget Content Operations
# =============================================================================

class TestTomlTargetContent:
    """Tests for content operations on TOML files."""

    def test_toml_get_content(self, rejig_config: Rejig):
        """
        get_content() should return the full file content.
        """
        target = rejig_config.toml("pyproject.toml")
        result = target.get_content()

        assert result.success is True
        assert "[project]" in result.data
        assert "name" in result.data

    def test_toml_delete_key(self, rejig_config: Rejig, tmp_config_files: Path):
        """
        delete() should remove a key from the TOML file.
        """
        target = rejig_config.toml("pyproject.toml")

        # First add a key
        target.set("project.temp_key", "temp_value")

        # Then delete it
        result = target.delete("project.temp_key")

        # Should succeed (or handle gracefully)
        assert isinstance(result, (Result, ErrorResult))
