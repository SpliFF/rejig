"""Main Rejig class - entry point for code refactoring operations."""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst

from rejig.result import FindResult, Match, RefactorResult

if TYPE_CHECKING:
    from rejig.scope import ClassScope, FunctionScope
    from rejig.targets import (
        ClassTarget,
        FileTarget,
        FunctionTarget,
        IniTarget,
        JsonTarget,
        ModuleTarget,
        PackageTarget,
        TextFileTarget,
        TomlTarget,
        YamlTarget,
    )
    from rejig.targets.base import TargetList
    from rejig.targets.python.todo import TodoTargetList


class Rejig:
    """
    Main entry point for code refactoring operations.

    Initialize with a path pattern to define the scope of files to work with.
    All refactoring operations will be applied to files matching this pattern.

    Parameters
    ----------
    path : str | Path
        A directory path, file path, or glob pattern defining the files to work with.
        - Directory: All .py files under this directory (recursive)
        - File: Just this single file
        - Glob pattern: All files matching the pattern (e.g., "src/**/*.py")
    dry_run : bool, optional
        If True, all operations will report what they would do without making
        actual changes. Defaults to False.

    Attributes
    ----------
    files : list[Path]
        List of Python files that match the path pattern.
    dry_run : bool
        Whether operations are in dry-run mode.

    Examples
    --------
    >>> # Work with all Python files in a directory
    >>> rj = Rejig("src/myproject/")
    >>>
    >>> # Work with specific files using glob
    >>> rj = Rejig("src/**/*_views.py")
    >>>
    >>> # Preview changes without modifying files
    >>> rj = Rejig("src/", dry_run=True)
    >>> result = rj.find_class("MyClass").add_attribute("x", "int", "0")
    >>> print(result.message)  # [DRY RUN] Would add attribute...
    """

    def __init__(self, path: str | Path, dry_run: bool = False):
        self.path = Path(path) if isinstance(path, str) else path
        self.dry_run = dry_run
        self._files: list[Path] | None = None
        self._rope_project = None
        self._root_path: Path | None = None

    @property
    def root(self) -> Path:
        """
        Root path for all operations.

        This is the resolved directory path used as the base for relative path operations.
        """
        if self._root_path is None:
            if self.path.is_file():
                self._root_path = self.path.parent.resolve()
            elif self.path.is_dir():
                self._root_path = self.path.resolve()
            else:
                # Glob pattern - use the base directory
                path_str = str(self.path)
                base = path_str.split("*")[0].rsplit("/", 1)[0] or "."
                self._root_path = Path(base).resolve()
        return self._root_path

    @property
    def root_path(self) -> Path:
        """Alias for root (for backwards compatibility)."""
        return self.root

    def _resolve_path(self, path: str | Path) -> Path:
        """Resolve a path relative to root, or return absolute paths unchanged."""
        p = Path(path)
        if p.is_absolute():
            return p
        return self.root / p

    @property
    def rope_project(self):
        """
        Lazily initialize rope project for move operations.

        Raises
        ------
        ImportError
            If rope is not installed.
        """
        if self._rope_project is None:
            try:
                from rope.base.project import Project as RopeProject
                self._rope_project = RopeProject(str(self.root_path))
            except ImportError:
                raise ImportError(
                    "rope is required for move operations. "
                    "Install it with: pip install rejig[rope]"
                )
        return self._rope_project

    def close(self) -> None:
        """
        Close the rope project and clean up .ropeproject directory.

        Always call this when finished with move operations to ensure
        proper cleanup.
        """
        if self._rope_project is not None:
            self._rope_project.close()
            self._rope_project = None

        # Remove .ropeproject directory created by rope
        rope_dir = self.root_path / ".ropeproject"
        if rope_dir.exists():
            shutil.rmtree(rope_dir)

    def __enter__(self):
        """Context manager support."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up on context exit."""
        self.close()
        return False

    @property
    def files(self) -> list[Path]:
        """
        List of Python files in the working set.

        Lazily computed on first access.
        """
        if self._files is None:
            self._files = self._discover_files()
        return self._files

    def _discover_files(self) -> list[Path]:
        """Discover all Python files matching the path pattern."""
        if self.path.is_file():
            return [self.path.resolve()]
        elif self.path.is_dir():
            return sorted(self.path.resolve().rglob("*.py"))
        else:
            # Treat as glob pattern
            # If path contains glob characters, use it directly
            path_str = str(self.path)
            if "*" in path_str or "?" in path_str or "[" in path_str:
                base_path = Path(path_str.split("*")[0].rsplit("/", 1)[0] or ".")
                pattern = path_str[len(str(base_path)) :].lstrip("/")
                return sorted(base_path.resolve().glob(pattern))
            # Otherwise, treat as directory that doesn't exist yet
            return []

    # =========================================================================
    # Target Factory Methods
    # =========================================================================
    # These methods create Target objects from the new unified target system.
    # They provide a fluent API for working with code elements.

    def file(self, path: str | Path) -> FileTarget:
        """
        Get a FileTarget for a Python file.

        Parameters
        ----------
        path : str | Path
            Path to the Python file (relative to root or absolute).

        Returns
        -------
        FileTarget
            A target for performing operations on the file.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> file_target = rj.file("mymodule.py")
        >>> file_target.find_class("MyClass").add_method("process")
        """
        from rejig.targets.python.file import FileTarget

        resolved = self._resolve_path(path)
        return FileTarget(self, resolved)

    def module(self, dotted_path: str) -> ModuleTarget:
        """
        Get a ModuleTarget for a Python module by its dotted path.

        Parameters
        ----------
        dotted_path : str
            Dotted module path (e.g., "myapp.models", "myapp.utils.helpers").

        Returns
        -------
        ModuleTarget
            A target for performing operations on the module.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> module = rj.module("myapp.models")
        >>> module.find_class("User").add_method("save")
        """
        from rejig.targets.python.module import ModuleTarget

        return ModuleTarget(self, dotted_path)

    def package(self, path: str | Path) -> PackageTarget:
        """
        Get a PackageTarget for a Python package (directory with __init__.py).

        Parameters
        ----------
        path : str | Path
            Path to the package directory (relative to root or absolute).

        Returns
        -------
        PackageTarget
            A target for performing operations on the package.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> pkg = rj.package("myapp/models")
        >>> pkg.find_classes()  # Find all classes in the package
        """
        from rejig.targets.python.package import PackageTarget

        resolved = self._resolve_path(path)
        return PackageTarget(self, resolved)

    def text_file(self, path: str | Path) -> TextFileTarget:
        """
        Get a TextFileTarget for any text file.

        Parameters
        ----------
        path : str | Path
            Path to the text file (relative to root or absolute).

        Returns
        -------
        TextFileTarget
            A target for performing operations on the text file.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> readme = rj.text_file("README.md")
        >>> readme.replace("old-version", "new-version")
        """
        from rejig.targets.text.text_file import TextFileTarget

        resolved = self._resolve_path(path)
        return TextFileTarget(self, resolved)

    def toml(self, path: str | Path) -> TomlTarget:
        """
        Get a TomlTarget for a TOML file.

        Parameters
        ----------
        path : str | Path
            Path to the TOML file (relative to root or absolute).

        Returns
        -------
        TomlTarget
            A target for performing operations on the TOML file.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> toml = rj.toml("pyproject.toml")
        >>> toml.set("project.version", "2.0.0")
        """
        from rejig.targets.config.toml import TomlTarget

        resolved = self._resolve_path(path)
        return TomlTarget(self, resolved)

    def yaml(self, path: str | Path) -> YamlTarget:
        """
        Get a YamlTarget for a YAML file.

        Parameters
        ----------
        path : str | Path
            Path to the YAML file (relative to root or absolute).

        Returns
        -------
        YamlTarget
            A target for performing operations on the YAML file.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> yaml = rj.yaml("config.yaml")
        >>> yaml.set("database.host", "localhost")
        """
        from rejig.targets.config.yaml import YamlTarget

        resolved = self._resolve_path(path)
        return YamlTarget(self, resolved)

    def json(self, path: str | Path) -> JsonTarget:
        """
        Get a JsonTarget for a JSON file.

        Parameters
        ----------
        path : str | Path
            Path to the JSON file (relative to root or absolute).

        Returns
        -------
        JsonTarget
            A target for performing operations on the JSON file.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> json = rj.json("package.json")
        >>> json.set("version", "1.0.0")
        """
        from rejig.targets.config.json import JsonTarget

        resolved = self._resolve_path(path)
        return JsonTarget(self, resolved)

    def ini(self, path: str | Path) -> IniTarget:
        """
        Get an IniTarget for an INI/CFG file.

        Parameters
        ----------
        path : str | Path
            Path to the INI file (relative to root or absolute).

        Returns
        -------
        IniTarget
            A target for performing operations on the INI file.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> ini = rj.ini("setup.cfg")
        >>> ini.set("metadata", "version", "1.0.0")
        """
        from rejig.targets.config.ini import IniTarget

        resolved = self._resolve_path(path)
        return IniTarget(self, resolved)

    # =========================================================================
    # Target-based Find Methods
    # =========================================================================
    # These methods return TargetList objects for batch operations.

    def find_files_as_targets(self, glob: str = "**/*.py") -> TargetList[FileTarget]:
        """
        Find files matching a glob pattern, returning as TargetList.

        Parameters
        ----------
        glob : str
            Glob pattern for matching files. Default: "**/*.py"

        Returns
        -------
        TargetList[FileTarget]
            List of matching FileTarget objects.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> files = rj.find_files_as_targets("**/*_test.py")
        """
        from rejig.targets.base import TargetList
        from rejig.targets.python.file import FileTarget

        targets = [FileTarget(self, p) for p in self.root.glob(glob) if p.is_file()]
        return TargetList(self, targets)

    def find_classes_as_targets(self, pattern: str | None = None) -> TargetList[ClassTarget]:
        """
        Find all classes, returning as TargetList of ClassTarget.

        Parameters
        ----------
        pattern : str | None
            Optional regex pattern to filter class names.

        Returns
        -------
        TargetList[ClassTarget]
            List of matching ClassTarget objects.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> test_classes = rj.find_classes_as_targets(pattern="^Test")
        >>> test_classes.add_decorator("pytest.mark.slow")
        """
        from rejig.targets.base import TargetList
        from rejig.targets.python.class_ import ClassTarget

        targets: list[ClassTarget] = []
        regex = re.compile(pattern) if pattern else None

        for file_path in self.files:
            try:
                content = file_path.read_text()
                tree = cst.parse_module(content)

                for node in tree.body:
                    if isinstance(node, cst.ClassDef):
                        name = node.name.value
                        if regex is None or regex.search(name):
                            targets.append(ClassTarget(self, name, file_path=file_path))
            except Exception:
                continue

        return TargetList(self, targets)

    def find_functions_as_targets(self, pattern: str | None = None) -> TargetList[FunctionTarget]:
        """
        Find all module-level functions, returning as TargetList of FunctionTarget.

        Parameters
        ----------
        pattern : str | None
            Optional regex pattern to filter function names.

        Returns
        -------
        TargetList[FunctionTarget]
            List of matching FunctionTarget objects.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> functions = rj.find_functions_as_targets(pattern="^test_")
        """
        from rejig.targets.base import TargetList
        from rejig.targets.python.function import FunctionTarget

        targets: list[FunctionTarget] = []
        regex = re.compile(pattern) if pattern else None

        for file_path in self.files:
            try:
                content = file_path.read_text()
                tree = cst.parse_module(content)

                for node in tree.body:
                    if isinstance(node, cst.FunctionDef):
                        name = node.name.value
                        if regex is None or regex.search(name):
                            targets.append(FunctionTarget(self, name, file_path=file_path))
            except Exception:
                continue

        return TargetList(self, targets)

    # =========================================================================
    # Scope-based Methods (original API)
    # =========================================================================

    def find_class(self, class_name: str) -> ClassScope:
        """
        Find a class by name across all files in the working set.

        Returns a ClassScope object that can be used to perform operations
        on the found class or to further narrow the scope to methods.

        Parameters
        ----------
        class_name : str
            Name of the class to find.

        Returns
        -------
        ClassScope
            A scope object for performing operations on the matched class.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> class_scope = rj.find_class("MyClass")
        >>> class_scope.add_attribute("count", "int", "0")
        """
        from rejig.scope import ClassScope

        return ClassScope(
            Rejig=self,
            class_name=class_name,
        )

    def find_function(self, function_name: str) -> FunctionScope:
        """
        Find a module-level function by name across all files.

        Returns a FunctionScope object that can be used to perform operations
        on the found function.

        Parameters
        ----------
        function_name : str
            Name of the function to find.

        Returns
        -------
        FunctionScope
            A scope object for performing operations on the matched function.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> func_scope = rj.find_function("process_data")
        >>> func_scope.add_parameter("timeout", "int", "30")
        """
        from rejig.scope import FunctionScope

        return FunctionScope(
            Rejig=self,
            function_name=function_name,
        )

    def find_classes(self, pattern: str | None = None) -> FindResult:
        """
        Find all classes in the working set, optionally filtered by pattern.

        Parameters
        ----------
        pattern : str | None
            Optional regex pattern to filter class names.

        Returns
        -------
        FindResult
            Result containing all matching classes.
        """
        matches: list[Match] = []
        regex = re.compile(pattern) if pattern else None

        for file_path in self.files:
            try:
                content = file_path.read_text()
                tree = cst.parse_module(content)

                for node in tree.body:
                    if isinstance(node, cst.ClassDef):
                        name = node.name.value
                        if regex is None or regex.search(name):
                            # Get line number
                            pos = tree.code_for_node(node)
                            line_num = content[: content.find(pos)].count("\n") + 1
                            matches.append(Match(file_path, name, line_num))
            except Exception:
                continue

        return FindResult(matches)

    def find_functions(self, pattern: str | None = None) -> FindResult:
        """
        Find all module-level functions in the working set.

        Parameters
        ----------
        pattern : str | None
            Optional regex pattern to filter function names.

        Returns
        -------
        FindResult
            Result containing all matching functions.
        """
        matches: list[Match] = []
        regex = re.compile(pattern) if pattern else None

        for file_path in self.files:
            try:
                content = file_path.read_text()
                tree = cst.parse_module(content)

                for node in tree.body:
                    if isinstance(node, cst.FunctionDef):
                        name = node.name.value
                        if regex is None or regex.search(name):
                            pos = tree.code_for_node(node)
                            line_num = content[: content.find(pos)].count("\n") + 1
                            matches.append(Match(file_path, name, line_num))
            except Exception:
                continue

        return FindResult(matches)

    def search(self, pattern: str) -> FindResult:
        """
        Search for a regex pattern across all files.

        Parameters
        ----------
        pattern : str
            Regex pattern to search for.

        Returns
        -------
        FindResult
            Result containing all matches.
        """
        matches: list[Match] = []
        regex = re.compile(pattern)

        for file_path in self.files:
            try:
                content = file_path.read_text()
                for i, line in enumerate(content.splitlines(), 1):
                    match = regex.search(line)
                    if match:
                        matches.append(Match(file_path, match.group(0), i))
            except Exception:
                continue

        return FindResult(matches)

    def transform_file(
        self,
        file_path: Path,
        transformer: cst.CSTTransformer,
    ) -> RefactorResult:
        """
        Apply a LibCST transformer to a file.

        This is a low-level method for applying custom transformations.

        Parameters
        ----------
        file_path : Path
            Path to the file to transform.
        transformer : cst.CSTTransformer
            LibCST transformer instance to apply.

        Returns
        -------
        RefactorResult
            Result of the transformation.
        """
        if not file_path.exists():
            return RefactorResult(
                success=False,
                message=f"File not found: {file_path}",
            )

        content = file_path.read_text()
        try:
            tree = cst.parse_module(content)
            new_tree = tree.visit(transformer)
            new_content = new_tree.code

            if new_content == content:
                return RefactorResult(
                    success=True,
                    message=f"No changes needed in {file_path}",
                )

            if self.dry_run:
                return RefactorResult(
                    success=True,
                    message=f"[DRY RUN] Would transform {file_path}",
                    files_changed=[file_path],
                )

            file_path.write_text(new_content)
            return RefactorResult(
                success=True,
                message=f"Transformed {file_path}",
                files_changed=[file_path],
            )

        except Exception as e:
            return RefactorResult(
                success=False,
                message=f"Transformation failed: {e}",
            )

    def add_import(
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
            Result of the operation.
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

        # Find the last import line and insert after it
        lines = content.splitlines(keepends=True)
        last_import_idx = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")) and not stripped.startswith("from __future__"):
                last_import_idx = i

        if last_import_idx >= 0:
            lines.insert(last_import_idx + 1, import_statement + "\n")
        else:
            # No imports found, add at the beginning (after any module docstring)
            insert_idx = 0
            if lines and lines[0].strip().startswith(('"""', "'''")):
                # Skip past docstring
                for i, line in enumerate(lines):
                    if i > 0 and (line.strip().endswith('"""') or line.strip().endswith("'''")):
                        insert_idx = i + 1
                        break
            lines.insert(insert_idx, import_statement + "\n")

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

    def remove_import(
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
            Result of the operation.
        """
        if not file_path.exists():
            return RefactorResult(
                success=False,
                message=f"File not found: {file_path}",
            )

        content = file_path.read_text()
        new_content = re.sub(rf"^{import_pattern}\n", "", content, flags=re.MULTILINE)

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

    # -------------------------------------------------------------------------
    # Rope-based Move Operations
    # -------------------------------------------------------------------------

    def _get_class_offset(self, file_path: Path, class_name: str) -> int | None:
        """Get the character offset of a class name in a class definition."""
        content = file_path.read_text()
        match = re.search(rf'\bclass\s+({class_name})\b', content)
        return match.start(1) if match else None

    def _get_function_offset(self, file_path: Path, function_name: str) -> int | None:
        """Get the character offset of a function name in a function definition."""
        content = file_path.read_text()
        match = re.search(rf'\bdef\s+({function_name})\b', content)
        return match.start(1) if match else None

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

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> result = rj.move_class(Path("src/old.py"), "MyClass", "new_module")
        >>> rj.close()  # Always close after move operations
        """
        from rope.refactor.move import create_move

        offset = self._get_class_offset(source_file, class_name)
        if offset is None:
            return RefactorResult(
                success=False,
                message=f"Could not find class {class_name} in {source_file}",
            )

        try:
            relative_path = source_file.relative_to(self.root_path)
            resource = self.rope_project.get_resource(str(relative_path))

            mover = create_move(self.rope_project, resource, offset)
            changes = mover.get_changes(dest_module)

            changed_files = [
                Path(self.root_path / change.path)
                for change in changes.get_changed_resources()
            ]

            if self.dry_run:
                return RefactorResult(
                    success=True,
                    message=f"[DRY RUN] Would move {class_name} to {dest_module}",
                    files_changed=changed_files,
                )

            self.rope_project.do(changes)
            return RefactorResult(
                success=True,
                message=f"Moved {class_name} to {dest_module}",
                files_changed=changed_files,
            )

        except Exception as e:
            return RefactorResult(
                success=False,
                message=f"Error moving {class_name}: {e}",
            )

    def move_function(
        self,
        source_file: Path,
        function_name: str,
        dest_module: str,
    ) -> RefactorResult:
        """
        Move a function from source file to destination module using rope.

        Rope automatically updates all imports throughout the project.

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

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> result = rj.move_function(Path("src/utils.py"), "helper", "new_utils")
        >>> rj.close()
        """
        from rope.refactor.move import create_move

        offset = self._get_function_offset(source_file, function_name)
        if offset is None:
            return RefactorResult(
                success=False,
                message=f"Could not find function {function_name} in {source_file}",
            )

        try:
            relative_path = source_file.relative_to(self.root_path)
            resource = self.rope_project.get_resource(str(relative_path))

            mover = create_move(self.rope_project, resource, offset)
            changes = mover.get_changes(dest_module)

            changed_files = [
                Path(self.root_path / change.path)
                for change in changes.get_changed_resources()
            ]

            if self.dry_run:
                return RefactorResult(
                    success=True,
                    message=f"[DRY RUN] Would move {function_name} to {dest_module}",
                    files_changed=changed_files,
                )

            self.rope_project.do(changes)
            return RefactorResult(
                success=True,
                message=f"Moved {function_name} to {dest_module}",
                files_changed=changed_files,
            )

        except Exception as e:
            return RefactorResult(
                success=False,
                message=f"Error moving {function_name}: {e}",
            )

    # -------------------------------------------------------------------------
    # TODO Comment Operations
    # -------------------------------------------------------------------------

    def find_todos(self) -> TodoTargetList:
        """
        Find all TODO/FIXME/XXX/HACK/NOTE/BUG comments in the codebase.

        Returns a TodoTargetList with filtering capabilities and batch operations.

        Returns
        -------
        TodoTargetList
            All TODO comments found in the working set.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> todos = rj.find_todos()
        >>> print(f"Found {len(todos)} TODOs")
        >>>
        >>> # Filter by type
        >>> fixmes = todos.by_type("FIXME")
        >>>
        >>> # Filter to high priority
        >>> urgent = todos.high_priority()
        >>>
        >>> # Find unlinked TODOs
        >>> unlinked = todos.without_issues()
        >>>
        >>> # Operations on individual TODOs
        >>> for todo in unlinked:
        ...     todo.link_to_issue("#123")
        """
        from rejig.todos.finder import TodoFinder

        finder = TodoFinder(self)
        return finder.find_all()
