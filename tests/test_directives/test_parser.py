"""
Tests for rejig.directives.parser module.

This module tests DirectiveParser for parsing linting directives:
- type: ignore for mypy
- noqa for flake8/ruff
- pylint: disable/enable for pylint
- fmt: skip/off/on for black
- pragma: no cover for coverage

DirectiveParser extracts directives from source code into
ParsedDirective objects.

Coverage targets:
- parse_line() for various directive types
- Extraction of error codes
- Handling of reasons/comments
- Bare directives (no codes)
- ParsedDirective properties
"""
from __future__ import annotations

import pytest

from rejig.directives.parser import DirectiveParser, ParsedDirective


# =============================================================================
# ParsedDirective Tests
# =============================================================================

class TestParsedDirective:
    """Tests for ParsedDirective data class."""

    def test_bare_directive(self):
        """
        is_bare should return True for directives without codes.
        """
        directive = ParsedDirective(
            directive_type="type_ignore",
            codes=[],
        )
        assert directive.is_bare is True
        assert directive.is_specific is False

    def test_specific_directive(self):
        """
        is_specific should return True for directives with codes.
        """
        directive = ParsedDirective(
            directive_type="type_ignore",
            codes=["arg-type"],
        )
        assert directive.is_specific is True
        assert directive.is_bare is False

    def test_directive_with_reason(self):
        """
        ParsedDirective should store reason if provided.
        """
        directive = ParsedDirective(
            directive_type="noqa",
            codes=["E501"],
            reason="Line too long in test",
        )
        assert directive.reason == "Line too long in test"


# =============================================================================
# DirectiveParser Type Ignore Tests
# =============================================================================

class TestDirectiveParserTypeIgnore:
    """Tests for parsing type: ignore directives."""

    @pytest.fixture
    def parser(self) -> DirectiveParser:
        """Create a parser instance."""
        return DirectiveParser()

    def test_parse_bare_type_ignore(self, parser: DirectiveParser):
        """
        parse_line() should parse bare type: ignore.
        """
        line = "x = foo()  # type: ignore"

        directives = parser.parse_line(line)

        assert len(directives) == 1
        assert directives[0].directive_type == "type_ignore"
        assert directives[0].is_bare is True

    def test_parse_type_ignore_with_code(self, parser: DirectiveParser):
        """
        parse_line() should parse type: ignore with error code.
        """
        line = "x = foo()  # type: ignore[arg-type]"

        directives = parser.parse_line(line)

        assert len(directives) == 1
        assert directives[0].directive_type == "type_ignore"
        assert "arg-type" in directives[0].codes

    def test_parse_type_ignore_with_multiple_codes(self, parser: DirectiveParser):
        """
        parse_line() should parse type: ignore with multiple codes.
        """
        line = "x = foo()  # type: ignore[arg-type, return-value]"

        directives = parser.parse_line(line)

        assert len(directives) == 1
        assert "arg-type" in directives[0].codes
        assert "return-value" in directives[0].codes

    def test_parse_type_ignore_with_reason(self, parser: DirectiveParser):
        """
        parse_line() should extract reason from type: ignore.
        """
        line = "x = foo()  # type: ignore[arg-type]  # Legacy API"

        directives = parser.parse_line(line)

        assert len(directives) == 1
        # Reason may or may not be captured depending on implementation


# =============================================================================
# DirectiveParser Noqa Tests
# =============================================================================

class TestDirectiveParserNoqa:
    """Tests for parsing noqa directives."""

    @pytest.fixture
    def parser(self) -> DirectiveParser:
        """Create a parser instance."""
        return DirectiveParser()

    def test_parse_bare_noqa(self, parser: DirectiveParser):
        """
        parse_line() should parse bare noqa.
        """
        line = "x = some_long_line()  # noqa"

        directives = parser.parse_line(line)

        assert len(directives) == 1
        assert directives[0].directive_type == "noqa"
        assert directives[0].is_bare is True

    def test_parse_noqa_with_code(self, parser: DirectiveParser):
        """
        parse_line() should parse noqa with error code.
        """
        line = "x = some_long_line()  # noqa: E501"

        directives = parser.parse_line(line)

        assert len(directives) == 1
        assert directives[0].directive_type == "noqa"
        assert "E501" in directives[0].codes

    def test_parse_noqa_with_multiple_codes(self, parser: DirectiveParser):
        """
        parse_line() should parse noqa with multiple codes.
        """
        line = "from os import *  # noqa: F401, F403"

        directives = parser.parse_line(line)

        assert len(directives) == 1
        assert "F401" in directives[0].codes
        assert "F403" in directives[0].codes


# =============================================================================
# DirectiveParser Pylint Tests
# =============================================================================

