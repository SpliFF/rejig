"""
Tests for rejig.targets.config.ini module.

This module tests IniTarget for INI/CFG configuration files:
- Reading and parsing INI files
- Getting/setting values in sections
- Section operations
- Type conversion (int, float, bool)

IniTarget uses Python's built-in configparser (no extra dependencies).

Coverage targets:
- File existence checks
- get/set operations with sections
- Type-specific getters
- Section operations
- Dry run mode
- Error handling
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig import Rejig


# =============================================================================
# IniTarget Basic Tests
# =============================================================================

class TestIniTargetBasic:
    """Tests for basic IniTarget operations."""

    @pytest.fixture
    def ini_file(self, tmp_path: Path) -> Path:
        """Create a sample INI file."""
        content = textwrap.dedent("""\
            [metadata]
            name = my-project
            version = 1.0.0
            author = Test Author

            [options]
            debug = true
            max_workers = 4
            timeout = 30.5

            [database]
            host = localhost
            port = 5432
        """)
        file_path = tmp_path / "setup.cfg"
        file_path.write_text(content)
        return file_path

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_ini_target_exists(self, rejig: Rejig, ini_file: Path):
        """
        IniTarget.exists() should return True for existing files.
        """
        target = rejig.ini(ini_file)
        assert target.exists() is True

    def test_ini_target_not_exists(self, rejig: Rejig, tmp_path: Path):
        """
        IniTarget.exists() should return False for missing files.
        """
        target = rejig.ini(tmp_path / "missing.ini")
        assert target.exists() is False

    def test_ini_get_value(self, rejig: Rejig, ini_file: Path):
        """
        get() should return string values from sections.
        """
        target = rejig.ini(ini_file)

        name = target.get("metadata", "name")
        assert name == "my-project"

        host = target.get("database", "host")
        assert host == "localhost"

    def test_ini_get_with_default(self, rejig: Rejig, ini_file: Path):
        """
        get() should return default for missing keys.
        """
        target = rejig.ini(ini_file)

        # Key exists
        value = target.get("metadata", "name", "default")
        assert value == "my-project"

        # Key doesn't exist
        value = target.get("metadata", "license", "MIT")
        assert value == "MIT"

        # Section doesn't exist
        value = target.get("nonexistent", "key", "default")
        assert value == "default"

    def test_ini_get_int(self, rejig: Rejig, ini_file: Path):
        """
        get_int() should return integer values.
        """
        target = rejig.ini(ini_file)

        workers = target.get_int("options", "max_workers")
        assert workers == 4
        assert isinstance(workers, int)

        # Default for missing
        missing = target.get_int("options", "missing", 10)
        assert missing == 10

    def test_ini_get_float(self, rejig: Rejig, ini_file: Path):
        """
        get_float() should return float values.
        """
        target = rejig.ini(ini_file)

        timeout = target.get_float("options", "timeout")
        assert timeout == 30.5
        assert isinstance(timeout, float)

        # Default for missing
        missing = target.get_float("options", "missing", 1.0)
        assert missing == 1.0

    def test_ini_get_bool(self, rejig: Rejig, ini_file: Path):
        """
        get_bool() should return boolean values.
        """
        target = rejig.ini(ini_file)

        debug = target.get_bool("options", "debug")
        assert debug is True
        assert isinstance(debug, bool)

        # Default for missing
        missing = target.get_bool("options", "missing", False)
        assert missing is False

    def test_ini_set_value(self, rejig: Rejig, ini_file: Path):
        """
        set() should update values in INI files.
        """
        target = rejig.ini(ini_file)

        result = target.set("metadata", "version", "2.0.0")
        assert result.success is True

        # Verify change
        assert target.get("metadata", "version") == "2.0.0"

    def test_ini_set_new_key(self, rejig: Rejig, ini_file: Path):
        """
        set() should create new keys in existing sections.
        """
        target = rejig.ini(ini_file)

        result = target.set("metadata", "license", "MIT")
        assert result.success is True

        assert target.get("metadata", "license") == "MIT"

    def test_ini_set_new_section(self, rejig: Rejig, ini_file: Path):
        """
        set() should create new sections if needed.
        """
        target = rejig.ini(ini_file)

        result = target.set("new_section", "key", "value")
        assert result.success is True

        assert target.get("new_section", "key") == "value"

    def test_ini_has_section(self, rejig: Rejig, ini_file: Path):
        """
        has_section() should check if sections exist.
        """
        target = rejig.ini(ini_file)

        assert target.has_section("metadata") is True
        assert target.has_section("nonexistent") is False

    def test_ini_has_key(self, rejig: Rejig, ini_file: Path):
        """
        has_key() should check if keys exist in sections.
        """
        target = rejig.ini(ini_file)

        assert target.has_key("metadata", "name") is True
        assert target.has_key("metadata", "missing") is False

    def test_ini_sections(self, rejig: Rejig, ini_file: Path):
        """
        sections() should return all section names.
        """
        target = rejig.ini(ini_file)

        sections = target.sections()
        assert "metadata" in sections
        assert "options" in sections
        assert "database" in sections

    def test_ini_keys(self, rejig: Rejig, ini_file: Path):
        """
        keys() should return all keys in a section.
        """
        target = rejig.ini(ini_file)

        keys = target.keys("metadata")
        assert "name" in keys
        assert "version" in keys
        assert "author" in keys


# =============================================================================
# IniTarget Section Operations
# =============================================================================

class TestIniTargetSections:
    """Tests for IniTarget section operations."""

    @pytest.fixture
    def ini_file(self, tmp_path: Path) -> Path:
        """Create a sample INI file."""
        content = textwrap.dedent("""\
            [section1]
            key1 = value1

            [section2]
            key2 = value2
        """)
        file_path = tmp_path / "config.ini"
        file_path.write_text(content)
        return file_path

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_ini_get_section(self, rejig: Rejig, ini_file: Path):
        """
        get_section() should return all key-value pairs in a section.
        """
        target = rejig.ini(ini_file)

        section = target.get_section("section1")
        assert section["key1"] == "value1"

    def test_ini_set_section(self, rejig: Rejig, ini_file: Path):
        """
        set_section() should replace an entire section.
        """
        target = rejig.ini(ini_file)

        result = target.set_section("section1", {
            "new_key1": "new_value1",
            "new_key2": "new_value2"
        })
        assert result.success is True

        section = target.get_section("section1")
        assert "new_key1" in section
        assert "key1" not in section  # Old key should be gone

    def test_ini_add_section(self, rejig: Rejig, ini_file: Path):
        """
        add_section() should create a new empty section.
        """
        target = rejig.ini(ini_file)

        result = target.add_section("new_section")
        assert result.success is True

        assert target.has_section("new_section") is True

    def test_ini_delete_section(self, rejig: Rejig, ini_file: Path):
        """
        delete_section() should remove a section.
        """
        target = rejig.ini(ini_file)

        result = target.delete_section("section2")
        assert result.success is True

        assert target.has_section("section2") is False

    def test_ini_delete_key(self, rejig: Rejig, ini_file: Path):
        """
        delete_key() should remove a key from a section.
        """
        target = rejig.ini(ini_file)

        result = target.delete_key("section1", "key1")
        assert result.success is True

        assert target.has_key("section1", "key1") is False


# =============================================================================
# IniTarget Dry Run
# =============================================================================

class TestIniTargetDryRun:
    """Tests for IniTarget dry run mode."""

    @pytest.fixture
    def ini_file(self, tmp_path: Path) -> Path:
        """Create a sample INI file."""
        content = textwrap.dedent("""\
            [section]
            setting = original
        """)
        file_path = tmp_path / "config.ini"
        file_path.write_text(content)
        return file_path

    def test_ini_dry_run_does_not_modify(self, tmp_path: Path, ini_file: Path):
        """
        In dry run mode, set() should not modify the file.
        """
        rejig = Rejig(str(tmp_path), dry_run=True)
        target = rejig.ini(ini_file)

        # Try to modify
        result = target.set("section", "setting", "modified")
        assert result.success is True
        assert "DRY RUN" in result.message

        # File should be unchanged
        content = ini_file.read_text()
        assert "original" in content
        assert "modified" not in content


# =============================================================================
# IniTarget Error Handling
# =============================================================================

class TestIniTargetErrors:
    """Tests for IniTarget error handling."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_ini_get_missing_file(self, rejig: Rejig, tmp_path: Path):
        """
        get() should return default for missing files.
        """
        target = rejig.ini(tmp_path / "missing.ini")

        value = target.get("section", "key", "default")
        assert value == "default"

    def test_ini_get_missing_section(self, rejig: Rejig, tmp_path: Path):
        """
        get() should return default for missing sections.
        """
        ini_file = tmp_path / "config.ini"
        ini_file.write_text("[section]\nkey = value\n")

        target = rejig.ini(ini_file)

        value = target.get("missing_section", "key", "default")
        assert value == "default"

    def test_ini_invalid_int(self, rejig: Rejig, tmp_path: Path):
        """
        get_int() should return default for non-integer values.
        """
        ini_file = tmp_path / "config.ini"
        ini_file.write_text("[section]\nkey = not_an_int\n")

        target = rejig.ini(ini_file)

        value = target.get_int("section", "key", 42)
        assert value == 42
