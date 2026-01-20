"""PackageTarget for operations on Python packages (directories with __init__.py)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from rejig.targets.base import ErrorTarget, Result, Target, TargetList
from rejig.targets.python.file import FileTarget

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class PackageTarget(Target):
    """Target for a Python package (directory with __init__.py).

    Provides operations for working with packages including finding modules,
    classes, and functions within the package.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    path : str | Path
        Path to the package directory.

    Examples
    --------
    >>> pkg = rj.package("myapp/models")
    >>> pkg.find_classes()  # Find all classes in the package
    >>> pkg.init_file.add_import("from .user import User")
    """

    def __init__(self, rejig: Rejig, path: str | Path) -> None:
        super().__init__(rejig)
        self.path = Path(path) if isinstance(path, str) else path

    @property
    def file_path(self) -> Path:
        """Path to the package directory."""
        return self.path

    @property
    def init_file(self) -> FileTarget | ErrorTarget:
        """Get the __init__.py file target."""
        init_path = self.path / "__init__.py"
        if init_path.exists():
            return FileTarget(self._rejig, init_path)
        return ErrorTarget(self._rejig, f"No __init__.py found in {self.path}")

    @property
    def name(self) -> str:
        """The package name (directory name)."""
        return self.path.name

    def __repr__(self) -> str:
        return f"PackageTarget({self.path})"

    def exists(self) -> bool:
        """Check if this package exists (directory with __init__.py)."""
        return self.path.is_dir() and (self.path / "__init__.py").exists()

    def get_content(self) -> Result:
        """Get the content of the package's __init__.py file.

        Returns
        -------
        Result
            Result with __init__.py content in `data` field if successful.
        """
        init_target = self.init_file
        if isinstance(init_target, ErrorTarget):
            return self._operation_failed("get_content", f"Package not found: {self.path}")
        return init_target.get_content()

    def get_modules(self) -> list[Path]:
        """Get all Python modules in this package.

        Returns
        -------
        list[Path]
            List of paths to Python files in the package (non-recursive).
        """
        if not self.exists():
            return []
        return sorted(self.path.glob("*.py"))

    def get_subpackages(self) -> list[Path]:
        """Get all subpackages in this package.

        Returns
        -------
        list[Path]
            List of paths to subpackage directories.
        """
        if not self.exists():
            return []
        subpackages = []
        for item in sorted(self.path.iterdir()):
            if item.is_dir() and (item / "__init__.py").exists():
                subpackages.append(item)
        return subpackages

    # ===== Navigation methods =====

    def find_module(self, name: str) -> FileTarget | ErrorTarget:
        """Find a module by name within this package.

        Parameters
        ----------
        name : str
            Module name (without .py extension).

        Returns
        -------
        FileTarget | ErrorTarget
            FileTarget if found, ErrorTarget otherwise.
        """
        module_path = self.path / f"{name}.py"
        if module_path.exists():
            return FileTarget(self._rejig, module_path)
        return ErrorTarget(self._rejig, f"Module '{name}' not found in {self.path}")

    def find_subpackage(self, name: str) -> PackageTarget | ErrorTarget:
        """Find a subpackage by name.

        Parameters
        ----------
        name : str
            Subpackage name.

        Returns
        -------
        PackageTarget | ErrorTarget
            PackageTarget if found, ErrorTarget otherwise.
        """
        subpkg_path = self.path / name
        if subpkg_path.is_dir() and (subpkg_path / "__init__.py").exists():
            return PackageTarget(self._rejig, subpkg_path)
        return ErrorTarget(self._rejig, f"Subpackage '{name}' not found in {self.path}")

    def find_class(self, name: str) -> Target:
        """Find a class by name across all modules in this package.

        Parameters
        ----------
        name : str
            Name of the class to find.

        Returns
        -------
        ClassTarget | ErrorTarget
            ClassTarget if found, ErrorTarget otherwise.
        """
        from rejig.targets.python.class_ import ClassTarget

        pattern = rf"\bclass\s+{re.escape(name)}\b"
        for module_path in self.get_modules():
            try:
                content = module_path.read_text()
                if re.search(pattern, content):
                    target = ClassTarget(self._rejig, name, file_path=module_path)
                    if target.exists():
                        return target
            except Exception:
                continue

        return ErrorTarget(self._rejig, f"Class '{name}' not found in package {self.path}")

    def find_function(self, name: str) -> Target:
        """Find a module-level function by name across all modules.

        Parameters
        ----------
        name : str
            Name of the function to find.

        Returns
        -------
        FunctionTarget | ErrorTarget
            FunctionTarget if found, ErrorTarget otherwise.
        """
        from rejig.targets.python.function import FunctionTarget

        pattern = rf"^def\s+{re.escape(name)}\b"
        for module_path in self.get_modules():
            try:
                content = module_path.read_text()
                if re.search(pattern, content, re.MULTILINE):
                    target = FunctionTarget(self._rejig, name, file_path=module_path)
                    if target.exists():
                        return target
            except Exception:
                continue

        return ErrorTarget(self._rejig, f"Function '{name}' not found in package {self.path}")

    def find_classes(self, pattern: str | None = None) -> TargetList[Target]:
        """Find all classes in this package.

        Parameters
        ----------
        pattern : str | None
            Optional regex pattern to filter class names.

        Returns
        -------
        TargetList[ClassTarget]
            List of matching ClassTarget objects.
        """
        all_targets: list[Target] = []
        for module_path in self.get_modules():
            file_target = FileTarget(self._rejig, module_path)
            targets = file_target.find_classes(pattern)
            all_targets.extend(targets.to_list())

        return TargetList(self._rejig, all_targets)

    def find_functions(self, pattern: str | None = None) -> TargetList[Target]:
        """Find all module-level functions in this package.

        Parameters
        ----------
        pattern : str | None
            Optional regex pattern to filter function names.

        Returns
        -------
        TargetList[FunctionTarget]
            List of matching FunctionTarget objects.
        """
        all_targets: list[Target] = []
        for module_path in self.get_modules():
            file_target = FileTarget(self._rejig, module_path)
            targets = file_target.find_functions(pattern)
            all_targets.extend(targets.to_list())

        return TargetList(self._rejig, all_targets)

    # ===== Modification operations =====

    def add_import(self, import_statement: str) -> Result:
        """Add an import statement to the package's __init__.py.

        Parameters
        ----------
        import_statement : str
            Import statement to add.

        Returns
        -------
        Result
            Result of the operation.
        """
        init_target = self.init_file
        if isinstance(init_target, ErrorTarget):
            return self._operation_failed("add_import", f"Package not found: {self.path}")
        return init_target.add_import(import_statement)

    def create_module(self, name: str, content: str = "") -> Result:
        """Create a new module in this package.

        Parameters
        ----------
        name : str
            Module name (without .py extension).
        content : str
            Initial content for the module.

        Returns
        -------
        Result
            Result of the operation.
        """
        if not self.exists():
            return self._operation_failed("create_module", f"Package not found: {self.path}")

        module_path = self.path / f"{name}.py"
        if module_path.exists():
            return self._operation_failed("create_module", f"Module '{name}' already exists")

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would create module {module_path}",
                files_changed=[module_path],
            )

        try:
            module_path.write_text(content)
            return Result(
                success=True,
                message=f"Created module {module_path}",
                files_changed=[module_path],
            )
        except Exception as e:
            return self._operation_failed("create_module", f"Failed to create module: {e}", e)

    def create_subpackage(self, name: str, init_content: str = "") -> Result:
        """Create a new subpackage in this package.

        Parameters
        ----------
        name : str
            Subpackage name.
        init_content : str
            Initial content for __init__.py.

        Returns
        -------
        Result
            Result of the operation.
        """
        if not self.exists():
            return self._operation_failed("create_subpackage", f"Package not found: {self.path}")

        subpkg_path = self.path / name
        if subpkg_path.exists():
            return self._operation_failed("create_subpackage", f"Path '{name}' already exists")

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would create subpackage {subpkg_path}",
                files_changed=[subpkg_path / "__init__.py"],
            )

        try:
            subpkg_path.mkdir(parents=True)
            init_path = subpkg_path / "__init__.py"
            init_path.write_text(init_content)
            return Result(
                success=True,
                message=f"Created subpackage {subpkg_path}",
                files_changed=[init_path],
            )
        except Exception as e:
            return self._operation_failed("create_subpackage", f"Failed to create subpackage: {e}", e)

    def delete(self) -> Result:
        """Delete this package and all its contents.

        Returns
        -------
        Result
            Result of the operation.
        """
        if not self.exists():
            return self._operation_failed("delete", f"Package not found: {self.path}")

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would delete package {self.path}",
                files_changed=[self.path],
            )

        try:
            import shutil

            shutil.rmtree(self.path)
            return Result(
                success=True,
                message=f"Deleted package {self.path}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("delete", f"Failed to delete package: {e}", e)

    # ===== Type hint operations =====

    def generate_stubs(self, output: str | Path | None = None) -> Result:
        """Generate type stub files (.pyi) for all modules in this package.

        Creates stub files that contain only function signatures, class
        definitions, and type annotations. This is useful for providing
        type hints for libraries or for use with type checkers.

        Parameters
        ----------
        output : str | Path | None
            Output directory for stub files. If None, creates a 'stubs/'
            directory next to the package.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> pkg = rj.package("src/mypackage")
        >>> pkg.generate_stubs()  # Creates stubs/ alongside package
        >>> pkg.generate_stubs("custom_stubs/")  # Use custom directory
        """
        from rejig.typehints.stubs import StubGenerator

        if not self.exists():
            return self._operation_failed("generate_stubs", f"Package not found: {self.path}")

        output_dir = Path(output) if output else None
        generator = StubGenerator(self._rejig)
        return generator.generate_for_package(self.path, output_dir)