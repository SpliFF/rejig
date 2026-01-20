"""Module merging utilities.

This module provides utilities for merging multiple Python modules into one.
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
class MergedContent:
    """Represents merged content from multiple modules."""

    imports: list[str] = field(default_factory=list)
    future_imports: list[str] = field(default_factory=list)
    docstrings: list[str] = field(default_factory=list)
    definitions: list[str] = field(default_factory=list)
    all_exports: list[str] = field(default_factory=list)


class ModuleMerger:
    """Merges multiple Python modules into one.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    """

    def __init__(self, rejig: Rejig) -> None:
        self._rejig = rejig

    def merge(
        self,
        module_paths: list[Path],
        output_path: Path,
        delete_originals: bool = False,
        generate_all: bool = True,
    ) -> Result:
        """Merge multiple modules into a single file.

        Parameters
        ----------
        module_paths : list[Path]
            List of paths to modules to merge.
        output_path : Path
            Path for the merged output file.
        delete_originals : bool
            Whether to delete the original files after merging.
        generate_all : bool
            Whether to generate an __all__ list.

        Returns
        -------
        Result
            Result of the operation.
        """
        # Validate inputs
        for path in module_paths:
            if not path.exists():
                return Result(
                    success=False,
                    message=f"Module not found: {path}",
                )

        # Collect content from all modules
        merged = MergedContent()

        for path in module_paths:
            try:
                content = path.read_text()
                self._extract_content(content, merged)
            except Exception as e:
                return Result(
                    success=False,
                    message=f"Failed to parse {path}: {e}",
                )

        # Build merged content
        merged_content = self._build_merged_file(merged, generate_all)

        if self._rejig.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would merge {len(module_paths)} modules into {output_path}",
                files_changed=[output_path],
            )

        try:
            output_path.write_text(merged_content)

            files_changed = [output_path]

            if delete_originals:
                for path in module_paths:
                    if path != output_path:  # Don't delete if output is one of inputs
                        path.unlink()
                        files_changed.append(path)

            return Result(
                success=True,
                message=f"Merged {len(module_paths)} modules into {output_path}",
                files_changed=files_changed,
            )
        except Exception as e:
            return Result(
                success=False,
                message=f"Failed to write merged file: {e}",
            )

    def _extract_content(self, content: str, merged: MergedContent) -> None:
        """Extract content from a module and add to merged content."""
        try:
            tree = cst.parse_module(content)
        except Exception:
            # If parsing fails, just add raw content to definitions
            merged.definitions.append(content)
            return

        for node in tree.body:
            code = tree.code_for_node(node).strip()

            # Check for module docstring (first string in body)
            if isinstance(node, cst.SimpleStatementLine):
                if node.body and isinstance(node.body[0], cst.Expr):
                    expr = node.body[0].value
                    if isinstance(expr, (cst.SimpleString, cst.ConcatenatedString)):
                        # It's a docstring
                        docstring = tree.code_for_node(expr)
                        if docstring not in merged.docstrings:
                            merged.docstrings.append(docstring)
                        continue

                # Check for imports
                for stmt in node.body:
                    if isinstance(stmt, cst.ImportFrom):
                        # Check for __future__ import
                        if isinstance(stmt.module, cst.Attribute):
                            module_name = self._get_module_name(stmt.module)
                        elif isinstance(stmt.module, cst.Name):
                            module_name = stmt.module.value
                        else:
                            module_name = ""

                        if module_name == "__future__":
                            if code not in merged.future_imports:
                                merged.future_imports.append(code)
                        else:
                            if code not in merged.imports:
                                merged.imports.append(code)
                    elif isinstance(stmt, cst.Import):
                        if code not in merged.imports:
                            merged.imports.append(code)
                    elif isinstance(stmt, cst.Assign):
                        # Check for __all__ assignment
                        for target in stmt.targets:
                            if isinstance(target.target, cst.Name):
                                if target.target.value == "__all__":
                                    # Extract names from __all__
                                    self._extract_all_names(stmt.value, merged)
                                    break
                        else:
                            # Regular assignment
                            if code not in merged.definitions:
                                merged.definitions.append(code)
                    else:
                        # Other simple statements
                        if code not in merged.definitions:
                            merged.definitions.append(code)

            elif isinstance(node, cst.ClassDef):
                merged.definitions.append(code)
                # Add class name to exports
                if node.name.value not in merged.all_exports:
                    merged.all_exports.append(node.name.value)

            elif isinstance(node, cst.FunctionDef):
                merged.definitions.append(code)
                # Add public function name to exports
                if not node.name.value.startswith("_"):
                    if node.name.value not in merged.all_exports:
                        merged.all_exports.append(node.name.value)

            else:
                # Any other node type
                if code not in merged.definitions:
                    merged.definitions.append(code)

    def _get_module_name(self, node: cst.BaseExpression) -> str:
        """Get the full module name from an attribute chain."""
        if isinstance(node, cst.Name):
            return node.value
        elif isinstance(node, cst.Attribute):
            return f"{self._get_module_name(node.value)}.{node.attr.value}"
        return ""

    def _extract_all_names(self, value: cst.BaseExpression, merged: MergedContent) -> None:
        """Extract names from an __all__ definition."""
        if isinstance(value, (cst.List, cst.Tuple)):
            for element in value.elements:
                if isinstance(element, cst.Element):
                    if isinstance(element.value, cst.SimpleString):
                        # Remove quotes
                        name = element.value.value.strip("'\"")
                        if name not in merged.all_exports:
                            merged.all_exports.append(name)

    def _build_merged_file(self, merged: MergedContent, generate_all: bool) -> str:
        """Build the merged file content."""
        parts: list[str] = []

        # Add combined docstring
        if merged.docstrings:
            # Use first docstring or combine them
            parts.append(merged.docstrings[0])
            parts.append("")

        # Add __future__ imports first
        if merged.future_imports:
            parts.extend(merged.future_imports)
            parts.append("")

        # Add regular imports (sorted)
        if merged.imports:
            # Sort imports
            regular_imports = []
            from_imports = []
            for imp in merged.imports:
                if imp.startswith("from "):
                    from_imports.append(imp)
                else:
                    regular_imports.append(imp)

            parts.extend(sorted(regular_imports))
            parts.extend(sorted(from_imports))
            parts.append("")

        # Add __all__ if requested
        if generate_all and merged.all_exports:
            parts.append("__all__ = [")
            for name in sorted(merged.all_exports):
                parts.append(f'    "{name}",')
            parts.append("]")
            parts.append("")

        # Add definitions
        if merged.definitions:
            parts.append("")
            parts.append("\n\n".join(merged.definitions))

        return "\n".join(parts) + "\n"


# Convenience function


def merge_modules(
    rejig: Rejig,
    module_paths: list[Path],
    output_path: Path,
    delete_originals: bool = False,
    generate_all: bool = True,
) -> Result:
    """Merge multiple modules into a single file.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    module_paths : list[Path]
        List of paths to modules to merge.
    output_path : Path
        Path for the merged output file.
    delete_originals : bool
        Whether to delete the original files after merging.
    generate_all : bool
        Whether to generate an __all__ list.

    Returns
    -------
    Result
        Result of the operation.
    """
    merger = ModuleMerger(rejig)
    return merger.merge(module_paths, output_path, delete_originals, generate_all)
