"""
Django URL configuration management utilities.

This module provides methods for modifying Django URL configuration files,
including adding, removing, and moving URL patterns.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from ..core.results import Result

if TYPE_CHECKING:
    from .project import DjangoProject


class UrlManager:
    """Manager for Django URL configuration operations."""

    def __init__(self, project: DjangoProject):
        self.project = project

    @property
    def root_urls_path(self) -> Path:
        return self.project.root_urls_path

    @property
    def django_root(self) -> Path:
        return self.project.django_root

    @property
    def dry_run(self) -> bool:
        return self.project.dry_run

    def add_url_include(
        self,
        urls_module: str,
        path_prefix: str = "",
        urls_file: Path | None = None,
        position: str = "first",
    ) -> Result:
        """
        Add an include() to a urls.py file.

        Parameters
        ----------
        urls_module : str
            Module path to include (e.g., 'myapp.urls').
        path_prefix : str, optional
            URL path prefix (e.g., 'api/'). Defaults to "".
        urls_file : Path | None, optional
            Path to urls.py (default: root urls.py).
        position : str, optional
            'first' or 'last'. Defaults to "first".

        Returns
        -------
        Result
            Result with success status.
        """
        urls_path = urls_file or self.root_urls_path
        if not urls_path.exists():
            return Result(
                success=False,
                message=f"URLs file not found: {urls_path}",
            )

        content = urls_path.read_text()

        if urls_module in content:
            return Result(
                success=True,
                message=f"URL include for {urls_module} already exists",
            )

        new_line = f'    path("{path_prefix}", include("{urls_module}")),\n'

        if position == "first":
            pattern = r'(urlpatterns = \[\n)'
            replacement = rf'\1{new_line}'
        else:
            pattern = r'(\n\])'
            replacement = rf'{new_line}\1'

        new_content = re.sub(pattern, replacement, content)

        if new_content == content:
            return Result(
                success=False,
                message=f"Could not add URL include for {urls_module}",
            )

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would add URL include: {urls_module}",
                files_changed=[urls_path],
            )

        urls_path.write_text(new_content)
        return Result(
            success=True,
            message=f"Added URL include: {urls_module}",
            files_changed=[urls_path],
        )

    def add_url_pattern(
        self,
        path_str: str,
        view: str,
        name: str | None = None,
        urls_file: Path | None = None,
        position: str = "last",
    ) -> Result:
        """
        Add a URL pattern to a urls.py file.

        Parameters
        ----------
        path_str : str
            URL path string (e.g., 'healthcheck/').
        view : str
            View reference (e.g., 'HealthcheckView.as_view()').
        name : str | None, optional
            Optional URL name.
        urls_file : Path | None, optional
            Path to urls.py (default: root urls.py).
        position : str, optional
            'first' or 'last' in urlpatterns. Defaults to "last".

        Returns
        -------
        Result
            Result with success status.
        """
        urls_path = urls_file or self.root_urls_path
        if not urls_path.exists():
            return Result(
                success=False,
                message=f"URLs file not found: {urls_path}",
            )

        content = urls_path.read_text()

        if f'"{path_str}"' in content and view in content:
            return Result(
                success=True,
                message=f"URL pattern for '{path_str}' already exists",
            )

        if name:
            new_line = f'    path("{path_str}", {view}, name="{name}"),\n'
        else:
            new_line = f'    path("{path_str}", {view}),\n'

        if position == "first":
            pattern = r'(urlpatterns\s*=\s*\[\n)'
            replacement = rf'\1{new_line}'
        else:
            pattern = r'(\n\])'
            replacement = rf'{new_line}\1'

        new_content = re.sub(pattern, replacement, content)

        if new_content == content:
            return Result(
                success=False,
                message=f"Could not add URL pattern for '{path_str}'",
            )

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would add URL pattern: {path_str}",
                files_changed=[urls_path],
            )

        urls_path.write_text(new_content)
        return Result(
            success=True,
            message=f"Added URL pattern: {path_str}",
            files_changed=[urls_path],
        )

    def remove_url_pattern(
        self,
        pattern_regex: str,
        urls_file: Path | None = None,
    ) -> Result:
        """
        Remove a URL pattern from a urls.py file.

        Parameters
        ----------
        pattern_regex : str
            Regex to match the path() line to remove.
        urls_file : Path | None, optional
            Path to urls.py (default: root urls.py).

        Returns
        -------
        Result
            Result with success status.
        """
        urls_path = urls_file or self.root_urls_path
        if not urls_path.exists():
            return Result(
                success=False,
                message=f"URLs file not found: {urls_path}",
            )

        content = urls_path.read_text()
        new_content = re.sub(pattern_regex, "", content)
        new_content = re.sub(r'\n{3,}', '\n\n', new_content)

        if new_content == content:
            return Result(
                success=True,
                message="No matching URL pattern found to remove",
            )

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would remove URL pattern from {urls_path}",
                files_changed=[urls_path],
            )

        urls_path.write_text(new_content)
        return Result(
            success=True,
            message=f"Removed URL pattern from {urls_path}",
            files_changed=[urls_path],
        )

    def remove_url_pattern_by_view(
        self,
        view_name: str,
        urls_file: Path | None = None,
    ) -> Result:
        """
        Remove a URL pattern by view name from a urls.py file.

        Parameters
        ----------
        view_name : str
            Name of the view class/function to remove.
        urls_file : Path | None, optional
            Path to urls.py (default: root urls.py).

        Returns
        -------
        Result
            Result with success status.
        """
        urls_path = urls_file or self.root_urls_path
        if not urls_path.exists():
            return Result(
                success=False,
                message=f"URLs file not found: {urls_path}",
            )

        content = urls_path.read_text()

        pattern = rf'^\s*path\([^)]*{re.escape(view_name)}[^)]*\),?\s*\n'
        new_content = re.sub(pattern, '', content, flags=re.MULTILINE)
        new_content = re.sub(r'\n{3,}', '\n\n', new_content)

        if new_content == content:
            return Result(
                success=True,
                message=f"No URL pattern found for view: {view_name}",
            )

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would remove URL pattern for view: {view_name}",
                files_changed=[urls_path],
            )

        urls_path.write_text(new_content)
        return Result(
            success=True,
            message=f"Removed URL pattern for view: {view_name}",
            files_changed=[urls_path],
        )

    def _discover_url_files(
        self,
        urls_file: Path,
        visited: set[Path] | None = None,
    ) -> list[Path]:
        """
        Recursively discover all urls.py files by following include() calls.

        Parameters
        ----------
        urls_file : Path
            Starting urls.py file.
        visited : set[Path] | None, optional
            Set of already visited files (to prevent cycles).

        Returns
        -------
        list[Path]
            List of all discovered urls.py file paths.
        """
        if visited is None:
            visited = set()

        if not urls_file.exists() or urls_file in visited:
            return []

        visited.add(urls_file)
        result = [urls_file]

        content = urls_file.read_text()

        for match in re.finditer(r'include\(["\']([^"\']+)["\']\)', content):
            module_path = match.group(1)
            file_path = self.django_root / module_path.replace('.', '/').replace('/urls', '/urls.py')
            if not file_path.suffix:
                file_path = file_path.with_suffix('.py')
            result.extend(self._discover_url_files(file_path, visited))

        return result

    def find_url_pattern(
        self,
        view_name: str | None = None,
        path_str: str | None = None,
        url_name: str | None = None,
        urls_file: Path | None = None,
    ) -> tuple[str, Path] | None:
        """
        Find a URL pattern line in urls.py file(s).

        If urls_file is not provided, recursively searches all URL files
        by following include() calls.

        Parameters
        ----------
        view_name : str | None, optional
            View class/function name to search for.
        path_str : str | None, optional
            URL path string to search for.
        url_name : str | None, optional
            URL name to search for.
        urls_file : Path | None, optional
            Specific urls.py to search (default: search all).

        Returns
        -------
        tuple[str, Path] | None
            Tuple of (matching_line, file_path) if found, None otherwise.
        """
        if urls_file:
            files_to_search = [urls_file] if urls_file.exists() else []
        else:
            files_to_search = self._discover_url_files(self.root_urls_path)

        for file_path in files_to_search:
            content = file_path.read_text()

            for line in content.splitlines():
                if 'path(' not in line:
                    continue
                if view_name and view_name in line:
                    return (line, file_path)
                if path_str and f'"{path_str}"' in line:
                    return (line, file_path)
                if url_name and f'name="{url_name}"' in line:
                    return (line, file_path)

        return None

    def find_all_url_files(self) -> list[Path]:
        """
        Find all urls.py files in the project by following include() calls.

        Returns
        -------
        list[Path]
            List of all urls.py file paths.
        """
        return self._discover_url_files(self.root_urls_path)

    def move_url_pattern(
        self,
        view_name: str,
        source_urls: Path,
        dest_urls: Path,
    ) -> Result:
        """
        Move a URL pattern from one urls.py to another.

        This will:
        1. Find the URL pattern in the source file
        2. Find the import statement for the view in the source file
        3. Add the URL pattern to the destination file
        4. Move the view import from source to destination
        5. Remove the URL pattern from the source file

        Parameters
        ----------
        view_name : str
            Name of the view class/function.
        source_urls : Path
            Source urls.py path.
        dest_urls : Path
            Destination urls.py path.

        Returns
        -------
        Result
            Result with success status.
        """
        if not source_urls.exists():
            return Result(
                success=False,
                message=f"Source URLs file not found: {source_urls}",
            )

        if not dest_urls.exists():
            return Result(
                success=False,
                message=f"Destination URLs file not found: {dest_urls}",
            )

        source_content = source_urls.read_text()

        pattern_match = None
        for line in source_content.splitlines():
            if 'path(' in line and view_name in line:
                pattern_match = line.strip()
                break

        if not pattern_match:
            return Result(
                success=False,
                message=f"URL pattern for {view_name} not found in {source_urls}",
            )

        view_import = None
        for line in source_content.splitlines():
            if ('import' in line and view_name in line and
                    not line.strip().startswith('#')):
                view_import = line.strip()
                break

        path_match = re.search(r'path\("([^"]*)"', pattern_match)
        name_match = re.search(r'name="([^"]*)"', pattern_match)

        if not path_match:
            return Result(
                success=False,
                message=f"Could not parse URL pattern: {pattern_match}",
            )

        path_str = path_match.group(1)
        url_name = name_match.group(1) if name_match else None

        view_match = re.search(rf'path\("[^"]*",\s*([^,)]+(?:\([^)]*\))?)', pattern_match)
        view_call = view_match.group(1).strip() if view_match else view_name

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would move URL pattern '{path_str}' from {source_urls.name} to {dest_urls.name}",
                files_changed=[source_urls, dest_urls],
            )

        dest_content = dest_urls.read_text()

        if url_name:
            new_line = f'    path("{path_str}", {view_call}, name="{url_name}"),\n'
        else:
            new_line = f'    path("{path_str}", {view_call}),\n'

        if f'"{path_str}"' not in dest_content:
            dest_content = re.sub(r'(\n\])', rf'{new_line}\1', dest_content)
            dest_urls.write_text(dest_content)

        if view_import and view_name not in dest_urls.read_text():
            self.project.add_import_to_file(dest_urls, view_import)

        self.remove_url_pattern_by_view(view_name, urls_file=source_urls)

        if view_import:
            self.project.remove_import_from_file(
                source_urls,
                rf".*{re.escape(view_name)}.*"
            )

        return Result(
            success=True,
            message=f"Moved URL pattern '{path_str}' from {source_urls.name} to {dest_urls.name}",
            files_changed=[source_urls, dest_urls],
        )
