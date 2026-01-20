"""Main Rejig class - entry point for code refactoring operations."""
from __future__ import annotations

import re
import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Generator

import libcst as cst

from rejig.core.results import Result

if TYPE_CHECKING:
    from rejig.core.transaction import Transaction
    from rejig.packaging.models import PackageConfig
    from rejig.project.targets import PyprojectTarget
    from rejig.targets import (
        ClassTarget,
        FileTarget,
        FunctionTarget,
        IniTarget,
        JsonTarget,
        LineTarget,
        ModuleTarget,
        PackageTarget,
        TextFileTarget,
        TomlTarget,
        YamlTarget,
    )
    from rejig.targets.base import TargetList
    from rejig.targets.python.todo import TodoTargetList
    from rejig.targets.text.text_block import TextBlock


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
        self._transaction: Transaction | None = None

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
    # Transaction Support
    # =========================================================================

    @property
    def in_transaction(self) -> bool:
        """Check if currently in a transaction.

        Returns
        -------
        bool
            True if a transaction is active.
        """
        return self._transaction is not None

    @property
    def current_transaction(self) -> Transaction | None:
        """Get the current active transaction.

        Returns
        -------
        Transaction | None
            The current transaction, or None if not in a transaction.
        """
        return self._transaction

    @contextmanager
    def transaction(self) -> Generator[Transaction, None, None]:
        """Start a transaction for atomic batch operations.

        All file writes within the transaction are collected and applied
        atomically on commit(). If any write fails, all changes are
        rolled back.

        Yields
        ------
        Transaction
            The transaction object for commit/rollback control.

        Raises
        ------
        RuntimeError
            If called when already in a transaction (nested transactions
            are not supported).

        Examples
        --------
        >>> with rj.transaction() as tx:
        ...     rj.find_class("Foo").rename("Bar")
        ...     rj.find_function("baz").delete()
        ...     print(tx.preview())  # See combined diff
        ...     result = tx.commit()  # Apply all atomically
        ...     # or tx.rollback()   # Discard all
        """
        from rejig.core.transaction import Transaction

        if self._transaction is not None:
            raise RuntimeError("Nested transactions are not supported")

        self._transaction = Transaction(self)
        try:
            yield self._transaction
        finally:
            # Auto-rollback if not committed
            if not self._transaction._committed and not self._transaction._rolled_back:
                self._transaction.rollback()
            self._transaction = None

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

    def text_block(self, path: str | Path) -> TextBlock:
        """
        Get a TextBlock for raw text pattern-based manipulation.

        TextBlock provides pattern-based operations (find, replace) for any
        text file without language-specific parsing. Use this when you need
        regex-based text manipulation.

        Parameters
        ----------
        path : str | Path
            Path to the text file (relative to root or absolute).

        Returns
        -------
        TextBlock
            A target for pattern-based text manipulation.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> block = rj.text_block("README.md")
        >>> block.replace_pattern(r"v\\d+\\.\\d+", "v2.0")
        >>>
        >>> # Find and operate on matches
        >>> matches = block.find_pattern(r"TODO:.*")
        >>> for match in matches:
        ...     print(f"Line {match.line_number}: {match.text}")
        """
        from rejig.targets.text.text_block import TextBlock

        resolved = self._resolve_path(path)
        return TextBlock(self, resolved)

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

    def pyproject(self, path: str | Path | None = None) -> PyprojectTarget:
        """
        Get a PyprojectTarget for pyproject.toml with section navigation.

        Parameters
        ----------
        path : str | Path | None
            Path to pyproject.toml. If None, uses "pyproject.toml" in root.

        Returns
        -------
        PyprojectTarget
            A target for performing operations on pyproject.toml sections.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> pyproject = rj.pyproject()
        >>>
        >>> # Navigate to sections
        >>> pyproject.dependencies().add("requests", ">=2.28.0")
        >>> pyproject.black().set(line_length=110)
        >>> pyproject.project().bump_version("minor")
        >>>
        >>> # Or use TomlTarget methods
        >>> pyproject.set("project.version", "2.0.0")
        """
        from rejig.project.targets import PyprojectTarget

        if path is None:
            resolved = self.root / "pyproject.toml"
        else:
            resolved = self._resolve_path(path)
        return PyprojectTarget(self, resolved)

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
    # Batch Find Methods (return TargetList)
    # =========================================================================

    def find_files(self, glob: str = "**/*.py") -> TargetList[FileTarget]:
        """
        Find files matching a glob pattern.

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
        >>> files = rj.find_files("**/*_test.py")
        >>> test_files = rj.find_files("**/test_*.py")
        """
        from rejig.targets.base import TargetList
        from rejig.targets.python.file import FileTarget

        targets = [FileTarget(self, p) for p in self.root.glob(glob) if p.is_file()]
        return TargetList(self, targets)

    def find_classes(self, pattern: str | None = None) -> TargetList[ClassTarget]:
        """
        Find all classes in the working set, optionally filtered by pattern.

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
        >>> all_classes = rj.find_classes()
        >>> test_classes = rj.find_classes(pattern="^Test")
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

    def find_functions(self, pattern: str | None = None) -> TargetList[FunctionTarget]:
        """
        Find all module-level functions in the working set.

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
        >>> all_funcs = rj.find_functions()
        >>> process_funcs = rj.find_functions(pattern="^process_")
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

    def search(self, pattern: str) -> TargetList[LineTarget]:
        """
        Search for a regex pattern across all files.

        Returns a TargetList of LineTarget objects for each matching line,
        allowing batch operations on search results.

        Parameters
        ----------
        pattern : str
            Regex pattern to search for.

        Returns
        -------
        TargetList[LineTarget]
            List of LineTarget objects for matching lines.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> matches = rj.search(r"TODO:.*")
        >>> for line in matches:
        ...     content = line.get_content()
        ...     print(f"{line.path}:{line.line_number}: {content.data}")
        """
        from rejig.targets.base import TargetList
        from rejig.targets.python.line import LineTarget

        targets: list[LineTarget] = []
        regex = re.compile(pattern)

        for file_path in self.files:
            try:
                content = file_path.read_text()
                for i, line in enumerate(content.splitlines(), 1):
                    if regex.search(line):
                        targets.append(LineTarget(self, file_path, i))
            except Exception:
                continue

        return TargetList(self, targets)

    # =========================================================================
    # Find Methods (return Targets)
    # =========================================================================

    def find_class(self, class_name: str) -> ClassTarget:
        """
        Find a class by name across all files in the working set.

        Returns a ClassTarget object that can be used to perform operations
        on the found class or to further narrow the scope to methods.

        Parameters
        ----------
        class_name : str
            Name of the class to find.

        Returns
        -------
        ClassTarget
            A target for performing operations on the matched class.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> cls = rj.find_class("MyClass")
        >>> cls.add_attribute("count", "int", "0")
        """
        from rejig.targets.python.class_ import ClassTarget

        return ClassTarget(self, class_name)

    def find_function(self, function_name: str) -> FunctionTarget:
        """
        Find a module-level function by name across all files.

        Returns a FunctionTarget object that can be used to perform operations
        on the found function.

        Parameters
        ----------
        function_name : str
            Name of the function to find.

        Returns
        -------
        FunctionTarget
            A target for performing operations on the matched function.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> func = rj.find_function("process_data")
        >>> func.add_parameter("timeout", "int", "30")
        """
        from rejig.targets.python.function import FunctionTarget

        return FunctionTarget(self, function_name)

    def transform_file(
        self,
        file_path: Path,
        transformer: cst.CSTTransformer,
    ) -> Result:
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
        Result
            Result of the transformation.
        """
        if not file_path.exists():
            return Result(
                success=False,
                message=f"File not found: {file_path}",
            )

        content = file_path.read_text()
        try:
            tree = cst.parse_module(content)
            new_tree = tree.visit(transformer)
            new_content = new_tree.code

            if new_content == content:
                return Result(
                    success=True,
                    message=f"No changes needed in {file_path}",
                )

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would transform {file_path}",
                    files_changed=[file_path],
                )

            file_path.write_text(new_content)
            return Result(
                success=True,
                message=f"Transformed {file_path}",
                files_changed=[file_path],
            )

        except Exception as e:
            return Result(
                success=False,
                message=f"Transformation failed: {e}",
            )

    def add_import(
        self,
        file_path: Path,
        import_statement: str,
    ) -> Result:
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
        Result
            Result of the operation.
        """
        if not file_path.exists():
            return Result(
                success=False,
                message=f"File not found: {file_path}",
            )

        content = file_path.read_text()

        if import_statement in content:
            return Result(
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
            return Result(
                success=True,
                message=f"[DRY RUN] Would add import to {file_path}",
                files_changed=[file_path],
            )

        file_path.write_text(new_content)
        return Result(
            success=True,
            message=f"Added import to {file_path}",
            files_changed=[file_path],
        )

    def remove_import(
        self,
        file_path: Path,
        import_pattern: str,
    ) -> Result:
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
        Result
            Result of the operation.
        """
        if not file_path.exists():
            return Result(
                success=False,
                message=f"File not found: {file_path}",
            )

        content = file_path.read_text()
        new_content = re.sub(rf"^{import_pattern}\n", "", content, flags=re.MULTILINE)

        if new_content == content:
            return Result(
                success=True,
                message=f"No matching import found in {file_path}",
            )

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would remove import from {file_path}",
                files_changed=[file_path],
            )

        file_path.write_text(new_content)
        return Result(
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
    ) -> Result:
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
        Result
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
            return Result(
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
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would move {class_name} to {dest_module}",
                    files_changed=changed_files,
                )

            self.rope_project.do(changes)
            return Result(
                success=True,
                message=f"Moved {class_name} to {dest_module}",
                files_changed=changed_files,
            )

        except Exception as e:
            return Result(
                success=False,
                message=f"Error moving {class_name}: {e}",
            )

    def move_function(
        self,
        source_file: Path,
        function_name: str,
        dest_module: str,
    ) -> Result:
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
        Result
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
            return Result(
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
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would move {function_name} to {dest_module}",
                    files_changed=changed_files,
                )

            self.rope_project.do(changes)
            return Result(
                success=True,
                message=f"Moved {function_name} to {dest_module}",
                files_changed=changed_files,
            )

        except Exception as e:
            return Result(
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

    # -------------------------------------------------------------------------
    # Package Configuration Operations
    # -------------------------------------------------------------------------

    def get_package_config(self) -> PackageConfig | None:
        """
        Detect and parse package configuration from the project root.

        Automatically detects the package format (requirements.txt, PEP 621,
        Poetry, UV) and returns a unified PackageConfig object.

        Returns
        -------
        PackageConfig | None
            Parsed package configuration, or None if not found.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> config = rj.get_package_config()
        >>> if config:
        ...     print(f"Format: {config.format}")
        ...     print(f"Dependencies: {len(config.dependencies)}")
        """
        from rejig.packaging.detector import get_package_config

        return get_package_config(self.root)

    def add_dependency(
        self,
        name: str,
        version: str | None = None,
        dev: bool = False,
        group: str | None = None,
    ) -> Result:
        """
        Add a dependency to the project's package configuration.

        Automatically detects the package format and adds the dependency
        in the appropriate format.

        Parameters
        ----------
        name : str
            Package name to add.
        version : str | None
            Version specification (e.g., ">=2.0", "^1.0").
        dev : bool
            Whether this is a development dependency.
        group : str | None
            Optional dependency group name.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> rj.add_dependency("requests", ">=2.28.0")
        >>> rj.add_dependency("pytest", ">=7.0", dev=True)
        """
        from rejig.packaging.detector import FormatDetector

        detector = FormatDetector(self)
        fmt = detector.detect(self.root)
        config_path = detector.get_config_path(self.root)

        if fmt is None or config_path is None:
            return Result(
                success=False,
                message="No package configuration found in project",
            )

        result: Result
        if fmt == "pep621":
            from rejig.packaging.pep621 import PEP621Parser
            parser = PEP621Parser(self)
            result = parser.add_dependency(
                config_path, name, version, dev=dev, group=group, dry_run=self.dry_run
            )
        elif fmt == "poetry":
            from rejig.packaging.poetry import PoetryParser
            parser = PoetryParser(self)
            result = parser.add_dependency(
                config_path, name, version, dev=dev, group=group, dry_run=self.dry_run
            )
        elif fmt == "uv":
            from rejig.packaging.uv import UVParser
            parser = UVParser(self)
            result = parser.add_dependency(
                config_path, name, version, dev=dev, group=group, dry_run=self.dry_run
            )
        elif fmt == "requirements":
            # For requirements.txt, append directly
            from rejig.packaging.models import Dependency
            dep = Dependency(name=name, version_spec=version)
            spec = dep.to_pip_spec()

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would add {spec} to {config_path}",
                    files_changed=[config_path],
                )

            try:
                content = config_path.read_text() if config_path.exists() else ""
                if spec not in content:
                    with open(config_path, "a") as f:
                        f.write(f"{spec}\n")
                return Result(
                    success=True,
                    message=f"Added {spec} to {config_path}",
                    files_changed=[config_path],
                )
            except Exception as e:
                return Result(success=False, message=f"Failed to add dependency: {e}")
        else:
            return Result(
                success=False,
                message=f"Unsupported package format: {fmt}",
            )

        return Result(
            success=result.success,
            message=result.message,
            files_changed=result.files_changed,
        )

    def remove_dependency(self, name: str) -> Result:
        """
        Remove a dependency from the project's package configuration.

        Parameters
        ----------
        name : str
            Package name to remove.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> rj.remove_dependency("requests")
        """
        from rejig.packaging.detector import FormatDetector

        detector = FormatDetector(self)
        fmt = detector.detect(self.root)
        config_path = detector.get_config_path(self.root)

        if fmt is None or config_path is None:
            return Result(
                success=False,
                message="No package configuration found in project",
            )

        result: Result
        if fmt == "pep621":
            from rejig.packaging.pep621 import PEP621Parser
            parser = PEP621Parser(self)
            result = parser.remove_dependency(config_path, name, dry_run=self.dry_run)
        elif fmt == "poetry":
            from rejig.packaging.poetry import PoetryParser
            parser = PoetryParser(self)
            result = parser.remove_dependency(config_path, name, dry_run=self.dry_run)
        elif fmt == "uv":
            from rejig.packaging.uv import UVParser
            parser = UVParser(self)
            result = parser.remove_dependency(config_path, name, dry_run=self.dry_run)
        elif fmt == "requirements":
            # For requirements.txt, filter out the line
            from rejig.packaging.models import Dependency
            normalized = Dependency._normalize_name(name)

            if not config_path.exists():
                return Result(success=True, message=f"Dependency {name} not found")

            try:
                content = config_path.read_text()
                lines = content.splitlines()
                new_lines = []
                found = False

                for line in lines:
                    dep = Dependency.from_pip_line(line)
                    if dep and dep.name == normalized:
                        found = True
                    else:
                        new_lines.append(line)

                if not found:
                    return Result(success=True, message=f"Dependency {name} not found")

                if self.dry_run:
                    return Result(
                        success=True,
                        message=f"[DRY RUN] Would remove {name} from {config_path}",
                        files_changed=[config_path],
                    )

                config_path.write_text("\n".join(new_lines) + "\n" if new_lines else "")
                return Result(
                    success=True,
                    message=f"Removed {name} from {config_path}",
                    files_changed=[config_path],
                )
            except Exception as e:
                return Result(success=False, message=f"Failed to remove dependency: {e}")
        else:
            return Result(
                success=False,
                message=f"Unsupported package format: {fmt}",
            )

        return Result(
            success=result.success,
            message=result.message,
            files_changed=result.files_changed,
        )

    def export_requirements(
        self, output: Path | None = None, include_dev: bool = False
    ) -> Result:
        """
        Export dependencies as a requirements.txt file.

        Parameters
        ----------
        output : Path | None
            Output file path. Defaults to "requirements.txt" in project root.
        include_dev : bool
            Whether to include development dependencies.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> rj.export_requirements()
        >>> rj.export_requirements(Path("requirements-dev.txt"), include_dev=True)
        """
        from rejig.packaging.converter import PackageConfigConverter
        from rejig.packaging.detector import get_package_config

        config = get_package_config(self.root)
        if config is None:
            return Result(
                success=False,
                message="No package configuration found in project",
            )

        if output is None:
            output = self.root / "requirements.txt"

        converter = PackageConfigConverter(self)
        result = converter.to_requirements(
            config, output, include_dev=include_dev, dry_run=self.dry_run
        )

        return Result(
            success=result.success,
            message=result.message,
            files_changed=result.files_changed,
        )

    def convert_package_config(
        self, target_format: str, output: Path | None = None
    ) -> Result:
        """
        Convert package configuration to a different format.

        Parameters
        ----------
        target_format : str
            Target format: "requirements", "pep621", "poetry".
        output : Path | None
            Output file path. Defaults based on format.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> rj.convert_package_config("pep621")  # Poetry -> PEP 621
        >>> rj.convert_package_config("requirements", Path("requirements.txt"))
        """
        from rejig.packaging.converter import PackageConfigConverter
        from rejig.packaging.detector import get_package_config

        config = get_package_config(self.root)
        if config is None:
            return Result(
                success=False,
                message="No package configuration found in project",
            )

        converter = PackageConfigConverter(self)

        if target_format == "requirements":
            if output is None:
                output = self.root / "requirements.txt"
            result = converter.to_requirements(config, output, dry_run=self.dry_run)
        elif target_format == "pep621":
            if output is None:
                output = self.root / "pyproject.toml"

            # Special case: Poetry to PEP 621 in-place conversion
            if config.format == "poetry" and output == config.source_path:
                result = converter.poetry_to_pep621(output, dry_run=self.dry_run)
            else:
                result = converter.to_pep621(config, output, dry_run=self.dry_run)
        else:
            return Result(
                success=False,
                message=f"Conversion to {target_format} not yet supported",
            )

        return Result(
            success=result.success,
            message=result.message,
            files_changed=result.files_changed,
        )

    # -------------------------------------------------------------------------
    # Import Management Operations
    # -------------------------------------------------------------------------

    def find_unused_imports(self) -> TargetList:
        """
        Find all unused imports across all files in the project.

        Returns
        -------
        TargetList
            List of ImportTarget objects for all unused imports.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> unused = rj.find_unused_imports()
        >>> print(f"Found {len(unused)} unused imports")
        >>> for imp in unused:
        ...     print(f"{imp.file_path}:{imp.line_number}: {imp.import_info.import_statement}")
        """
        from rejig.imports.analyzer import ImportAnalyzer
        from rejig.imports.targets import ImportTarget, ImportTargetList

        analyzer = ImportAnalyzer(self)
        all_targets: list[ImportTarget] = []

        for file_path in self.files:
            unused = analyzer.find_unused_imports(file_path)
            for info in unused:
                all_targets.append(ImportTarget(self, file_path, info))

        return ImportTargetList(self, all_targets)

    def find_circular_imports(self) -> list:
        """
        Find all circular import chains in the project.

        Returns
        -------
        list[CircularImport]
            List of circular import chains found.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> cycles = rj.find_circular_imports()
        >>> for cycle in cycles:
        ...     print(f"Circular import: {cycle}")
        """
        from rejig.imports.graph import ImportGraph

        graph = ImportGraph(self)
        graph.build()
        return graph.find_circular_imports()

    def get_import_graph(self):
        """
        Get the import dependency graph for the project.

        Returns
        -------
        ImportGraph
            The import graph object with methods for analysis.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> graph = rj.get_import_graph()
        >>>
        >>> # Get dependencies of a module
        >>> deps = graph.get_dependencies("myapp.models")
        >>>
        >>> # Get modules that depend on a module
        >>> dependents = graph.get_dependents("myapp.utils")
        >>>
        >>> # Export as dictionary
        >>> dep_dict = graph.to_dict()
        """
        from rejig.imports.graph import ImportGraph

        graph = ImportGraph(self)
        graph.build()
        return graph

    def rename_import(self, old_path: str, new_path: str) -> Result:
        """
        Rename an import across all files in the project.

        Updates all import statements that reference the old path to use
        the new path. This is useful after moving or renaming modules.

        Parameters
        ----------
        old_path : str
            The old import path (e.g., "old_module.OldClass").
        new_path : str
            The new import path (e.g., "new_module.NewClass").

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> rj.rename_import("myapp.old_module.OldClass", "myapp.new_module.NewClass")
        """
        import re as regex_module

        old_module = ".".join(old_path.rsplit(".", 1)[:-1]) if "." in old_path else old_path
        old_name = old_path.rsplit(".", 1)[-1] if "." in old_path else None
        new_module = ".".join(new_path.rsplit(".", 1)[:-1]) if "." in new_path else new_path
        new_name = new_path.rsplit(".", 1)[-1] if "." in new_path else None

        files_changed = []
        total_changes = 0

        for file_path in self.files:
            try:
                content = file_path.read_text()
                original = content

                # Handle 'from module import name' -> 'from new_module import new_name'
                if old_name and new_name:
                    # Pattern: from old_module import ..., old_name, ...
                    pattern = rf"(from\s+{regex_module.escape(old_module)}\s+import\s+)(\w+(?:\s*,\s*\w+)*)"

                    def replace_import(m):
                        prefix = m.group(1)
                        names = m.group(2)
                        new_names = regex_module.sub(rf"\b{regex_module.escape(old_name)}\b", new_name, names)
                        if old_module != new_module:
                            prefix = f"from {new_module} import "
                        return prefix + new_names

                    content = regex_module.sub(pattern, replace_import, content)

                # Handle 'import module' -> 'import new_module'
                if old_module and not old_name:
                    content = regex_module.sub(
                        rf"(import\s+){regex_module.escape(old_module)}\b",
                        rf"\1{new_module}",
                        content,
                    )
                    content = regex_module.sub(
                        rf"(from\s+){regex_module.escape(old_module)}(\s+import)",
                        rf"\1{new_module}\2",
                        content,
                    )

                if content != original:
                    if self.dry_run:
                        files_changed.append(file_path)
                        total_changes += 1
                    else:
                        file_path.write_text(content)
                        files_changed.append(file_path)
                        total_changes += 1

            except Exception:
                continue

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would update {total_changes} files",
                files_changed=files_changed,
            )

        return Result(
            success=True,
            message=f"Updated imports in {total_changes} files",
            files_changed=files_changed,
        )

    def organize_all_imports(
        self, first_party_packages: set[str] | None = None
    ) -> Result:
        """
        Organize imports in all Python files in the project.

        Parameters
        ----------
        first_party_packages : set[str] | None
            Set of package names to treat as first-party.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> rj.organize_all_imports()
        """
        from rejig.imports.organizer import ImportOrganizer

        organizer = ImportOrganizer(self, first_party_packages)
        files_changed = []

        for file_path in self.files:
            result = organizer.organize(file_path)
            if result.success and result.files_changed:
                files_changed.extend(result.files_changed)

        return Result(
            success=True,
            message=f"Organized imports in {len(files_changed)} files",
            files_changed=files_changed,
        )

    def remove_all_unused_imports(self) -> Result:
        """
        Remove all unused imports from all files in the project.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> rj.remove_all_unused_imports()
        """
        files_changed = []
        total_removed = 0

        for file_path in self.files:
            file_target = self.file(file_path)
            unused = file_target.find_unused_imports()

            if unused:
                # Delete in reverse order to avoid line number shifts
                for imp in sorted(unused.to_list(), key=lambda t: t.line_number, reverse=True):
                    result = imp.delete()
                    if result.success:
                        total_removed += 1

                files_changed.append(file_path)

        return Result(
            success=True,
            message=f"Removed {total_removed} unused imports from {len(files_changed)} files",
            files_changed=files_changed,
        )

    # -------------------------------------------------------------------------
    # Type Hint Operations
    # -------------------------------------------------------------------------

    def find_functions_without_type_hints(self) -> TargetList[FunctionTarget]:
        """
        Find all functions that lack return type annotations.

        Returns functions where the return type is not annotated.
        This helps identify code that needs type hints added.

        Returns
        -------
        TargetList[FunctionTarget]
            List of FunctionTarget objects for functions without return types.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> untyped = rj.find_functions_without_type_hints()
        >>> print(f"Found {len(untyped)} functions without type hints")
        >>> for func in untyped:
        ...     print(f"  {func.name} in {func.file_path}")
        """
        from rejig.targets.base import TargetList
        from rejig.targets.python.function import FunctionTarget

        targets: list[FunctionTarget] = []

        for file_path in self.files:
            try:
                content = file_path.read_text()
                tree = cst.parse_module(content)

                for node in tree.body:
                    if isinstance(node, cst.FunctionDef):
                        # Check if return type is missing
                        if node.returns is None:
                            targets.append(
                                FunctionTarget(self, node.name.value, file_path=file_path)
                            )
            except Exception:
                continue

        return TargetList(self, targets)

    def find_parameters_without_type_hints(
        self,
    ) -> list[tuple[FunctionTarget | ClassTarget, str]]:
        """
        Find all function/method parameters that lack type annotations.

        Returns a list of tuples containing the target (FunctionTarget or
        ClassTarget with method info) and the parameter name that needs
        type hints.

        Returns
        -------
        list[tuple[FunctionTarget | ClassTarget, str]]
            List of (target, param_name) tuples for parameters without types.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> untyped_params = rj.find_parameters_without_type_hints()
        >>> print(f"Found {len(untyped_params)} parameters without type hints")
        >>> for target, param_name in untyped_params:
        ...     print(f"  {param_name} in {target}")
        """
        from rejig.targets.python.function import FunctionTarget

        results: list[tuple[FunctionTarget | ClassTarget, str]] = []

        for file_path in self.files:
            try:
                content = file_path.read_text()
                tree = cst.parse_module(content)

                class ParamFinder(cst.CSTVisitor):
                    def __init__(self):
                        self.current_class: str | None = None
                        self.untyped_params: list[tuple[str | None, str, str]] = []

                    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
                        self.current_class = node.name.value
                        return True

                    def leave_ClassDef(self, node: cst.ClassDef) -> None:
                        self.current_class = None

                    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
                        func_name = node.name.value
                        for param in node.params.params:
                            # Skip self/cls
                            if param.name.value in ("self", "cls"):
                                continue
                            if param.annotation is None:
                                self.untyped_params.append(
                                    (self.current_class, func_name, param.name.value)
                                )
                        return False

                finder = ParamFinder()
                tree.walk(finder)

                for class_name, func_name, param_name in finder.untyped_params:
                    if class_name:
                        # It's a method - use ClassTarget with method info
                        from rejig.targets.python.class_ import ClassTarget
                        target = ClassTarget(self, class_name, file_path=file_path)
                        method = target.find_method(func_name)
                        results.append((method, param_name))
                    else:
                        # It's a module-level function
                        target = FunctionTarget(self, func_name, file_path=file_path)
                        results.append((target, param_name))

            except Exception:
                continue

        return results

    def modernize_all_type_hints(self) -> Result:
        """
        Modernize type hints in all Python files.

        Converts old-style type hints to Python 3.10+ syntax:
        - List[str] → list[str]
        - Dict[str, int] → dict[str, int]
        - Optional[str] → str | None
        - Union[str, int] → str | int

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> rj.modernize_all_type_hints()
        """
        files_changed = []

        for file_path in self.files:
            file_target = self.file(file_path)
            result = file_target.modernize_type_hints()
            if result.success and result.files_changed:
                files_changed.extend(result.files_changed)

        return Result(
            success=True,
            message=f"Modernized type hints in {len(files_changed)} files",
            files_changed=files_changed,
        )

    # -------------------------------------------------------------------------
    # Docstring Operations
    # -------------------------------------------------------------------------

    def find_missing_docstrings(self) -> TargetList:
        """
        Find all functions, methods, and classes without docstrings.

        Returns
        -------
        TargetList
            List of FunctionTarget, MethodTarget, and ClassTarget objects
            that don't have docstrings.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> missing = rj.find_missing_docstrings()
        >>> print(f"Found {len(missing)} items without docstrings")
        >>> missing.generate_docstrings()  # Add docstrings to all
        """
        from rejig.targets.base import TargetList

        all_targets = []
        for file_path in self.files:
            file_target = self.file(file_path)
            targets = file_target.find_missing_docstrings()
            all_targets.extend(targets.to_list())

        return TargetList(self, all_targets)

    def find_outdated_docstrings(self) -> list[dict]:
        """
        Find all functions/methods with outdated docstrings across the project.

        A docstring is considered outdated if:
        - It documents parameters that no longer exist in the signature
        - It's missing documentation for parameters in the signature

        Returns
        -------
        list[dict]
            List of dicts with:
            - file_path: Path to the file
            - name: function/method name
            - class_name: class name (or None for functions)
            - stale_params: params documented but not in signature
            - missing_params: params in signature but not documented

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> outdated = rj.find_outdated_docstrings()
        >>> for item in outdated:
        ...     print(f"{item['file_path']}:{item['name']}")
        ...     print(f"  Stale: {item['stale_params']}")
        ...     print(f"  Missing: {item['missing_params']}")
        """
        results = []

        for file_path in self.files:
            file_target = self.file(file_path)
            result = file_target.find_outdated_docstrings()
            if result.success and result.data:
                for item in result.data:
                    item["file_path"] = file_path
                    results.append(item)

        return results

    def generate_all_docstrings(
        self,
        style: str = "google",
        overwrite: bool = False,
    ) -> Result:
        """
        Generate docstrings for all functions and methods in the project.

        Parameters
        ----------
        style : str
            Docstring style: "google", "numpy", or "sphinx".
            Defaults to "google".
        overwrite : bool
            Whether to overwrite existing docstrings. Default False.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> rj.generate_all_docstrings()
        >>> rj.generate_all_docstrings(style="numpy", overwrite=True)
        """
        files_changed = []
        total_generated = 0

        for file_path in self.files:
            file_target = self.file(file_path)
            result = file_target.generate_all_docstrings(style=style, overwrite=overwrite)
            if result.success and result.files_changed:
                files_changed.extend(result.files_changed)
                # Extract count from message if available
                import re
                match = re.search(r"(\d+) docstrings", result.message)
                if match:
                    total_generated += int(match.group(1))

        return Result(
            success=True,
            message=f"Generated {total_generated} docstrings in {len(files_changed)} files",
            files_changed=files_changed,
        )

    def convert_all_docstring_styles(
        self,
        from_style: str | None,
        to_style: str,
    ) -> Result:
        """
        Convert all docstrings from one style to another across the project.

        Parameters
        ----------
        from_style : str | None
            Source docstring style ("google", "numpy", "sphinx"),
            or None to auto-detect.
        to_style : str
            Target docstring style ("google", "numpy", "sphinx").

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> rj = Rejig("src/")
        >>> rj.convert_all_docstring_styles("sphinx", "google")
        >>> rj.convert_all_docstring_styles(None, "numpy")  # auto-detect
        """
        files_changed = []
        total_converted = 0

        for file_path in self.files:
            file_target = self.file(file_path)
            result = file_target.convert_docstring_style(from_style, to_style)
            if result.success and result.files_changed:
                files_changed.extend(result.files_changed)
                # Extract count from message if available
                import re
                match = re.search(r"(\d+) docstrings", result.message)
                if match:
                    total_converted += int(match.group(1))

        return Result(
            success=True,
            message=f"Converted {total_converted} docstrings in {len(files_changed)} files",
            files_changed=files_changed,
        )
