"""
Tests for rejig.todos.parser module.

This module tests parsing of TODO/FIXME/XXX/HACK/NOTE/BUG comments:
- Different comment formats
- Extraction of author, priority, issue references
- Date parsing in TODOs
- Line number tracking

The TodoParser requires a Rejig instance and returns TodoTarget objects.

Coverage targets:
- Standard TODO formats (# TODO: message)
- Author format (# TODO(author): message)
- Priority format (# TODO(P1): message)
- Issue references (# TODO: #123 message)
- Date parsing (# TODO: 2024-01-15 message)
- FIXME, XXX, HACK, NOTE, BUG variants
"""
from __future__ import annotations

import textwrap
from datetime import date
from pathlib import Path

import pytest

from rejig import Rejig
from rejig.todos.parser import TodoParser
from rejig.targets.python.todo import TodoTarget


# =============================================================================
# TodoParser Tests
# =============================================================================

class TestTodoParser:
    """Tests for TodoParser class.

    The TodoParser is used to extract TODO comments from Python source code.
    It parses different TODO formats and extracts metadata like author,
    priority, issue references, and dates.
    """

    @pytest.fixture
    def parser(self, tmp_path: Path) -> TodoParser:
        """Create a TodoParser with a Rejig instance.

        TodoParser requires a Rejig instance to attach to the TodoTarget
        objects it creates.
        """
        rj = Rejig(str(tmp_path))
        return TodoParser(rj)

    def test_parse_simple_todo(self, parser: TodoParser, tmp_path: Path):
        """
        Parser should detect simple TODO comments.

        The most basic TODO format is: # TODO: message
        The parser extracts the type (TODO) and text content.
        """
        line = "# TODO: Implement this function"
        file_path = tmp_path / "test.py"

        result = parser.parse_line(line, file_path, 1)

        # parse_line returns TodoTarget if a TODO is found, None otherwise
        assert result is not None
        assert isinstance(result, TodoTarget)
        assert result.todo_type == "TODO"
        assert "Implement this function" in result.todo_text

    def test_parse_fixme(self, parser: TodoParser, tmp_path: Path):
        """
        Parser should detect FIXME comments.

        FIXME is recognized as a TODO type, typically indicating
        something that needs to be fixed (higher priority than TODO).
        """
        line = "# FIXME: This is broken"
        file_path = tmp_path / "test.py"

        result = parser.parse_line(line, file_path, 1)

        assert result is not None
        assert result.todo_type == "FIXME"
        assert "This is broken" in result.todo_text

    def test_parse_xxx(self, parser: TodoParser, tmp_path: Path):
        """
        Parser should detect XXX comments.

        XXX is a traditional marker for code that needs attention,
        often indicating temporary hacks or concerns.
        """
        line = "# XXX: Temporary workaround"
        file_path = tmp_path / "test.py"

        result = parser.parse_line(line, file_path, 1)

        assert result is not None
        assert result.todo_type == "XXX"
        assert "Temporary workaround" in result.todo_text

    def test_parse_hack(self, parser: TodoParser, tmp_path: Path):
        """
        Parser should detect HACK comments.

        HACK indicates code that is known to be a workaround
        rather than a proper solution.
        """
        line = "# HACK: Quick fix for demo"
        file_path = tmp_path / "test.py"

        result = parser.parse_line(line, file_path, 1)

        assert result is not None
        assert result.todo_type == "HACK"
        assert "Quick fix for demo" in result.todo_text

    def test_parse_note(self, parser: TodoParser, tmp_path: Path):
        """
        Parser should detect NOTE comments.

        NOTE is informational and less urgent than TODO or FIXME.
        """
        line = "# NOTE: This is important to understand"
        file_path = tmp_path / "test.py"

        result = parser.parse_line(line, file_path, 1)

        assert result is not None
        assert result.todo_type == "NOTE"

    def test_parse_bug(self, parser: TodoParser, tmp_path: Path):
        """
        Parser should detect BUG comments.

        BUG indicates a known bug that needs to be fixed.
        """
        line = "# BUG: Race condition here"
        file_path = tmp_path / "test.py"

        result = parser.parse_line(line, file_path, 1)

        assert result is not None
        assert result.todo_type == "BUG"

    def test_parse_todo_with_author(self, parser: TodoParser, tmp_path: Path):
        """
        Parser should extract author from TODO(author) format.

        The author is specified in parentheses after the TODO type.
        This is useful for tracking who added the TODO.
        """
        line = "# TODO(john): Review this code"
        file_path = tmp_path / "test.py"

        result = parser.parse_line(line, file_path, 1)

        assert result is not None
        assert result.author == "john"
        assert "Review this code" in result.todo_text

    def test_parse_todo_with_priority(self, parser: TodoParser, tmp_path: Path):
        """
        Parser should extract priority from TODO(P1) format.

        Priority is specified as P followed by a number (1-9).
        P1 is highest priority.
        """
        line = "# TODO(P1): Critical fix needed"
        file_path = tmp_path / "test.py"

        result = parser.parse_line(line, file_path, 1)

        assert result is not None
        assert result.priority == 1
        # When priority is specified, author should be None
        assert result.author is None

    def test_parse_todo_with_issue_reference(self, parser: TodoParser, tmp_path: Path):
        """
        Parser should extract issue references from TODO text.

        Issue references like #123, GH-456, JIRA-789 are extracted
        from the TODO text content.
        """
        line = "# TODO: #123 Fix the login bug"
        file_path = tmp_path / "test.py"

        result = parser.parse_line(line, file_path, 1)

        assert result is not None
        assert result.issue_ref == "#123"

    def test_parse_todo_with_date(self, parser: TodoParser, tmp_path: Path):
        """
        Parser should extract dates from TODO text.

        Dates in ISO format (YYYY-MM-DD) are extracted from the text.
        This can indicate when the TODO was added or a deadline.
        """
        line = "# TODO: 2024-01-15 Complete this by then"
        file_path = tmp_path / "test.py"

        result = parser.parse_line(line, file_path, 1)

        assert result is not None
        assert result.todo_date == date(2024, 1, 15)

    def test_parse_line_no_todo(self, parser: TodoParser, tmp_path: Path):
        """
        Parser should return None when no TODO is found.

        Regular comments without TODO markers should not match.
        """
        line = "# This is a regular comment"
        file_path = tmp_path / "test.py"

        result = parser.parse_line(line, file_path, 1)

        assert result is None

    def test_parse_line_regular_code(self, parser: TodoParser, tmp_path: Path):
        """
        Parser should return None for regular code lines.
        """
        line = "x = 42"
        file_path = tmp_path / "test.py"

        result = parser.parse_line(line, file_path, 1)

        assert result is None

    def test_parse_file(self, parser: TodoParser, tmp_path: Path):
        """
        parse_file should find all TODOs in a file.

        This method reads the file and parses each line, returning
        a list of all TodoTarget objects found.
        """
        code = textwrap.dedent('''\
            # TODO: First task
            def func():
                # FIXME: Fix this bug
                pass  # XXX: Temporary
        ''')

        test_file = tmp_path / "test.py"
        test_file.write_text(code)

        todos = parser.parse_file(test_file)

        # Should find 3 TODOs
        assert len(todos) >= 3
        # All should be TodoTarget objects
        assert all(isinstance(t, TodoTarget) for t in todos)

    def test_parse_content(self, parser: TodoParser, tmp_path: Path):
        """
        parse_content should work on string content without reading a file.

        This is useful for parsing code that hasn't been written to disk.
        """
        code = textwrap.dedent('''\
            # TODO: First item
            # FIXME: Second item
        ''')
        file_path = tmp_path / "virtual.py"

        todos = parser.parse_content(code, file_path)

        assert len(todos) >= 2
        assert any(t.todo_type == "TODO" for t in todos)
        assert any(t.todo_type == "FIXME" for t in todos)

    def test_parse_file_nonexistent(self, parser: TodoParser, tmp_path: Path):
        """
        parse_file should return empty list for non-existent files.

        This follows the "never raise" pattern - errors return empty results.
        """
        file_path = tmp_path / "nonexistent.py"

        todos = parser.parse_file(file_path)

        assert todos == []

    def test_todo_line_number(self, parser: TodoParser, tmp_path: Path):
        """
        TodoTarget should have correct line number.

        Line numbers are 1-based and track where the TODO appears in the file.
        """
        result = parser.parse_line("# TODO: Something", Path("test.py"), 42)

        assert result is not None
        assert result.line_number == 42


