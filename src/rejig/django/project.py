"""
Django project class for refactoring operations.

This module provides the main DjangoProject class that combines all
Django-specific refactoring capabilities.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from ..core import Manipylate
from ..result import RefactorResult
from .dependencies import DependencyManager
from .settings import SettingsManager
from .urls import UrlManager


class DjangoProject:
    """
    Represents a Django project for refactoring operations.

    This is the main entry point for Django-specific refactoring operations.
    Initialize with the path to your project root directory and optionally
    enable dry-run mode to preview changes without modifying files.

    Parameters
    ----------
    project_root : Path | str
        Path to the project root directory (parent of django-root).
    dry_run : bool, optional
        If True, all operations will report what they would do without making
        actual changes. Defaults to False.
    django_root_name : str, optional
        Name of the Django root directory. Defaults to "django-root".

    Attributes
    ----------
    project_root : Path
        Resolved absolute path to the project root directory.
    django_root : Path
        Path to the django-root subdirectory.
    dry_run : bool
        Whether operations are in dry-run mode.

    Raises
    ------
    ValueError
        If project_root or django_root directory does not exist.

    Examples
    --------
    >>> project = DjangoProject("/path/to/myproject")
    >>> project.find_app_containing_class("MyView")
    'myapp'

    >>> # Preview changes without modifying files
    >>> project = DjangoProject("/path/to/myproject", dry_run=True)
    >>> result = project.add_installed_app("newapp")
    >>> print(result.message)
    [DRY RUN] Would add newapp to INSTALLED_APPS

    Notes
    -----
    When using rope-based operations (move_class, move_function), always call
    close() when finished to ensure all changes are written and cleanup is done.
    """

    def __init__(
        self,
        project_root: Path | str,
        dry_run: bool = False,
        django_root_name: str = "django-root",
    ):
        self.project_root = Path(project_root).resolve()
        self.django_root = self.project_root / django_root_name
        self.dry_run = dry_run
        self._rope_project = None

        if not self.project_root.exists():
            raise ValueError(f"Project root directory not found: {self.project_root}")
        if not self.django_root.exists():
            raise ValueError(f"Django root directory not found: {self.django_root}")

        # Initialize sub-managers
        self._settings = SettingsManager(self)
        self._urls = UrlManager(self)
        self._dependencies = DependencyManager(self)

        # Create internal Manipylate instance for rope operations
        self._manipylate = Manipylate(self.django_root, dry_run=dry_run)

    @property
    def settings_path(self) -> Path:
        """Path to the base settings file."""
        return self.django_root / "django_site" / "settings" / "base.py"

    @property
    def root_urls_path(self) -> Path:
        """Path to the root urls.py file."""
        return self.django_root / "django_site" / "urls.py"

    @property
    def pyproject_path(self) -> Path:
        """Path to the pyproject.toml file."""
        return self.project_root / "pyproject.toml"

    @property
    def rope_project(self):
        """Lazily initialize rope project."""
        if self._rope_project is None:
            try:
                from rope.base.project import Project as RopeProject
                self._rope_project = RopeProject(str(self.django_root))
            except ImportError:
                raise ImportError(
                    "rope is required for move operations. "
                    "Install it with: pip install rejig[rope]"
                )
        return self._rope_project

    def close(self) -> None:
        """Close the rope project and clean up .ropeproject directory."""
        # Close the internal Manipylate instance (handles rope cleanup)
        self._manipylate.close()

        # Also close legacy rope project if it was used directly
        if self._rope_project is not None:
            self._rope_project.close()
            self._rope_project = None

        # Remove .ropeproject directory created by rope
        rope_dir = self.django_root / ".ropeproject"
        if rope_dir.exists():
            shutil.rmtree(rope_dir)

    def __enter__(self):
        """Context manager support."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up on context exit."""
        self.close()
        return False

    def get_app_path(self, app_name: str) -> Path:
        """Get the path to a Django app directory."""
        return self.django_root / app_name

    def app_exists(self, app_name: str) -> bool:
        """Check if a Django app exists."""
        return (self.get_app_path(app_name) / "__init__.py").exists()

    # -------------------------------------------------------------------------
    # App Discovery Methods
    # -------------------------------------------------------------------------

    def find_app_containing_class(
        self,
        class_name: str,
        filename: str = "views.py",
        exclude_apps: list[str] | None = None,
    ) -> str | None:
        """
        Find the Django app that contains a specific class.

        Parameters
        ----------
        class_name : str
            Name of the class to find.
        filename : str, optional
            Name of the file to search in. Defaults to "views.py".
        exclude_apps : list[str] | None, optional
            List of app names to skip during search.

        Returns
        -------
        str | None
            App name if found, None otherwise.
        """
        exclude = set(exclude_apps or [])
        pattern = rf"\bclass\s+{class_name}\b"
        for filepath in self.django_root.glob(f"*/{filename}"):
            app_name = filepath.parent.name
            if app_name in exclude:
                continue
            content = filepath.read_text()
            if re.search(pattern, content):
                return app_name
        return None

    def find_app_containing_pattern(
        self,
        pattern: str,
        filename: str = "*.py",
        exclude_apps: list[str] | None = None,
    ) -> str | None:
        """
        Find the Django app that contains a specific pattern.

        Parameters
        ----------
        pattern : str
            Regex pattern to search for.
        filename : str, optional
            Glob pattern for files to search. Defaults to "*.py".
        exclude_apps : list[str] | None, optional
            List of app names to skip during search.

        Returns
        -------
        str | None
            App name if found, None otherwise.
        """
        exclude = set(exclude_apps or [])
        for filepath in self.django_root.glob(f"*/{filename}"):
            app_name = filepath.parent.name
            if app_name in exclude:
                continue
            content = filepath.read_text()
            if re.search(pattern, content):
                return app_name
        return None

    def find_file_containing_class(
        self,
        class_name: str,
        glob_pattern: str = "*/*.py",
        exclude_apps: list[str] | None = None,
    ) -> Path | None:
        """
        Find the file that contains a specific class.

        Parameters
        ----------
        class_name : str
            Name of the class to find.
        glob_pattern : str, optional
            Glob pattern for files to search.
        exclude_apps : list[str] | None, optional
            List of app names to skip during search.

        Returns
        -------
        Path | None
            Path to file if found, None otherwise.
        """
        exclude = set(exclude_apps or [])
        pattern = rf"\bclass\s+{class_name}\b"
        for filepath in self.django_root.glob(glob_pattern):
            try:
                rel_path = filepath.relative_to(self.django_root)
                app_name = rel_path.parts[0] if rel_path.parts else None
                if app_name in exclude:
                    continue
            except ValueError:
                pass
            content = filepath.read_text()
            if re.search(pattern, content):
                return filepath
        return None

    # -------------------------------------------------------------------------
    # App Creation Methods
    # -------------------------------------------------------------------------

    def create_app(
        self,
        app_name: str,
        files: dict[str, str] | None = None,
    ) -> RefactorResult:
        """
        Create a new Django app directory with specified files.

        Parameters
        ----------
        app_name : str
            Name of the app to create.
        files : dict[str, str] | None, optional
            Dict mapping filename to content.

        Returns
        -------
        RefactorResult
            Result with success status.
        """
        app_path = self.get_app_path(app_name)

        if self.dry_run:
            return RefactorResult(
                success=True,
                message=f"[DRY RUN] Would create app: {app_name}",
                files_changed=[app_path],
            )

        app_path.mkdir(exist_ok=True)
        created_files = [app_path]

        # Always create __init__.py
        init_file = app_path / "__init__.py"
        if not init_file.exists():
            init_file.touch()
            created_files.append(init_file)

        # Create additional files
        if files:
            for filename, content in files.items():
                filepath = app_path / filename
                filepath.write_text(content)
                created_files.append(filepath)

        return RefactorResult(
            success=True,
            message=f"Created app: {app_name}",
            files_changed=created_files,
        )

    # -------------------------------------------------------------------------
    # Rope-based Refactoring Methods (delegated to Manipylate)
    # -------------------------------------------------------------------------

    def move_class(
        self,
        source_file: Path,
        class_name: str,
        dest_module: str,
    ) -> RefactorResult:
        """
        Move a class from source file to destination module using rope.

        Rope automatically updates all imports throughout the project.

        Parameters
        ----------
        source_file : Path
            Path to the file containing the class.
        class_name : str
            Name of the class to move.
        dest_module : str
            Destination module path (e.g., 'myapp.views').

        Returns
        -------
        RefactorResult
            Result with success status.
        """
        return self._manipylate.move_class(source_file, class_name, dest_module)

    def move_function(
        self,
        source_file: Path,
        function_name: str,
        dest_module: str,
    ) -> RefactorResult:
        """
        Move a function from source file to destination module using rope.

        Parameters
        ----------
        source_file : Path
            Path to the file containing the function.
        function_name : str
            Name of the function to move.
        dest_module : str
            Destination module path.

        Returns
        -------
        RefactorResult
            Result with success status.
        """
        return self._manipylate.move_function(source_file, function_name, dest_module)

    # -------------------------------------------------------------------------
    # Settings Management (delegated to SettingsManager)
    # -------------------------------------------------------------------------

    def add_installed_app(
        self,
        app_name: str,
        after_app: str | None = None,
    ) -> RefactorResult:
        """Add an app to INSTALLED_APPS in Django settings."""
        return self._settings.add_installed_app(app_name, after_app)

    def update_middleware_path(
        self,
        old_path: str,
        new_path: str,
    ) -> RefactorResult:
        """Update a middleware path in Django settings."""
        return self._settings.update_middleware_path(old_path, new_path)

    def add_middleware(
        self,
        middleware_path: str,
        position: str = "first",
        after: str | None = None,
    ) -> RefactorResult:
        """Add a middleware to Django settings."""
        return self._settings.add_middleware(middleware_path, position, after)

    def add_setting(
        self,
        setting_name: str,
        value: str,
        comment: str | None = None,
        settings_file: Path | None = None,
    ) -> RefactorResult:
        """Add a new setting to Django settings file."""
        return self._settings.add_setting(setting_name, value, comment, settings_file)

    def update_setting(
        self,
        setting_name: str,
        new_value: str,
        comment: str | None = None,
        settings_file: Path | None = None,
    ) -> RefactorResult:
        """Update an existing setting in Django settings file."""
        return self._settings.update_setting(setting_name, new_value, comment, settings_file)

    def delete_setting(
        self,
        setting_name: str,
        delete_comment: bool = True,
        settings_file: Path | None = None,
    ) -> RefactorResult:
        """Delete a setting from Django settings file."""
        return self._settings.delete_setting(setting_name, delete_comment, settings_file)

    # -------------------------------------------------------------------------
    # URL Configuration (delegated to UrlManager)
    # -------------------------------------------------------------------------

    def add_url_include(
        self,
        urls_module: str,
        path_prefix: str = "",
        urls_file: Path | None = None,
        position: str = "first",
    ) -> RefactorResult:
        """Add an include() to a urls.py file."""
        return self._urls.add_url_include(urls_module, path_prefix, urls_file, position)

    def add_url_pattern(
        self,
        path_str: str,
        view: str,
        name: str | None = None,
        urls_file: Path | None = None,
        position: str = "last",
    ) -> RefactorResult:
        """Add a URL pattern to a urls.py file."""
        return self._urls.add_url_pattern(path_str, view, name, urls_file, position)

    def remove_url_pattern(
        self,
        pattern_regex: str,
        urls_file: Path | None = None,
    ) -> RefactorResult:
        """Remove a URL pattern from a urls.py file."""
        return self._urls.remove_url_pattern(pattern_regex, urls_file)

    def remove_url_pattern_by_view(
        self,
        view_name: str,
        urls_file: Path | None = None,
    ) -> RefactorResult:
        """Remove a URL pattern by view name from a urls.py file."""
        return self._urls.remove_url_pattern_by_view(view_name, urls_file)

    def find_url_pattern(
        self,
        view_name: str | None = None,
        path_str: str | None = None,
        url_name: str | None = None,
        urls_file: Path | None = None,
    ) -> tuple[str, Path] | None:
        """Find a URL pattern line in urls.py file(s)."""
        return self._urls.find_url_pattern(view_name, path_str, url_name, urls_file)

    def find_all_url_files(self) -> list[Path]:
        """Find all urls.py files in the project by following include() calls."""
        return self._urls.find_all_url_files()

    def move_url_pattern(
        self,
        view_name: str,
        source_urls: Path,
        dest_urls: Path,
    ) -> RefactorResult:
        """Move a URL pattern from one urls.py to another."""
        return self._urls.move_url_pattern(view_name, source_urls, dest_urls)

    # -------------------------------------------------------------------------
    # Dependency Management (delegated to DependencyManager)
    # -------------------------------------------------------------------------

    def add_dependency(
        self,
        package_name: str,
        version: str,
        extras: list[str] | None = None,
        optional: bool = False,
        section: str = "tool.poetry.dependencies",
        pyproject_file: Path | None = None,
    ) -> RefactorResult:
        """Add a new dependency to pyproject.toml."""
        return self._dependencies.add_dependency(
            package_name, version, extras, optional, section, pyproject_file
        )

    def update_dependency(
        self,
        package_name: str,
        version: str,
        extras: list[str] | None = None,
        optional: bool | None = None,
        section: str = "tool.poetry.dependencies",
        pyproject_file: Path | None = None,
    ) -> RefactorResult:
        """Update an existing dependency in pyproject.toml."""
        return self._dependencies.update_dependency(
            package_name, version, extras, optional, section, pyproject_file
        )

    def remove_dependency(
        self,
        package_name: str,
        section: str = "tool.poetry.dependencies",
        pyproject_file: Path | None = None,
    ) -> RefactorResult:
        """Remove a dependency from pyproject.toml."""
        return self._dependencies.remove_dependency(package_name, section, pyproject_file)

    # -------------------------------------------------------------------------
    # File Manipulation Methods
    # -------------------------------------------------------------------------

    def update_imports_in_file(
        self,
        file_path: Path,
        old_module: str,
        new_module: str,
    ) -> RefactorResult:
        """
        Update import statements in a file.

        Parameters
        ----------
        file_path : Path
            Path to the file to modify.
        old_module : str
            Old module path to replace.
        new_module : str
            New module path.

        Returns
        -------
        RefactorResult
            Result with success status.
        """
        if not file_path.exists():
            return RefactorResult(
                success=False,
                message=f"File not found: {file_path}",
            )

        content = file_path.read_text()

        patterns = [
            (rf'from {re.escape(old_module)} import', f'from {new_module} import'),
            (rf'import {re.escape(old_module)}', f'import {new_module}'),
        ]

        new_content = content
        for pattern, replacement in patterns:
            new_content = re.sub(pattern, replacement, new_content)

        if new_content == content:
            return RefactorResult(
                success=True,
                message=f"No imports to update in {file_path}",
            )

        if self.dry_run:
            return RefactorResult(
                success=True,
                message=f"[DRY RUN] Would update imports in {file_path}",
                files_changed=[file_path],
            )

        file_path.write_text(new_content)
        return RefactorResult(
            success=True,
            message=f"Updated imports in {file_path}",
            files_changed=[file_path],
        )

    def add_import_to_file(
        self,
        file_path: Path,
        import_statement: str,
    ) -> RefactorResult:
        """
        Add an import statement to a file.

        Parameters
        ----------
        file_path : Path
            Path to the file to modify.
        import_statement : str
            Import statement to add (without newline).

        Returns
        -------
        RefactorResult
            Result with success status.
        """
        if not file_path.exists():
            return RefactorResult(
                success=False,
                message=f"File not found: {file_path}",
            )

        content = file_path.read_text()

        if import_statement in content:
            return RefactorResult(
                success=True,
                message=f"Import already exists in {file_path}",
            )

        lines = content.splitlines(keepends=True)
        last_import_idx = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")) and not stripped.startswith("from __future__"):
                last_import_idx = i

        if last_import_idx >= 0:
            lines.insert(last_import_idx + 1, import_statement + "\n")
        else:
            lines.insert(0, import_statement + "\n")

        new_content = "".join(lines)

        if self.dry_run:
            return RefactorResult(
                success=True,
                message=f"[DRY RUN] Would add import to {file_path}",
                files_changed=[file_path],
            )

        file_path.write_text(new_content)
        return RefactorResult(
            success=True,
            message=f"Added import to {file_path}",
            files_changed=[file_path],
        )

    def remove_import_from_file(
        self,
        file_path: Path,
        import_pattern: str,
    ) -> RefactorResult:
        """
        Remove an import statement from a file.

        Parameters
        ----------
        file_path : Path
            Path to the file to modify.
        import_pattern : str
            Regex pattern to match the import line.

        Returns
        -------
        RefactorResult
            Result with success status.
        """
        if not file_path.exists():
            return RefactorResult(
                success=False,
                message=f"File not found: {file_path}",
            )

        content = file_path.read_text()
        new_content = re.sub(rf'^{import_pattern}\n', '', content, flags=re.MULTILINE)

        if new_content == content:
            return RefactorResult(
                success=True,
                message=f"No matching import found in {file_path}",
            )

        if self.dry_run:
            return RefactorResult(
                success=True,
                message=f"[DRY RUN] Would remove import from {file_path}",
                files_changed=[file_path],
            )

        file_path.write_text(new_content)
        return RefactorResult(
            success=True,
            message=f"Removed import from {file_path}",
            files_changed=[file_path],
        )
