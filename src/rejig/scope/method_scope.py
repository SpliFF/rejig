"""MethodScope for operations on a specific method within a class."""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from rejig.result import RefactorResult
from rejig.transformers import (
    AddFirstParameter,
    AddMethodDecorator,
    InsertAtMatch,
    InsertAtMethodStart,
    RemoveMethodDecorator,
    RenameMethod,
    ReplaceIdentifier,
    StaticToClassMethod,
)

from .base import BaseScope

if TYPE_CHECKING:
    from rejig.core import Manipylate


class MethodScope(BaseScope):
    """
    Scope for operations on a specific method within a class.

    This class provides methods for modifying a method within a class.

    Parameters
    ----------
    manipylate : Manipylate
        The parent Manipylate instance.
    class_name : str
        Name of the class containing the method.
    method_name : str
        Name of the method to operate on.

    Examples
    --------
    >>> method_scope = class_scope.find_method("process")
    >>> method_scope.add_parameter("timeout", "int", "30")
    >>> method_scope.insert_statement("self.validate()")
    """

    def __init__(self, manipylate: Manipylate, class_name: str, method_name: str):
        super().__init__(manipylate)
        self.class_name = class_name
        self.method_name = method_name
        self._file_path: Path | None = None

    def _find_method_file(self) -> Path | None:
        """Find the file containing the class with this method."""
        if self._file_path is not None:
            return self._file_path

        class_pattern = rf"\bclass\s+{re.escape(self.class_name)}\b"
        method_pattern = rf"\bdef\s+{re.escape(self.method_name)}\b"

        for file_path in self.files:
            try:
                content = file_path.read_text()
                if re.search(class_pattern, content) and re.search(method_pattern, content):
                    self._file_path = file_path
                    return file_path
            except Exception:
                continue
        return None

    @property
    def file_path(self) -> Path | None:
        """Path to the file containing this method."""
        return self._find_method_file()

    def exists(self) -> bool:
        """Check if the method exists."""
        return self._find_method_file() is not None

    def insert_statement(self, statement: str, position: str = "start") -> RefactorResult:
        """
        Insert a statement into the method body.

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

        Examples
        --------
        >>> method_scope.insert_statement("self.validate()")
        >>> method_scope.insert_statement("return result", position="end")
        """
        file_path = self._find_method_file()
        if not file_path:
            return RefactorResult(
                success=False,
                message=f"Method {self.class_name}.{self.method_name} not found",
            )

        transformer = InsertAtMethodStart(self.class_name, self.method_name, statement)
        return self.manipylate.transform_file(file_path, transformer)

    def add_parameter(
        self,
        param_name: str,
        type_annotation: str | None = None,
        default_value: str | None = None,
        position: str = "end",
    ) -> RefactorResult:
        """
        Add a parameter to the method signature.

        Parameters
        ----------
        param_name : str
            Name of the parameter to add.
        type_annotation : str | None, optional
            Type annotation for the parameter.
        default_value : str | None, optional
            Default value for the parameter.
        position : str, optional
            Where to add: "start" (after self/cls), "end".
            Defaults to "end".

        Returns
        -------
        RefactorResult
            Result of the operation.
        """
        file_path = self._find_method_file()
        if not file_path:
            return RefactorResult(
                success=False,
                message=f"Method {self.class_name}.{self.method_name} not found",
            )

        if position == "start":
            transformer = AddFirstParameter(self.class_name, self.method_name, param_name)
            return self.manipylate.transform_file(file_path, transformer)

        # For end position, we need a different transformer
        # For now, use regex-based approach
        content = file_path.read_text()

        # Build the parameter string
        param_str = param_name
        if type_annotation:
            param_str = f"{param_name}: {type_annotation}"
        if default_value is not None:
            param_str = f"{param_str} = {default_value}"

        # Find and update the method signature
        # This is a simplified approach - for complex cases, use CST
        pattern = rf"(def\s+{re.escape(self.method_name)}\s*\([^)]*)()\)"
        new_content = re.sub(
            pattern,
            rf"\1, {param_str})",
            content,
        )

        if new_content == content:
            return RefactorResult(
                success=False,
                message=f"Could not add parameter to {self.method_name}",
            )

        if self.dry_run:
            return RefactorResult(
                success=True,
                message=f"[DRY RUN] Would add parameter {param_name} to {self.method_name}",
                files_changed=[file_path],
            )

        file_path.write_text(new_content)
        return RefactorResult(
            success=True,
            message=f"Added parameter {param_name} to {self.method_name}",
            files_changed=[file_path],
        )

    def replace_identifier(self, old_name: str, new_name: str) -> RefactorResult:
        """
        Replace identifier references within the method.

        Parameters
        ----------
        old_name : str
            Identifier to replace.
        new_name : str
            New identifier name (can include dots, e.g., "cls.cache").

        Returns
        -------
        RefactorResult
            Result of the operation.

        Examples
        --------
        >>> method_scope.replace_identifier("cache", "cls._cache")
        """
        file_path = self._find_method_file()
        if not file_path:
            return RefactorResult(
                success=False,
                message=f"Method {self.class_name}.{self.method_name} not found",
            )

        transformer = ReplaceIdentifier(
            self.class_name, self.method_name, old_name, new_name
        )
        return self.manipylate.transform_file(file_path, transformer)

    def convert_to_classmethod(self) -> RefactorResult:
        """
        Convert a staticmethod to a classmethod and add cls parameter.

        Returns
        -------
        RefactorResult
            Result of the operation.
        """
        file_path = self._find_method_file()
        if not file_path:
            return RefactorResult(
                success=False,
                message=f"Method {self.class_name}.{self.method_name} not found",
            )

        # First convert decorator
        transformer1 = StaticToClassMethod(self.class_name, self.method_name)
        result1 = self.manipylate.transform_file(file_path, transformer1)

        if not result1.success:
            return result1

        # Then add cls parameter
        transformer2 = AddFirstParameter(self.class_name, self.method_name, "cls")
        return self.manipylate.transform_file(file_path, transformer2)

    def add_decorator(self, decorator: str) -> RefactorResult:
        """
        Add a decorator to the method.

        Parameters
        ----------
        decorator : str
            Decorator to add (without @ prefix).

        Returns
        -------
        RefactorResult
            Result of the operation.
        """
        file_path = self._find_method_file()
        if not file_path:
            return RefactorResult(
                success=False,
                message=f"Method {self.class_name}.{self.method_name} not found",
            )

        transformer = AddMethodDecorator(self.class_name, self.method_name, decorator)
        return self.manipylate.transform_file(file_path, transformer)

    def remove_decorator(self, decorator: str) -> RefactorResult:
        """
        Remove a decorator from the method.

        Parameters
        ----------
        decorator : str
            Decorator to remove (without @ prefix).

        Returns
        -------
        RefactorResult
            Result of the operation.
        """
        file_path = self._find_method_file()
        if not file_path:
            return RefactorResult(
                success=False,
                message=f"Method {self.class_name}.{self.method_name} not found",
            )

        transformer = RemoveMethodDecorator(self.class_name, self.method_name, decorator)
        return self.manipylate.transform_file(file_path, transformer)

    def rename(self, new_name: str) -> RefactorResult:
        """
        Rename the method.

        Note: This only renames the method definition. It does not update
        calls to the method throughout the codebase.

        Parameters
        ----------
        new_name : str
            New name for the method.

        Returns
        -------
        RefactorResult
            Result of the operation.
        """
        file_path = self._find_method_file()
        if not file_path:
            return RefactorResult(
                success=False,
                message=f"Method {self.class_name}.{self.method_name} not found",
            )

        transformer = RenameMethod(self.class_name, self.method_name, new_name)
        result = self.manipylate.transform_file(file_path, transformer)

        if result.success and transformer.renamed:
            self.method_name = new_name
            return RefactorResult(
                success=True,
                message=f"Renamed method to {new_name}",
                files_changed=[file_path],
            )
        return result

    def insert_before_match(self, pattern: str, code: str) -> RefactorResult:
        """
        Insert code before a line matching a regex pattern.

        Parameters
        ----------
        pattern : str
            Regex pattern to match against line content.
        code : str
            Code to insert before the matching line.

        Returns
        -------
        RefactorResult
            Result of the operation.
        """
        file_path = self._find_method_file()
        if not file_path:
            return RefactorResult(
                success=False,
                message=f"Method {self.class_name}.{self.method_name} not found",
            )

        transformer = InsertAtMatch(
            pattern=pattern,
            code=code,
            position="before",
            scope="method",
            class_name=self.class_name,
            method_name=self.method_name,
        )
        return self.manipylate.transform_file(file_path, transformer)

    def insert_after_match(self, pattern: str, code: str) -> RefactorResult:
        """
        Insert code after a line matching a regex pattern.

        Parameters
        ----------
        pattern : str
            Regex pattern to match against line content.
        code : str
            Code to insert after the matching line.

        Returns
        -------
        RefactorResult
            Result of the operation.
        """
        file_path = self._find_method_file()
        if not file_path:
            return RefactorResult(
                success=False,
                message=f"Method {self.class_name}.{self.method_name} not found",
            )

        transformer = InsertAtMatch(
            pattern=pattern,
            code=code,
            position="after",
            scope="method",
            class_name=self.class_name,
            method_name=self.method_name,
        )
        return self.manipylate.transform_file(file_path, transformer)

    def replace_match(self, pattern: str, code: str) -> RefactorResult:
        """
        Replace a line matching a regex pattern with new code.

        Parameters
        ----------
        pattern : str
            Regex pattern to match against line content.
        code : str
            Code to replace the matching line with.

        Returns
        -------
        RefactorResult
            Result of the operation.
        """
        file_path = self._find_method_file()
        if not file_path:
            return RefactorResult(
                success=False,
                message=f"Method {self.class_name}.{self.method_name} not found",
            )

        transformer = InsertAtMatch(
            pattern=pattern,
            code=code,
            position="replace",
            scope="method",
            class_name=self.class_name,
            method_name=self.method_name,
        )
        return self.manipylate.transform_file(file_path, transformer)
