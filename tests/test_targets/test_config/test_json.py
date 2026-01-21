"""
Tests for rejig.targets.config.json module.

This module tests JsonTarget for JSON configuration files:
- Reading and parsing JSON
- Getting/setting values via dotted key paths
- package.json specific helpers

JsonTarget uses Python's built-in json module (no extra dependencies).

Coverage targets:
- File existence checks
- get/set operations with dotted paths
- delete operations
- package.json helpers
- Dry run mode
- Error handling
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from rejig import Rejig


# =============================================================================
# JsonTarget Basic Tests
# =============================================================================

class TestJsonTargetBasic:
    """Tests for basic JsonTarget operations."""

    @pytest.fixture
    def json_file(self, tmp_path: Path) -> Path:
        """Create a sample JSON file."""
        content = {
            "name": "my-project",
            "version": "1.0.0",
            "scripts": {
                "build": "npm run build",
                "test": "jest"
            },
            "dependencies": {
                "react": "^18.0.0",
                "lodash": "^4.17.0"
            },
            "features": ["auth", "api", "ui"]
        }
        file_path = tmp_path / "package.json"
        file_path.write_text(json.dumps(content, indent=2))
        return file_path

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_json_target_exists(self, rejig: Rejig, json_file: Path):
        """
        JsonTarget.exists() should return True for existing files.
        """
        target = rejig.json(json_file)
        assert target.exists() is True

    def test_json_target_not_exists(self, rejig: Rejig, tmp_path: Path):
        """
        JsonTarget.exists() should return False for missing files.
        """
        target = rejig.json(tmp_path / "missing.json")
        assert target.exists() is False

    def test_json_get_simple_value(self, rejig: Rejig, json_file: Path):
        """
        get() should return values using dotted key paths.
        """
        target = rejig.json(json_file)

        # Get top-level value
        name = target.get("name")
        assert name == "my-project"

        # Get nested value
        build_cmd = target.get("scripts.build")
        assert build_cmd == "npm run build"

    def test_json_get_with_default(self, rejig: Rejig, json_file: Path):
        """
        get() should return default for missing keys.
        """
        target = rejig.json(json_file)

        # Key exists
        value = target.get("name", "default")
        assert value == "my-project"

        # Key doesn't exist
        value = target.get("author", "Unknown")
        assert value == "Unknown"

    def test_json_get_list(self, rejig: Rejig, json_file: Path):
        """
        get() should return list values.
        """
        target = rejig.json(json_file)

        features = target.get("features")
        assert isinstance(features, list)
        assert "auth" in features
        assert "api" in features

    def test_json_set_value(self, rejig: Rejig, json_file: Path):
        """
        set() should update values in the JSON file.
        """
        target = rejig.json(json_file)

        # Set new value
        result = target.set("version", "2.0.0")
        assert result.success is True

        # Verify change
        assert target.get("version") == "2.0.0"

    def test_json_set_nested_value(self, rejig: Rejig, json_file: Path):
        """
        set() should update nested values.
        """
        target = rejig.json(json_file)

        # Set nested value
        result = target.set("scripts.lint", "eslint .")
        assert result.success is True

        # Verify change
        assert target.get("scripts.lint") == "eslint ."

    def test_json_set_new_key(self, rejig: Rejig, json_file: Path):
        """
        set() should create new keys if they don't exist.
        """
        target = rejig.json(json_file)

        # Set new top-level key
        result = target.set("author", "Test Author")
        assert result.success is True

        # Verify new key
        assert target.get("author") == "Test Author"

    def test_json_has_key(self, rejig: Rejig, json_file: Path):
        """
        has_key() should check if keys exist.
        """
        target = rejig.json(json_file)

        assert target.has_key("name") is True
        assert target.has_key("scripts.build") is True
        assert target.has_key("missing") is False

    def test_json_keys(self, rejig: Rejig, json_file: Path):
        """
        keys() should return keys at a section.
        """
        target = rejig.json(json_file)

        # Root keys
        root_keys = target.keys()
        assert "name" in root_keys
        assert "version" in root_keys
        assert "scripts" in root_keys

        # Section keys
        script_keys = target.keys("scripts")
        assert "build" in script_keys
        assert "test" in script_keys

    def test_json_delete(self, rejig: Rejig, json_file: Path):
        """
        delete() should remove keys from the JSON file.
        """
        target = rejig.json(json_file)

        # Delete a key
        result = target.delete("scripts.test")
        assert result.success is True

        # Verify deletion
        assert target.has_key("scripts.test") is False


# =============================================================================
# JsonTarget package.json Helpers
# =============================================================================

class TestJsonTargetPackageHelpers:
    """Tests for package.json-specific helper methods."""

    @pytest.fixture
    def package_json(self, tmp_path: Path) -> Path:
        """Create a sample package.json file."""
        content = {
            "name": "my-app",
            "version": "1.0.0",
            "scripts": {
                "start": "node index.js"
            }
        }
        file_path = tmp_path / "package.json"
        file_path.write_text(json.dumps(content, indent=2))
        return file_path

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_get_package_name(self, rejig: Rejig, package_json: Path):
        """
        get_package_name() should return the package name.
        """
        target = rejig.json(package_json)
        assert target.get_package_name() == "my-app"

    def test_get_package_version(self, rejig: Rejig, package_json: Path):
        """
        get_package_version() should return the version.
        """
        target = rejig.json(package_json)
        assert target.get_package_version() == "1.0.0"

    def test_set_package_version(self, rejig: Rejig, package_json: Path):
        """
        set_package_version() should update the version.
        """
        target = rejig.json(package_json)

        result = target.set_package_version("2.0.0")
        assert result.success is True
        assert target.get_package_version() == "2.0.0"

    def test_get_scripts(self, rejig: Rejig, package_json: Path):
        """
        get_scripts() should return the scripts object.
        """
        target = rejig.json(package_json)

        scripts = target.get_scripts()
        assert scripts["start"] == "node index.js"

    def test_add_script(self, rejig: Rejig, package_json: Path):
        """
        add_script() should add a new script.
        """
        target = rejig.json(package_json)

        result = target.add_script("build", "webpack")
        assert result.success is True

        scripts = target.get_scripts()
        assert scripts["build"] == "webpack"


# =============================================================================
# JsonTarget Dry Run
# =============================================================================

class TestJsonTargetDryRun:
    """Tests for JsonTarget dry run mode."""

    @pytest.fixture
    def json_file(self, tmp_path: Path) -> Path:
        """Create a sample JSON file."""
        content = {"setting": "original"}
        file_path = tmp_path / "config.json"
        file_path.write_text(json.dumps(content, indent=2))
        return file_path

    def test_json_dry_run_does_not_modify(self, tmp_path: Path, json_file: Path):
        """
        In dry run mode, set() should not modify the file.
        """
        rejig = Rejig(str(tmp_path), dry_run=True)
        target = rejig.json(json_file)

        # Try to modify
        result = target.set("setting", "modified")
        assert result.success is True
        assert "DRY RUN" in result.message

        # File should be unchanged
        data = json.loads(json_file.read_text())
        assert data["setting"] == "original"


# =============================================================================
# JsonTarget Error Handling
# =============================================================================

class TestJsonTargetErrors:
    """Tests for JsonTarget error handling."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_json_invalid_json(self, rejig: Rejig, tmp_path: Path):
        """
        JsonTarget should handle invalid JSON gracefully.
        """
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("not valid json {")

        target = rejig.json(invalid_file)

        # get() should return default for invalid files
        value = target.get("key", "default")
        assert value == "default"

    def test_json_rewrite_invalid(self, rejig: Rejig, tmp_path: Path):
        """
        rewrite() should fail for invalid JSON content.
        """
        file_path = tmp_path / "config.json"
        file_path.write_text("{}")

        target = rejig.json(file_path)

        # Try to rewrite with invalid JSON
        result = target.rewrite("not valid json")
        assert result.success is False
        assert "Invalid JSON" in result.message

    def test_json_get_missing_file(self, rejig: Rejig, tmp_path: Path):
        """
        get() should return default for missing files.
        """
        target = rejig.json(tmp_path / "missing.json")

        value = target.get("key", "default")
        assert value == "default"
