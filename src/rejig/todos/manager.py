"""TODO comment manager for adding, updating, and removing TODO comments."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rejig.core.results import Result
from rejig.targets.python.todo import TodoTarget, TodoType

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class TodoManager:
    """Add, update, and remove TODO comments.

    Provides methods to manipulate TODO comments in Python files.

    Parameters
    ----------
    rejig : Rejig
        The Rejig instance to use for file operations.

    Examples
    --------
    >>> manager = TodoManager(rj)
    >>> manager.add_todo(Path("myfile.py"), 42, "Fix this bug", todo_type="FIXME")
    >>> some_todo.remove()  # Use TodoTarget methods directly
    >>> some_todo.link_to_issue("#123")  # Use TodoTarget methods directly
    """

    def __init__(self, rejig: Rejig) -> None:
        self._rejig = rejig

    def add_todo(
        self,
        file_path: Path,
        line_number: int,
        text: str,
        todo_type: TodoType = "TODO",
        author: str | None = None,
        priority: int | None = None,
    ) -> Result:
        """Add a TODO comment to a specific line.

        The TODO is added as an inline comment at the end of the line.

        Parameters
        ----------
        file_path : Path
            Path to the file.
        line_number : int
            1-based line number to add the TODO to.
        text : str
            Text content of the TODO.
        todo_type : TodoType
            Type of TODO (default: "TODO").
        author : str | None
            Optional author name.
        priority : int | None
            Optional priority (1-5).

        Returns
        -------
        Result
            Result of the operation.
        """
        if not file_path.exists():
            return Result(success=False, message=f"File not found: {file_path}")

        try:
            content = file_path.read_text()
            lines = content.splitlines(keepends=True)

            if not (1 <= line_number <= len(lines)):
                return Result(
                    success=False,
                    message=f"Line {line_number} out of range (file has {len(lines)} lines)",
                )

            # Build the TODO comment
            todo_comment = TodoTarget._format_todo(todo_type, text, author, priority)

            # Get the line and add the comment
            idx = line_number - 1
            line = lines[idx].rstrip("\n\r")

            # Check if line already has a comment
            if "  #" in line:
                # Append to existing comment
                line = f"{line}  {todo_comment}"
            else:
                # Add new comment
                line = f"{line}  {todo_comment}"

            lines[idx] = line + "\n"
            new_content = "".join(lines)

            if self._rejig.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would add {todo_type} to line {line_number}",
                    files_changed=[file_path],
                )

            file_path.write_text(new_content)
            return Result(
                success=True,
                message=f"Added {todo_type} to line {line_number}",
                files_changed=[file_path],
            )

        except Exception as e:
            return Result(success=False, message=f"Failed to add TODO: {e}")

    def add_todo_line(
        self,
        file_path: Path,
        line_number: int,
        text: str,
        todo_type: TodoType = "TODO",
        author: str | None = None,
        priority: int | None = None,
    ) -> Result:
        """Add a TODO comment as a new line before the specified line.

        Parameters
        ----------
        file_path : Path
            Path to the file.
        line_number : int
            1-based line number to insert the TODO before.
        text : str
            Text content of the TODO.
        todo_type : TodoType
            Type of TODO (default: "TODO").
        author : str | None
            Optional author name.
        priority : int | None
            Optional priority (1-5).

        Returns
        -------
        Result
            Result of the operation.
        """
        if not file_path.exists():
            return Result(success=False, message=f"File not found: {file_path}")

        try:
            content = file_path.read_text()
            lines = content.splitlines(keepends=True)

            if not (1 <= line_number <= len(lines) + 1):
                return Result(
                    success=False,
                    message=f"Line {line_number} out of range (file has {len(lines)} lines)",
                )

            # Build the TODO comment
            todo_comment = TodoTarget._format_todo(todo_type, text, author, priority)

            # Determine indentation from the target line
            idx = line_number - 1
            if idx < len(lines):
                target_line = lines[idx]
                indent = len(target_line) - len(target_line.lstrip())
                indentation = target_line[:indent]
            else:
                indentation = ""

            # Insert the new TODO line
            new_line = f"{indentation}{todo_comment}\n"
            lines.insert(idx, new_line)
            new_content = "".join(lines)

            if self._rejig.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would add {todo_type} line before line {line_number}",
                    files_changed=[file_path],
                )

            file_path.write_text(new_content)
            return Result(
                success=True,
                message=f"Added {todo_type} line before line {line_number}",
                files_changed=[file_path],
            )

        except Exception as e:
            return Result(success=False, message=f"Failed to add TODO line: {e}")

    def convert_todos_to_issues(
        self,
        todos: list[TodoTarget],
        issue_format: str = "github",
    ) -> list[dict]:
        """Convert TODO comments to issue data structures.

        This doesn't create actual issues, but returns data that can be used
        to create issues via an API.

        Parameters
        ----------
        todos : list[TodoTarget]
            List of TODO comments to convert.
        issue_format : str
            Format for the issue data ("github", "gitlab", "jira").

        Returns
        -------
        list[dict]
            List of issue data dictionaries.
        """
        issues = []

        for todo in todos:
            text = todo.todo_text
            truncated_text = text[:50] + "..." if len(text) > 50 else text

            if issue_format == "github":
                issue = {
                    "title": f"{todo.todo_type}: {truncated_text}",
                    "body": f"**Source:** {todo.location}\n\n{text}",
                    "labels": [todo.todo_type.lower()],
                }
                if todo.author:
                    issue["assignees"] = [todo.author]
            elif issue_format == "gitlab":
                issue = {
                    "title": f"{todo.todo_type}: {truncated_text}",
                    "description": f"**Source:** {todo.location}\n\n{text}",
                    "labels": todo.todo_type.lower(),
                }
            elif issue_format == "jira":
                issue = {
                    "summary": f"{todo.todo_type}: {truncated_text}",
                    "description": f"Source: {todo.location}\n\n{text}",
                    "issuetype": {"name": "Task" if todo.todo_type == "TODO" else "Bug"},
                    "labels": [todo.todo_type],
                }
                if todo.priority:
                    # Map priority 1-5 to Jira priorities
                    priority_map = {1: "Highest", 2: "High", 3: "Medium", 4: "Low", 5: "Lowest"}
                    issue["priority"] = {"name": priority_map.get(todo.priority, "Medium")}
            else:
                issue = {
                    "type": todo.todo_type,
                    "text": text,
                    "location": todo.location,
                    "author": todo.author,
                    "priority": todo.priority,
                }

            issues.append(issue)

        return issues
