"""TODO comment reporter for generating reports."""
from __future__ import annotations

import csv
import io
import json
from collections import Counter
from typing import TYPE_CHECKING

from rejig.targets.python.todo import TodoTarget, TodoTargetList

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class TodoReporter:
    """Generate reports from TODO comments.

    Provides various output formats for TODO comment analysis.

    Parameters
    ----------
    rejig : Rejig
        The Rejig instance to use.
    todos : TodoTargetList
        The TODO comments to report on.

    Examples
    --------
    >>> todos = rj.find_todos()
    >>> reporter = TodoReporter(rj, todos)
    >>> print(reporter.to_markdown())
    >>> summary = reporter.summary()
    """

    def __init__(self, rejig: Rejig, todos: TodoTargetList) -> None:
        self._rejig = rejig
        self._todos = todos

    def summary(self) -> dict:
        """Generate a summary dictionary of TODO statistics.

        Returns
        -------
        dict
            Dictionary with summary statistics including:
            - total: Total number of TODOs
            - by_type: Count by type (TODO, FIXME, etc.)
            - by_author: Count by author
            - with_issues: Count with issue references
            - without_issues: Count without issue references
            - high_priority: Count of high priority TODOs
            - files_affected: Number of files with TODOs
        """
        todos_list = self._todos.to_list()

        by_type: Counter[str] = Counter()
        by_author: Counter[str] = Counter()
        files: set[str] = set()
        with_issues = 0
        high_priority = 0

        for todo in todos_list:
            by_type[todo.todo_type] += 1
            if todo.author:
                by_author[todo.author] += 1
            if todo.issue_ref:
                with_issues += 1
            if todo.is_high_priority:
                high_priority += 1
            files.add(str(todo.file_path))

        return {
            "total": len(todos_list),
            "by_type": dict(by_type),
            "by_author": dict(by_author),
            "with_issues": with_issues,
            "without_issues": len(todos_list) - with_issues,
            "high_priority": high_priority,
            "files_affected": len(files),
        }

    def to_markdown(self) -> str:
        """Generate a markdown report of TODOs.

        Returns
        -------
        str
            Markdown formatted report.
        """
        todos_list = self._todos.to_list()
        summary = self.summary()

        lines = [
            "# TODO Report",
            "",
            "## Summary",
            "",
            f"- **Total TODOs:** {summary['total']}",
            f"- **Files affected:** {summary['files_affected']}",
            f"- **High priority:** {summary['high_priority']}",
            f"- **With issue references:** {summary['with_issues']}",
            f"- **Without issue references:** {summary['without_issues']}",
            "",
            "### By Type",
            "",
        ]

        for todo_type, count in sorted(summary["by_type"].items()):
            lines.append(f"- {todo_type}: {count}")

        if summary["by_author"]:
            lines.extend(["", "### By Author", ""])
            for author, count in sorted(summary["by_author"].items()):
                lines.append(f"- {author}: {count}")

        lines.extend(["", "## TODOs", ""])

        # Group by file
        by_file: dict[str, list[TodoTarget]] = {}
        for todo in todos_list:
            key = str(todo.file_path)
            if key not in by_file:
                by_file[key] = []
            by_file[key].append(todo)

        for file_path, file_todos in sorted(by_file.items()):
            lines.append(f"### {file_path}")
            lines.append("")
            for todo in sorted(file_todos, key=lambda t: t.line_number):
                prefix = ""
                if todo.is_high_priority:
                    prefix = "**[HIGH]** "
                elif todo.issue_ref:
                    prefix = f"[{todo.issue_ref}] "

                author_suffix = f" (@{todo.author})" if todo.author else ""
                lines.append(
                    f"- Line {todo.line_number}: {prefix}{todo.todo_type}: {todo.todo_text}{author_suffix}"
                )
            lines.append("")

        return "\n".join(lines)

    def to_json(self, indent: int = 2) -> str:
        """Generate a JSON report of TODOs.

        Parameters
        ----------
        indent : int
            Indentation level for JSON output. Default: 2.

        Returns
        -------
        str
            JSON formatted report.
        """
        todos_list = self._todos.to_list()

        data = {
            "summary": self.summary(),
            "todos": [
                {
                    "type": todo.todo_type,
                    "text": todo.todo_text,
                    "file": str(todo.file_path),
                    "line": todo.line_number,
                    "author": todo.author,
                    "issue_ref": todo.issue_ref,
                    "priority": todo.priority,
                    "is_high_priority": todo.is_high_priority,
                    "date": todo.todo_date.isoformat() if todo.todo_date else None,
                }
                for todo in todos_list
            ],
        }

        return json.dumps(data, indent=indent)

    def to_csv(self) -> str:
        """Generate a CSV report of TODOs.

        Returns
        -------
        str
            CSV formatted report.
        """
        todos_list = self._todos.to_list()

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "Type",
            "Text",
            "File",
            "Line",
            "Author",
            "Issue Ref",
            "Priority",
            "High Priority",
            "Date",
        ])

        # Data rows
        for todo in todos_list:
            writer.writerow([
                todo.todo_type,
                todo.todo_text,
                str(todo.file_path),
                todo.line_number,
                todo.author or "",
                todo.issue_ref or "",
                todo.priority or "",
                "Yes" if todo.is_high_priority else "No",
                todo.todo_date.isoformat() if todo.todo_date else "",
            ])

        return output.getvalue()

    def to_table(self) -> str:
        """Generate an ASCII table report of TODOs.

        Returns
        -------
        str
            ASCII table formatted report.
        """
        todos_list = self._todos.to_list()

        if not todos_list:
            return "No TODOs found."

        # Calculate column widths
        type_width = max(len(t.todo_type) for t in todos_list)
        type_width = max(type_width, 4)  # minimum "Type"

        file_width = min(40, max(len(str(t.file_path)) for t in todos_list))
        file_width = max(file_width, 4)  # minimum "File"

        text_width = min(50, max(len(t.todo_text) for t in todos_list))
        text_width = max(text_width, 4)  # minimum "Text"

        # Header
        header = f"{'Type':<{type_width}} | {'Line':>5} | {'File':<{file_width}} | {'Text':<{text_width}}"
        separator = "-" * len(header)

        lines = [header, separator]

        for todo in sorted(todos_list, key=lambda t: (str(t.file_path), t.line_number)):
            file_str = str(todo.file_path)
            if len(file_str) > file_width:
                file_str = "..." + file_str[-(file_width - 3):]

            text_str = todo.todo_text
            if len(text_str) > text_width:
                text_str = text_str[:text_width - 3] + "..."

            lines.append(
                f"{todo.todo_type:<{type_width}} | {todo.line_number:>5} | {file_str:<{file_width}} | {text_str:<{text_width}}"
            )

        return "\n".join(lines)
