"""TODO comment parser for extracting TODO/FIXME/XXX/HACK/NOTE/BUG comments."""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from rejig.targets.python.todo import TODO_TYPES, TodoTarget, TodoType

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class TodoParser:
    """Parse TODO comments from Python source code.

    Recognizes various TODO formats:
    - # TODO: message
    - # TODO(author): message
    - # FIXME: #123 message
    - # TODO(P1): high priority
    - # TODO: 2024-01-15 message with date

    Examples
    --------
    >>> parser = TodoParser(rj)
    >>> todo = parser.parse_line("# TODO(john): Fix this bug", Path("foo.py"), 10)
    >>> print(todo.author)
    john
    """

    # Main pattern for TODO comments
    # Matches: # TODO, # TODO:, # TODO(meta):, etc.
    PATTERN = re.compile(
        r"#\s*"
        r"(?P<type>TODO|FIXME|XXX|HACK|NOTE|BUG)"
        r"(?:\((?P<meta>[^)]+)\))?"
        r"\s*:?\s*"
        r"(?P<text>.*)",
        re.IGNORECASE,
    )

    # Pattern for issue references in text
    ISSUE_PATTERN = re.compile(
        r"(?P<ref>#\d+|GH-\d+|JIRA-\d+|[A-Z]+-\d+)",
        re.IGNORECASE,
    )

    # Pattern for dates in text
    DATE_PATTERN = re.compile(
        r"(?P<date>\d{4}-\d{2}-\d{2})",
    )

    # Pattern for priority in meta (e.g., P1, P2)
    PRIORITY_PATTERN = re.compile(
        r"P(?P<priority>\d)",
        re.IGNORECASE,
    )

    def __init__(self, rejig: Rejig) -> None:
        """Initialize the parser.

        Parameters
        ----------
        rejig : Rejig
            Rejig instance to attach to parsed TodoTargets.
        """
        self._rejig = rejig

    def parse_line(
        self, line: str, file_path: Path, line_number: int
    ) -> TodoTarget | None:
        """Parse a single line for TODO comments.

        Parameters
        ----------
        line : str
            The line to parse.
        file_path : Path
            Path to the file containing the line.
        line_number : int
            1-based line number.

        Returns
        -------
        TodoTarget | None
            Parsed TodoTarget or None if no TODO found.
        """
        match = self.PATTERN.search(line)
        if not match:
            return None

        todo_type: TodoType = match.group("type").upper()  # type: ignore
        meta = match.group("meta")
        text = match.group("text").strip()

        # Parse metadata from parentheses
        author: str | None = None
        priority: int | None = None

        if meta:
            # Check for priority (P1, P2, etc.)
            priority_match = self.PRIORITY_PATTERN.search(meta)
            if priority_match:
                priority = int(priority_match.group("priority"))
            else:
                # Assume it's an author name
                author = meta.strip()

        # Parse issue reference from text
        issue_ref: str | None = None
        issue_match = self.ISSUE_PATTERN.search(text)
        if issue_match:
            issue_ref = issue_match.group("ref")

        # Parse date from text
        todo_date: date | None = None
        date_match = self.DATE_PATTERN.search(text)
        if date_match:
            try:
                todo_date = date.fromisoformat(date_match.group("date"))
            except ValueError:
                pass

        return TodoTarget(
            rejig=self._rejig,
            file_path=file_path,
            line_number=line_number,
            content=line.strip(),
            todo_type=todo_type,
            todo_text=text,
            author=author,
            issue_ref=issue_ref,
            todo_date=todo_date,
            priority=priority,
        )

    def parse_file(self, file_path: Path) -> list[TodoTarget]:
        """Parse all TODO comments from a file.

        Parameters
        ----------
        file_path : Path
            Path to the file to parse.

        Returns
        -------
        list[TodoTarget]
            List of parsed TodoTarget objects.
        """
        todos: list[TodoTarget] = []

        if not file_path.exists():
            return todos

        try:
            content = file_path.read_text()
            for line_number, line in enumerate(content.splitlines(), 1):
                todo = self.parse_line(line, file_path, line_number)
                if todo:
                    todos.append(todo)
        except Exception:
            pass

        return todos

    def parse_content(
        self, content: str, file_path: Path
    ) -> list[TodoTarget]:
        """Parse TODO comments from content string.

        Parameters
        ----------
        content : str
            The content to parse.
        file_path : Path
            Path to associate with the comments.

        Returns
        -------
        list[TodoTarget]
            List of parsed TodoTarget objects.
        """
        todos: list[TodoTarget] = []

        for line_number, line in enumerate(content.splitlines(), 1):
            todo = self.parse_line(line, file_path, line_number)
            if todo:
                todos.append(todo)

        return todos
