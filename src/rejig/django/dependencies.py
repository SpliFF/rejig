"""
Dependency management utilities for pyproject.toml.

This module provides methods for adding, updating, and removing
dependencies in Poetry-style pyproject.toml files.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from ..core.results import Result

if TYPE_CHECKING:
    from .project import DjangoProject


class DependencyManager:
    """Manager for pyproject.toml dependency operations."""

    def __init__(self, project: DjangoProject):
        self.project = project

    @property
    def pyproject_path(self) -> Path:
        return self.project.pyproject_path

    @property
    def dry_run(self) -> bool:
        return self.project.dry_run

    def _find_dependencies_section(
        self,
        content: str,
        section: str = "tool.poetry.dependencies",
    ) -> tuple[int, int] | None:
        """
        Find the start and end positions of a dependencies section.

        Parameters
        ----------
        content : str
            File content.
        section : str, optional
            Section name (e.g., 'tool.poetry.dependencies').

        Returns
        -------
        tuple[int, int] | None
            Tuple of (section_start, section_end) or None if not found.
        """
        section_pattern = r'^\[' + re.escape(section) + r'\]\s*\n'
        match = re.search(section_pattern, content, re.MULTILINE)
        if not match:
            return None

        section_start = match.start()
        content_start = match.end()

        remaining = content[content_start:]
        next_section = re.search(r'^\[', remaining, re.MULTILINE)
        if next_section:
            section_end = content_start + next_section.start()
        else:
            section_end = len(content)

        return (section_start, section_end)

    def _find_dependency_line(
        self,
        content: str,
        package_name: str,
        section: str = "tool.poetry.dependencies",
    ) -> tuple[int, int] | None:
        """
        Find the start and end positions of a dependency line.

        Parameters
        ----------
        content : str
            File content.
        package_name : str
            Name of the package to find.
        section : str, optional
            Section to search in.

        Returns
        -------
        tuple[int, int] | None
            Tuple of (line_start, line_end) or None if not found.
        """
        section_bounds = self._find_dependencies_section(content, section)
        if section_bounds is None:
            return None

        section_start, section_end = section_bounds
        section_content = content[section_start:section_end]

        pattern = rf'^{re.escape(package_name)}\s*=\s*'
        match = re.search(pattern, section_content, re.MULTILINE)
        if not match:
            return None

        line_start = section_start + match.start()
        value_start = section_start + match.end()

        remaining = content[value_start:]
        first_char = remaining.lstrip()[0] if remaining.strip() else ''

        if first_char == '{':
            brace_depth = 0
            in_string = False
            string_char = ''
            i = 0
            while i < len(remaining):
                char = remaining[i]
                if not in_string:
                    if char in '"\'':
                        in_string = True
                        string_char = char
                    elif char == '{':
                        brace_depth += 1
                    elif char == '}':
                        brace_depth -= 1
                        if brace_depth == 0:
                            line_end = value_start + i + 1
                            if line_end < len(content) and content[line_end] == '\n':
                                line_end += 1
                            return (line_start, line_end)
                else:
                    if char == string_char and (i == 0 or remaining[i-1] != '\\'):
                        in_string = False
                i += 1
            return (line_start, len(content))
        else:
            newline_pos = remaining.find('\n')
            if newline_pos == -1:
                line_end = len(content)
            else:
                line_end = value_start + newline_pos + 1
            return (line_start, line_end)

    def add_dependency(
        self,
        package_name: str,
        version: str,
        extras: list[str] | None = None,
        optional: bool = False,
        section: str = "tool.poetry.dependencies",
        pyproject_file: Path | None = None,
    ) -> Result:
        """
        Add a new dependency to pyproject.toml.

        Parameters
        ----------
        package_name : str
            Name of the package (e.g., 'requests').
        version : str
            Version specifier (e.g., '^2.28.0' or '>=1.0,<2.0').
        extras : list[str] | None, optional
            Optional list of extras (e.g., ['security']).
        optional : bool, optional
            If True, mark as optional dependency. Defaults to False.
        section : str, optional
            TOML section for dependencies.
        pyproject_file : Path | None, optional
            Path to pyproject.toml (default: root/pyproject.toml).

        Returns
        -------
        Result
            Result with success status.
        """
        pyproject_path = pyproject_file or self.pyproject_path
        if not pyproject_path.exists():
            return Result(
                success=False,
                message=f"pyproject.toml not found: {pyproject_path}",
            )

        content = pyproject_path.read_text()

        if self._find_dependency_line(content, package_name, section) is not None:
            return Result(
                success=False,
                message=f"Dependency {package_name} already exists (use update_dependency)",
            )

        section_bounds = self._find_dependencies_section(content, section)
        if section_bounds is None:
            return Result(
                success=False,
                message=f"Section [{section}] not found in pyproject.toml",
            )

        section_start, section_end = section_bounds

        if extras or optional:
            parts = [f'version = "{version}"']
            if extras:
                extras_str = ", ".join(f'"{e}"' for e in extras)
                parts.append(f"extras = [{extras_str}]")
            if optional:
                parts.append("optional = true")
            dep_line = f'{package_name} = {{{", ".join(parts)}}}\n'
        else:
            dep_line = f'{package_name} = "{version}"\n'

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would add dependency: {package_name}",
                files_changed=[pyproject_path],
            )

        section_content = content[section_start:section_end].rstrip()
        new_content = (
            content[:section_start]
            + section_content
            + "\n"
            + dep_line
            + "\n"
            + content[section_end:].lstrip('\n')
        )

        pyproject_path.write_text(new_content)
        return Result(
            success=True,
            message=f'Added dependency: {package_name} = "{version}"',
            files_changed=[pyproject_path],
        )

    def update_dependency(
        self,
        package_name: str,
        version: str,
        extras: list[str] | None = None,
        optional: bool | None = None,
        section: str = "tool.poetry.dependencies",
        pyproject_file: Path | None = None,
    ) -> Result:
        """
        Update an existing dependency in pyproject.toml.

        Parameters
        ----------
        package_name : str
            Name of the package to update.
        version : str
            New version specifier.
        extras : list[str] | None, optional
            Optional list of extras (None to keep existing).
        optional : bool | None, optional
            Optional flag (None to keep existing).
        section : str, optional
            TOML section for dependencies.
        pyproject_file : Path | None, optional
            Path to pyproject.toml (default: root/pyproject.toml).

        Returns
        -------
        Result
            Result with success status.
        """
        pyproject_path = pyproject_file or self.pyproject_path
        if not pyproject_path.exists():
            return Result(
                success=False,
                message=f"pyproject.toml not found: {pyproject_path}",
            )

        content = pyproject_path.read_text()

        line_bounds = self._find_dependency_line(content, package_name, section)
        if line_bounds is None:
            return Result(
                success=False,
                message=f"Dependency {package_name} not found (use add_dependency)",
            )

        start, end = line_bounds

        if extras is not None or optional is not None:
            parts = [f'version = "{version}"']
            if extras:
                extras_str = ", ".join(f'"{e}"' for e in extras)
                parts.append(f"extras = [{extras_str}]")
            if optional:
                parts.append("optional = true")
            dep_line = f'{package_name} = {{{", ".join(parts)}}}\n'
        else:
            existing = content[start:end]
            if '{' in existing:
                dep_line = re.sub(
                    r'version\s*=\s*"[^"]*"',
                    f'version = "{version}"',
                    existing,
                )
                if dep_line == existing:
                    dep_line = f'{package_name} = "{version}"\n'
            else:
                dep_line = f'{package_name} = "{version}"\n'

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would update dependency: {package_name}",
                files_changed=[pyproject_path],
            )

        new_content = content[:start] + dep_line + content[end:]
        pyproject_path.write_text(new_content)
        return Result(
            success=True,
            message=f'Updated dependency: {package_name} = "{version}"',
            files_changed=[pyproject_path],
        )

    def remove_dependency(
        self,
        package_name: str,
        section: str = "tool.poetry.dependencies",
        pyproject_file: Path | None = None,
    ) -> Result:
        """
        Remove a dependency from pyproject.toml.

        Parameters
        ----------
        package_name : str
            Name of the package to remove.
        section : str, optional
            TOML section for dependencies.
        pyproject_file : Path | None, optional
            Path to pyproject.toml (default: root/pyproject.toml).

        Returns
        -------
        Result
            Result with success status.
        """
        pyproject_path = pyproject_file or self.pyproject_path
        if not pyproject_path.exists():
            return Result(
                success=False,
                message=f"pyproject.toml not found: {pyproject_path}",
            )

        content = pyproject_path.read_text()

        line_bounds = self._find_dependency_line(content, package_name, section)
        if line_bounds is None:
            return Result(
                success=True,
                message=f"Dependency {package_name} not found (already removed?)",
            )

        start, end = line_bounds

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would remove dependency: {package_name}",
                files_changed=[pyproject_path],
            )

        new_content = content[:start] + content[end:]
        new_content = re.sub(r'\n{3,}', '\n\n', new_content)
        pyproject_path.write_text(new_content)
        return Result(
            success=True,
            message=f"Removed dependency: {package_name}",
            files_changed=[pyproject_path],
        )
