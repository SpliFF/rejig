"""FunctionScope for operations on module-level functions."""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from rejig.result import RefactorResult
from rejig.transformers import InsertAtMethodStart

from .base import BaseScope

if TYPE_CHECKING:
    from rejig.core import Manipylate


class FunctionScope(BaseScope):
    """
    Scope for operations on a module-level function.

    Parameters
    ----------
    manipylate : Manipylate
        The parent Manipylate instance.
    function_name : str
        Name of the function to operate on.

    Examples
    --------
    >>> func_scope = pym.find_function("process_data")
    >>> func_scope.add_parameter("timeout", "int", "30")
    """

    def __init__(self, manipylate: Manipylate, function_name: str):
        super().__init__(manipylate)
        self.function_name = function_name
        self._file_path: Path | None = None

    def _find_function_file(self) -> Path | None:
        """Find the file containing this function."""
        if self._file_path is not None:
            return self._file_path

        pattern = rf"^def\s+{re.escape(self.function_name)}\b"
        for file_path in self.files:
            try:
                content = file_path.read_text()
                if re.search(pattern, content, re.MULTILINE):
                    self._file_path = file_path
                    return file_path
            except Exception:
                continue
        return None

    @property
    def file_path(self) -> Path | None:
        """Path to the file containing this function."""
        return self._find_function_file()

    def exists(self) -> bool:
        """Check if the function exists."""
        return self._find_function_file() is not None

    def insert_statement(self, statement: str, position: str = "start") -> RefactorResult:
        """
        Insert a statement into the function body.

        Parameters
        ----------
        statement : str
            Python statement to insert.
        position : str, optional
            Where to insert: "start" (after docstring) or "end".
            Defaults to "start".

        Returns
        -------
        RefactorResult
            Result of the operation.
        """
        file_path = self._find_function_file()
        if not file_path:
            return RefactorResult(
                success=False,
                message=f"Function {self.function_name} not found",
            )

        # Use InsertAtMethodStart but with no class context
        transformer = InsertAtMethodStart(None, self.function_name, statement)
        return self.manipylate.transform_file(file_path, transformer)

    def add_decorator(self, decorator: str) -> RefactorResult:
        """
        Add a decorator to the function.

        Parameters
        ----------
        decorator : str
            Decorator to add (without @ prefix).

        Returns
        -------
        RefactorResult
            Result of the operation.
        """
        file_path = self._find_function_file()
        if not file_path:
            return RefactorResult(
                success=False,
                message=f"Function {self.function_name} not found",
            )

        content = file_path.read_text()
        pattern = rf"(^def\s+{re.escape(self.function_name)}\b)"
        replacement = f"@{decorator}\n\\1"
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        if new_content == content:
            return RefactorResult(
                success=False,
                message=f"Could not add decorator to {self.function_name}",
            )

        if self.dry_run:
            return RefactorResult(
                success=True,
                message=f"[DRY RUN] Would add @{decorator} to {self.function_name}",
                files_changed=[file_path],
            )

        file_path.write_text(new_content)
        return RefactorResult(
            success=True,
            message=f"Added @{decorator} to {self.function_name}",
            files_changed=[file_path],
        )

    def rename(self, new_name: str) -> RefactorResult:
        """
        Rename the function.

        Parameters
        ----------
        new_name : str
            New name for the function.

        Returns
        -------
        RefactorResult
            Result of the operation.
        """
        file_path = self._find_function_file()
        if not file_path:
            return RefactorResult(
                success=False,
                message=f"Function {self.function_name} not found",
            )

        content = file_path.read_text()
        pattern = rf"^(def\s+){re.escape(self.function_name)}(\s*\()"
        replacement = rf"\1{new_name}\2"
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        if new_content == content:
            return RefactorResult(
                success=False,
                message=f"Could not rename {self.function_name}",
            )

        if self.dry_run:
            return RefactorResult(
                success=True,
                message=f"[DRY RUN] Would rename {self.function_name} to {new_name}",
                files_changed=[file_path],
            )

        file_path.write_text(new_content)
        old_name = self.function_name
        self.function_name = new_name
        return RefactorResult(
            success=True,
            message=f"Renamed {old_name} to {new_name}",
            files_changed=[file_path],
        )

    def move_to(self, dest_module: str) -> RefactorResult:
        """
        Move this function to a different module using rope.

        Rope automatically updates all imports throughout the project.

        Parameters
        ----------
        dest_module : str
            Destination module path (e.g., 'utils.helpers').

        Returns
        -------
        RefactorResult
            Result with success status.

        Examples
        --------
        >>> with Manipylate("src/") as pym:
        ...     pym.find_function("helper").move_to("utils.common")
        """
        file_path = self._find_function_file()
        if not file_path:
            return RefactorResult(
                success=False,
                message=f"Function {self.function_name} not found",
            )

        return self.manipylate.move_function(file_path, self.function_name, dest_module)
