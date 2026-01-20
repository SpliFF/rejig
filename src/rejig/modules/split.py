"""Module splitting utilities.

This module provides utilities for splitting Python files:
- Split by class: One file per class
- Split by function: One file per top-level function
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig

from rejig.core.results import Result


@dataclass
class SplitItem:
    """Represents an item to be split out into its own file."""

    name: str
    kind: str  # "class" or "function"
    code: str
    imports: list[str] = field(default_factory=list)
    leading_comments: str = ""


class ModuleSplitter:
    """Splits a Python module into multiple files.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    """

    def __init__(self, rejig: Rejig) -> None:
        self._rejig = rejig

    def split_by_class(
        self,
        file_path: Path,
        output_dir: Path | None = None,
        create_init: bool = True,
    ) -> Result:
        """Split a file into one file per class.

        Parameters
        ----------
        file_path : Path
            Path to the Python file to split.
        output_dir : Path | None
            Output directory. Defaults to a package named after the file.
        create_init : bool
            Whether to create an __init__.py with imports.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self._split(file_path, "class", output_dir, create_init)

    def split_by_function(
        self,
        file_path: Path,
        output_dir: Path | None = None,
        create_init: bool = True,
    ) -> Result:
        """Split a file into one file per top-level function.

        Parameters
        ----------
        file_path : Path
            Path to the Python file to split.
        output_dir : Path | None
            Output directory. Defaults to a package named after the file.
        create_init : bool
            Whether to create an __init__.py with imports.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self._split(file_path, "function", output_dir, create_init)

    def _split(
        self,
        file_path: Path,
        by: str,
        output_dir: Path | None,
        create_init: bool,
    ) -> Result:
        """Internal method to perform the split."""
        if not file_path.exists():
            return Result(
                success=False,
                message=f"File not found: {file_path}",
            )

        try:
            content = file_path.read_text()
            tree = cst.parse_module(content)
        except Exception as e:
            return Result(
                success=False,
                message=f"Failed to parse {file_path}: {e}",
            )

        # Extract imports from the original file
        imports = self._extract_imports(tree)

        # Extract items to split
        items = self._extract_items(tree, by)

        if not items:
            return Result(
                success=True,
                message=f"No {by}es found to split in {file_path}",
            )

        # Determine output directory
        if output_dir is None:
            output_dir = file_path.parent / file_path.stem

        if self._rejig.dry_run:
            file_list = [output_dir / f"{self._to_filename(item.name)}.py" for item in items]
            if create_init:
                file_list.append(output_dir / "__init__.py")
            return Result(
                success=True,
                message=f"[DRY RUN] Would split {file_path} into {len(items)} files",
                files_changed=file_list,
            )

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        files_created: list[Path] = []

        # Write each item to its own file
        for item in items:
            filename = f"{self._to_filename(item.name)}.py"
            item_path = output_dir / filename

            # Build file content
            item_content = self._build_item_file(item, imports)
            item_path.write_text(item_content)
            files_created.append(item_path)

        # Create __init__.py if requested
        if create_init:
            init_content = self._build_init_file(items)
            init_path = output_dir / "__init__.py"
            init_path.write_text(init_content)
            files_created.append(init_path)

        return Result(
            success=True,
            message=f"Split {file_path} into {len(items)} files in {output_dir}",
            files_changed=files_created,
        )

    def _extract_imports(self, tree: cst.Module) -> list[str]:
        """Extract all import statements from a module."""
        imports: list[str] = []
        for node in tree.body:
            if isinstance(node, (cst.SimpleStatementLine,)):
                for stmt in node.body:
                    if isinstance(stmt, (cst.Import, cst.ImportFrom)):
                        imports.append(tree.code_for_node(node).strip())
                        break
        return imports

    def _extract_items(self, tree: cst.Module, by: str) -> list[SplitItem]:
        """Extract classes or functions from a module."""
        items: list[SplitItem] = []

        for node in tree.body:
            if by == "class" and isinstance(node, cst.ClassDef):
                items.append(
                    SplitItem(
                        name=node.name.value,
                        kind="class",
                        code=tree.code_for_node(node),
                    )
                )
            elif by == "function" and isinstance(node, cst.FunctionDef):
                items.append(
                    SplitItem(
                        name=node.name.value,
                        kind="function",
                        code=tree.code_for_node(node),
                    )
                )

        return items

    def _to_filename(self, name: str) -> str:
        """Convert a class/function name to a filename.

        CamelCase becomes snake_case.
        """
        import re

        # Insert underscore before uppercase letters (except at start)
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        # Insert underscore before uppercase letters following lowercase
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    def _build_item_file(self, item: SplitItem, imports: list[str]) -> str:
        """Build the file content for a split item."""
        parts: list[str] = []

        # Add docstring
        parts.append(f'"""{item.kind.capitalize()} {item.name}."""')

        # Add imports
        if imports:
            parts.append("")
            parts.extend(imports)

        # Add the item code
        parts.append("")
        parts.append("")
        parts.append(item.code)

        return "\n".join(parts) + "\n"

    def _build_init_file(self, items: list[SplitItem]) -> str:
        """Build the __init__.py content."""
        parts: list[str] = []

        # Add docstring
        parts.append('"""Package exports."""')
        parts.append("")

        # Add imports
        for item in items:
            filename = self._to_filename(item.name)
            parts.append(f"from .{filename} import {item.name}")

        # Add __all__
        parts.append("")
        parts.append("__all__ = [")
        for item in items:
            parts.append(f'    "{item.name}",')
        parts.append("]")

        return "\n".join(parts) + "\n"

    def convert_to_package(
        self,
        file_path: Path,
        keep_original: bool = False,
    ) -> Result:
        """Convert a module file to a package directory.

        Transforms utils.py into utils/__init__.py.

        Parameters
        ----------
        file_path : Path
            Path to the Python file to convert.
        keep_original : bool
            Whether to keep the original file. Default False.

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

        # Create package directory
        package_dir = file_path.parent / file_path.stem
        init_path = package_dir / "__init__.py"

        if self._rejig.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would convert {file_path} to {package_dir}/",
                files_changed=[init_path],
            )

        try:
            content = file_path.read_text()

            package_dir.mkdir(parents=True, exist_ok=True)
            init_path.write_text(content)

            if not keep_original:
                file_path.unlink()

            return Result(
                success=True,
                message=f"Converted {file_path} to package {package_dir}/",
                files_changed=[init_path],
            )
        except Exception as e:
            return Result(
                success=False,
                message=f"Failed to convert to package: {e}",
            )


# Convenience functions


def split_by_class(
    rejig: Rejig,
    file_path: Path,
    output_dir: Path | None = None,
    create_init: bool = True,
) -> Result:
    """Split a file into one file per class.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    file_path : Path
        Path to the Python file to split.
    output_dir : Path | None
        Output directory. Defaults to a package named after the file.
    create_init : bool
        Whether to create an __init__.py with imports.

    Returns
    -------
    Result
        Result of the operation.
    """
    splitter = ModuleSplitter(rejig)
    return splitter.split_by_class(file_path, output_dir, create_init)


def split_by_function(
    rejig: Rejig,
    file_path: Path,
    output_dir: Path | None = None,
    create_init: bool = True,
) -> Result:
    """Split a file into one file per top-level function.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    file_path : Path
        Path to the Python file to split.
    output_dir : Path | None
        Output directory. Defaults to a package named after the file.
    create_init : bool
        Whether to create an __init__.py with imports.

    Returns
    -------
    Result
        Result of the operation.
    """
    splitter = ModuleSplitter(rejig)
    return splitter.split_by_function(file_path, output_dir, create_init)
