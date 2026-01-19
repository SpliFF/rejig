"""TODO comment management for Python codebases.

This package provides tools for parsing, finding, managing, and reporting on
TODO/FIXME/XXX/HACK/NOTE/BUG comments in Python source code.

Classes
-------
TodoTarget
    Target representing a TODO comment (subclass of CommentTarget).

TodoTargetList
    Specialized TargetList for TODO comments with filtering helpers.

TodoParser
    Parse TODO comments from source code.

TodoFinder
    Find TODO comments across a codebase.

TodoManager
    Add TODO comments to files.

TodoReporter
    Generate reports from TODO comments.

TodoType
    Literal type for valid TODO types.

Examples
--------
>>> from rejig import Rejig
>>> rj = Rejig("src/")
>>>
>>> # Find all TODOs
>>> todos = rj.find_todos()
>>> print(f"Found {len(todos)} TODOs")
>>>
>>> # Filter by type
>>> fixmes = todos.by_type("FIXME")
>>>
>>> # Filter by author
>>> johns_todos = todos.by_author("john")
>>>
>>> # Find TODOs without issue references
>>> unlinked = todos.without_issues()
>>>
>>> # Operations on TodoTarget
>>> for todo in unlinked:
...     todo.link_to_issue("#123")
>>>
>>> # Generate a report
>>> from rejig.todos import TodoReporter
>>> reporter = TodoReporter(rj, todos)
>>> print(reporter.to_markdown())
"""

from rejig.targets.python.todo import (
    TODO_TYPES,
    TodoTarget,
    TodoTargetList,
    TodoType,
)
from rejig.todos.finder import TodoFinder
from rejig.todos.manager import TodoManager
from rejig.todos.parser import TodoParser
from rejig.todos.reporter import TodoReporter

__all__ = [
    "TodoTarget",
    "TodoTargetList",
    "TodoParser",
    "TodoFinder",
    "TodoManager",
    "TodoReporter",
    "TodoType",
    "TODO_TYPES",
]
