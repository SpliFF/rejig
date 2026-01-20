"""
Django settings management utilities.

This module provides methods for modifying Django settings files,
including INSTALLED_APPS, MIDDLEWARE, and custom settings.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from ..core.results import Result

if TYPE_CHECKING:
    from .project import DjangoProject


class SettingsManager:
    """Manager for Django settings file operations."""

    def __init__(self, project: DjangoProject):
        self.project = project

    @property
    def settings_path(self) -> Path:
        return self.project.settings_path

    @property
    def dry_run(self) -> bool:
        return self.project.dry_run

    def add_installed_app(
        self,
        app_name: str,
        after_app: str | None = None,
    ) -> Result:
        """
        Add an app to INSTALLED_APPS in Django settings.

        Parameters
        ----------
        app_name : str
            Name of the app to add.
        after_app : str | None, optional
            Insert after this app (if specified).

        Returns
        -------
        Result
            Result with success status.
        """
        settings_path = self.settings_path
        if not settings_path.exists():
            return Result(
                success=False,
                message=f"Settings file not found: {settings_path}",
            )

        content = settings_path.read_text()

        if f'"{app_name}"' in content or f"'{app_name}'" in content:
            return Result(
                success=True,
                message=f"App {app_name} already in INSTALLED_APPS",
            )

        if after_app:
            pattern = rf'(["\']){after_app}\1,'
            replacement = rf'\g<0>\n    "{app_name}",'
            new_content = re.sub(pattern, replacement, content)
        else:
            pattern = r'(INSTALLED_APPS[^)]+)\)'
            replacement = rf'\1    "{app_name}",\n)'
            new_content = re.sub(pattern, replacement, content)

        if new_content == content:
            return Result(
                success=False,
                message=f"Could not add {app_name} to INSTALLED_APPS",
            )

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would add {app_name} to INSTALLED_APPS",
                files_changed=[settings_path],
            )

        settings_path.write_text(new_content)
        return Result(
            success=True,
            message=f"Added {app_name} to INSTALLED_APPS",
            files_changed=[settings_path],
        )

    def update_middleware_path(
        self,
        old_path: str,
        new_path: str,
    ) -> Result:
        """
        Update a middleware path in Django settings.

        Parameters
        ----------
        old_path : str
            Current middleware path.
        new_path : str
            New middleware path.

        Returns
        -------
        Result
            Result with success status.
        """
        settings_path = self.settings_path
        if not settings_path.exists():
            return Result(
                success=False,
                message=f"Settings file not found: {settings_path}",
            )

        content = settings_path.read_text()

        if old_path not in content:
            return Result(
                success=False,
                message=f"Middleware {old_path} not found in settings",
            )

        new_content = content.replace(f'"{old_path}"', f'"{new_path}"')
        new_content = new_content.replace(f"'{old_path}'", f"'{new_path}'")

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would update middleware: {old_path} -> {new_path}",
                files_changed=[settings_path],
            )

        settings_path.write_text(new_content)
        return Result(
            success=True,
            message=f"Updated middleware: {old_path} -> {new_path}",
            files_changed=[settings_path],
        )

    def add_middleware(
        self,
        middleware_path: str,
        position: str = "first",
        after: str | None = None,
    ) -> Result:
        """
        Add a middleware to Django settings.

        Parameters
        ----------
        middleware_path : str
            Full path to the middleware class.
        position : str, optional
            'first', 'last', or 'after'. Defaults to "first".
        after : str | None, optional
            Middleware to insert after (when position='after').

        Returns
        -------
        Result
            Result with success status.
        """
        settings_path = self.settings_path
        if not settings_path.exists():
            return Result(
                success=False,
                message=f"Settings file not found: {settings_path}",
            )

        content = settings_path.read_text()

        if middleware_path in content:
            return Result(
                success=True,
                message=f"Middleware {middleware_path} already in settings",
            )

        if position == "first":
            pattern = r'(MIDDLEWARE[^(]*\(\s*\n)'
            replacement = rf'\1    "{middleware_path}",\n'
        elif position == "last":
            pattern = r'(MIDDLEWARE[^)]+)\)'
            replacement = rf'\1    "{middleware_path}",\n)'
        elif position == "after" and after:
            pattern = rf'(["\']){re.escape(after)}\1,'
            replacement = rf'\g<0>\n    "{middleware_path}",'
        else:
            return Result(
                success=False,
                message="Invalid position or missing 'after' parameter",
            )

        new_content = re.sub(pattern, replacement, content)

        if new_content == content:
            return Result(
                success=False,
                message=f"Could not add middleware {middleware_path}",
            )

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would add middleware: {middleware_path}",
                files_changed=[settings_path],
            )

        settings_path.write_text(new_content)
        return Result(
            success=True,
            message=f"Added middleware: {middleware_path}",
            files_changed=[settings_path],
        )

    def _find_setting_bounds(
        self,
        content: str,
        setting_name: str,
    ) -> tuple[int, int] | None:
        """
        Find the start and end positions of a setting in content.

        Handles multiline settings by tracking bracket depth.

        Returns
        -------
        tuple[int, int] | None
            Tuple of (start, end) positions or None if not found.
        """
        pattern = rf'^{setting_name}\s*='
        match = re.search(pattern, content, re.MULTILINE)
        if not match:
            return None

        start = match.start()
        value_start = match.end()
        remaining = content[value_start:]

        stripped = remaining.lstrip()
        if not stripped:
            return (start, len(content))

        first_char = stripped[0]

        if first_char in '([{':
            bracket_map = {'(': ')', '[': ']', '{': '}'}
            open_bracket = first_char
            close_bracket = bracket_map[first_char]
            depth = 0
            in_string = False
            string_char = ''
            i = 0

            while i < len(remaining):
                char = remaining[i]

                if not in_string:
                    if remaining[i:i+3] in ('"""', "'''"):
                        in_string = True
                        string_char = remaining[i:i+3]
                        i += 3
                        continue
                    elif char in '"\'':
                        in_string = True
                        string_char = char
                else:
                    if len(string_char) == 3 and remaining[i:i+3] == string_char:
                        in_string = False
                        i += 3
                        continue
                    elif len(string_char) == 1 and char == string_char:
                        if i == 0 or remaining[i-1] != '\\':
                            in_string = False
                    i += 1
                    continue

                if char == open_bracket:
                    depth += 1
                elif char == close_bracket:
                    depth -= 1
                    if depth == 0:
                        end = value_start + i + 1
                        if end < len(content) and content[end] == '\n':
                            end += 1
                        return (start, end)

                i += 1

            return (start, len(content))
        else:
            newline_pos = remaining.find('\n')
            if newline_pos == -1:
                end = len(content)
            else:
                end = value_start + newline_pos + 1
            return (start, end)

    def add_setting(
        self,
        setting_name: str,
        value: str,
        comment: str | None = None,
        settings_file: Path | None = None,
    ) -> Result:
        """
        Add a new setting to Django settings file.

        Parameters
        ----------
        setting_name : str
            Name of the setting (e.g., 'MY_SETTING').
        value : str
            Value to assign (as Python code, e.g., '"string"' or 'True').
        comment : str | None, optional
            Optional comment line(s) to add above the setting.
        settings_file : Path | None, optional
            Path to settings file (default: base settings).

        Returns
        -------
        Result
            Result with success status.
        """
        settings_path = settings_file or self.settings_path
        if not settings_path.exists():
            return Result(
                success=False,
                message=f"Settings file not found: {settings_path}",
            )

        content = settings_path.read_text()

        if re.search(rf'^{setting_name}\s*=', content, re.MULTILINE):
            return Result(
                success=False,
                message=f"Setting {setting_name} already exists (use update_setting instead)",
            )

        lines = ["\n"]
        if comment:
            for line in comment.splitlines():
                lines.append(f"# {line}\n")
        lines.append(f"{setting_name} = {value}\n")
        new_setting = "".join(lines)

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would add setting: {setting_name}",
                files_changed=[settings_path],
            )

        new_content = content.rstrip() + new_setting
        settings_path.write_text(new_content)
        return Result(
            success=True,
            message=f"Added setting: {setting_name}",
            files_changed=[settings_path],
        )

    def update_setting(
        self,
        setting_name: str,
        new_value: str,
        comment: str | None = None,
        settings_file: Path | None = None,
    ) -> Result:
        """
        Update an existing setting in Django settings file.

        Parameters
        ----------
        setting_name : str
            Name of the setting to update.
        new_value : str
            New value to assign (as Python code).
        comment : str | None, optional
            Optional comment line(s) to add/replace above the setting.
        settings_file : Path | None, optional
            Path to settings file (default: base settings).

        Returns
        -------
        Result
            Result with success status.
        """
        settings_path = settings_file or self.settings_path
        if not settings_path.exists():
            return Result(
                success=False,
                message=f"Settings file not found: {settings_path}",
            )

        content = settings_path.read_text()

        bounds = self._find_setting_bounds(content, setting_name)
        if bounds is None:
            return Result(
                success=False,
                message=f"Setting {setting_name} not found (use add_setting instead)",
            )

        start, end = bounds

        comment_start = start
        if comment is not None:
            lines_before = content[:start].splitlines(keepends=True)
            while lines_before and lines_before[-1].strip().startswith('#'):
                comment_start -= len(lines_before.pop())

        replacement_lines = []
        if comment is not None and comment:
            for line in comment.splitlines():
                replacement_lines.append(f"# {line}\n")
        replacement_lines.append(f"{setting_name} = {new_value}\n")
        replacement = "".join(replacement_lines)

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would update setting: {setting_name}",
                files_changed=[settings_path],
            )

        new_content = content[:comment_start] + replacement + content[end:]
        settings_path.write_text(new_content)
        return Result(
            success=True,
            message=f"Updated setting: {setting_name}",
            files_changed=[settings_path],
        )

    def delete_setting(
        self,
        setting_name: str,
        delete_comment: bool = True,
        settings_file: Path | None = None,
    ) -> Result:
        """
        Delete a setting from Django settings file.

        Parameters
        ----------
        setting_name : str
            Name of the setting to delete.
        delete_comment : bool, optional
            If True, also delete comment lines immediately above.
            Defaults to True.
        settings_file : Path | None, optional
            Path to settings file (default: base settings).

        Returns
        -------
        Result
            Result with success status.
        """
        settings_path = settings_file or self.settings_path
        if not settings_path.exists():
            return Result(
                success=False,
                message=f"Settings file not found: {settings_path}",
            )

        content = settings_path.read_text()

        bounds = self._find_setting_bounds(content, setting_name)
        if bounds is None:
            return Result(
                success=True,
                message=f"Setting {setting_name} not found (already deleted?)",
            )

        start, end = bounds

        if delete_comment:
            lines_before = content[:start].splitlines(keepends=True)
            while lines_before and lines_before[-1].strip().startswith('#'):
                start -= len(lines_before.pop())

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would delete setting: {setting_name}",
                files_changed=[settings_path],
            )

        new_content = content[:start] + content[end:]
        new_content = re.sub(r'\n{3,}', '\n\n', new_content)
        settings_path.write_text(new_content)
        return Result(
            success=True,
            message=f"Deleted setting: {setting_name}",
            files_changed=[settings_path],
        )
