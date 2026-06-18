"""Tests for FileTarget.replace_pattern.

Covers:
- Basic regex replacement with literal and word-boundary patterns.
- Backreference substitution.
- ``count`` and ``flags`` parameters.
- No-match returns a success Result with no files changed.
- Missing file returns an error Result.
- Dry-run mode reports the change without writing.
"""
from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import Generator

import pytest

from rejig import Rejig


SOURCE = textwrap.dedent('''\
    def is_token_expired(t):
        return t == "x"


    def caller():
        return is_token_expired("y")


    NAME = "is_token_expired"
''')


@pytest.fixture
def python_file(tmp_path: Path) -> Path:
    path = tmp_path / "module.py"
    path.write_text(SOURCE)
    return path


@pytest.fixture
def rj(tmp_path: Path, python_file: Path) -> Generator[Rejig, None, None]:
    with Rejig(str(tmp_path)) as instance:
        yield instance


class TestReplacePattern:
    def test_replaces_word_boundary_pattern(self, rj: Rejig, python_file: Path) -> None:
        result = rj.file(python_file.name).replace_pattern(
            r"\bis_token_expired\b", "is_token_valid"
        )
        assert result.success is True
        content = python_file.read_text()
        assert "def is_token_valid(t):" in content
        assert "is_token_valid(\"y\")" in content
        # string literal also replaced because the boundary still matches
        assert 'NAME = "is_token_valid"' in content
        assert "is_token_expired" not in content

    def test_returns_no_matches_message_when_pattern_absent(
        self, rj: Rejig, python_file: Path
    ) -> None:
        before = python_file.read_text()
        result = rj.file(python_file.name).replace_pattern(r"\bnon_existent\b", "X")
        assert result.success is True
        assert "No matches" in result.message
        assert result.files_changed == []
        assert python_file.read_text() == before

    def test_supports_backreferences(self, rj: Rejig, python_file: Path) -> None:
        result = rj.file(python_file.name).replace_pattern(
            r"def (\w+)\(t\):", r"def \1(token):"
        )
        assert result.success is True
        assert "def is_token_expired(token):" in python_file.read_text()

    def test_count_limits_replacements(self, rj: Rejig, python_file: Path) -> None:
        result = rj.file(python_file.name).replace_pattern(
            r"is_token_expired", "X", count=1
        )
        assert result.success is True
        content = python_file.read_text()
        # Three occurrences in source; only the first should be replaced.
        assert content.count("X") == 1
        assert content.count("is_token_expired") == 2

    def test_flags_are_honored(self, rj: Rejig, python_file: Path) -> None:
        result = rj.file(python_file.name).replace_pattern(
            r"IS_TOKEN_EXPIRED", "renamed", flags=re.IGNORECASE
        )
        assert result.success is True
        assert "is_token_expired" not in python_file.read_text()

    def test_missing_file_returns_error(self, rj: Rejig, tmp_path: Path) -> None:
        result = rj.file("does_not_exist.py").replace_pattern(r"x", "y")
        assert result.success is False

    def test_dry_run_does_not_write(self, tmp_path: Path, python_file: Path) -> None:
        before = python_file.read_text()
        with Rejig(str(tmp_path), dry_run=True) as rj:
            result = rj.file(python_file.name).replace_pattern(
                r"\bis_token_expired\b", "is_token_valid"
            )
        assert result.success is True
        assert "[DRY RUN]" in result.message
        assert python_file.read_text() == before


class TestReplaceLiteral:
    def test_replace_is_literal_not_regex(self, rj: Rejig, python_file: Path) -> None:
        # The pattern contains '(', an invalid standalone regex; literal replace
        # must handle it without error and only touch the call sites.
        result = rj.file(python_file.name).replace("is_token_expired(", "is_token_valid(")
        assert result.success is True
        content = python_file.read_text()
        assert 'is_token_valid("y")' in content
        # The bare NAME = "is_token_expired" (no paren) is untouched.
        assert 'NAME = "is_token_expired"' in content

    def test_count_limits_replacements(self, rj: Rejig, python_file: Path) -> None:
        result = rj.file(python_file.name).replace("is_token_expired", "X", count=1)
        assert result.success is True
        content = python_file.read_text()
        assert content.count("X") == 1
        assert content.count("is_token_expired") == 2

    def test_no_match_is_noop(self, rj: Rejig, python_file: Path) -> None:
        before = python_file.read_text()
        result = rj.file(python_file.name).replace("non_existent", "X")
        assert result.success is True
        assert result.files_changed == []
        assert python_file.read_text() == before

    def test_dry_run_does_not_write(self, tmp_path: Path, python_file: Path) -> None:
        before = python_file.read_text()
        with Rejig(str(tmp_path), dry_run=True) as rj:
            result = rj.file(python_file.name).replace("is_token_expired", "X")
        assert result.success is True
        assert "[DRY RUN]" in result.message
        assert python_file.read_text() == before


class TestReplaceAllAcrossFiles:
    def test_replace_all_over_glob(self, tmp_path: Path) -> None:
        for name in ("a", "b"):
            pkg = tmp_path / "pkg" / name
            pkg.mkdir(parents=True)
            (pkg / "api.py").write_text("x = not is_token_expired(t)\n")
        # Outside the glob -> must stay untouched.
        (tmp_path / "pkg" / "other.py").write_text("not is_token_expired(t)\n")

        with Rejig(str(tmp_path)) as rj:
            result = rj.find_files("pkg/*/api.py").replace_all(
                "not is_token_expired(", "is_token_expired("
            )

        assert result.success
        assert len(result.files_changed) == 2
        for name in ("a", "b"):
            assert (tmp_path / "pkg" / name / "api.py").read_text() == "x = is_token_expired(t)\n"
        assert (tmp_path / "pkg" / "other.py").read_text() == "not is_token_expired(t)\n"
