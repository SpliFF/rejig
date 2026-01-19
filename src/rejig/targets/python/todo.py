"""TodoTarget for operations on TODO/FIXME/XXX/HACK/NOTE/BUG comments."""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterator, Literal

from rejig.targets.base import BatchResult, Result, TargetList
from rejig.targets.python.comment import CommentTarget

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig

TodoType = Literal["TODO", "FIXME", "XXX", "HACK", "NOTE", "BUG"]

# All recognized TODO types
TODO_TYPES: tuple[TodoType, ...] = ("TODO", "FIXME", "XXX", "HACK", "NOTE", "BUG")


class TodoTarget(CommentTarget):
    """Target for a TODO/FIXME/XXX/HACK/NOTE/BUG comment.

    Extends CommentTarget with TODO-specific attributes and operations.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    file_path : Path
        Path to the file containing the comment.
    line_number : int
        1-based line number where the comment is located.
    content : str
        The comment content (including # prefix).
    todo_type : TodoType
        Type of TODO comment (TODO, FIXME, XXX, HACK, NOTE, BUG).
    todo_text : str
        The text content of the TODO (without type prefix).
    author : str | None
        Author from "TODO(author):" format.
    issue_ref : str | None
        Issue reference from "TODO: #123" or "TODO: GH-123" format.
    todo_date : date | None
        Date from "TODO: 2024-01-15" format.
    priority : int | None
        Priority from "TODO(P1):" format.

    Examples
    --------
    >>> todos = rj.find_todos()
    >>> for todo in todos:
    ...     print(f"{todo.location}: {todo.todo_type} - {todo.todo_text}")
    """

    # Pattern for issue references in text
    ISSUE_PATTERN = re.compile(
        r"(?P<ref>#\d+|GH-\d+|JIRA-\d+|[A-Z]+-\d+)",
        re.IGNORECASE,
    )

    def __init__(
        self,
        rejig: Rejig,
        file_path: Path,
        line_number: int,
        content: str,
        todo_type: TodoType,
        todo_text: str,
        author: str | None = None,
        issue_ref: str | None = None,
        todo_date: date | None = None,
        priority: int | None = None,
    ) -> None:
        super().__init__(rejig, file_path, line_number, content)
        self._todo_type = todo_type
        self._todo_text = todo_text
        self._author = author
        self._issue_ref = issue_ref
        self._todo_date = todo_date
        self._priority = priority

    @property
    def todo_type(self) -> TodoType:
        """Type of TODO comment (TODO, FIXME, XXX, HACK, NOTE, BUG)."""
        return self._todo_type

    @property
    def todo_text(self) -> str:
        """The text content of the TODO (without type prefix)."""
        return self._todo_text

    @property
    def author(self) -> str | None:
        """Author from "TODO(author):" format."""
        return self._author

    @property
    def issue_ref(self) -> str | None:
        """Issue reference from "TODO: #123" or "TODO: GH-123" format."""
        return self._issue_ref

    @property
    def todo_date(self) -> date | None:
        """Date from "TODO: 2024-01-15" format."""
        return self._todo_date

    @property
    def priority(self) -> int | None:
        """Priority from "TODO(P1):" format."""
        return self._priority

    @property
    def location(self) -> str:
        """Get the file:line location string."""
        return f"{self.path}:{self.line_number}"

    @property
    def is_high_priority(self) -> bool:
        """Check if this is a high priority TODO.

        Returns True if:
        - Type is FIXME or BUG (inherently high priority)
        - Priority is 1 (P1)
        """
        return self._todo_type in ("FIXME", "BUG") or self._priority == 1

    def __repr__(self) -> str:
        preview = self._todo_text[:30] + "..." if len(self._todo_text) > 30 else self._todo_text
        return f"TodoTarget({self.path}:{self.line_number}, {self._todo_type}: {preview!r})"

    def remove(self) -> Result:
        """Remove this TODO comment from the file.

        Alias for delete() to maintain compatibility.

        Returns
        -------
        Result
            Result of the removal operation.
        """
        return self.delete()

    def link_to_issue(self, issue_ref: str) -> Result:
        """Link this TODO to an issue reference.

        Prepends the issue reference to the TODO text.

        Parameters
        ----------
        issue_ref : str
            Issue reference (e.g., "#123", "GH-456").

        Returns
        -------
        Result
            Result of the linking operation.
        """
        if self._issue_ref == issue_ref:
            return Result(
                success=True,
                message=f"TODO already linked to {issue_ref}",
            )

        # Build the new TODO comment
        new_text = f"{issue_ref} {self._todo_text}"
        new_comment = self._format_todo(self._todo_type, new_text, self._author, self._priority)
        return self.rewrite(new_comment)

    def update(
        self,
        new_text: str | None = None,
        new_type: TodoType | None = None,
        new_author: str | None = None,
        new_priority: int | None = None,
    ) -> Result:
        """Update this TODO comment.

        Parameters
        ----------
        new_text : str | None
            New text content (None to keep existing).
        new_type : TodoType | None
            New type (None to keep existing).
        new_author : str | None
            New author (None to keep existing).
        new_priority : int | None
            New priority (None to keep existing).

        Returns
        -------
        Result
            Result of the operation.
        """
        final_type = new_type or self._todo_type
        final_text = new_text if new_text is not None else self._todo_text
        final_author = new_author if new_author is not None else self._author
        final_priority = new_priority if new_priority is not None else self._priority

        new_comment = self._format_todo(final_type, final_text, final_author, final_priority)
        result = self.rewrite(new_comment)

        if result.success:
            # Update internal state
            self._todo_type = final_type
            self._todo_text = final_text
            self._author = final_author
            self._priority = final_priority

        return result

    @staticmethod
    def _format_todo(
        todo_type: TodoType,
        text: str,
        author: str | None = None,
        priority: int | None = None,
    ) -> str:
        """Format a TODO comment string."""
        meta = ""
        if priority is not None:
            meta = f"P{priority}"
        elif author is not None:
            meta = author

        if meta:
            return f"# {todo_type}({meta}): {text}"
        return f"# {todo_type}: {text}"


