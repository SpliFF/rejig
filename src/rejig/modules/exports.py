"""Module exports (__all__) management utilities.

This module provides utilities for managing Python module exports:
- Get current __all__ exports
- Generate __all__ from definitions
- Update __all__ to sync with definitions
- Add/remove items from __all__
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig

from rejig.core.results import Result


class ExportsManager:
    """Manages __all__ exports for a Python module.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    """

    def __init__(self, rejig: Rejig) -> None:
        self._rejig = rejig

    def get_exports(self, file_path: Path) -> list[str]:
        """Get the current __all__ exports from a file.

        Parameters
        ----------
        file_path : Path
            Path to the Python file.

        Returns
        -------
        list[str]
            List of exported names, or empty list if no __all__.
        """
        if not file_path.exists():
            return []

        try:
            content = file_path.read_text()
            return self._parse_all(content)
        except Exception:
            return []

    def generate_exports(
        self,
        file_path: Path,
        include_private: bool = False,
    ) -> Result:
        """Generate __all__ from all public definitions in a file.

        Parameters
        ----------
        file_path : Path
            Path to the Python file.
        include_private : bool
            Whether to include private names (starting with _).

        Returns
        -------
        Result
            Result with generated __all__ in data field.
        """
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

        # Extract all public definitions
        exports = self._extract_definitions(tree, include_private)

        if not exports:
            return Result(
                success=True,
                message="No public definitions found",
                data=[],
            )

        # Build new content with __all__
        new_content = self._update_or_add_all(content, tree, exports)

        if self._rejig.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would generate __all__ with {len(exports)} exports",
                data=exports,
                files_changed=[file_path],
            )

        file_path.write_text(new_content)
        return Result(
            success=True,
            message=f"Generated __all__ with {len(exports)} exports",
            data=exports,
            files_changed=[file_path],
        )

    def update_exports(
        self,
        file_path: Path,
        include_private: bool = False,
    ) -> Result:
        """Update __all__ to sync with actual definitions.

        Adds missing exports and removes stale ones.

        Parameters
        ----------
        file_path : Path
            Path to the Python file.
        include_private : bool
            Whether to include private names (starting with _).

        Returns
        -------
        Result
            Result of the operation.
        """
        # This is essentially the same as generate_exports
        return self.generate_exports(file_path, include_private)

    def add_export(self, file_path: Path, name: str) -> Result:
        """Add a name to __all__.

        Parameters
        ----------
        file_path : Path
            Path to the Python file.
        name : str
            Name to add to __all__.

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

        try:
            content = file_path.read_text()
            current = self._parse_all(content)
        except Exception as e:
            return Result(
                success=False,
                message=f"Failed to parse {file_path}: {e}",
            )

        if name in current:
            return Result(
                success=True,
                message=f"'{name}' already in __all__",
            )

        # Add the name
        new_exports = current + [name]

        # Parse and update
        try:
            tree = cst.parse_module(content)
            new_content = self._update_or_add_all(content, tree, new_exports)
        except Exception as e:
            return Result(
                success=False,
                message=f"Failed to update {file_path}: {e}",
            )

        if self._rejig.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would add '{name}' to __all__",
                files_changed=[file_path],
            )

        file_path.write_text(new_content)
        return Result(
            success=True,
            message=f"Added '{name}' to __all__",
            files_changed=[file_path],
        )

    def remove_export(self, file_path: Path, name: str) -> Result:
        """Remove a name from __all__.

        Parameters
        ----------
        file_path : Path
            Path to the Python file.
        name : str
            Name to remove from __all__.

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

        try:
            content = file_path.read_text()
            current = self._parse_all(content)
        except Exception as e:
            return Result(
                success=False,
                message=f"Failed to parse {file_path}: {e}",
            )

        if name not in current:
            return Result(
                success=True,
                message=f"'{name}' not in __all__",
            )

        # Remove the name
        new_exports = [n for n in current if n != name]

        # Parse and update
        try:
            tree = cst.parse_module(content)
            new_content = self._update_or_add_all(content, tree, new_exports)
        except Exception as e:
            return Result(
                success=False,
                message=f"Failed to update {file_path}: {e}",
            )

        if self._rejig.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would remove '{name}' from __all__",
                files_changed=[file_path],
            )

        file_path.write_text(new_content)
        return Result(
            success=True,
            message=f"Removed '{name}' from __all__",
            files_changed=[file_path],
        )

    def _parse_all(self, content: str) -> list[str]:
        """Parse __all__ from file content."""
        try:
            tree = cst.parse_module(content)
        except Exception:
            return []

        for node in tree.body:
            if isinstance(node, cst.SimpleStatementLine):
                for stmt in node.body:
                    if isinstance(stmt, cst.Assign):
                        for target in stmt.targets:
                            if isinstance(target.target, cst.Name):
                                if target.target.value == "__all__":
                                    return self._extract_all_names(stmt.value)

        return []

    def _extract_all_names(self, value: cst.BaseExpression) -> list[str]:
        """Extract names from an __all__ definition."""
        names: list[str] = []

        if isinstance(value, (cst.List, cst.Tuple)):
            for element in value.elements:
                if isinstance(element, cst.Element):
                    if isinstance(element.value, cst.SimpleString):
                        # Remove quotes
                        name = element.value.value.strip("'\"")
                        names.append(name)

        return names

    def _extract_definitions(self, tree: cst.Module, include_private: bool) -> list[str]:
        """Extract all public definitions from a module."""
        names: list[str] = []

        for node in tree.body:
            if isinstance(node, cst.ClassDef):
                name = node.name.value
                if include_private or not name.startswith("_"):
                    names.append(name)

            elif isinstance(node, cst.FunctionDef):
                name = node.name.value
                if include_private or not name.startswith("_"):
                    names.append(name)

            elif isinstance(node, cst.SimpleStatementLine):
                for stmt in node.body:
                    if isinstance(stmt, cst.Assign):
                        for target in stmt.targets:
                            if isinstance(target.target, cst.Name):
                                name = target.target.value
                                # Skip __all__ and other special names
                                if name == "__all__":
                                    continue
                                if include_private or not name.startswith("_"):
                                    names.append(name)
                    elif isinstance(stmt, cst.AnnAssign):
                        if isinstance(stmt.target, cst.Name):
                            name = stmt.target.value
                            if include_private or not name.startswith("_"):
                                names.append(name)

        return names

    def _update_or_add_all(
        self,
        content: str,
        tree: cst.Module,
        exports: list[str],
    ) -> str:
        """Update existing __all__ or add new one."""

        class AllUpdater(cst.CSTTransformer):
            def __init__(self, new_exports: list[str]) -> None:
                self.exports = new_exports
                self.found = False

            def leave_Assign(
                self, original_node: cst.Assign, updated_node: cst.Assign
            ) -> cst.Assign:
                for target in original_node.targets:
                    if isinstance(target.target, cst.Name):
                        if target.target.value == "__all__":
                            self.found = True
                            # Build new __all__ list
                            elements = [
                                cst.Element(cst.SimpleString(f'"{name}"'))
                                for name in sorted(self.exports)
                            ]
                            new_list = cst.List(elements=elements)
                            return updated_node.with_changes(value=new_list)
                return updated_node

        updater = AllUpdater(exports)
        new_tree = tree.visit(updater)

        if updater.found:
            return new_tree.code

        # No existing __all__, add one after imports
        lines = content.split("\n")
        insert_idx = 0

        # Find last import line
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                insert_idx = i + 1
            elif stripped.startswith("if TYPE_CHECKING:"):
                # Skip TYPE_CHECKING block
                j = i + 1
                while j < len(lines) and (lines[j].startswith("    ") or not lines[j].strip()):
                    j += 1
                insert_idx = j

        # Build __all__ string
        all_str = "__all__ = [\n"
        for name in sorted(exports):
            all_str += f'    "{name}",\n'
        all_str += "]\n"

        # Insert after imports
        lines.insert(insert_idx, "")
        lines.insert(insert_idx + 1, all_str)

        return "\n".join(lines)


# Convenience functions


def get_all_exports(rejig: Rejig, file_path: Path) -> list[str]:
    """Get the current __all__ exports from a file.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    file_path : Path
        Path to the Python file.

    Returns
    -------
    list[str]
        List of exported names.
    """
    manager = ExportsManager(rejig)
    return manager.get_exports(file_path)


def generate_all_exports(
    rejig: Rejig,
    file_path: Path,
    include_private: bool = False,
) -> Result:
    """Generate __all__ from all public definitions in a file.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    file_path : Path
        Path to the Python file.
    include_private : bool
        Whether to include private names.

    Returns
    -------
    Result
        Result of the operation.
    """
    manager = ExportsManager(rejig)
    return manager.generate_exports(file_path, include_private)


def update_all_exports(
    rejig: Rejig,
    file_path: Path,
    include_private: bool = False,
) -> Result:
    """Update __all__ to sync with actual definitions.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    file_path : Path
        Path to the Python file.
    include_private : bool
        Whether to include private names.

    Returns
    -------
    Result
        Result of the operation.
    """
    manager = ExportsManager(rejig)
    return manager.update_exports(file_path, include_private)


def add_to_all(rejig: Rejig, file_path: Path, name: str) -> Result:
    """Add a name to __all__.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    file_path : Path
        Path to the Python file.
    name : str
        Name to add.

    Returns
    -------
    Result
        Result of the operation.
    """
    manager = ExportsManager(rejig)
    return manager.add_export(file_path, name)


def remove_from_all(rejig: Rejig, file_path: Path, name: str) -> Result:
    """Remove a name from __all__.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    file_path : Path
        Path to the Python file.
    name : str
        Name to remove.

    Returns
    -------
    Result
        Result of the operation.
    """
    manager = ExportsManager(rejig)
    return manager.remove_export(file_path, name)