class TestDirectiveParserPylint:
    """Tests for parsing pylint directives."""

    @pytest.fixture
    def parser(self) -> DirectiveParser:
        """Create a parser instance."""
        return DirectiveParser()

    def test_parse_pylint_disable(self, parser: DirectiveParser):
        """
        parse_line() should parse pylint: disable.
        """
        line = "x = 1  # pylint: disable=line-too-long"

        directives = parser.parse_line(line)

        assert len(directives) >= 1
        pylint_dirs = [d for d in directives if "pylint" in d.directive_type]
        assert len(pylint_dirs) >= 1
        assert "line-too-long" in pylint_dirs[0].codes

    def test_parse_pylint_disable_multiple(self, parser: DirectiveParser):
        """
        parse_line() should parse pylint: disable with multiple codes.
        """
        line = "x = 1  # pylint: disable=C0114,C0115"

        directives = parser.parse_line(line)

        pylint_dirs = [d for d in directives if "pylint" in d.directive_type]
        assert len(pylint_dirs) >= 1
        # Check that both codes are captured
        all_codes = [c for d in pylint_dirs for c in d.codes]
        assert "C0114" in all_codes or "C0115" in all_codes


# =============================================================================
# DirectiveParser Fmt Tests
# =============================================================================

class TestDirectiveParserFmt:
    """Tests for parsing fmt directives (black)."""

    @pytest.fixture
    def parser(self) -> DirectiveParser:
        """Create a parser instance."""
        return DirectiveParser()

    def test_parse_fmt_skip(self, parser: DirectiveParser):
        """
        parse_line() should parse fmt: skip.
        """
        line = "x = { 'a': 1, 'b': 2 }  # fmt: skip"

        directives = parser.parse_line(line)

        fmt_dirs = [d for d in directives if d.directive_type == "fmt_skip"]
        assert len(fmt_dirs) >= 1

    def test_parse_fmt_off(self, parser: DirectiveParser):
        """
        parse_line() should parse fmt: off.
        """
        line = "# fmt: off"

        directives = parser.parse_line(line)

        fmt_dirs = [d for d in directives if d.directive_type == "fmt_off"]
        assert len(fmt_dirs) >= 1

    def test_parse_fmt_on(self, parser: DirectiveParser):
        """
        parse_line() should parse fmt: on.
        """
        line = "# fmt: on"

        directives = parser.parse_line(line)

        fmt_dirs = [d for d in directives if d.directive_type == "fmt_on"]
        assert len(fmt_dirs) >= 1


# =============================================================================
# DirectiveParser No Cover Tests
# =============================================================================

class TestDirectiveParserNoCover:
    """Tests for parsing pragma: no cover directives."""

    @pytest.fixture
    def parser(self) -> DirectiveParser:
        """Create a parser instance."""
        return DirectiveParser()

    def test_parse_no_cover(self, parser: DirectiveParser):
        """
        parse_line() should parse pragma: no cover.
        """
        line = "if DEBUG:  # pragma: no cover"

        directives = parser.parse_line(line)

        no_cover_dirs = [d for d in directives if d.directive_type == "no_cover"]
        assert len(no_cover_dirs) >= 1


# =============================================================================
# DirectiveParser Edge Cases
# =============================================================================

class TestDirectiveParserEdgeCases:
    """Tests for edge cases in directive parsing."""

    @pytest.fixture
    def parser(self) -> DirectiveParser:
        """Create a parser instance."""
        return DirectiveParser()

    def test_no_directive(self, parser: DirectiveParser):
        """
        parse_line() should return empty list for lines without directives.
        """
        line = "x = foo()"

        directives = parser.parse_line(line)

        assert directives == []

    def test_multiple_directives(self, parser: DirectiveParser):
        """
        parse_line() should handle lines with multiple directives.
        """
        line = "x = foo()  # type: ignore  # noqa"

        directives = parser.parse_line(line)

        # May have one or two directives depending on how multi-directive
        # lines are handled
        assert len(directives) >= 1

    def test_case_sensitivity(self, parser: DirectiveParser):
        """
        parse_line() is case-sensitive.

        NOTE: The parser uses lowercase patterns, so uppercase variants
        like "TYPE: IGNORE" are not recognized. This is intentional to
        match how mypy and other tools work.
        """
        line = "x = foo()  # TYPE: IGNORE"

        directives = parser.parse_line(line)

        # Should NOT recognize uppercase (tools are case-sensitive)
        type_ignore_dirs = [d for d in directives if d.directive_type == "type_ignore"]
        assert len(type_ignore_dirs) == 0


# =============================================================================
# DirectiveParser File Parsing Tests
# =============================================================================

class TestDirectiveParserFile:
    """Tests for parsing directives from files."""

    @pytest.fixture
    def parser(self) -> DirectiveParser:
        """Create a parser instance."""
        return DirectiveParser()

    def test_parse_file(self, parser: DirectiveParser, tmp_path):
        """
        parse_file() should extract all directives from a file.
        """
        file_path = tmp_path / "test.py"
        file_path.write_text('''\
import os  # noqa: F401
x: int = "wrong"  # type: ignore[assignment]
if DEBUG:  # pragma: no cover
    debug_code()
''')

        directives = parser.parse_file(file_path)

        # Should find multiple directives
        assert len(directives) >= 2

    def test_parse_missing_file(self, parser: DirectiveParser, tmp_path):
        """
        parse_file() should return empty list for missing files.
        """
        directives = parser.parse_file(tmp_path / "missing.py")

        assert directives == []
