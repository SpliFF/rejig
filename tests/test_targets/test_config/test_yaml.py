"""
Tests for rejig.targets.config.yaml module.

This module tests YamlTarget for YAML configuration files:
- Reading and parsing YAML
- Getting/setting values via dotted key paths
- Section operations
- List operations

YamlTarget requires PyYAML to be installed.

Coverage targets:
- File existence checks
- get/set operations with dotted paths
- Section and list operations
- Dry run mode
- Error handling
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig import Rejig

# Check if PyYAML is available
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# Skip all tests if PyYAML is not available
pytestmark = pytest.mark.skipif(not HAS_YAML, reason="PyYAML not installed")


# =============================================================================
# YamlTarget Basic Tests
# =============================================================================

class TestYamlTargetBasic:
    """Tests for basic YamlTarget operations."""

    @pytest.fixture
    def yaml_file(self, tmp_path: Path) -> Path:
        """Create a sample YAML file."""
        content = textwrap.dedent("""\
            database:
              host: localhost
              port: 5432
              name: mydb
            server:
              debug: true
              workers: 4
            features:
              - auth
              - logging
              - caching
        """)
        file_path = tmp_path / "config.yaml"
        file_path.write_text(content)
        return file_path

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_yaml_target_exists(self, rejig: Rejig, yaml_file: Path):
        """
        YamlTarget.exists() should return True for existing files.
        """
        target = rejig.yaml(yaml_file)
        assert target.exists() is True

    def test_yaml_target_not_exists(self, rejig: Rejig, tmp_path: Path):
        """
        YamlTarget.exists() should return False for missing files.
        """
        target = rejig.yaml(tmp_path / "missing.yaml")
        assert target.exists() is False

    def test_yaml_get_simple_value(self, rejig: Rejig, yaml_file: Path):
        """
        get() should return values using dotted key paths.
        """
        target = rejig.yaml(yaml_file)

        # Get nested value
        host = target.get("database.host")
        assert host == "localhost"

        # Get integer value
        port = target.get("database.port")
        assert port == 5432

    def test_yaml_get_with_default(self, rejig: Rejig, yaml_file: Path):
        """
        get() should return default for missing keys.
        """
        target = rejig.yaml(yaml_file)

        # Key exists
        value = target.get("database.host", "default")
        assert value == "localhost"

        # Key doesn't exist
        value = target.get("database.timeout", 30)
        assert value == 30

    def test_yaml_get_list(self, rejig: Rejig, yaml_file: Path):
        """
        get() should return list values.
        """
        target = rejig.yaml(yaml_file)

        features = target.get("features")
        assert isinstance(features, list)
        assert "auth" in features
        assert "logging" in features

    def test_yaml_get_section(self, rejig: Rejig, yaml_file: Path):
        """
        get_section() should return a dictionary for nested sections.
        """
        target = rejig.yaml(yaml_file)

        database = target.get_section("database")
        assert database is not None
        assert database["host"] == "localhost"
        assert database["port"] == 5432

    def test_yaml_set_value(self, rejig: Rejig, yaml_file: Path):
        """
        set() should update values in the YAML file.
        """
        target = rejig.yaml(yaml_file)

        # Set new value
        result = target.set("database.port", 3306)
        assert result.success is True

        # Verify change
        assert target.get("database.port") == 3306

    def test_yaml_set_new_key(self, rejig: Rejig, yaml_file: Path):
        """
        set() should create new keys if they don't exist.
        """
        target = rejig.yaml(yaml_file)

        # Set new nested key
        result = target.set("database.timeout", 60)
        assert result.success is True

        # Verify new key
        assert target.get("database.timeout") == 60

    def test_yaml_has_key(self, rejig: Rejig, yaml_file: Path):
        """
        has_key() should check if keys exist.
        """
        target = rejig.yaml(yaml_file)

        assert target.has_key("database.host") is True
        assert target.has_key("database.missing") is False

    def test_yaml_keys(self, rejig: Rejig, yaml_file: Path):
        """
        keys() should return keys at a section.
        """
        target = rejig.yaml(yaml_file)

        # Root keys
        root_keys = target.keys()
        assert "database" in root_keys
        assert "server" in root_keys

        # Section keys
        db_keys = target.keys("database")
        assert "host" in db_keys
        assert "port" in db_keys

    def test_yaml_delete(self, rejig: Rejig, yaml_file: Path):
        """
        delete() should remove keys from the YAML file.
        """
        target = rejig.yaml(yaml_file)

        # Delete a key
        result = target.delete("server.debug")
        assert result.success is True

        # Verify deletion
        assert target.has_key("server.debug") is False


# =============================================================================
# YamlTarget List Operations
# =============================================================================

class TestYamlTargetLists:
    """Tests for YamlTarget list operations."""

    @pytest.fixture
    def yaml_file(self, tmp_path: Path) -> Path:
        """Create a YAML file with lists."""
        content = textwrap.dedent("""\
            plugins:
              - plugin-a
              - plugin-b
            settings:
              enabled_features: []
        """)
        file_path = tmp_path / "config.yaml"
        file_path.write_text(content)
        return file_path

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_append_to_list(self, rejig: Rejig, yaml_file: Path):
        """
        append_to_list() should add items to lists.
        """
        target = rejig.yaml(yaml_file)

        result = target.append_to_list("plugins", "plugin-c")
        assert result.success is True

        plugins = target.get("plugins")
        assert "plugin-c" in plugins

    def test_remove_from_list(self, rejig: Rejig, yaml_file: Path):
        """
        remove_from_list() should remove items from lists.
        """
        target = rejig.yaml(yaml_file)

        result = target.remove_from_list("plugins", "plugin-a")
        assert result.success is True

        plugins = target.get("plugins")
        assert "plugin-a" not in plugins


# =============================================================================
# YamlTarget Dry Run
# =============================================================================

class TestYamlTargetDryRun:
    """Tests for YamlTarget dry run mode."""

    @pytest.fixture
    def yaml_file(self, tmp_path: Path) -> Path:
        """Create a sample YAML file."""
        content = "setting: original\n"
        file_path = tmp_path / "config.yaml"
        file_path.write_text(content)
        return file_path

    def test_yaml_dry_run_does_not_modify(self, tmp_path: Path, yaml_file: Path):
        """
        In dry run mode, set() should not modify the file.
        """
        rejig = Rejig(str(tmp_path), dry_run=True)
        target = rejig.yaml(yaml_file)

        # Try to modify
        result = target.set("setting", "modified")
        assert result.success is True
        assert "DRY RUN" in result.message

        # File should be unchanged
        content = yaml_file.read_text()
        assert "original" in content
        assert "modified" not in content
