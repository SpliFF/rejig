"""Tests for KeyPath and multi-form config key paths.

Config targets (TOML/YAML/JSON) historically split every key path on ``.``,
so a key that *contains* a literal dot (e.g. ``"SFTY-2026.0616"``) could not be
addressed. These tests cover the fixes:

- ``KeyPath``: a pathlib-style, ``/``-composable key-path builder whose segments
  are always literal.
- ``normalize_key_path``: accepts a dotted string, a list/tuple of segments, a
  ``KeyPath``, or a ``pathlib.PurePath``.
- get/set/delete on each config target addressing a dotted key via the new forms.
"""
from __future__ import annotations

from pathlib import Path, PurePosixPath

import pytest

from rejig import KeyPath, Rejig
from rejig.targets.config.base import normalize_key_path

# Optional backends for the integration tests.
try:
    import ruamel.yaml  # noqa: F401

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    import tomli_w  # noqa: F401

    HAS_TOML_WRITE = True
except ImportError:
    HAS_TOML_WRITE = False


# =============================================================================
# KeyPath unit tests
# =============================================================================

class TestKeyPath:
    def test_construct_from_multiple_segments(self):
        assert KeyPath("a", "b", "c").parts == ("a", "b", "c")

    def test_truediv_appends_segments(self):
        kp = KeyPath("a") / "b" / "c"
        assert kp.parts == ("a", "b", "c")

    def test_segments_are_literal_dots_preserved(self):
        kp = KeyPath("security") / "ignore" / "SFTY-2026.0616"
        assert kp.parts == ("security", "ignore", "SFTY-2026.0616")

    def test_keypath_flattens_nested_keypaths(self):
        assert KeyPath(KeyPath("a", "b"), "c").parts == ("a", "b", "c")
        assert (KeyPath("a") / KeyPath("b", "c")).parts == ("a", "b", "c")

    def test_accepts_purepath_segments(self):
        assert KeyPath(PurePosixPath("a") / "b").parts == ("a", "b")

    def test_non_str_segments_coerced(self):
        assert KeyPath("servers", 0, "name").parts == ("servers", "0", "name")

    def test_rtruediv(self):
        # "a" / KeyPath("b") -> KeyPath("a", "b")
        assert ("a" / KeyPath("b")).parts == ("a", "b")

    def test_is_a_sequence(self):
        kp = KeyPath("a", "b", "c")
        assert len(kp) == 3
        assert kp[0] == "a"
        assert kp[-1] == "c"
        assert list(kp) == ["a", "b", "c"]
        assert "b" in kp

    def test_equality_and_hash(self):
        assert KeyPath("a", "b") == KeyPath("a") / "b"
        assert KeyPath("a", "b") != KeyPath("a", "c")
        assert KeyPath("a", "b") != "a.b"  # not equal to the dotted string
        assert hash(KeyPath("a", "b")) == hash(KeyPath("a", "b"))

    def test_str_and_repr(self):
        kp = KeyPath("a", "b.c")
        assert str(kp) == "a/b.c"
        assert repr(kp) == "KeyPath('a', 'b.c')"

    def test_immutable_truediv_returns_new(self):
        base = KeyPath("a")
        derived = base / "b"
        assert base.parts == ("a",)
        assert derived.parts == ("a", "b")


# =============================================================================
# normalize_key_path unit tests
# =============================================================================

class TestNormalizeKeyPath:
    def test_dotted_string(self):
        assert normalize_key_path("a.b.c") == ["a", "b", "c"]

    def test_single_segment_string(self):
        assert normalize_key_path("single") == ["single"]

    def test_string_slash_is_literal_not_split(self):
        # A plain string is only split on '.', so '/' stays inside the segment.
        assert normalize_key_path("a/b") == ["a/b"]

    def test_list_of_segments(self):
        assert normalize_key_path(["a", "b.c"]) == ["a", "b.c"]

    def test_tuple_of_segments(self):
        assert normalize_key_path(("a", "b")) == ["a", "b"]

    def test_numeric_segment_coerced(self):
        assert normalize_key_path(["servers", 0, "name"]) == ["servers", "0", "name"]

    def test_keypath(self):
        assert normalize_key_path(KeyPath("a") / "b.c") == ["a", "b.c"]

    def test_purepath(self):
        assert normalize_key_path(PurePosixPath("a") / "b") == ["a", "b"]


# =============================================================================
# Integration: addressing a dotted key on each config target
# =============================================================================

DOTTED_KEY = "SFTY-2026.0616"  # a single key that itself contains a '.'


def _rj(tmp_path: Path) -> Rejig:
    return Rejig(str(tmp_path))