class TodoTargetList(TargetList["TodoTarget"]):
    """Specialized TargetList for TODO comments with filtering helpers.

    Extends TargetList with TODO-specific filtering and batch operations.

    Examples
    --------
    >>> todos = rj.find_todos()
    >>> fixmes = todos.by_type("FIXME")
    >>> unlinked = todos.without_issues()
    >>> for todo in unlinked:
    ...     print(todo.location, todo.todo_text)
    """

    def __repr__(self) -> str:
        return f"TodoTargetList({len(self._targets)} todos)"

    # ===== TODO-specific filtering methods =====

    def by_type(self, todo_type: TodoType) -> TodoTargetList:
        """Filter to TODOs of a specific type.

        Parameters
        ----------
        todo_type : TodoType
            Type to filter by (TODO, FIXME, XXX, HACK, NOTE, BUG).

        Returns
        -------
        TodoTargetList
            TODOs matching the specified type.
        """
        return TodoTargetList(
            self._rejig, [t for t in self._targets if t.todo_type == todo_type]
        )

    def by_author(self, author: str) -> TodoTargetList:
        """Filter to TODOs by a specific author.

        Parameters
        ----------
        author : str
            Author name to filter by (case-insensitive).

        Returns
        -------
        TodoTargetList
            TODOs by the specified author.
        """
        author_lower = author.lower()
        return TodoTargetList(
            self._rejig,
            [t for t in self._targets if t.author is not None and t.author.lower() == author_lower],
        )

    def high_priority(self) -> TodoTargetList:
        """Filter to high priority TODOs.

        Returns TODOs that are:
        - Type FIXME or BUG
        - Priority P1

        Returns
        -------
        TodoTargetList
            High priority TODOs.
        """
        return TodoTargetList(
            self._rejig, [t for t in self._targets if t.is_high_priority]
        )

    def with_issues(self) -> TodoTargetList:
        """Filter to TODOs that have issue references.

        Returns
        -------
        TodoTargetList
            TODOs with issue references.
        """
        return TodoTargetList(
            self._rejig, [t for t in self._targets if t.issue_ref is not None]
        )

    def without_issues(self) -> TodoTargetList:
        """Filter to TODOs that don't have issue references.

        Returns
        -------
        TodoTargetList
            TODOs without issue references.
        """
        return TodoTargetList(
            self._rejig, [t for t in self._targets if t.issue_ref is None]
        )

    def in_file(self, file_path: Path | str) -> TodoTargetList:
        """Filter to TODOs in a specific file.

        Parameters
        ----------
        file_path : Path | str
            Path to the file.

        Returns
        -------
        TodoTargetList
            TODOs in the specified file.
        """
        path = Path(file_path) if isinstance(file_path, str) else file_path
        return TodoTargetList(
            self._rejig, [t for t in self._targets if t.file_path == path]
        )

    def matching(self, pattern: str) -> TodoTargetList:
        """Filter to TODOs whose text matches a pattern.

        Parameters
        ----------
        pattern : str
            Regex pattern to match against TODO text.

        Returns
        -------
        TodoTargetList
            TODOs with text matching the pattern.
        """
        regex = re.compile(pattern, re.IGNORECASE)
        return TodoTargetList(
            self._rejig, [t for t in self._targets if regex.search(t.todo_text) is not None]
        )

    def filter(self, predicate: Callable[[TodoTarget], bool]) -> TodoTargetList:
        """Filter TODOs by a predicate function.

        Parameters
        ----------
        predicate : Callable[[TodoTarget], bool]
            Function that returns True for TODOs to keep.

        Returns
        -------
        TodoTargetList
            Filtered list of TODOs.
        """
        return TodoTargetList(self._rejig, [t for t in self._targets if predicate(t)])

    # ===== TODO-specific batch operations =====

    def remove_all(self) -> BatchResult:
        """Remove all TODOs in this list.

        Returns
        -------
        BatchResult
            Results of the removal operations.
        """
        return BatchResult([todo.remove() for todo in self._targets])

    def link_all_to_issue(self, issue_ref: str) -> BatchResult:
        """Link all TODOs to an issue reference.

        Parameters
        ----------
        issue_ref : str
            Issue reference to add (e.g., "#123", "GH-456").

        Returns
        -------
        BatchResult
            Results of the linking operations.
        """
        return BatchResult([todo.link_to_issue(issue_ref) for todo in self._targets])