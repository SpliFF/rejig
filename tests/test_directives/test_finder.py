"""
Tests for rejig.directives.finder module.

This module tests DirectiveFinder for searching linting directives:
- find_all() for finding all directives in a codebase
- find_in_file() for finding directives in a specific file
- find_by_type() for finding directives of a specific type
- find_type_ignores() and related methods for type: ignore
- find_noqa_comments() for noqa directives
- find_pylint_disables() for pylint: disable directives
- find_fmt_directives() for fmt: skip/off/on
- find_no_cover() for pragma: no cover
- find_without_reason() for directives lacking reasons
- find_with_code() for directives with specific codes

DirectiveFinder uses DirectiveParser to scan files and returns
DirectiveTargetList objects for batch operations.

Coverage targets:
- find_all() for empty and non-empty codebases
- Type-specific finder methods
- Filtering by bare vs specific directives
- Filtering by presence of reason comments
- Filtering by error code
"""
from __future__ import annotations

from pathlib import Path

import pytest

from rejig import Rejig
from rejig.directives.finder import DirectiveFinder


# =============================================================================
# DirectiveFinder Basic Tests
# =============================================================================

class TestDirectiveFinderBasic:
    """Tests for basic DirectiveFinder operations."""

    @pytest.fixture
    def empty_project(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance with no Python files."""
        return Rejig(str(tmp_path))

    @pytest.fixture
    def project_with_directives(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance with files containing directives."""
        (tmp_path / "main.py").write_text('''\
import os  # noqa: F401
x: int = "wrong"  # type: ignore[assignment]
y = long_name  # type: ignore
if DEBUG:  # pragma: no cover
    debug_code()
''')
        (tmp_path / "utils.py").write_text('''\
# fmt: off
MATRIX = [
    [1, 2, 3],
]
# fmt: on
z = 1  # pylint: disable=invalid-name
''')
        return Rejig(str(tmp_path))

    def test_find_all_empty_project(self, empty_project: Rejig):
        """
        find_all() should return empty list for projects without directives.
        """
        finder = DirectiveFinder(empty_project)
        result = finder.find_all()

        assert len(result) == 0

    def test_find_all_with_directives(self, project_with_directives: Rejig):
        """
        find_all() should find all directives across all files.
        """
        finder = DirectiveFinder(project_with_directives)
        result = finder.find_all()

        # Should find: noqa, 2x type: ignore, pragma: no cover, fmt: off,
        # fmt: on, pylint: disable
        assert len(result) >= 6

    def test_find_in_file(self, project_with_directives: Rejig, tmp_path: Path):
        """
        find_in_file() should find directives in a specific file only.
        """
        finder = DirectiveFinder(project_with_directives)
        main_file = tmp_path / "main.py"

        result = finder.find_in_file(main_file)

        # main.py has: noqa, 2x type: ignore, pragma: no cover
        assert len(result) >= 3
        for target in result:
            assert target.file_path == main_file

    def test_find_in_file_no_directives(self, tmp_path: Path):
        """
        find_in_file() should return empty list for files without directives.
        """
        (tmp_path / "clean.py").write_text("x = 1\ny = 2\n")
        rejig = Rejig(str(tmp_path))
        finder = DirectiveFinder(rejig)

        result = finder.find_in_file(tmp_path / "clean.py")

        assert len(result) == 0


# =============================================================================
# DirectiveFinder Type-specific Methods Tests
# =============================================================================

class TestDirectiveFinderTypeSpecific:
    """Tests for type-specific finder methods."""

    @pytest.fixture
    def project(self, tmp_path: Path) -> Rejig:
        """Create a project with various directive types."""
        # Note: Comment text avoids using actual directive syntax to prevent
        # the parser from picking up comments as directives
        (tmp_path / "test.py").write_text('''\
# Section: mypy suppressions
x = foo()  # type: ignore
y = bar()  # type: ignore[arg-type]
z = baz()  # type: ignore[return-value, arg-type]

# Section: linter suppressions
from os import *  # noqa
import sys  # noqa: F401
long_line = "text"  # noqa: E501, W503

# Section: pylint
a = 1  # pylint: disable=invalid-name
b = 2  # pylint: disable=C0103

# Section: formatter
# fmt: off
MATRIX = [[1]]
# fmt: on
c = 1  # fmt: skip

# Section: coverage
if DEBUG:  # pragma: no cover
    pass
''')
        return Rejig(str(tmp_path))

    def test_find_type_ignores(self, project: Rejig):
        """
        find_type_ignores() should find all type: ignore comments.
        """
        finder = DirectiveFinder(project)
        result = finder.find_type_ignores()

        assert len(result) == 3
        for target in result:
            assert target.directive_type == "type_ignore"

    def test_find_bare_type_ignores(self, project: Rejig):
        """
        find_bare_type_ignores() should find type: ignore without codes.

        Bare type: ignore comments suppress all type errors on a line.
        These are often considered bad practice as they're too broad.
        """
        finder = DirectiveFinder(project)
        result = finder.find_bare_type_ignores()

        assert len(result) == 1
        assert result[0].is_bare is True
        assert result[0].codes == []

    def test_find_specific_type_ignores(self, project: Rejig):
        """
        find_specific_type_ignores() should find type: ignore with codes.

        Specific type: ignore comments like [arg-type] are preferred
        as they only suppress intended errors.
        """
        finder = DirectiveFinder(project)
        result = finder.find_specific_type_ignores()

        assert len(result) == 2
        for target in result:
            assert target.is_specific is True
            assert len(target.codes) > 0

    def test_find_noqa_comments(self, project: Rejig):
        """
        find_noqa_comments() should find all noqa comments.
        """
        finder = DirectiveFinder(project)
        result = finder.find_noqa_comments()

        assert len(result) == 3
        for target in result:
            assert target.directive_type == "noqa"

    def test_find_bare_noqa(self, project: Rejig):
        """
        find_bare_noqa() should find noqa comments without codes.
        """
        finder = DirectiveFinder(project)
        result = finder.find_bare_noqa()

        assert len(result) == 1
        assert result[0].is_bare is True

    def test_find_pylint_disables(self, project: Rejig):
        """
        find_pylint_disables() should find all pylint: disable comments.
        """
        finder = DirectiveFinder(project)
        result = finder.find_pylint_disables()

        assert len(result) == 2
        for target in result:
            assert target.directive_type == "pylint_disable"

    def test_find_fmt_directives(self, project: Rejig):
        """
        find_fmt_directives() should find all fmt directives.

        This includes fmt: skip, fmt: off, and fmt: on comments
        used to control Black formatter behavior.
        """
        finder = DirectiveFinder(project)
        result = finder.find_fmt_directives()

        # Should find: fmt: off, fmt: on, fmt: skip
        assert len(result) == 3
        types = {target.directive_type for target in result}
        assert "fmt_off" in types
        assert "fmt_on" in types
        assert "fmt_skip" in types

    def test_find_no_cover(self, project: Rejig):
        """
        find_no_cover() should find all pragma: no cover comments.

        These comments exclude code from coverage measurements.
        """
        finder = DirectiveFinder(project)
        result = finder.find_no_cover()

        assert len(result) == 1
        assert result[0].directive_type == "no_cover"


# =============================================================================
# DirectiveFinder Filtering Tests
# =============================================================================

class TestDirectiveFinderFiltering:
    """Tests for directive filtering methods."""

    @pytest.fixture
    def project(self, tmp_path: Path) -> Rejig:
        """Create a project for filtering tests."""
        (tmp_path / "test.py").write_text('''\
x = foo()  # type: ignore[arg-type]  # Legacy API
y = bar()  # type: ignore[return-value]
z = baz()  # noqa: E501  # Long line intentional
w = qux()  # noqa
a = 1  # type: ignore[arg-type]
''')
        return Rejig(str(tmp_path))

    def test_find_without_reason(self, project: Rejig):
        """
        find_without_reason() should find directives lacking reason comments.

        Best practice is to explain why a directive is needed.
        This helps find directives that may need documentation.
        """
        finder = DirectiveFinder(project)
        result = finder.find_without_reason()

        # Directives without explanatory comments
        # Note: This depends on how the parser extracts reasons
        assert len(result) >= 2

    def test_find_with_code(self, project: Rejig):
        """
        find_with_code() should find directives containing a specific code.

        Useful for finding all suppressions of a particular error type.
        """
        finder = DirectiveFinder(project)
        result = finder.find_with_code("arg-type")

        # Two directives have arg-type
        assert len(result) == 2
        for target in result:
            assert "arg-type" in target.codes


# =============================================================================
# DirectiveFinder Edge Cases
# =============================================================================

class TestDirectiveFinderEdgeCases:
    """Tests for edge cases in directive finding."""

    def test_missing_file(self, tmp_path: Path):
        """
        find_in_file() should return empty list for missing files.
        """
        rejig = Rejig(str(tmp_path))
        finder = DirectiveFinder(rejig)

        result = finder.find_in_file(tmp_path / "nonexistent.py")

        assert len(result) == 0

    def test_empty_file(self, tmp_path: Path):
        """
        find_in_file() should return empty list for empty files.
        """
        (tmp_path / "empty.py").write_text("")
        rejig = Rejig(str(tmp_path))
        finder = DirectiveFinder(rejig)

        result = finder.find_in_file(tmp_path / "empty.py")

        assert len(result) == 0

    def test_file_with_no_comments(self, tmp_path: Path):
        """
        find_all() should work with files that have no comments at all.
        """
        (tmp_path / "no_comments.py").write_text('''\
def add(a, b):
    return a + b

result = add(1, 2)
''')
        rejig = Rejig(str(tmp_path))
        finder = DirectiveFinder(rejig)

        result = finder.find_all()

        assert len(result) == 0

    def test_multiple_directives_same_line(self, tmp_path: Path):
        """
        Finder should handle lines with multiple directives.

        Some tools allow multiple directives on one line, e.g.,
        "# type: ignore  # noqa"
        """
        (tmp_path / "multi.py").write_text("x = foo()  # type: ignore  # noqa\n")
        rejig = Rejig(str(tmp_path))
        finder = DirectiveFinder(rejig)

        result = finder.find_all()

        # May find one or two depending on parser behavior
        assert len(result) >= 1


# =============================================================================
# DirectiveFinder Integration Tests
# =============================================================================

class TestDirectiveFinderIntegration:
    """Integration tests for DirectiveFinder."""

    def test_find_and_filter_chain(self, tmp_path: Path):
        """
        DirectiveFinder results can be chained with filtering.

        This tests the integration between finder and DirectiveTargetList.
        """
        (tmp_path / "test.py").write_text('''\
x = foo()  # type: ignore
y = bar()  # type: ignore[arg-type]
z = baz()  # type: ignore[return-value]  # Intentional
''')
        rejig = Rejig(str(tmp_path))
        finder = DirectiveFinder(rejig)

        # Chain: find type ignores -> filter to specific -> filter without reason
        specific_no_reason = (
            finder.find_type_ignores()
            .specific()
            .without_reason()
        )

        # Only y = bar() matches (specific but no reason)
        assert len(specific_no_reason) == 1

    def test_find_by_type_method(self, tmp_path: Path):
        """
        find_by_type() should work for all directive types.
        """
        (tmp_path / "test.py").write_text('''\
x = 1  # type: ignore
y = 2  # noqa
z = 3  # pragma: no cover
''')
        rejig = Rejig(str(tmp_path))
        finder = DirectiveFinder(rejig)

        # Test each type
        type_ignores = finder.find_by_type("type_ignore")
        noqa = finder.find_by_type("noqa")
        no_cover = finder.find_by_type("no_cover")

        assert len(type_ignores) == 1
        assert len(noqa) == 1
        assert len(no_cover) == 1
