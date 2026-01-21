"""
Tests for rejig.todos.manager module.

This module tests TodoManager for adding and manipulating TODOs:
- add_todo() for adding inline TODO comments
- add_todo_line() for adding TODO as a new line
- convert_todos_to_issues() for issue tracker integration
- Dry run mode for all operations

TodoManager provides operations for creating and modifying TODO comments.

Coverage targets:
- Adding TODOs with various metadata (author, priority)
- Line-based vs inline TODO addition
- Dry run mode
- Error handling for missing files
- Issue conversion for different platforms
"""
from __future__ import annotations

from pathlib import Path

import pytest

from rejig import Rejig
from rejig.todos.manager import TodoManager
from rejig.targets.python.todo import TodoTarget


# =============================================================================
# TodoManager add_todo Tests
# =============================================================================

class TestTodoManagerAddTodo:
    """Tests for adding inline TODO comments."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    @pytest.fixture
    def python_file(self, tmp_path: Path) -> Path:
        """Create a sample Python file."""
        content = '''\
def hello():
    print("Hello")
    return True
'''
        file_path = tmp_path / "sample.py"
        file_path.write_text(content)
        return file_path

    def test_add_todo_simple(self, rejig: Rejig, python_file: Path):
        """
        add_todo() should add a TODO comment at the end of a line.
        """
        manager = TodoManager(rejig)

        result = manager.add_todo(python_file, 2, "Fix this greeting")

        assert result.success is True
        content = python_file.read_text()
        assert "# TODO: Fix this greeting" in content

    def test_add_todo_with_type(self, rejig: Rejig, python_file: Path):
        """
        add_todo() should support different TODO types.
        """
        manager = TodoManager(rejig)

        result = manager.add_todo(python_file, 2, "Broken code", todo_type="FIXME")

        assert result.success is True
        content = python_file.read_text()
        assert "# FIXME: Broken code" in content

    def test_add_todo_with_author(self, rejig: Rejig, python_file: Path):
        """
        add_todo() should include author in the comment.
        """
        manager = TodoManager(rejig)

        result = manager.add_todo(
            python_file, 2, "Review this",
            author="john"
        )

        assert result.success is True
        content = python_file.read_text()
        assert "# TODO(john): Review this" in content

    def test_add_todo_with_priority(self, rejig: Rejig, python_file: Path):
        """
        add_todo() should include priority in the comment.
        """
        manager = TodoManager(rejig)

        result = manager.add_todo(
            python_file, 2, "Critical fix",
            priority=1
        )

        assert result.success is True
        content = python_file.read_text()
        assert "# TODO(P1): Critical fix" in content

    def test_add_todo_missing_file(self, rejig: Rejig, tmp_path: Path):
        """
        add_todo() should fail for missing files.
        """
        manager = TodoManager(rejig)

        result = manager.add_todo(tmp_path / "missing.py", 1, "Task")

        assert result.success is False
        assert "not found" in result.message.lower()

    def test_add_todo_line_out_of_range(self, rejig: Rejig, python_file: Path):
        """
        add_todo() should fail for out-of-range line numbers.
        """
        manager = TodoManager(rejig)

        result = manager.add_todo(python_file, 100, "Task")

        assert result.success is False
        assert "out of range" in result.message.lower()

    def test_add_todo_dry_run(self, tmp_path: Path):
        """
        In dry run mode, add_todo() should not modify the file.
        """
        file_path = tmp_path / "test.py"
        original = "x = 1\n"
        file_path.write_text(original)

        rejig = Rejig(str(tmp_path), dry_run=True)
        manager = TodoManager(rejig)

        result = manager.add_todo(file_path, 1, "Add this")

        assert result.success is True
        assert "DRY RUN" in result.message
        # File should be unchanged
        content = file_path.read_text()
        assert content == original


# =============================================================================
# TodoManager add_todo_line Tests
# =============================================================================

class TestTodoManagerAddTodoLine:
    """Tests for adding TODO comments as new lines."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    @pytest.fixture
    def python_file(self, tmp_path: Path) -> Path:
        """Create a sample Python file."""
        content = '''\
def hello():
    print("Hello")
    return True
'''
        file_path = tmp_path / "sample.py"
        file_path.write_text(content)
        return file_path

    def test_add_todo_line_simple(self, rejig: Rejig, python_file: Path):
        """
        add_todo_line() should insert a TODO as a new line before the target.
        """
        manager = TodoManager(rejig)

        result = manager.add_todo_line(python_file, 2, "Fix greeting")

        assert result.success is True
        content = python_file.read_text()
        lines = content.splitlines()
        # TODO should be inserted before line 2
        assert "# TODO: Fix greeting" in lines[1]

    def test_add_todo_line_preserves_indentation(self, rejig: Rejig, tmp_path: Path):
        """
        add_todo_line() should match indentation of the target line.
        """
        file_path = tmp_path / "indent.py"
        file_path.write_text("def foo():\n    x = 1\n")

        manager = TodoManager(rejig)
        result = manager.add_todo_line(file_path, 2, "Fix this")

        assert result.success is True
        content = file_path.read_text()
        # The TODO line should be indented to match "    x = 1"
        assert "    # TODO: Fix this" in content

    def test_add_todo_line_dry_run(self, tmp_path: Path):
        """
        In dry run mode, add_todo_line() should not modify the file.
        """
        file_path = tmp_path / "test.py"
        original = "x = 1\n"
        file_path.write_text(original)

        rejig = Rejig(str(tmp_path), dry_run=True)
        manager = TodoManager(rejig)

        result = manager.add_todo_line(file_path, 1, "Add task")

        assert result.success is True
        assert "DRY RUN" in result.message
        content = file_path.read_text()
        assert content == original


