"""FunctionTarget for operations on module-level Python functions."""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst

from rejig.core.position import find_function_line, find_function_lines
from rejig.targets.base import ErrorResult, Result, Target
from rejig.transformers import (
    AddFunctionDecorator,
    AddLogging,
    AddParameter,
    ConvertToAsync,
    ConvertToSync,
    InferTypeHints,
    InsertAtMethodEnd,
    InsertAtMethodStart,
    RemoveParameter,
    RemoveTypeHints,
    RenameParameter,
    ReorderParameters,
    SetParameterType,
    SetReturnType,
    WrapWithTryExcept,
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
        """Line number where the function is defined (alias for start_line)."""
        return self.start_line

    @property
    def start_line(self) -> int | None:
        """Starting line number of this function definition (1-indexed)."""
        if self._line_number is None:
            self._find_function()
        return self._line_number

    @property
    def end_line(self) -> int | None:
        """Ending line number of this function definition (1-indexed)."""
        file_path = self._find_function()
        if not file_path:
            return None
        try:
            content = file_path.read_text()
            lines = find_function_lines(content, self.name)
            return lines[1] if lines else None
        except Exception:
            return None

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

    def remove_parameter(self, param_name: str) -> Result:
        """Remove a parameter from the function signature.

        Parameters
        ----------
        param_name : str
            Name of the parameter to remove.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> func.remove_parameter("deprecated_arg")
        """
        transformer = RemoveParameter(None, self.name, param_name)
        result = self._transform(transformer)

        if result.success and transformer.removed:
            return Result(
                success=True,
                message=f"Removed parameter {param_name} from {self.name}",
                files_changed=result.files_changed,
            )
        elif result.success:
            return self._operation_failed(
                "remove_parameter", f"Parameter '{param_name}' not found in {self.name}"
            )
        return result

    def rename_parameter(self, old_name: str, new_name: str) -> Result:
        """Rename a parameter in the function signature.

        Also updates all references to the parameter within the function body.

        Parameters
        ----------
        old_name : str
            Current name of the parameter.
        new_name : str
            New name for the parameter.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> func.rename_parameter("old_arg", "new_arg")
        """
        transformer = RenameParameter(None, self.name, old_name, new_name)
        result = self._transform(transformer)

        if result.success and transformer.renamed:
            return Result(
                success=True,
                message=f"Renamed parameter {old_name} to {new_name} in {self.name}",
                files_changed=result.files_changed,
            )
        elif result.success:
            return self._operation_failed(
                "rename_parameter", f"Parameter '{old_name}' not found in {self.name}"
            )
        return result

    def reorder_parameters(self, param_order: list[str]) -> Result:
        """Reorder parameters in the function signature.

        Parameters not in the order list are appended at the end in their
        original relative order.

        Parameters
        ----------
        param_order : list[str]
            Ordered list of parameter names defining the new order.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> func.reorder_parameters(["required", "optional", "extra"])
        """
        transformer = ReorderParameters(None, self.name, param_order)
        result = self._transform(transformer)

        if result.success and transformer.reordered:
            return Result(
                success=True,
                message=f"Reordered parameters in {self.name}",
                files_changed=result.files_changed,
            )
        return result

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

    # ===== Type hint operations =====

    def set_return_type(self, return_type: str) -> Result:
        """Set the return type annotation for this function.

        Parameters
        ----------
        return_type : str
            The return type annotation (e.g., "list[str]", "None").

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> func.set_return_type("list[str]")
        >>> func.set_return_type("dict[str, Any]")
        """
        transformer = SetReturnType(None, self.name, return_type)
        result = self._transform(transformer)

        if result.success and transformer.changed:
            return Result(
                success=True,
                message=f"Set return type of {self.name} to {return_type}",
                files_changed=result.files_changed,
            )
        return result

    def set_parameter_type(self, param_name: str, param_type: str) -> Result:
        """Set the type annotation for a parameter.

        Parameters
        ----------
        param_name : str
            Name of the parameter to annotate.
        param_type : str
            The type annotation (e.g., "dict[str, Any]").

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> func.set_parameter_type("data", "dict[str, Any]")
        >>> func.set_parameter_type("timeout", "int")
        """
        transformer = SetParameterType(None, self.name, param_name, param_type)
        result = self._transform(transformer)

        if result.success and transformer.changed:
            return Result(
                success=True,
                message=f"Set type of {param_name} to {param_type} in {self.name}",
                files_changed=result.files_changed,
            )
        return result

    def remove_type_hints(self) -> Result:
        """Remove all type hints from this function.

        Removes return type annotations and parameter type annotations.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> func.remove_type_hints()
        """
        transformer = RemoveTypeHints(None, self.name)
        result = self._transform(transformer)

        if result.success and transformer.changed:
            return Result(
                success=True,
                message=f"Removed type hints from {self.name}",
                files_changed=result.files_changed,
            )
        return result

    def infer_type_hints(self, overwrite: bool = False) -> Result:
        """Infer and add type hints based on defaults and name heuristics.

        Uses heuristics to infer types from:
        - Default parameter values (e.g., = 0 → int)
        - Parameter names (e.g., count → int, is_valid → bool)

        Parameters
        ----------
        overwrite : bool
            If True, overwrite existing type hints. Default False.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> func.infer_type_hints()
        >>> func.infer_type_hints(overwrite=True)
        """
        transformer = InferTypeHints(None, self.name, overwrite)
        result = self._transform(transformer)

        if result.success and transformer.changed:
            return Result(
                success=True,
                message=f"Inferred type hints for {self.name}",
                files_changed=result.files_changed,
            )
        return result

    # ===== Docstring operations =====

    @property
    def has_docstring(self) -> bool:
        """Check if this function has a docstring.

        Returns
        -------
        bool
            True if the function has a docstring.

        Examples
        --------
        >>> if not func.has_docstring:
        ...     func.generate_docstring()
        """
        file_path = self._find_function()
        if not file_path:
            return False

        try:
            from rejig.docstrings.parser import has_docstring as check_docstring

            content = file_path.read_text()
            tree = cst.parse_module(content)

            for node in tree.body:
                if isinstance(node, cst.FunctionDef) and node.name.value == self.name:
                    return check_docstring(node)
            return False
        except Exception:
            return False

    def get_docstring(self) -> Result:
        """Get the docstring of this function.

        Returns
        -------
        Result
            Result with docstring text in `data` field if successful.
            Returns empty string if no docstring exists.

        Examples
        --------
        >>> result = func.get_docstring()
        >>> if result.success and result.data:
        ...     print(result.data)
        """
        file_path = self._find_function()
        if not file_path:
            return self._operation_failed("get_docstring", f"Function '{self.name}' not found")

        try:
            from rejig.docstrings.parser import extract_docstring

            content = file_path.read_text()
            tree = cst.parse_module(content)

            for node in tree.body:
                if isinstance(node, cst.FunctionDef) and node.name.value == self.name:
                    docstring = extract_docstring(node)
                    return Result(success=True, message="OK", data=docstring or "")

            return self._operation_failed(
                "get_docstring", f"Function '{self.name}' not found in AST"
            )
        except Exception as e:
            return self._operation_failed("get_docstring", f"Failed to get docstring: {e}", e)

    def generate_docstring(
        self,
        style: str = "google",
        summary: str = "",
        overwrite: bool = False,
    ) -> Result:
        """Generate a docstring for this function.

        Creates a docstring from the function signature including
        parameters, return type, and raised exceptions.

        Parameters
        ----------
        style : str
            Docstring style: "google", "numpy", or "sphinx".
            Defaults to "google".
        summary : str
            Custom summary line. If empty, auto-generates from function name.
        overwrite : bool
            Whether to overwrite existing docstring. Default False.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> func.generate_docstring()
        >>> func.generate_docstring(style="numpy")
        >>> func.generate_docstring(summary="Process the input data.")
        """
        from rejig.docstrings.updater import AddDocstringTransformer

        transformer = AddDocstringTransformer(
            target_class=None,
            target_func=self.name,
            style=style,
            summary=summary,
            overwrite=overwrite,
        )
        result = self._transform(transformer)

        if result.success and transformer.added:
            return Result(
                success=True,
                message=f"Generated docstring for {self.name}",
                files_changed=result.files_changed,
            )
        return result

    def update_docstring_param(self, param_name: str, description: str) -> Result:
        """Update or add a parameter description in the docstring.

        Parameters
        ----------
        param_name : str
            Name of the parameter to document.
        description : str
            Description of the parameter.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> func.update_docstring_param("timeout", "Maximum wait time in seconds")
        """
        from rejig.docstrings.updater import UpdateDocstringTransformer

        transformer = UpdateDocstringTransformer(
            target_class=None,
            target_func=self.name,
            updates={"param": (param_name, description)},
        )
        result = self._transform(transformer)

        if result.success and transformer.updated:
            return Result(
                success=True,
                message=f"Updated docstring param {param_name} in {self.name}",
                files_changed=result.files_changed,
            )
        elif result.success:
            return self._operation_failed(
                "update_docstring_param",
                f"Function '{self.name}' has no docstring to update",
            )
        return result

    def add_docstring_raises(self, exception: str, description: str) -> Result:
        """Add a raises entry to the docstring.

        Parameters
        ----------
        exception : str
            Name of the exception (e.g., "ValueError").
        description : str
            Description of when the exception is raised.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> func.add_docstring_raises("ValueError", "If input is negative")
        """
        from rejig.docstrings.updater import UpdateDocstringTransformer

        transformer = UpdateDocstringTransformer(
            target_class=None,
            target_func=self.name,
            updates={"raises": (exception, description)},
        )
        result = self._transform(transformer)

        if result.success and transformer.updated:
            return Result(
                success=True,
                message=f"Added raises {exception} to {self.name}",
                files_changed=result.files_changed,
            )
        elif result.success:
            return self._operation_failed(
                "add_docstring_raises",
                f"Function '{self.name}' has no docstring to update",
            )
        return result

    def add_docstring_example(self, example: str) -> Result:
        """Add an example to the docstring.

        Parameters
        ----------
        example : str
            Example code (can include >>> and output).

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> func.add_docstring_example(">>> process(5)\\n10")
        """
        from rejig.docstrings.updater import UpdateDocstringTransformer

        transformer = UpdateDocstringTransformer(
            target_class=None,
            target_func=self.name,
            updates={"example": example},
        )
        result = self._transform(transformer)

        if result.success and transformer.updated:
            return Result(
                success=True,
                message=f"Added example to {self.name}",
                files_changed=result.files_changed,
            )
        elif result.success:
            return self._operation_failed(
                "add_docstring_example",
                f"Function '{self.name}' has no docstring to update",
            )
        return result

    def add_docstring_returns(self, description: str) -> Result:
        """Add or update the returns section in the docstring.

        Parameters
        ----------
        description : str
            Description of the return value.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> func.add_docstring_returns("The processed result")
        """
        from rejig.docstrings.updater import UpdateDocstringTransformer

        transformer = UpdateDocstringTransformer(
            target_class=None,
            target_func=self.name,
            updates={"returns": description},
        )
        result = self._transform(transformer)

        if result.success and transformer.updated:
            return Result(
                success=True,
                message=f"Updated returns in {self.name}",
                files_changed=result.files_changed,
            )
        elif result.success:
            return self._operation_failed(
                "add_docstring_returns",
                f"Function '{self.name}' has no docstring to update",
            )
        return result

    # ===== Async/sync conversion =====

    def convert_to_async(self) -> Result:
        """Convert this function to async.

        Adds the `async` keyword to the function definition.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> func.convert_to_async()
        """
        transformer = ConvertToAsync(None, self.name)
        result = self._transform(transformer)

        if result.success and transformer.converted:
            return Result(
                success=True,
                message=f"Converted {self.name} to async",
                files_changed=result.files_changed,
            )
        elif result.success:
            return self._operation_failed(
                "convert_to_async", f"Function '{self.name}' is already async"
            )
        return result

    def convert_to_sync(self) -> Result:
        """Convert this function from async to sync.

        Removes the `async` keyword and all `await` expressions.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> func.convert_to_sync()
        """
        transformer = ConvertToSync(None, self.name)
        result = self._transform(transformer)

        if result.success and transformer.converted:
            return Result(
                success=True,
                message=f"Converted {self.name} to sync",
                files_changed=result.files_changed,
            )
        elif result.success:
            return self._operation_failed(
                "convert_to_sync", f"Function '{self.name}' is not async"
            )
        return result

    # ===== Decorator convenience methods =====

    def add_retry_decorator(
        self,
        max_attempts: int = 3,
        exceptions: list[str] | None = None,
    ) -> Result:
        """Add a retry decorator to this function.

        Parameters
        ----------
        max_attempts : int
            Maximum number of retry attempts. Defaults to 3.
        exceptions : list[str] | None
            List of exception types to catch for retry.
            Defaults to ["Exception"].

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> func.add_retry_decorator(max_attempts=3, exceptions=["ConnectionError"])
        """
        exc_list = exceptions or ["Exception"]
        exc_str = ", ".join(exc_list)
        decorator = f"retry(max_attempts={max_attempts}, exceptions=({exc_str},))"
        return self.add_decorator(decorator)

    def add_caching_decorator(self, ttl: int | None = None) -> Result:
        """Add a caching decorator to this function.

        Parameters
        ----------
        ttl : int | None
            Time-to-live in seconds. If None, uses lru_cache without maxsize.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> func.add_caching_decorator()
        >>> func.add_caching_decorator(ttl=300)
        """
        if ttl is not None:
            decorator = f"cache(ttl={ttl})"
        else:
            decorator = "lru_cache(maxsize=None)"
        return self.add_decorator(decorator)

    def add_timing_decorator(self) -> Result:
        """Add a timing decorator to this function.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> func.add_timing_decorator()
        """
        return self.add_decorator("timing")

    # ===== Error handling =====

    def wrap_with_try_except(
        self,
        exceptions: list[str],
        handler: str,
    ) -> Result:
        """Wrap the function body with a try/except block.

        Parameters
        ----------
        exceptions : list[str]
            List of exception types to catch.
        handler : str
            Handler code to execute in the except block.
            Use 'e' to reference the caught exception.
            Separate multiple statements with semicolons.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> func.wrap_with_try_except(
        ...     ["ValueError", "TypeError"],
        ...     "logger.error(f'Error: {e}'); raise"
        ... )
        """
        transformer = WrapWithTryExcept(None, self.name, exceptions, handler)
        result = self._transform(transformer)

        if result.success and transformer.wrapped:
            return Result(
                success=True,
                message=f"Wrapped {self.name} with try/except",
                files_changed=result.files_changed,
            )
        elif result.success:
            return self._operation_failed(
                "wrap_with_try_except",
                f"Function '{self.name}' is already wrapped or has no body",
            )
        return result

    # ===== Logging =====

    def add_logging(
        self,
        level: str = "debug",
        include_args: bool = False,
        logger_name: str = "logger",
    ) -> Result:
        """Add logging statement at the start of this function.

        Parameters
        ----------
        level : str
            Logging level: "debug", "info", "warning", "error", "critical".
            Defaults to "debug".
        include_args : bool
            If True, include argument values in the log message.
            Defaults to False.
        logger_name : str
            Name of the logger variable. Defaults to "logger".

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> func.add_logging(level="debug", include_args=True)
        """
        transformer = AddLogging(None, self.name, level, include_args, logger_name)
        result = self._transform(transformer)

        if result.success and transformer.added:
            return Result(
                success=True,
                message=f"Added logging to {self.name}",
                files_changed=result.files_changed,
            )
        return result
