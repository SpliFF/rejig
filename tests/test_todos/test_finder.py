"""
Tests for rejig.todos.finder module.

This module tests TodoFinder for searching TODO comments:
- find_all() for finding all TODOs across the codebase
- find_in_file() for finding TODOs in a specific file
- find_by_type() for filtering by TODO type
- find_by_author() for filtering by author
- find_stale() for finding old TODOs
- find_high_priority() for urgent items
- find_unlinked() for TODOs without issue references
- find_matching() for text pattern matching

TodoFinder uses TodoParser internally and returns TodoTargetList.

Coverage targets:
- Finding TODOs across multiple files
- Type-based filtering (TODO, FIXME, XXX, etc.)
- Author-based filtering
- Stale TODO detection by date
- High priority TODO identification
- Issue reference tracking
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from rejig import Rejig
from rejig.todos.finder import TodoFinder
from rejig.targets.python.todo import TodoTargetList


# =============================================================================
# TodoFinder Basic Tests
# =============================================================================

class TestTodoFinderBasic:
    """Tests for basic TodoFinder operations."""

    @pytest.fixture
    def empty_project(self, tmp_path: Path) -> Rejig:
        """Create a project with no Python files."""
        return Rejig(str(tmp_path))

    @pytest.fixture
    def project_with_todos(self, tmp_path: Path) -> Rejig:
        """Create a project with files containing various TODOs."""
        (tmp_path / "main.py").write_text('''\
# Main application file
# TODO: Add configuration loading
def main():
    # FIXME: Handle errors properly
    pass
''')
        (tmp_path / "utils.py").write_text('''\
# TODO(john): Refactor this function
def helper():
    # XXX: Temporary hack
    # BUG: Race condition here
    pass
''')
        return Rejig(str(tmp_path))

    def test_find_all_empty_project(self, empty_project: Rejig):
        """
        find_all() should return empty list for projects without TODOs.
        """
        finder = TodoFinder(empty_project)
        result = finder.find_all()

        assert isinstance(result, TodoTargetList)
        assert len(result) == 0

    def test_find_all_with_todos(self, project_with_todos: Rejig):
        """
        find_all() should find all TODOs across all files.
        """
        finder = TodoFinder(project_with_todos)
        result = finder.find_all()

        # Should find: TODO (main), FIXME (main), TODO (utils), XXX, BUG
        assert len(result) >= 5

    def test_find_in_file(self, project_with_todos: Rejig, tmp_path: Path):
        """
        find_in_file() should find TODOs only in the specified file.
        """
        finder = TodoFinder(project_with_todos)
        main_file = tmp_path / "main.py"

        result = finder.find_in_file(main_file)

        # main.py has: TODO (config), FIXME (errors)
        assert len(result) == 2
        for todo in result:
            assert todo.file_path == main_file

    def test_find_in_file_no_todos(self, tmp_path: Path):
        """
        find_in_file() should return empty list for files without TODOs.
        """
        (tmp_path / "clean.py").write_text("# Just a comment\nx = 1\n")
        rejig = Rejig(str(tmp_path))
        finder = TodoFinder(rejig)

        result = finder.find_in_file(tmp_path / "clean.py")

        assert len(result) == 0


# =============================================================================
# TodoFinder Type-specific Tests
# =============================================================================

class TestTodoFinderByType:
    """Tests for finding TODOs by type."""

    @pytest.fixture
    def project(self, tmp_path: Path) -> Rejig:
        """Create a project with various TODO types."""
        (tmp_path / "test.py").write_text('''\
# TODO: First task
# TODO: Second task
# FIXME: Broken code
# XXX: Questionable approach
# HACK: Quick workaround
# NOTE: Important information
# BUG: Known issue
''')
        return Rejig(str(tmp_path))

    def test_find_by_type_todo(self, project: Rejig):
        """
        find_by_type("TODO") should find only TODO comments.
        """
        finder = TodoFinder(project)
        result = finder.find_by_type("TODO")

        assert len(result) == 2
        for todo in result:
            assert todo.todo_type == "TODO"

    def test_find_by_type_fixme(self, project: Rejig):
        """
        find_by_type("FIXME") should find only FIXME comments.
        """
        finder = TodoFinder(project)
        result = finder.find_by_type("FIXME")

        assert len(result) == 1
        assert result[0].todo_type == "FIXME"

    def test_find_by_type_xxx(self, project: Rejig):
        """
        find_by_type("XXX") should find only XXX comments.
        """
        finder = TodoFinder(project)
        result = finder.find_by_type("XXX")

        assert len(result) == 1
        assert result[0].todo_type == "XXX"

    def test_find_by_type_bug(self, project: Rejig):
        """
        find_by_type("BUG") should find only BUG comments.
        """
        finder = TodoFinder(project)
        result = finder.find_by_type("BUG")

        assert len(result) == 1
        assert result[0].todo_type == "BUG"


# =============================================================================
# TodoFinder Author Tests
# =============================================================================

class TestTodoFinderByAuthor:
    """Tests for finding TODOs by author."""

    @pytest.fixture
    def project(self, tmp_path: Path) -> Rejig:
        """Create a project with various authored TODOs."""
        (tmp_path / "test.py").write_text('''\
# TODO(alice): Alice's task
# TODO(bob): Bob's task
# TODO(Alice): Another Alice task (case variation)
# TODO: Unattributed task
''')
        return Rejig(str(tmp_path))

    def test_find_by_author(self, project: Rejig):
        """
        find_by_author() should find TODOs by a specific author.
        """
        finder = TodoFinder(project)
        result = finder.find_by_author("alice")

        # Should find both "alice" and "Alice" (case-insensitive)
        assert len(result) >= 1


# =============================================================================
# TodoFinder Stale Tests
# =============================================================================

class TestTodoFinderStale:
    """Tests for finding stale (old) TODOs."""

    def test_find_stale_old_todos(self, tmp_path: Path):
        """
        find_stale() should find TODOs older than the specified days.

        TODOs with dates in the past beyond the threshold are considered stale.
        """
        old_date = (date.today() - timedelta(days=100)).isoformat()
        (tmp_path / "test.py").write_text(f'''\
# TODO: {old_date} This is an old TODO
# TODO: This has no date
''')
        rejig = Rejig(str(tmp_path))
        finder = TodoFinder(rejig)

        result = finder.find_stale(older_than_days=90)

        # Only the TODO with the old date should be found
        assert len(result) == 1

    def test_find_stale_recent_todos(self, tmp_path: Path):
        """
        find_stale() should not find recently dated TODOs.
        """
        recent_date = (date.today() - timedelta(days=10)).isoformat()
        (tmp_path / "test.py").write_text(f'''\
# TODO: {recent_date} This is recent
''')
        rejig = Rejig(str(tmp_path))
        finder = TodoFinder(rejig)

        result = finder.find_stale(older_than_days=90)

        # Recent TODO should not be stale
        assert len(result) == 0

    def test_find_stale_no_dates(self, tmp_path: Path):
        """
        find_stale() should not match TODOs without dates.

        TODOs without dates cannot be determined to be stale.
        """
        (tmp_path / "test.py").write_text('''\
# TODO: No date here
# FIXME: Also no date
''')
        rejig = Rejig(str(tmp_path))
        finder = TodoFinder(rejig)

        result = finder.find_stale(older_than_days=30)

        assert len(result) == 0


# =============================================================================
# TodoFinder Priority Tests
# =============================================================================

class TestTodoFinderHighPriority:
    """Tests for finding high priority TODOs."""

    @pytest.fixture
    def project(self, tmp_path: Path) -> Rejig:
        """Create a project with various priority TODOs."""
        (tmp_path / "test.py").write_text('''\
# TODO: Regular task
# TODO(P1): High priority task
# FIXME: Important fix
# BUG: Critical bug
# NOTE: Just a note
# TODO(P2): Medium priority
''')
        return Rejig(str(tmp_path))

    def test_find_high_priority(self, project: Rejig):
        """
        find_high_priority() should find FIXME, BUG, and P1 TODOs.

        High priority is defined as:
        - Type FIXME or BUG (inherently urgent)
        - Priority P1
        """
        finder = TodoFinder(project)
        result = finder.find_high_priority()

        # Should find: TODO(P1), FIXME, BUG
        assert len(result) >= 3
        for todo in result:
            assert todo.is_high_priority is True


# =============================================================================
# TodoFinder Issue Reference Tests
# =============================================================================

class TestTodoFinderIssueRefs:
    """Tests for finding TODOs with/without issue references."""

    @pytest.fixture
    def project(self, tmp_path: Path) -> Rejig:
        """Create a project with and without issue references."""
        (tmp_path / "test.py").write_text('''\
# TODO: #123 Fix this bug
# TODO: GH-456 GitHub issue
# TODO: JIRA-789 Jira ticket
# TODO: No issue reference here
# FIXME: Also no reference
''')
        return Rejig(str(tmp_path))

    def test_find_unlinked(self, project: Rejig):
        """
        find_unlinked() should find TODOs without issue references.

        TODOs without references may indicate work that isn't being tracked.
        """
        finder = TodoFinder(project)
        result = finder.find_unlinked()

        # Should find the TODOs without issue references
        assert len(result) >= 2
        for todo in result:
            assert todo.issue_ref is None


# =============================================================================
# TodoFinder Pattern Matching Tests
# =============================================================================

class TestTodoFinderMatching:
    """Tests for finding TODOs matching text patterns."""

    @pytest.fixture
    def project(self, tmp_path: Path) -> Rejig:
        """Create a project with various TODO texts."""
        (tmp_path / "test.py").write_text('''\
# TODO: Fix authentication bug
# TODO: Add login feature
# TODO: Update documentation
# FIXME: Fix logout issue
''')
        return Rejig(str(tmp_path))

    def test_find_matching_simple(self, project: Rejig):
        """
        find_matching() should find TODOs matching a text pattern.
        """
        finder = TodoFinder(project)
        result = finder.find_matching("authentication")

        assert len(result) == 1
        assert "authentication" in result[0].todo_text

    def test_find_matching_regex(self, project: Rejig):
        """
        find_matching() should support regex patterns.
        """
        finder = TodoFinder(project)
        result = finder.find_matching("log(in|out)")

        # Should match "login" and "logout"
        assert len(result) >= 2


# =============================================================================
# TodoFinder Edge Cases
# =============================================================================

class TestTodoFinderEdgeCases:
    """Tests for edge cases in TODO finding."""

    def test_missing_file(self, tmp_path: Path):
        """
        find_in_file() should return empty for non-existent files.
        """
        rejig = Rejig(str(tmp_path))
        finder = TodoFinder(rejig)

        result = finder.find_in_file(tmp_path / "nonexistent.py")

        assert len(result) == 0

    def test_empty_file(self, tmp_path: Path):
        """
        find_in_file() should return empty for empty files.
        """
        (tmp_path / "empty.py").write_text("")
        rejig = Rejig(str(tmp_path))
        finder = TodoFinder(rejig)

        result = finder.find_in_file(tmp_path / "empty.py")

        assert len(result) == 0

    def test_inline_todo(self, tmp_path: Path):
        """
        Finder should detect inline TODO comments.
        """
        (tmp_path / "test.py").write_text("x = foo()  # TODO: Fix this\n")
        rejig = Rejig(str(tmp_path))
        finder = TodoFinder(rejig)

        result = finder.find_all()

        assert len(result) == 1
