"""Module renaming and moving utilities.

This module provides utilities for renaming and moving Python modules
with automatic import updates across the project.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig

from rejig.core.results import Result


class ModuleRenamer:
    """Renames or moves Python modules with import updates.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    """

    def __init__(self, rejig: Rejig) -> None:
        self._rejig = rejig

    def rename(
        self,
        old_module: str,
        new_module: str,
        update_imports: bool = True,
    ) -> Result:
        """Rename a module and update all imports.

        Parameters
        ----------
        old_module : str
            Current module path (e.g., "myapp.old_utils").
        new_module : str
            New module path (e.g., "myapp.new_utils").
        update_imports : bool
            Whether to update imports across the project.

        Returns
        -------
        Result
            Result of the operation.
        """
        # Find the file for the old module
        old_file = self._find_module_file(old_module)
        if old_file is None:
            return Result(
                success=False,
                message=f"Module not found: {old_module}",
            )

        # Calculate new file path
        new_file = self._calculate_new_path(old_module, new_module, old_file)

        if self._rejig.dry_run:
            files_changed = [old_file, new_file]
            if update_imports:
                import_files = self._find_files_with_import(old_module)
                files_changed.extend(import_files)
            return Result(
                success=True,
                message=f"[DRY RUN] Would rename {old_module} to {new_module}",
                files_changed=files_changed,
            )

        # Create new directory if needed
        new_file.parent.mkdir(parents=True, exist_ok=True)

        # Move/rename the file
        try:
            content = old_file.read_text()
            new_file.write_text(content)
            old_file.unlink()
        except Exception as e:
            return Result(
                success=False,
                message=f"Failed to rename file: {e}",
            )

        files_changed = [old_file, new_file]

        # Update imports if requested
        if update_imports:
            update_result = self._update_imports(old_module, new_module)
            files_changed.extend(update_result.get("files", []))

        return Result(
            success=True,
            message=f"Renamed {old_module} to {new_module}",
            files_changed=files_changed,
        )

    def move_to(
        self,
        module_path: str,
        new_location: str,
        update_imports: bool = True,
    ) -> Result:
        """Move a module to a new location.

        Parameters
        ----------
        module_path : str
            Current module path (e.g., "myapp.utils").
        new_location : str
            New module path (e.g., "myapp.core.utils").
        update_imports : bool
            Whether to update imports across the project.

        Returns
        -------
        Result
            Result of the operation.
        """
        # Moving is essentially the same as renaming
        return self.rename(module_path, new_location, update_imports)

    def _find_module_file(self, module_path: str) -> Path | None:
        """Find the file for a module path."""
        parts = module_path.split(".")

        # Try to find the file
        for file_path in self._rejig.files:
            try:
                rel_path = file_path.relative_to(self._rejig.root)
            except ValueError:
                continue

            # Convert path to module-style parts
            path_parts = list(rel_path.parts)
            if path_parts[-1].endswith(".py"):
                path_parts[-1] = path_parts[-1][:-3]

            # Handle __init__.py
            if path_parts[-1] == "__init__":
                path_parts = path_parts[:-1]

            if path_parts == parts:
                return file_path

        return None

    def _calculate_new_path(
        self,
        old_module: str,
        new_module: str,
        old_file: Path,
    ) -> Path:
        """Calculate the new file path for a renamed module."""
        old_parts = old_module.split(".")
        new_parts = new_module.split(".")

        # Check if old file is __init__.py
        is_init = old_file.name == "__init__.py"

        if is_init:
            # Package rename: myapp/old/ -> myapp/new/
            new_path = self._rejig.root / Path(*new_parts) / "__init__.py"
        else:
            # Module rename: myapp/old.py -> myapp/new.py
            new_path = self._rejig.root / Path(*new_parts[:-1]) / f"{new_parts[-1]}.py"

        return new_path

    def _find_files_with_import(self, module_path: str) -> list[Path]:
        """Find all files that import the given module."""
        files: list[Path] = []

        # Patterns to match
        patterns = [
            rf"import\s+{re.escape(module_path)}\b",
            rf"from\s+{re.escape(module_path)}\s+import",
            rf"from\s+{re.escape(module_path.rsplit('.', 1)[0])}\s+import\s+.*\b{re.escape(module_path.rsplit('.', 1)[-1])}\b"
            if "." in module_path
            else None,
        ]
        patterns = [p for p in patterns if p is not None]

        for file_path in self._rejig.files:
            try:
                content = file_path.read_text()
                for pattern in patterns:
                    if re.search(pattern, content):
                        files.append(file_path)
                        break
            except Exception:
                continue

        return files

    def _update_imports(self, old_module: str, new_module: str) -> dict:
        """Update imports across the project."""
        files_changed: list[Path] = []

        for file_path in self._rejig.files:
            try:
                content = file_path.read_text()
                original_content = content

                # Update various import forms
                content = self._update_import_statements(content, old_module, new_module)

                if content != original_content:
                    file_path.write_text(content)
                    files_changed.append(file_path)
            except Exception:
                continue

        return {"files": files_changed}

    def _update_import_statements(
        self,
        content: str,
        old_module: str,
        new_module: str,
    ) -> str:
        """Update import statements in content."""
        # Direct module import: import myapp.old_utils
        content = re.sub(
            rf"\bimport\s+{re.escape(old_module)}\b",
            f"import {new_module}",
            content,
        )

        # From import: from myapp.old_utils import X
        content = re.sub(
            rf"\bfrom\s+{re.escape(old_module)}\s+import\b",
            f"from {new_module} import",
            content,
        )

        # Also handle if the module is part of a from import
        # from myapp import old_utils
        if "." in old_module:
            parent, name = old_module.rsplit(".", 1)
            new_parent, new_name = new_module.rsplit(".", 1)

            if parent == new_parent:
                # Same parent, just rename the imported name
                # from myapp import old_utils -> from myapp import new_utils
                content = re.sub(
                    rf"(\bfrom\s+{re.escape(parent)}\s+import\s+(?:.*,\s*)?)(\b{re.escape(name)}\b)",
                    rf"\1{new_name}",
                    content,
                )

        return content


class ImportUpdater(cst.CSTTransformer):
    """CST transformer for updating import statements."""

    def __init__(self, old_module: str, new_module: str) -> None:
        self.old_module = old_module
        self.new_module = new_module
        self.changed = False

    def leave_ImportFrom(
        self,
        original_node: cst.ImportFrom,
        updated_node: cst.ImportFrom,
    ) -> cst.ImportFrom:
        if updated_node.module is None:
            return updated_node

        module_name = self._get_full_name(updated_node.module)

        if module_name == self.old_module:
            self.changed = True
            new_module_node = self._build_module(self.new_module)
            return updated_node.with_changes(module=new_module_node)

        return updated_node

    def _get_full_name(self, node: cst.BaseExpression) -> str:
        """Get the full dotted name from an expression."""
        if isinstance(node, cst.Name):
            return node.value
        elif isinstance(node, cst.Attribute):
            return f"{self._get_full_name(node.value)}.{node.attr.value}"
        return ""

    def _build_module(self, name: str) -> cst.BaseExpression:
        """Build a module expression from a dotted name."""
        parts = name.split(".")
        result: cst.BaseExpression = cst.Name(parts[0])
        for part in parts[1:]:
            result = cst.Attribute(value=result, attr=cst.Name(part))
        return result


# Convenience functions


def rename_module(
    rejig: Rejig,
    old_module: str,
    new_module: str,
    update_imports: bool = True,
) -> Result:
    """Rename a module and update all imports.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    old_module : str
        Current module path.
    new_module : str
        New module path.
    update_imports : bool
        Whether to update imports across the project.

    Returns
    -------
    Result
        Result of the operation.
    """
    renamer = ModuleRenamer(rejig)
    return renamer.rename(old_module, new_module, update_imports)


def move_module(
    rejig: Rejig,
    module_path: str,
    new_location: str,
    update_imports: bool = True,
) -> Result:
    """Move a module to a new location.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    module_path : str
        Current module path.
    new_location : str
        New module path.
    update_imports : bool
        Whether to update imports across the project.

    Returns
    -------
    Result
        Result of the operation.
    """
    renamer = ModuleRenamer(rejig)
    return renamer.move_to(module_path, new_location, update_imports)