class TestJsonDottedKey:
    """JSON needs no optional backend."""

    def _make(self, tmp_path: Path) -> Path:
        import json

        data = {"security": {"ignore": {DOTTED_KEY: {"reason": "reviewed"}}}}
        path = tmp_path / "config.json"
        path.write_text(json.dumps(data))
        return path

    def test_dotted_string_cannot_reach_dotted_key(self, tmp_path: Path):
        target = _rj(tmp_path).json(self._make(tmp_path))
        # The dotted string is (wrongly) split, so the key is unreachable.
        assert target.get(f"security.ignore.{DOTTED_KEY}.reason") is None

    def test_keypath_reaches_dotted_key(self, tmp_path: Path):
        target = _rj(tmp_path).json(self._make(tmp_path))
        kp = KeyPath("security") / "ignore" / DOTTED_KEY / "reason"
        assert target.get(kp) == "reviewed"

    def test_list_reaches_dotted_key(self, tmp_path: Path):
        target = _rj(tmp_path).json(self._make(tmp_path))
        assert target.get(["security", "ignore", DOTTED_KEY, "reason"]) == "reviewed"

    def test_set_keypath_creates_literal_key(self, tmp_path: Path):
        import json

        path = tmp_path / "out.json"
        path.write_text("{}")
        target = _rj(tmp_path).json(path)
        result = target.set(KeyPath("security") / "ignore" / DOTTED_KEY, "ok")
        assert result.success
        # The on-disk structure has ONE literal key, not a nested chain.
        written = json.loads(path.read_text())
        assert written == {"security": {"ignore": {DOTTED_KEY: "ok"}}}

    def test_delete_keypath(self, tmp_path: Path):
        path = self._make(tmp_path)
        target = _rj(tmp_path).json(path)
        kp = KeyPath("security") / "ignore" / DOTTED_KEY
        assert target.get(kp) == {"reason": "reviewed"}
        assert target.delete(kp).success
        # Re-read from disk to confirm the deletion persisted.
        assert _rj(tmp_path).json(path).get(kp) is None

    def test_dotted_string_still_works_for_plain_keys(self, tmp_path: Path):
        target = _rj(tmp_path).json(self._make(tmp_path))
        assert target.get("security.ignore") == {DOTTED_KEY: {"reason": "reviewed"}}


@pytest.mark.skipif(not HAS_YAML, reason="ruamel.yaml not installed")
class TestYamlDottedKey:
    def _make(self, tmp_path: Path) -> Path:
        path = tmp_path / "config.yaml"
        path.write_text(
            "security:\n"
            "  ignore:\n"
            f'    "{DOTTED_KEY}":\n'
            "      reason: reviewed\n"
        )
        return path

    def test_dotted_string_cannot_reach_dotted_key(self, tmp_path: Path):
        target = _rj(tmp_path).yaml(self._make(tmp_path))
        assert target.get(f"security.ignore.{DOTTED_KEY}.reason") is None

    def test_keypath_reaches_dotted_key(self, tmp_path: Path):
        target = _rj(tmp_path).yaml(self._make(tmp_path))
        kp = KeyPath("security") / "ignore" / DOTTED_KEY / "reason"
        assert target.get(kp) == "reviewed"

    def test_set_and_delete_keypath(self, tmp_path: Path):
        target = _rj(tmp_path).yaml(self._make(tmp_path))
        kp = KeyPath("security") / "ignore" / DOTTED_KEY / "status"
        assert target.set(kp, "ok").success
        assert _rj(tmp_path).yaml(target.path).get(kp) == "ok"
        assert target.delete(kp).success
        assert _rj(tmp_path).yaml(target.path).get(kp) is None


@pytest.mark.skipif(not HAS_TOML_WRITE, reason="tomli_w not installed")
class TestTomlDottedKey:
    def _make(self, tmp_path: Path) -> Path:
        path = tmp_path / "config.toml"
        # A bare dotted key must be quoted in TOML.
        path.write_text(f'[security.ignore."{DOTTED_KEY}"]\nreason = "reviewed"\n')
        return path

    def test_dotted_string_cannot_reach_dotted_key(self, tmp_path: Path):
        target = _rj(tmp_path).toml(self._make(tmp_path))
        assert target.get(f"security.ignore.{DOTTED_KEY}.reason") is None

    def test_keypath_reaches_dotted_key(self, tmp_path: Path):
        target = _rj(tmp_path).toml(self._make(tmp_path))
        kp = KeyPath("security") / "ignore" / DOTTED_KEY / "reason"
        assert target.get(kp) == "reviewed"

    def test_set_keypath_creates_literal_key(self, tmp_path: Path):
        path = tmp_path / "out.toml"
        path.write_text("")
        target = _rj(tmp_path).toml(path)
        kp = KeyPath("security") / "ignore" / DOTTED_KEY
        assert target.set(kp, "ok").success
        assert _rj(tmp_path).toml(path).get(kp) == "ok"
