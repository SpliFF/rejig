"""MethodTarget for operations on class methods."""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst

from rejig.core.position import find_method_line
from rejig.targets.base import Result, Target
from rejig.transformers import (
    AddFirstParameter,
    AddMethodDecorator,
    AddParameter,
    InsertAtMatch,
    InsertAtMethodEnd,
    InsertAtMethodStart,
    RemoveMethodDecorator,
    RenameMethod,
    ReplaceIdentifier,
    StaticToClassMethod,
)

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class MethodTarget(Target):
    """Target for a method within a Python class.

    Provides operations for modifying method body, decorators,
    parameters, and more.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    class_name : str
        Name of the class containing the method.
    name : str
        Name of the method.
    file_path : Path | None
        Optional path to the file containing the class.

    Examples
    --------
    >>> method = rj.file("models.py").find_class("User").find_method("save")
    >>> method.insert_statement("self.validate()")
    >>> method.add_decorator("transaction.atomic")
    """

    def __init__(
        self,
        rejig: Rejig,
        class_name: str,
        name: str,
        file_path: Path | None = None,
    ) -> None:
        super().__init__(rejig)
        self.class_name = class_name
        self.name = name
        self._file_path = file_path
        self._line_number: int | None = None

    @property
    def file_path(self) -> Path | None:
        """Path to the file containing this method."""
        if self._file_path is None:
            self._find_method()
        return self._file_path

    @property
    def line_number(self) -> int | None:
        """Line number where the method is defined."""
        if self._line_number is None:
            self._find_method()
        return self._line_number

    def __repr__(self) -> str:
        if self._file_path:
            return f"MethodTarget({self.class_name}.{self.name!r}, file={self._file_path})"
        return f"MethodTarget({self.class_name}.{self.name!r})"

    def _find_method(self) -> Path | None:
        """Find the file containing the class with this method."""
        if self._file_path is not None:
            if self._verify_method_in_file(self._file_path):
                return self._file_path
            return None

        class_pattern = rf"\bclass\s+{re.escape(self.class_name)}\b"
        method_pattern = rf"\bdef\s+{re.escape(self.name)}\b"

        for fp in self._rejig.files:
            try:
                content = fp.read_text()
                if re.search(class_pattern, content) and re.search(method_pattern, content):
                    # Verify it's actually a method of this class
                    if self._verify_method_in_file(fp):
                        self._file_path = fp
                        return fp
            except Exception:
                continue
        return None

    def _verify_method_in_file(self, file_path: Path) -> bool:
        """Verify the method exists in the specified class in the file."""
        try:
            content = file_path.read_text()
            line_number = find_method_line(content, self.class_name, self.name)
            if line_number is not None:
                self._line_number = line_number
                return True
        except Exception:
            pass
        return False

    def exists(self) -> bool:
        """Check if this method exists."""
        return self._find_method() is not None

    def get_content(self) -> Result:
        """Get the source code of this method.

        Returns
        -------
        Result
            Result with method source code in `data` field if successful.
        """
        file_path = self._find_method()
        if not file_path:
            return self._operation_failed(
                "get_content", f"Method '{self.class_name}.{self.name}' not found"
            )

        try:
            content = file_path.read_text()
            tree = cst.parse_module(content)

            class MethodExtractor(cst.CSTVisitor):
                def __init__(self, target_class: str, target_method: str):
                    self.target_class = target_class
                    self.target_method = target_method
                    self.in_target_class = False
                    self.method_code: str | None = None

                def visit_ClassDef(self, node: cst.ClassDef) -> bool:
                    if node.name.value == self.target_class:
                        self.in_target_class = True
                    return True

                def leave_ClassDef(self, node: cst.ClassDef) -> None:
                    if node.name.value == self.target_class:
                        self.in_target_class = False

                def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
                    if self.in_target_class and node.name.value == self.target_method:
                        self.method_code = tree.code_for_node(node)
                    return False

            extractor = MethodExtractor(self.class_name, self.name)
            tree.walk(extractor)

            if extractor.method_code:
                return Result(success=True, message="OK", data=extractor.method_code)

            return self._operation_failed(
                "get_content", f"Method '{self.class_name}.{self.name}' not found in AST"
            )
        except Exception as e:
            return self._operation_failed("get_content", f"Failed to get method content: {e}", e)

    def _transform(self, transformer: cst.CSTTransformer) -> Result:
        """Apply a LibCST transformer to the file containing this method."""
        file_path = self._find_method()
        if not file_path:
            return self._operation_failed(
                "transform", f"Method '{self.class_name}.{self.name}' not found"
            )

        try:
            content = file_path.read_text()
            tree = cst.parse_module(content)
            new_tree = tree.visit(transformer)
            new_content = new_tree.code

            if new_content == content:
                return Result(
                    success=True, message=f"No changes needed for {self.class_name}.{self.name}"
                )

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would modify method {self.class_name}.{self.name}",
                    files_changed=[file_path],
                )

            file_path.write_text(new_content)
            return Result(
                success=True,
                message=f"Modified method {self.class_name}.{self.name}",
                files_changed=[file_path],
            )
        except Exception as e:
            return self._operation_failed("transform", f"Transformation failed: {e}", e)

    # ===== Modification operations =====

    def insert_statement(self, statement: str, position: str = "start") -> Result:
        """Insert a statement into the method body.

        Parameters
        ----------
        statement : str
            Python statement to insert.
        position : str
            Where to insert: "start" (after docstring) or "end".
            Defaults to "start".

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> method.insert_statement("self.validate()")
        >>> method.insert_statement("return result", position="end")
        """
        if position == "end":
            transformer = InsertAtMethodEnd(self.class_name, self.name, statement)
        else:
            transformer = InsertAtMethodStart(self.class_name, self.name, statement)
        return self._transform(transformer)

    def add_parameter(
        self,
        param_name: str,
        type_annotation: str | None = None,
        default_value: str | None = None,
        position: str = "end",
    ) -> Result:
        """Add a parameter to the method signature.

        Parameters
        ----------
        param_name : str
            Name of the parameter to add.
        type_annotation : str | None
            Type annotation for the parameter.
        default_value : str | None
            Default value for the parameter.
        position : str
            Where to add: "start" (after self/cls), "end".
            Defaults to "end".

        Returns
        -------
        Result
            Result of the operation.
        """
        transformer = AddParameter(
            self.class_name,
            self.name,
            param_name,
            type_annotation,
            default_value,
            position,
        )
        return self._transform(transformer)

    def replace_identifier(self, old_name: str, new_name: str) -> Result:
        """Replace identifier references within the method.

        Parameters
        ----------
        old_name : str
            Identifier to replace.
        new_name : str
            New identifier name (can include dots, e.g., "cls.cache").

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> method.replace_identifier("cache", "cls._cache")
        """
        transformer = ReplaceIdentifier(self.class_name, self.name, old_name, new_name)
        return self._transform(transformer)

    def convert_to_classmethod(self) -> Result:
        """Convert a staticmethod to a classmethod and add cls parameter.

        Returns
        -------
        Result
            Result of the operation.
        """
        # First convert decorator
        transformer1 = StaticToClassMethod(self.class_name, self.name)
        result1 = self._transform(transformer1)

        if not result1.success:
            return result1

        # Then add cls parameter
        transformer2 = AddFirstParameter(self.class_name, self.name, "cls")
        return self._transform(transformer2)

    def add_decorator(self, decorator: str) -> Result:
        """Add a decorator to this method.

        Parameters
        ----------
        decorator : str
            Decorator to add (without @ prefix).

        Returns
        -------
        Result
            Result of the operation.
        """
        transformer = AddMethodDecorator(self.class_name, self.name, decorator)
        return self._transform(transformer)

    def remove_decorator(self, decorator: str) -> Result:
        """Remove a decorator from this method.

        Parameters
        ----------
        decorator : str
            Decorator to remove (without @ prefix).

        Returns
        -------
        Result
            Result of the operation.
        """
        transformer = RemoveMethodDecorator(self.class_name, self.name, decorator)
        return self._transform(transformer)

    def rename(self, new_name: str) -> Result:
        """Rename this method.

        Note: This only renames the method definition. It does not update
        calls to the method throughout the codebase.

        Parameters
        ----------
        new_name : str
            New name for the method.

        Returns
        -------
        Result
            Result of the operation.
        """
        transformer = RenameMethod(self.class_name, self.name, new_name)
        result = self._transform(transformer)

        if result.success and transformer.renamed:
            old_name = self.name
            self.name = new_name
            return Result(
                success=True,
                message=f"Renamed method {old_name} to {new_name}",
                files_changed=result.files_changed,
            )
        return result

    def insert_before_match(self, pattern: str, code: str) -> Result:
        """Insert code before a line matching a regex pattern.

        Parameters
        ----------
        pattern : str
            Regex pattern to match against line content.
        code : str
            Code to insert before the matching line.

        Returns
        -------
        Result
            Result of the operation.
        """
        transformer = InsertAtMatch(
            pattern=pattern,
            code=code,
            position="before",
            scope="method",
            class_name=self.class_name,
            method_name=self.name,
        )
        return self._transform(transformer)

    def insert_after_match(self, pattern: str, code: str) -> Result:
        """Insert code after a line matching a regex pattern.

        Parameters
        ----------
        pattern : str
            Regex pattern to match against line content.
        code : str
            Code to insert after the matching line.

        Returns
        -------
        Result
            Result of the operation.
        """
        transformer = InsertAtMatch(
            pattern=pattern,
            code=code,
            position="after",
            scope="method",
            class_name=self.class_name,
            method_name=self.name,
        )
        return self._transform(transformer)

    def replace_match(self, pattern: str, code: str) -> Result:
        """Replace a line matching a regex pattern with new code.

        Parameters
        ----------
        pattern : str
            Regex pattern to match against line content.
        code : str
            Code to replace the matching line with.

        Returns
        -------
        Result
            Result of the operation.
        """
        transformer = InsertAtMatch(
            pattern=pattern,
            code=code,
            position="replace",
            scope="method",
            class_name=self.class_name,
            method_name=self.name,
        )
        return self._transform(transformer)

    def delete(self) -> Result:
        """Delete this method from the class.

        Returns
        -------
        Result
            Result of the operation.
        """
        file_path = self._find_method()
        if not file_path:
            return self._operation_failed(
                "delete", f"Method '{self.class_name}.{self.name}' not found"
            )

        try:
            content = file_path.read_text()
            tree = cst.parse_module(content)

            class MethodRemover(cst.CSTTransformer):
                def __init__(self, target_class: str, target_method: str):
                    self.target_class = target_class
                    self.target_method = target_method
                    self.in_target_class = False
                    self.removed = False

                def visit_ClassDef(self, node: cst.ClassDef) -> bool:
                    if node.name.value == self.target_class:
                        self.in_target_class = True
                    return True

                def leave_ClassDef(
                    self, original_node: cst.ClassDef, updated_node: cst.ClassDef
                ) -> cst.ClassDef:
                    if original_node.name.value == self.target_class:
                        self.in_target_class = False
                    return updated_node

                def leave_FunctionDef(
                    self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
                ) -> cst.FunctionDef | cst.RemovalSentinel:
                    if (
                        self.in_target_class
                        and original_node.name.value == self.target_method
                    ):
                        self.removed = True
                        return cst.RemovalSentinel.REMOVE
                    return updated_node

            remover = MethodRemover(self.class_name, self.name)
            new_tree = tree.visit(remover)

            if not remover.removed:
                return self._operation_failed(
                    "delete", f"Could not remove method {self.class_name}.{self.name}"
                )

            new_content = new_tree.code

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would delete method {self.class_name}.{self.name}",
                    files_changed=[file_path],
                )

            file_path.write_text(new_content)
            return Result(
                success=True,
                message=f"Deleted method {self.class_name}.{self.name}",
                files_changed=[file_path],
            )
        except Exception as e:
            return self._operation_failed("delete", f"Failed to delete method: {e}", e)
