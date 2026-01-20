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

    # ===== Test operations =====

    def convert_unittest_to_pytest(self) -> Result:
        """Convert unittest test cases to pytest style.

        Transforms all test files in this package (recursively) from
        unittest style to pytest style, converting:
        - self.assertEqual(a, b) -> assert a == b
        - self.assertTrue(x) -> assert x
        - self.assertFalse(x) -> assert not x
        - self.assertIsNone(x) -> assert x is None
        - self.assertRaises(X) -> pytest.raises(X)
        - And many more assertion methods

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> tests_pkg = rj.package("tests/")
        >>> tests_pkg.convert_unittest_to_pytest()
        """
        import libcst as cst

        from rejig.generation.tests import UnittestToPytestConverter

        if not self.exists():
            return self._operation_failed(
                "convert_unittest_to_pytest",
                f"Package not found: {self.path}",
            )

        converted_files: list[Path] = []
        errors: list[str] = []

        # Find all Python files recursively
        for file_path in self.path.rglob("*.py"):
            # Skip __pycache__ and other non-test files
            if "__pycache__" in str(file_path):
                continue

            try:
                content = file_path.read_text()

                # Skip files that don't contain unittest patterns
                if "self.assert" not in content and "TestCase" not in content:
                    continue

                tree = cst.parse_module(content)
                transformer = UnittestToPytestConverter()
                new_tree = tree.visit(transformer)
                new_content = new_tree.code

                if new_content != content and transformer.converted:
                    # Add pytest import if needed
                    if transformer._needs_pytest_import and "import pytest" not in new_content:
                        new_content = "import pytest\n" + new_content

                    if not self.dry_run:
                        file_path.write_text(new_content)
                    converted_files.append(file_path)
            except Exception as e:
                errors.append(f"{file_path}: {e}")

        if errors:
            return Result(
                success=len(converted_files) > 0,
                message=f"Converted {len(converted_files)} files with {len(errors)} errors",
                files_changed=converted_files,
                data={"errors": errors},
            )

        if not converted_files:
            return Result(
                success=True,
                message="No unittest files found to convert",
            )

        prefix = "[DRY RUN] Would convert" if self.dry_run else "Converted"
        return Result(
            success=True,
            message=f"{prefix} {len(converted_files)} files to pytest style",
            files_changed=converted_files,
        )

    def update_test_imports(
        self,
        old_module: str,
        new_module: str,
    ) -> Result:
        """Update imports in test files after refactoring.

        Useful for updating test imports when source modules are moved or renamed.

        Parameters
        ----------
        old_module : str
            The old module path (e.g., "myapp.utils").
        new_module : str
            The new module path (e.g., "myapp.helpers.utils").

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> tests_pkg = rj.package("tests/")
        >>> tests_pkg.update_test_imports("myapp.utils", "myapp.helpers.utils")
        """
        if not self.exists():
            return self._operation_failed(
                "update_test_imports",
                f"Package not found: {self.path}",
            )

        updated_files: list[Path] = []

        # Find all Python files recursively
        for file_path in self.path.rglob("*.py"):
            if "__pycache__" in str(file_path):
                continue

            try:
                content = file_path.read_text()

                if old_module not in content:
                    continue

                new_content = content.replace(old_module, new_module)

                if new_content != content:
                    if not self.dry_run:
                        file_path.write_text(new_content)
                    updated_files.append(file_path)
            except Exception as e:
                continue  # Skip files that can't be read

        if not updated_files:
            return Result(
                success=True,
                message=f"No imports of '{old_module}' found to update",
            )

        prefix = "[DRY RUN] Would update" if self.dry_run else "Updated"
        return Result(
            success=True,
            message=f"{prefix} imports in {len(updated_files)} files",
            files_changed=updated_files,
        )

    def generate_test_stubs(self, test_dir: str | Path | None = None) -> Result:
        """Generate test stubs for all classes and functions in this package.

        Creates test files with stub test functions for all public
        classes and functions found in the package.

        Parameters
        ----------
        test_dir : str | Path | None
            Base directory for tests. Defaults to "tests" in project root.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> pkg = rj.package("src/myapp")
        >>> pkg.generate_test_stubs()  # Creates tests/test_*.py files
        """
        from rejig.generation.tests import TestGenerator, extract_class_signatures, extract_function_signature

        if not self.exists():
            return self._operation_failed(
                "generate_test_stubs",
                f"Package not found: {self.path}",
            )

        # Determine test directory
        if test_dir is None:
            test_dir = self._rejig.root_path / "tests" if self._rejig.root_path else Path("tests")
        else:
            test_dir = Path(test_dir)

        generated_files: list[Path] = []
        generator = TestGenerator()

        # Process all Python files recursively
        for file_path in self.path.rglob("*.py"):
            if "__pycache__" in str(file_path) or file_path.name.startswith("_"):
                continue

            try:
                content = file_path.read_text()
                test_content_parts: list[str] = []

                # Extract class signatures
                # Look for class definitions
                import re

                for match in re.finditer(r"class\s+(\w+)", content):
                    class_name = match.group(1)
                    if class_name.startswith("_"):
                        continue
                    methods, docstring = extract_class_signatures(content, class_name)
                    if methods:
                        test_content_parts.append(
                            generator.generate_class_test_file(
                                class_name, methods, class_docstring=docstring
                            )
                        )

                # Extract function signatures
                for match in re.finditer(r"^def\s+(\w+)", content, re.MULTILINE):
                    func_name = match.group(1)
                    if func_name.startswith("_"):
                        continue
                    sig = extract_function_signature(content, func_name)
                    if sig:
                        test_content_parts.append(generator.generate_function_test_stub(sig))

                if test_content_parts:
                    test_filename = f"test_{file_path.stem}.py"
                    output_path = test_dir / test_filename

                    test_content = "\n\n".join(test_content_parts)

                    if not self.dry_run:
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        output_path.write_text(test_content)
                    generated_files.append(output_path)
            except Exception:
                continue

        if not generated_files:
            return Result(
                success=True,
                message="No classes or functions found to generate tests for",
            )

        prefix = "[DRY RUN] Would generate" if self.dry_run else "Generated"
        return Result(
            success=True,
            message=f"{prefix} {len(generated_files)} test files",
            files_changed=generated_files,
        )

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

    # ===== Module operations =====

    def merge_modules(
        self,
        module_names: list[str],
        into: str,
        delete_originals: bool = False,
        generate_all: bool = True,
    ) -> Result:
        """Merge multiple modules in this package into one.

        Parameters
        ----------
        module_names : list[str]
            List of module names to merge (without .py extension).
        into : str
            Target module name (without .py extension).
        delete_originals : bool
            Whether to delete the original files after merging.
        generate_all : bool
            Whether to generate an __all__ list.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> pkg = rj.package("mypackage/")
        >>> pkg.merge_modules(["utils_a", "utils_b"], into="utils")
        """
        from rejig.modules.merge import ModuleMerger

        if not self.exists():
            return self._operation_failed(
                "merge_modules", f"Package not found: {self.path}"
            )

        # Convert module names to paths
        module_paths = [self.path / f"{name}.py" for name in module_names]

        # Validate all modules exist
        for i, module_path in enumerate(module_paths):
            if not module_path.exists():
                return self._operation_failed(
                    "merge_modules",
                    f"Module not found: {module_names[i]}",
                )

        output_path = self.path / f"{into}.py"

        merger = ModuleMerger(self._rejig)
        return merger.merge(module_paths, output_path, delete_originals, generate_all)

    # ===== Header management operations =====

    def add_copyright_header(
        self,
        copyright_text: str,
        year: int | None = None,
        recursive: bool = True,
    ) -> Result:
        """Add a copyright header to all Python files in this package.

        Parameters
        ----------
        copyright_text : str
            Copyright holder text (e.g., "MyCompany Inc.").
        year : int | None
            Copyright year. Defaults to current year.
        recursive : bool
            Whether to include files in subpackages. Default True.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> pkg = rj.package("mypackage/")
        >>> pkg.add_copyright_header("Copyright 2024 MyCompany")
        """
        from rejig.modules.headers import HeaderManager

        if not self.exists():
            return self._operation_failed(
                "add_copyright_header", f"Package not found: {self.path}"
            )

        manager = HeaderManager(self._rejig)
        files_changed: list[Path] = []

        # Get all Python files
        pattern = "**/*.py" if recursive else "*.py"
        for file_path in self.path.glob(pattern):
            if "__pycache__" in str(file_path):
                continue

            result = manager.add_copyright_header(file_path, copyright_text, year)
            if result.success and result.files_changed:
                files_changed.extend(result.files_changed)

        if not files_changed:
            return Result(
                success=True,
                message=f"No files needed copyright header in {self.path}",
            )

        prefix = "[DRY RUN] Would add" if self.dry_run else "Added"
        return Result(
            success=True,
            message=f"{prefix} copyright header to {len(files_changed)} files",
            files_changed=files_changed,
        )

    def add_license_header(
        self,
        license_name: str,
        copyright_holder: str | None = None,
        year: int | None = None,
        recursive: bool = True,
    ) -> Result:
        """Add a license header to all Python files in this package.

        Parameters
        ----------
        license_name : str
            License identifier: "MIT", "Apache-2.0", "GPL-3.0",
            "BSD-3-Clause", or "Proprietary".
        copyright_holder : str | None
            Copyright holder name. If None, uses a placeholder.
        year : int | None
            Copyright year. Defaults to current year.
        recursive : bool
            Whether to include files in subpackages. Default True.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> pkg = rj.package("mypackage/")
        >>> pkg.add_license_header("MIT", "MyCompany Inc.")
        """
        from rejig.modules.headers import HeaderManager

        if not self.exists():
            return self._operation_failed(
                "add_license_header", f"Package not found: {self.path}"
            )

        manager = HeaderManager(self._rejig)
        files_changed: list[Path] = []

        # Get all Python files
        pattern = "**/*.py" if recursive else "*.py"
        for file_path in self.path.glob(pattern):
            if "__pycache__" in str(file_path):
                continue

            result = manager.add_license_header(
                file_path, license_name, copyright_holder, year
            )
            if result.success and result.files_changed:
                files_changed.extend(result.files_changed)

        if not files_changed:
            return Result(
                success=True,
                message=f"No files needed license header in {self.path}",
            )

        prefix = "[DRY RUN] Would add" if self.dry_run else "Added"
        return Result(
            success=True,
            message=f"{prefix} license header to {len(files_changed)} files",
            files_changed=files_changed,
        )

    def update_copyright_year(
        self,
        new_year: int | None = None,
        recursive: bool = True,
    ) -> Result:
        """Update the copyright year in all Python files in this package.

        Updates patterns like:
        - "Copyright 2023" -> "Copyright 2023-2024"
        - "Copyright 2023-2024" -> "Copyright 2023-2025"

        Parameters
        ----------
        new_year : int | None
            Target year. Defaults to current year.
        recursive : bool
            Whether to include files in subpackages. Default True.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> pkg = rj.package("mypackage/")
        >>> pkg.update_copyright_year()
        """
        from rejig.modules.headers import HeaderManager

        if not self.exists():
            return self._operation_failed(
                "update_copyright_year", f"Package not found: {self.path}"
            )

        manager = HeaderManager(self._rejig)
        files_changed: list[Path] = []

        # Get all Python files
        pattern = "**/*.py" if recursive else "*.py"
        for file_path in self.path.glob(pattern):
            if "__pycache__" in str(file_path):
                continue

            result = manager.update_copyright_year(file_path, new_year)
            if result.success and result.files_changed:
                files_changed.extend(result.files_changed)

        if not files_changed:
            return Result(
                success=True,
                message=f"No files needed copyright year update in {self.path}",
            )

        prefix = "[DRY RUN] Would update" if self.dry_run else "Updated"
        return Result(
            success=True,
            message=f"{prefix} copyright year in {len(files_changed)} files",
            files_changed=files_changed,
        )