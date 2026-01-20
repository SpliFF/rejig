"""FunctionTarget for operations on module-level Python functions."""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst

from rejig.core.position import find_function_line
from rejig.targets.base import ErrorResult, Result, Target
from rejig.transformers import (
    AddFunctionDecorator,
    AddParameter,
    InsertAtMethodEnd,
    InsertAtMethodStart,
)

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class FunctionTarget(Target):
    """Target for a module-level Python function.

    Provides operations for modifying function body, decorators,
    parameters, and more.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    name : str
        Name of the function.
    file_path : Path | None
        Optional path to the file containing the function.
        If not provided, the function will be searched across all files.

    Examples
    --------
    >>> func = rj.file("utils.py").find_function("process_data")
    >>> func.insert_statement("logger.info('Processing started')")
    >>> func.add_decorator("timing")
    """

    def __init__(
        self,
        rejig: Rejig,
        name: str,
        file_path: Path | None = None,
    ) -> None:
        super().__init__(rejig)
        self.name = name
        self._file_path = file_path
        self._line_number: int | None = None

    @property
    def file_path(self) -> Path | None:
        """Path to the file containing this function."""
        if self._file_path is None:
            self._find_function()
        return self._file_path

    @property
    def line_number(self) -> int | None:
        """Line number where the function is defined."""
        if self._line_number is None:
            self._find_function()
        return self._line_number

    def __repr__(self) -> str:
        if self._file_path:
            return f"FunctionTarget({self.name!r}, file={self._file_path})"
        return f"FunctionTarget({self.name!r})"

    def _find_function(self) -> Path | None:
        """Find the file containing this function."""
        if self._file_path is not None:
            if self._verify_function_in_file(self._file_path):
                return self._file_path
            return None

        # Search across all files - look for module-level function
        for fp in self._rejig.files:
            try:
                content = fp.read_text()
                line_number = find_function_line(content, self.name)
                if line_number is not None:
                    self._file_path = fp
                    self._line_number = line_number
                    return fp
            except Exception:
                continue
        return None

    def _verify_function_in_file(self, file_path: Path) -> bool:
        """Verify the function exists in the specified file."""
        try:
            content = file_path.read_text()
            line_number = find_function_line(content, self.name)
            if line_number is not None:
                self._line_number = line_number
                return True
        except Exception:
            pass
        return False

    def exists(self) -> bool:
        """Check if this function exists."""
        return self._find_function() is not None

    def get_content(self) -> Result:
        """Get the source code of this function.

        Returns
        -------
        Result
            Result with function source code in `data` field if successful.
        """
        file_path = self._find_function()
        if not file_path:
            return self._operation_failed("get_content", f"Function '{self.name}' not found")

        try:
            content = file_path.read_text()
            tree = cst.parse_module(content)

            for node in tree.body:
                if isinstance(node, cst.FunctionDef) and node.name.value == self.name:
                    func_code = tree.code_for_node(node)
                    return Result(success=True, message="OK", data=func_code)

            return self._operation_failed(
                "get_content", f"Function '{self.name}' not found in AST"
            )
        except Exception as e:
            return self._operation_failed("get_content", f"Failed to get function content: {e}", e)

    def _transform(self, transformer: cst.CSTTransformer) -> Result:
        """Apply a LibCST transformer to the file containing this function."""
        file_path = self._find_function()
        if not file_path:
            return self._operation_failed("transform", f"Function '{self.name}' not found")

        try:
            content = file_path.read_text()
            tree = cst.parse_module(content)
            new_tree = tree.visit(transformer)
            new_content = new_tree.code

            if new_content == content:
                return Result(success=True, message=f"No changes needed for {self.name}")

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would modify function {self.name}",
                    files_changed=[file_path],
                )

            file_path.write_text(new_content)
            return Result(
                success=True,
                message=f"Modified function {self.name}",
                files_changed=[file_path],
            )
        except Exception as e:
            return self._operation_failed("transform", f"Transformation failed: {e}", e)

    # ===== Modification operations =====

    def insert_statement(self, statement: str, position: str = "start") -> Result:
        """Insert a statement into the function body.

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
        >>> func.insert_statement("logger.info('Starting')")
        >>> func.insert_statement("return result", position="end")
        """
        # Use transformers with no class context for module-level functions
        if position == "end":
            transformer = InsertAtMethodEnd(None, self.name, statement)
        else:
            transformer = InsertAtMethodStart(None, self.name, statement)
        return self._transform(transformer)

    def add_parameter(
        self,
        param_name: str,
        type_annotation: str | None = None,
        default_value: str | None = None,
        position: str = "end",
    ) -> Result:
        """Add a parameter to the function signature.

        Parameters
        ----------
        param_name : str
            Name of the parameter to add.
        type_annotation : str | None
            Type annotation for the parameter.
        default_value : str | None
            Default value for the parameter.
        position : str
            Where to add: "start", "end".
            Defaults to "end".

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> func.add_parameter("timeout", "int", "30")
        >>> func.add_parameter("verbose", "bool", "False")
        """
        # Use None for class_name to target module-level functions
        transformer = AddParameter(
            None,
            self.name,
            param_name,
            type_annotation,
            default_value,
            position,
        )
        return self._transform(transformer)

    def add_decorator(self, decorator: str) -> Result:
        """Add a decorator to this function.

        Parameters
        ----------
        decorator : str
            Decorator to add (without @ prefix). Can include arguments,
            e.g., "lru_cache(maxsize=128)".

        Returns
        -------
        Result
            Result of the operation.
        """
        transformer = AddFunctionDecorator(self.name, decorator)
        result = self._transform(transformer)

        if result.success and transformer.added:
            return Result(
                success=True,
                message=f"Added @{decorator} to {self.name}",
                files_changed=result.files_changed,
            )
        return result

    def remove_decorator(self, decorator: str) -> Result:
        """Remove a decorator from this function.

        Parameters
        ----------
        decorator : str
            Decorator to remove (without @ prefix).

        Returns
        -------
        Result
            Result of the operation.
        """
        file_path = self._find_function()
        if not file_path:
            return self._operation_failed("remove_decorator", f"Function '{self.name}' not found")

        try:
            content = file_path.read_text()
            # Remove the decorator line before the function
            pattern = rf"^@{re.escape(decorator)}\n(def\s+{re.escape(self.name)}\b)"
            new_content = re.sub(pattern, r"\1", content, flags=re.MULTILINE)

            if new_content == content:
                return self._operation_failed(
                    "remove_decorator", f"Decorator @{decorator} not found on {self.name}"
                )

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would remove @{decorator} from {self.name}",
                    files_changed=[file_path],
                )

            file_path.write_text(new_content)
            return Result(
                success=True,
                message=f"Removed @{decorator} from {self.name}",
                files_changed=[file_path],
            )
        except Exception as e:
            return self._operation_failed("remove_decorator", f"Failed to remove decorator: {e}", e)

    def rename(self, new_name: str) -> Result:
        """Rename this function.

        Note: This only renames the function definition. It does not update
        calls to the function throughout the codebase.

        Parameters
        ----------
        new_name : str
            New name for the function.

        Returns
        -------
        Result
            Result of the operation.
        """
        file_path = self._find_function()
        if not file_path:
            return self._operation_failed("rename", f"Function '{self.name}' not found")

        try:
            content = file_path.read_text()
            pattern = rf"^(def\s+){re.escape(self.name)}(\s*\()"
            replacement = rf"\1{new_name}\2"
            new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

            if new_content == content:
                return self._operation_failed("rename", f"Could not rename {self.name}")

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would rename {self.name} to {new_name}",
                    files_changed=[file_path],
                )

            file_path.write_text(new_content)
            old_name = self.name
            self.name = new_name
            return Result(
                success=True,
                message=f"Renamed {old_name} to {new_name}",
                files_changed=[file_path],
            )
        except Exception as e:
            return self._operation_failed("rename", f"Failed to rename function: {e}", e)

    def move_to(self, destination: str | Target) -> Result:
        """Move this function to a different module using rope.

        Parameters
        ----------
        destination : str | Target
            Destination module path (e.g., 'utils.helpers').

        Returns
        -------
        Result
            Result of the operation.
        """
        file_path = self._find_function()
        if not file_path:
            return self._operation_failed("move_to", f"Function '{self.name}' not found")

        dest_module = str(destination) if isinstance(destination, Target) else destination

        if hasattr(self._rejig, "move_function"):
            return self._rejig.move_function(file_path, self.name, dest_module)

        return self._unsupported_operation("move_to")

    def delete(self) -> Result:
        """Delete this function from the file.

        Returns
        -------
        Result
            Result of the operation.
        """
        file_path = self._find_function()
        if not file_path:
            return self._operation_failed("delete", f"Function '{self.name}' not found")

        try:
            content = file_path.read_text()
            tree = cst.parse_module(content)

            class FunctionRemover(cst.CSTTransformer):
                def __init__(self, func_name: str):
                    self.func_name = func_name
                    self.removed = False

                def leave_FunctionDef(
                    self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
                ) -> cst.FunctionDef | cst.RemovalSentinel:
                    if original_node.name.value == self.func_name:
                        self.removed = True
                        return cst.RemovalSentinel.REMOVE
                    return updated_node

            remover = FunctionRemover(self.name)
            new_tree = tree.visit(remover)

            if not remover.removed:
                return self._operation_failed("delete", f"Could not remove function {self.name}")

            new_content = new_tree.code

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would delete function {self.name}",
                    files_changed=[file_path],
                )

            file_path.write_text(new_content)
            return Result(
                success=True,
                message=f"Deleted function {self.name}",
                files_changed=[file_path],
            )
        except Exception as e:
            return self._operation_failed("delete", f"Failed to delete function: {e}", e)