# =============================================================================
# TodoManager convert_todos_to_issues Tests
# =============================================================================

class TestTodoManagerConvertToIssues:
    """Tests for converting TODOs to issue tracker format."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    @pytest.fixture
    def todos(self, rejig: Rejig) -> list[TodoTarget]:
        """Create sample TodoTarget objects."""
        return [
            TodoTarget(
                rejig=rejig,
                file_path=Path("app.py"),
                line_number=10,
                content="# TODO: Fix login",
                todo_type="TODO",
                todo_text="Fix the login functionality",
            ),
            TodoTarget(
                rejig=rejig,
                file_path=Path("api.py"),
                line_number=25,
                content="# FIXME(john): Critical bug",
                todo_type="FIXME",
                todo_text="Critical bug in API",
                author="john",
                priority=1,
            ),
        ]

    def test_convert_to_github_format(self, rejig: Rejig, todos: list[TodoTarget]):
        """
        convert_todos_to_issues() should produce GitHub issue format.
        """
        manager = TodoManager(rejig)

        issues = manager.convert_todos_to_issues(todos, issue_format="github")

        assert len(issues) == 2
        # Check first issue structure
        assert "title" in issues[0]
        assert "body" in issues[0]
        assert "labels" in issues[0]
        # Check TODO is in labels
        assert "todo" in issues[0]["labels"]
        # Check FIXME issue has assignee
        assert "assignees" in issues[1]
        assert "john" in issues[1]["assignees"]

    def test_convert_to_gitlab_format(self, rejig: Rejig, todos: list[TodoTarget]):
        """
        convert_todos_to_issues() should produce GitLab issue format.
        """
        manager = TodoManager(rejig)

        issues = manager.convert_todos_to_issues(todos, issue_format="gitlab")

        assert len(issues) == 2
        # GitLab uses "description" instead of "body"
        assert "title" in issues[0]
        assert "description" in issues[0]
        assert "labels" in issues[0]

    def test_convert_to_jira_format(self, rejig: Rejig, todos: list[TodoTarget]):
        """
        convert_todos_to_issues() should produce Jira issue format.
        """
        manager = TodoManager(rejig)

        issues = manager.convert_todos_to_issues(todos, issue_format="jira")

        assert len(issues) == 2
        # Jira uses "summary" instead of "title"
        assert "summary" in issues[0]
        assert "description" in issues[0]
        assert "issuetype" in issues[0]
        # FIXME with priority should have Jira priority
        assert "priority" in issues[1]

    def test_convert_to_generic_format(self, rejig: Rejig, todos: list[TodoTarget]):
        """
        convert_todos_to_issues() with unknown format returns generic structure.
        """
        manager = TodoManager(rejig)

        issues = manager.convert_todos_to_issues(todos, issue_format="unknown")

        assert len(issues) == 2
        # Generic format has type, text, location
        assert "type" in issues[0]
        assert "text" in issues[0]
        assert "location" in issues[0]
