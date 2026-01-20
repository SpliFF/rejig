"""ImportTarget for operations on individual import statements."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst

from rejig.core.results import BatchResult, Result
from rejig.imports.analyzer import ImportInfo
from rejig.targets.base import Target

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class ImportTarget(Target):
    """Target for a specific import statement in a file.

    Provides operations for modifying individual import statements.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    file_path : Path
        Path to the file containing the import.
    import_info : ImportInfo
        Information about the import statement.

    Examples
    --------
    >>> file = rj.file("mymodule.py")
    >>> unused = file.find_unused_imports()
    >>> for imp in unused:
    ...     print(f"Line {imp.line_number}: {imp.import_statement}")
    ...     imp.delete()
    """

    def __init__(
        self,
        rejig: Rejig,
        file_path: Path,
        import_info: ImportInfo,
    ) -> None:
        super().__init__(rejig)
        self.file_path = file_path
        self.import_info = import_info

    def __repr__(self) -> str:
        return f"ImportTarget({self.import_info.import_statement!r}, line={self.import_info.line_number})"

    @property
    def line_number(self) -> int:
        """The line number of this import."""
        return self.import_info.line_number

    @property
    def module(self) -> str | None:
        """The module being imported from (for from imports)."""
        return self.import_info.module

    @property
    def names(self) -> list[str]:
        """The names being imported."""
        return self.import_info.names

    @property
    def is_relative(self) -> bool:
        """Whether this is a relative import."""
        return self.import_info.is_relative

    @property
    def is_unused(self) -> bool:
        """Check if this import is unused in the file."""
        from rejig.imports.analyzer import ImportAnalyzer

        analyzer = ImportAnalyzer(self._rejig)
        unused = analyzer.find_unused_imports(self.file_path)
        return any(
            u.line_number == self.import_info.line_number and u.names == self.import_info.names
            for u in unused
        )

    def exists(self) -> bool:
        """Check if this import still exists in the file."""
        if not self.file_path.exists():
            return False

        from rejig.imports.analyzer import ImportAnalyzer

        analyzer = ImportAnalyzer(self._rejig)
        imports = analyzer.get_imports(self.file_path)
        return any(
            i.line_number == self.import_info.line_number
            and i.import_statement == self.import_info.import_statement
            for i in imports
        )

    def get_content(self) -> Result:
        """Get the import statement text."""
        return Result(
            success=True,
            message="OK",
            data=self.import_info.import_statement,
        )

    def delete(self) -> Result:
        """Remove this import from the file.

        Returns
        -------
        Result
            Result of the operation.
        """
        if not self.file_path.exists():
            return self._operation_failed("delete", f"File not found: {self.file_path}")

        content = self._get_file_content(self.file_path)
        if content is None:
            return self._operation_failed("delete", f"Could not read file: {self.file_path}")

        try:
            tree = cst.parse_module(content)
            transformer = RemoveImportTransformer(self.import_info)
            new_tree = tree.visit(transformer)
            new_content = new_tree.code

            if new_content == content:
                return Result(success=True, message="Import not found or already removed")

            return self._write_with_diff(
                self.file_path,
                content,
                new_content,
                f"remove import: {self.import_info.import_statement}",
            )
        except Exception as e:
            return self._operation_failed("delete", f"Failed to remove import: {e}", e)

    def convert_to_absolute(self, package_name: str) -> Result:
        """Convert a relative import to an absolute import.

        Parameters
        ----------
        package_name : str
            The package name to use as the base for the absolute import.

        Returns
        -------
        Result
            Result of the operation.
        """
        if not self.import_info.is_relative:
            return Result(success=True, message="Import is already absolute")

        if not self.file_path.exists():
            return self._operation_failed("convert_to_absolute", f"File not found: {self.file_path}")

        content = self._get_file_content(self.file_path)
        if content is None:
            return self._operation_failed("convert_to_absolute", f"Could not read file: {self.file_path}")

        # Calculate the absolute module path
        absolute_module = self._resolve_relative_import(package_name)
        if absolute_module is None:
            return self._operation_failed(
                "convert_to_absolute",
                "Could not resolve relative import path",
            )

        try:
            tree = cst.parse_module(content)
            transformer = ConvertToAbsoluteTransformer(
                self.import_info, absolute_module
            )
            new_tree = tree.visit(transformer)
            new_content = new_tree.code

            if new_content == content:
                return Result(success=True, message="No changes needed")

            return self._write_with_diff(
                self.file_path,
                content,
                new_content,
                f"convert to absolute import: {absolute_module}",
            )
        except Exception as e:
            return self._operation_failed("convert_to_absolute", f"Conversion failed: {e}", e)

    def convert_to_relative(self) -> Result:
        """Convert an absolute import to a relative import.

        Returns
        -------
        Result
            Result of the operation.
        """
        if self.import_info.is_relative:
            return Result(success=True, message="Import is already relative")

        if not self.file_path.exists():
            return self._operation_failed("convert_to_relative", f"File not found: {self.file_path}")

        content = self._get_file_content(self.file_path)
        if content is None:
            return self._operation_failed("convert_to_relative", f"Could not read file: {self.file_path}")

        # Calculate the relative import
        relative_info = self._calculate_relative_import()
        if relative_info is None:
            return self._operation_failed(
                "convert_to_relative",
                "Could not calculate relative import path",
            )

        level, module = relative_info

        try:
            tree = cst.parse_module(content)
            transformer = ConvertToRelativeTransformer(self.import_info, level, module)
            new_tree = tree.visit(transformer)
            new_content = new_tree.code

            if new_content == content:
                return Result(success=True, message="No changes needed")

            return self._write_with_diff(
                self.file_path,
                content,
                new_content,
                f"convert to relative import",
            )
        except Exception as e:
            return self._operation_failed("convert_to_relative", f"Conversion failed: {e}", e)

    def _resolve_relative_import(self, package_name: str) -> str | None:
        """Resolve a relative import to an absolute module path."""
        if not self.import_info.is_relative:
            return self.import_info.module

        # Get the current file's package path
        try:
            file_dir = self.file_path.parent
            root = self._rejig.root

            # Get the relative path from root to file directory
            rel_path = file_dir.relative_to(root)
            current_parts = list(rel_path.parts)

            # Go up 'level - 1' directories (level 1 means current package)
            level = self.import_info.relative_level
            if level > len(current_parts):
                return None

            base_parts = current_parts[: len(current_parts) - level + 1]

            # Build the absolute path
            parts = [package_name] + list(base_parts)
            if self.import_info.module:
                parts.append(self.import_info.module)

            return ".".join(parts)
        except Exception:
            return None

    def _calculate_relative_import(self) -> tuple[int, str | None] | None:
        """Calculate the relative import equivalent for an absolute import."""
        if not self.import_info.module:
            return None

        try:
            file_dir = self.file_path.parent
            root = self._rejig.root

            # Get the current package path
            rel_path = file_dir.relative_to(root)
            current_parts = list(rel_path.parts)

            # Parse the module path
            module_parts = self.import_info.module.split(".")

            # Find the common prefix
            common_len = 0
            for i in range(min(len(current_parts), len(module_parts))):
                if current_parts[i] == module_parts[i]:
                    common_len = i + 1
                else:
                    break

            # Calculate level (how many directories to go up)
            level = len(current_parts) - common_len + 1

            # Calculate remaining module path
            remaining_parts = module_parts[common_len:]
            module = ".".join(remaining_parts) if remaining_parts else None

            return (level, module)
        except Exception:
            return None


class ImportTargetList:
    """A list of ImportTargets for batch operations."""

    def __init__(self, rejig: Rejig, targets: list[ImportTarget]) -> None:
        self._rejig = rejig
        self._targets = targets

    def __iter__(self):
        return iter(self._targets)

    def __len__(self) -> int:
        return len(self._targets)

    def __bool__(self) -> bool:
        return len(self._targets) > 0

    def __getitem__(self, index: int) -> ImportTarget:
        return self._targets[index]

    def __repr__(self) -> str:
        return f"ImportTargetList({len(self._targets)} imports)"

    def to_list(self) -> list[ImportTarget]:
        """Return the underlying list of targets."""
        return list(self._targets)

    def delete(self) -> BatchResult:
        """Delete all imports in the list."""
        return BatchResult([t.delete() for t in self._targets])

    def delete_all(self) -> BatchResult:
        """Alias for delete()."""
        return self.delete()

    def filter_unused(self) -> ImportTargetList:
        """Filter to only unused imports."""
        return ImportTargetList(
            self._rejig, [t for t in self._targets if t.is_unused]
        )

    def filter_relative(self) -> ImportTargetList:
        """Filter to only relative imports."""
        return ImportTargetList(
            self._rejig, [t for t in self._targets if t.is_relative]
        )

    def filter_absolute(self) -> ImportTargetList:
        """Filter to only absolute imports."""
        return ImportTargetList(
            self._rejig, [t for t in self._targets if not t.is_relative]
        )

    def in_file(self, path: Path | str) -> ImportTargetList:
        """Filter to imports in a specific file."""
        path = Path(path) if isinstance(path, str) else path
        return ImportTargetList(
            self._rejig, [t for t in self._targets if t.file_path == path]
        )


class RemoveImportTransformer(cst.CSTTransformer):
    """Transformer to remove a specific import."""

    def __init__(self, import_info: ImportInfo) -> None:
        self.import_info = import_info
        self.removed = False

    def leave_SimpleStatementLine(
        self,
        original_node: cst.SimpleStatementLine,
        updated_node: cst.SimpleStatementLine,
    ) -> cst.BaseStatement | cst.RemovalSentinel:
        """Remove the import statement line if it matches."""
        if self.removed:
            return updated_node

        for stmt in updated_node.body:
            code = cst.Module(body=[cst.SimpleStatementLine(body=[stmt])]).code.strip()
            if code == self.import_info.import_statement:
                self.removed = True
                return cst.RemovalSentinel.REMOVE

        return updated_node


class ConvertToAbsoluteTransformer(cst.CSTTransformer):
    """Transformer to convert relative imports to absolute."""

    def __init__(self, import_info: ImportInfo, absolute_module: str) -> None:
        self.import_info = import_info
        self.absolute_module = absolute_module
        self.converted = False

    def leave_ImportFrom(
        self,
        original_node: cst.ImportFrom,
        updated_node: cst.ImportFrom,
    ) -> cst.ImportFrom:
        """Convert the relative import to absolute."""
        if self.converted:
            return updated_node

        code = cst.Module(body=[cst.SimpleStatementLine(body=[updated_node])]).code.strip()
        if code != self.import_info.import_statement:
            return updated_node

        # Build the new module reference
        parts = self.absolute_module.split(".")
        module: cst.Attribute | cst.Name = cst.Name(parts[0])
        for part in parts[1:]:
            module = cst.Attribute(value=module, attr=cst.Name(part))

        self.converted = True
        return updated_node.with_changes(
            relative=[],
            module=module,
        )


class ConvertToRelativeTransformer(cst.CSTTransformer):
    """Transformer to convert absolute imports to relative."""

    def __init__(self, import_info: ImportInfo, level: int, module: str | None) -> None:
        self.import_info = import_info
        self.level = level
        self.module = module
        self.converted = False

    def leave_ImportFrom(
        self,
        original_node: cst.ImportFrom,
        updated_node: cst.ImportFrom,
    ) -> cst.ImportFrom:
        """Convert the absolute import to relative."""
        if self.converted:
            return updated_node

        code = cst.Module(body=[cst.SimpleStatementLine(body=[updated_node])]).code.strip()
        if code != self.import_info.import_statement:
            return updated_node

        # Build the relative dots
        relative = [cst.Dot() for _ in range(self.level)]

        # Build the new module reference
        new_module = None
        if self.module:
            parts = self.module.split(".")
            new_module: cst.Attribute | cst.Name = cst.Name(parts[0])
            for part in parts[1:]:
                new_module = cst.Attribute(value=new_module, attr=cst.Name(part))

        self.converted = True
        return updated_node.with_changes(
            relative=relative,
            module=new_module,
        )
