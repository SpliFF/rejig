"""
Tests for rejig.todos.reporter module.

This module tests TodoReporter for generating reports:
- summary() for statistics
- to_markdown() for markdown output
- to_json() for JSON output
- to_csv() for CSV output
- to_table() for ASCII table output

TodoReporter generates various report formats from TodoTargetList.

Coverage targets:
- Summary statistics calculation
- Markdown report formatting
- JSON report formatting
- CSV report formatting
- ASCII table formatting
- Empty TODO list handling
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from rejig import Rejig
from rejig.todos.reporter import TodoReporter
from rejig.targets.python.todo import TodoTarget, TodoTargetList


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def rejig(tmp_path: Path) -> Rejig:
    """Create a Rejig instance."""
    return Rejig(str(tmp_path))


@pytest.fixture
def sample_todos(rejig: Rejig) -> TodoTargetList:
    """Create a sample list of TODOs for reporting."""
    todos = [
        TodoTarget(
            rejig=rejig,
            file_path=Path("app/main.py"),
            line_number=10,
            content="# TODO: Implement feature",
            todo_type="TODO",
            todo_text="Implement feature",
            author="alice",
        ),
        TodoTarget(
            rejig=rejig,
            file_path=Path("app/main.py"),
            line_number=25,
            content="# FIXME: Fix bug",
            todo_type="FIXME",
            todo_text="Fix bug",
            issue_ref="#123",
        ),
        TodoTarget(
            rejig=rejig,
            file_path=Path("app/utils.py"),
            line_number=5,
            content="# TODO(P1): Critical task",
            todo_type="TODO",
            todo_text="Critical task",
            priority=1,
        ),
        TodoTarget(
            rejig=rejig,
            file_path=Path("app/utils.py"),
            line_number=15,
            content="# BUG: Known issue",
            todo_type="BUG",
            todo_text="Known issue",
            author="bob",
        ),
    ]
    return TodoTargetList(rejig, todos)


@pytest.fixture
def empty_todos(rejig: Rejig) -> TodoTargetList:
    """Create an empty TODO list."""
    return TodoTargetList(rejig, [])


# =============================================================================
# TodoReporter summary() Tests
# =============================================================================

class TestTodoReporterSummary:
    """Tests for summary() method."""

    def test_summary_total_count(
        self, rejig: Rejig, sample_todos: TodoTargetList
    ):
        """
        summary() should include total count of TODOs.
        """
        reporter = TodoReporter(rejig, sample_todos)

        summary = reporter.summary()

        assert summary["total"] == 4

    def test_summary_by_type(
        self, rejig: Rejig, sample_todos: TodoTargetList
    ):
        """
        summary() should include counts by type.
        """
        reporter = TodoReporter(rejig, sample_todos)

        summary = reporter.summary()

        assert "by_type" in summary
        assert summary["by_type"]["TODO"] == 2
        assert summary["by_type"]["FIXME"] == 1
        assert summary["by_type"]["BUG"] == 1

    def test_summary_by_author(
        self, rejig: Rejig, sample_todos: TodoTargetList
    ):
        """
        summary() should include counts by author.
        """
        reporter = TodoReporter(rejig, sample_todos)

        summary = reporter.summary()

        assert "by_author" in summary
        assert summary["by_author"]["alice"] == 1
        assert summary["by_author"]["bob"] == 1

    def test_summary_issue_counts(
        self, rejig: Rejig, sample_todos: TodoTargetList
    ):
        """
        summary() should count TODOs with/without issue references.
        """
        reporter = TodoReporter(rejig, sample_todos)

        summary = reporter.summary()

        assert summary["with_issues"] == 1  # Only FIXME has #123
        assert summary["without_issues"] == 3

    def test_summary_high_priority(
        self, rejig: Rejig, sample_todos: TodoTargetList
    ):
        """
        summary() should count high priority TODOs.
        """
        reporter = TodoReporter(rejig, sample_todos)

        summary = reporter.summary()

        # High priority: FIXME, BUG, and TODO(P1)
        assert summary["high_priority"] == 3

    def test_summary_files_affected(
        self, rejig: Rejig, sample_todos: TodoTargetList
    ):
        """
        summary() should count affected files.
        """
        reporter = TodoReporter(rejig, sample_todos)

        summary = reporter.summary()

        assert summary["files_affected"] == 2

    def test_summary_empty_list(
        self, rejig: Rejig, empty_todos: TodoTargetList
    ):
        """
        summary() should handle empty TODO list.
        """
        reporter = TodoReporter(rejig, empty_todos)

        summary = reporter.summary()

        assert summary["total"] == 0
        assert summary["by_type"] == {}
        assert summary["by_author"] == {}


# =============================================================================
# TodoReporter to_markdown() Tests
# =============================================================================

class TestTodoReporterMarkdown:
    """Tests for to_markdown() method."""

    def test_markdown_has_header(
        self, rejig: Rejig, sample_todos: TodoTargetList
    ):
        """
        to_markdown() should include a header.
        """
        reporter = TodoReporter(rejig, sample_todos)

        output = reporter.to_markdown()

        assert "# TODO Report" in output

    def test_markdown_has_summary(
        self, rejig: Rejig, sample_todos: TodoTargetList
    ):
        """
        to_markdown() should include summary section.
        """
        reporter = TodoReporter(rejig, sample_todos)

        output = reporter.to_markdown()

        assert "## Summary" in output
        assert "Total TODOs" in output
        assert "Files affected" in output

    def test_markdown_has_type_breakdown(
        self, rejig: Rejig, sample_todos: TodoTargetList
    ):
        """
        to_markdown() should show count by type.
        """
        reporter = TodoReporter(rejig, sample_todos)

        output = reporter.to_markdown()

        assert "By Type" in output
        assert "TODO" in output
        assert "FIXME" in output

    def test_markdown_groups_by_file(
        self, rejig: Rejig, sample_todos: TodoTargetList
    ):
        """
        to_markdown() should group TODOs by file.
        """
        reporter = TodoReporter(rejig, sample_todos)

        output = reporter.to_markdown()

        assert "app/main.py" in output
        assert "app/utils.py" in output

    def test_markdown_shows_high_priority(
        self, rejig: Rejig, sample_todos: TodoTargetList
    ):
        """
        to_markdown() should highlight high priority items.
        """
        reporter = TodoReporter(rejig, sample_todos)

        output = reporter.to_markdown()

        # High priority items should be marked
        assert "[HIGH]" in output or "High priority" in output


# =============================================================================
# TodoReporter to_json() Tests
# =============================================================================

class TestTodoReporterJSON:
    """Tests for to_json() method."""

    def test_json_is_valid(
        self, rejig: Rejig, sample_todos: TodoTargetList
    ):
        """
        to_json() should produce valid JSON.
        """
        reporter = TodoReporter(rejig, sample_todos)

        output = reporter.to_json()
        data = json.loads(output)  # Should not raise

        assert isinstance(data, dict)

    def test_json_has_summary(
        self, rejig: Rejig, sample_todos: TodoTargetList
    ):
        """
        to_json() should include summary data.
        """
        reporter = TodoReporter(rejig, sample_todos)

        output = reporter.to_json()
        data = json.loads(output)

        assert "summary" in data
        assert data["summary"]["total"] == 4

    def test_json_has_todos_list(
        self, rejig: Rejig, sample_todos: TodoTargetList
    ):
        """
        to_json() should include list of TODOs.
        """
        reporter = TodoReporter(rejig, sample_todos)

        output = reporter.to_json()
        data = json.loads(output)

        assert "todos" in data
        assert len(data["todos"]) == 4

    def test_json_todo_structure(
        self, rejig: Rejig, sample_todos: TodoTargetList
    ):
        """
        to_json() TODO items should have expected fields.
        """
        reporter = TodoReporter(rejig, sample_todos)

        output = reporter.to_json()
        data = json.loads(output)
        todo = data["todos"][0]

        assert "type" in todo
        assert "text" in todo
        assert "file" in todo
        assert "line" in todo
        assert "author" in todo
        assert "issue_ref" in todo
        assert "priority" in todo

    def test_json_custom_indent(
        self, rejig: Rejig, sample_todos: TodoTargetList
    ):
        """
        to_json() should respect indent parameter.
        """
        reporter = TodoReporter(rejig, sample_todos)

        output_2 = reporter.to_json(indent=2)
        output_4 = reporter.to_json(indent=4)

        # Different indents produce different string lengths
        # (more indentation = longer output)
        assert len(output_4) > len(output_2)


# =============================================================================
# TodoReporter to_csv() Tests
# =============================================================================

class TestTodoReporterCSV:
    """Tests for to_csv() method."""

    def test_csv_has_header(
        self, rejig: Rejig, sample_todos: TodoTargetList
    ):
        """
        to_csv() should include a header row.
        """
        reporter = TodoReporter(rejig, sample_todos)

        output = reporter.to_csv()
        lines = output.splitlines()

        # First line should be header
        header = lines[0]
        assert "Type" in header
        assert "Text" in header
        assert "File" in header
        assert "Line" in header

    def test_csv_has_data_rows(
        self, rejig: Rejig, sample_todos: TodoTargetList
    ):
        """
        to_csv() should include data rows for each TODO.
        """
        reporter = TodoReporter(rejig, sample_todos)

        output = reporter.to_csv()
        lines = output.splitlines()

        # Header + 4 data rows
        assert len(lines) == 5

    def test_csv_empty_list(
        self, rejig: Rejig, empty_todos: TodoTargetList
    ):
        """
        to_csv() should work with empty list (header only).
        """
        reporter = TodoReporter(rejig, empty_todos)

        output = reporter.to_csv()
        lines = output.splitlines()

        # Just the header
        assert len(lines) == 1


# =============================================================================
# TodoReporter to_table() Tests
# =============================================================================

class TestTodoReporterTable:
    """Tests for to_table() method."""

    def test_table_has_header(
        self, rejig: Rejig, sample_todos: TodoTargetList
    ):
        """
        to_table() should include a header row.
        """
        reporter = TodoReporter(rejig, sample_todos)

        output = reporter.to_table()

        assert "Type" in output
        assert "Line" in output
        assert "File" in output
        assert "Text" in output

    def test_table_has_separator(
        self, rejig: Rejig, sample_todos: TodoTargetList
    ):
        """
        to_table() should have a separator line.
        """
        reporter = TodoReporter(rejig, sample_todos)

        output = reporter.to_table()

        assert "---" in output

    def test_table_truncates_long_text(
        self, rejig: Rejig
    ):
        """
        to_table() should truncate long text.
        """
        long_text = "x" * 100
        todos = TodoTargetList(rejig, [
            TodoTarget(
                rejig=rejig,
                file_path=Path("test.py"),
                line_number=1,
                content=f"# TODO: {long_text}",
                todo_type="TODO",
                todo_text=long_text,
            ),
        ])
        reporter = TodoReporter(rejig, todos)

        output = reporter.to_table()

        # Should be truncated with "..."
        assert "..." in output

    def test_table_empty_list(
        self, rejig: Rejig, empty_todos: TodoTargetList
    ):
        """
        to_table() should handle empty list gracefully.
        """
        reporter = TodoReporter(rejig, empty_todos)

        output = reporter.to_table()

        assert "No TODOs found" in output
