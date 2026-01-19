"""TODO comment finder for searching across codebases."""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from rejig.targets.python.todo import TodoTarget, TodoTargetList, TodoType
from rejig.todos.parser import TodoParser

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class TodoFinder:
    """Find TODO comments across a codebase.

    Provides methods to search for TODO comments in Python files with various
    filtering options.

    Parameters
    ----------
    rejig : Rejig
        The Rejig instance to use for finding files.

    Examples
    --------
    >>> finder = TodoFinder(rj)
    >>> all_todos = finder.find_all()
    >>> fixmes = finder.find_by_type("FIXME")
    >>> johns_todos = finder.find_by_author("john")
    """

    def __init__(self, rejig: Rejig) -> None:
        self._rejig = rejig
        self._parser = TodoParser(rejig)

    def find_all(self) -> TodoTargetList:
        """Find all TODO comments in the codebase.

        Returns
        -------
        TodoTargetList
            All TODO comments found.
        """
        todos: list[TodoTarget] = []

        for file_path in self._rejig.files:
            todos.extend(self._parser.parse_file(file_path))

        return TodoTargetList(self._rejig, todos)

    def find_in_file(self, file_path: Path) -> TodoTargetList:
        """Find all TODO comments in a specific file.

        Parameters
        ----------
        file_path : Path
            Path to the file to search.

        Returns
        -------
        TodoTargetList
            TODO comments found in the file.
        """
        todos = self._parser.parse_file(file_path)
        return TodoTargetList(self._rejig, todos)

    def find_by_type(self, todo_type: TodoType) -> TodoTargetList:
        """Find TODO comments of a specific type.

        Parameters
        ----------
        todo_type : TodoType
            Type of TODO to find (TODO, FIXME, XXX, HACK, NOTE, BUG).

        Returns
        -------
        TodoTargetList
            TODO comments of the specified type.
        """
        return self.find_all().by_type(todo_type)

    def find_by_author(self, author: str) -> TodoTargetList:
        """Find TODO comments by a specific author.

        Parameters
        ----------
        author : str
            Author name to search for (case-insensitive).

        Returns
        -------
        TodoTargetList
            TODO comments by the specified author.
        """
        return self.find_all().by_author(author)

    def find_stale(self, older_than_days: int = 90) -> TodoTargetList:
        """Find TODO comments that are older than a specified number of days.

        Only finds TODOs that have dates in their format (e.g., "TODO: 2024-01-15").
        TODOs without dates are not considered stale.

        Parameters
        ----------
        older_than_days : int
            Number of days after which a TODO is considered stale. Default: 90.

        Returns
        -------
        TodoTargetList
            TODO comments older than the specified number of days.
        """
        cutoff_date = date.today() - timedelta(days=older_than_days)

        def is_stale(todo: TodoTarget) -> bool:
            return todo.todo_date is not None and todo.todo_date < cutoff_date

        return self.find_all().filter(is_stale)

    def find_high_priority(self) -> TodoTargetList:
        """Find high priority TODO comments.

        Returns TODOs that are:
        - Type FIXME or BUG
        - Priority P1

        Returns
        -------
        TodoTargetList
            High priority TODO comments.
        """
        return self.find_all().high_priority()

    def find_unlinked(self) -> TodoTargetList:
        """Find TODO comments without issue references.

        Returns
        -------
        TodoTargetList
            TODO comments that don't have issue references.
        """
        return self.find_all().without_issues()

    def find_matching(self, pattern: str) -> TodoTargetList:
        """Find TODO comments matching a text pattern.

        Parameters
        ----------
        pattern : str
            Regex pattern to match against TODO text.

        Returns
        -------
        TodoTargetList
            TODO comments with text matching the pattern.
        """
        return self.find_all().matching(pattern)