# =============================================================================
# TodoTarget Tests
# =============================================================================

class TestTodoTarget:
    """Tests for TodoTarget class.

    TodoTarget extends CommentTarget with TODO-specific attributes
    and operations like is_high_priority, link_to_issue, update, etc.
    """

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance for testing."""
        return Rejig(str(tmp_path))

    def test_is_high_priority_for_fixme(self, rejig: Rejig):
        """
        FIXME type should be considered high priority.

        FIXME and BUG types are inherently high priority.
        """
        todo = TodoTarget(
            rejig=rejig,
            file_path=Path("test.py"),
            line_number=1,
            content="# FIXME: Important",
            todo_type="FIXME",
            todo_text="Important",
        )

        assert todo.is_high_priority is True

    def test_is_high_priority_for_bug(self, rejig: Rejig):
        """
        BUG type should be considered high priority.
        """
        todo = TodoTarget(
            rejig=rejig,
            file_path=Path("test.py"),
            line_number=1,
            content="# BUG: Something wrong",
            todo_type="BUG",
            todo_text="Something wrong",
        )

        assert todo.is_high_priority is True

    def test_is_high_priority_for_p1(self, rejig: Rejig):
        """
        Priority 1 should be considered high priority.
        """
        todo = TodoTarget(
            rejig=rejig,
            file_path=Path("test.py"),
            line_number=1,
            content="# TODO(P1): Critical",
            todo_type="TODO",
            todo_text="Critical",
            priority=1,
        )

        assert todo.is_high_priority is True

    def test_not_high_priority_for_todo(self, rejig: Rejig):
        """
        Regular TODO without P1 priority should not be high priority.
        """
        todo = TodoTarget(
            rejig=rejig,
            file_path=Path("test.py"),
            line_number=1,
            content="# TODO: Normal task",
            todo_type="TODO",
            todo_text="Normal task",
        )

        assert todo.is_high_priority is False

    def test_location_property(self, rejig: Rejig):
        """
        location property should return file:line format.
        """
        todo = TodoTarget(
            rejig=rejig,
            file_path=Path("src/app.py"),
            line_number=42,
            content="# TODO: Something",
            todo_type="TODO",
            todo_text="Something",
        )

        assert todo.location == "src/app.py:42"

    def test_repr(self, rejig: Rejig):
        """
        __repr__ should include file, line, type, and text preview.
        """
        todo = TodoTarget(
            rejig=rejig,
            file_path=Path("test.py"),
            line_number=10,
            content="# TODO: Test this",
            todo_type="TODO",
            todo_text="Test this",
        )

        repr_str = repr(todo)
        assert "TodoTarget" in repr_str
        assert "10" in repr_str
        assert "TODO" in repr_str

    def test_format_todo_basic(self):
        """
        _format_todo should produce correct TODO string format.
        """
        result = TodoTarget._format_todo("TODO", "Fix this bug")
        assert result == "# TODO: Fix this bug"

    def test_format_todo_with_author(self):
        """
        _format_todo should include author when provided.
        """
        result = TodoTarget._format_todo("TODO", "Fix this", author="john")
        assert result == "# TODO(john): Fix this"

    def test_format_todo_with_priority(self):
        """
        _format_todo should include priority when provided.
        Priority takes precedence over author in the format.
        """
        result = TodoTarget._format_todo("FIXME", "Critical bug", priority=1)
        assert result == "# FIXME(P1): Critical bug"
