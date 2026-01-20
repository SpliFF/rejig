"""MethodTarget for operations on class methods."""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst

from rejig.core.position import find_method_line, find_method_lines
from rejig.targets.base import Result, Target
from rejig.transformers import (
    AddFirstParameter,
    AddMethodDecorator,
    AddParameter,
    InferTypeHints,
    InsertAtMatch,
    InsertAtMethodEnd,
    InsertAtMethodStart,
    RemoveMethodDecorator,
    RemoveTypeHints,
    RenameMethod,
    ReplaceIdentifier,
    SetParameterType,
    SetReturnType,
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
        """Line number where the method is defined (alias for start_line)."""
        return self.start_line

    @property
    def start_line(self) -> int | None:
        """Starting line number of this method definition (1-indexed)."""
        if self._line_number is None:
            self._find_method()
        return self._line_number

    @property
    def end_line(self) -> int | None:
        """Ending line number of this method definition (1-indexed)."""
        file_path = self._find_method()
        if not file_path:
            return None
        try:
            content = file_path.read_text()
            lines = find_method_lines(content, self.class_name, self.name)
            return lines[1] if lines else None
        except Exception:
            return None

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

    def extract_to_function(self, name: str) -> Result:
        """Extract this method to a module-level function.

        The method is converted to a standalone function, and the method
        is replaced with a call to that function. The first parameter
        (self/cls) is preserved.

        Parameters
        ----------
        name : str
            Name for the extracted function.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> result = method.extract_to_function("process_user_data")
        >>> if result.success:
        ...     func = rj.find_function("process_user_data")
        """
        file_path = self._find_method()
        if not file_path:
            return self._operation_failed(
                "extract_to_function", f"Method '{self.class_name}.{self.name}' not found"
            )

        try:
            content = file_path.read_text()
            tree = cst.parse_module(content)

            class MethodExtractor(cst.CSTTransformer):
                def __init__(self, target_class: str, target_method: str, func_name: str):
                    self.target_class = target_class
                    self.target_method = target_method
                    self.func_name = func_name
                    self.in_target_class = False
                    self.extracted_func: cst.FunctionDef | None = None
                    self.extracted = False

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
                ) -> cst.FunctionDef:
                    if (
                        self.in_target_class
                        and original_node.name.value == self.target_method
                    ):
                        # Save the method as a function with the new name
                        # Remove class-specific decorators
                        decorators = [
                            d
                            for d in original_node.decorators
                            if not self._is_class_decorator(d)
                        ]

                        # Create the extracted function (keep body unchanged, dedented later)
                        self.extracted_func = original_node.with_changes(
                            name=cst.Name(self.func_name),
                            decorators=decorators,
                        )
                        self.extracted = True

                        # Replace method body with call to extracted function
                        # Get first param name (self/cls)
                        first_param = "self"
                        if original_node.params.params:
                            first_param = original_node.params.params[0].name.value

                        # Build args list for the call
                        param_names = self._get_param_names(original_node.params)

                        call_args = ", ".join(param_names)
                        call_stmt = cst.parse_statement(
                            f"return {self.func_name}({call_args})"
                        )

                        return updated_node.with_changes(
                            body=cst.IndentedBlock(body=[call_stmt])
                        )

                    return updated_node

                def _is_class_decorator(self, decorator: cst.Decorator) -> bool:
                    """Check if a decorator is class-specific (staticmethod, classmethod)."""
                    if isinstance(decorator.decorator, cst.Name):
                        return decorator.decorator.value in ("staticmethod", "classmethod")
                    return False

                def _get_param_names(self, params: cst.Parameters) -> list[str]:
                    """Get all parameter names from a Parameters node."""
                    names: list[str] = []
                    for param in params.params:
                        names.append(param.name.value)
                    for param in params.kwonly_params:
                        names.append(f"{param.name.value}={param.name.value}")
                    if params.star_arg and isinstance(params.star_arg, cst.Param):
                        names.append(f"*{params.star_arg.name.value}")
                    if params.star_kwarg:
                        names.append(f"**{params.star_kwarg.name.value}")
                    return names

                def leave_Module(
                    self, original_node: cst.Module, updated_node: cst.Module
                ) -> cst.Module:
                    if self.extracted_func is None:
                        return updated_node

                    # Insert the extracted function before the class
                    new_body: list[cst.BaseStatement] = []
                    for stmt in updated_node.body:
                        if isinstance(stmt, cst.ClassDef) and stmt.name.value == self.target_class:
                            # Insert extracted function before the class
                            new_body.append(self.extracted_func)
                            new_body.append(cst.EmptyLine(whitespace=cst.SimpleWhitespace("")))
                        new_body.append(stmt)
                    return updated_node.with_changes(body=new_body)

            extractor = MethodExtractor(self.class_name, self.name, name)
            new_tree = tree.visit(extractor)

            if not extractor.extracted:
                return self._operation_failed(
                    "extract_to_function",
                    f"Could not extract method {self.class_name}.{self.name}",
                )

            new_content = new_tree.code

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would extract {self.class_name}.{self.name} to function {name}",
                    files_changed=[file_path],
                )

            file_path.write_text(new_content)
            return Result(
                success=True,
                message=f"Extracted {self.class_name}.{self.name} to function {name}",
                files_changed=[file_path],
            )
        except Exception as e:
            return self._operation_failed(
                "extract_to_function", f"Failed to extract method: {e}", e
            )

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

    # ===== Type hint operations =====

    def set_return_type(self, return_type: str) -> Result:
        """Set the return type annotation for this method.

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
        >>> method.set_return_type("list[str]")
        >>> method.set_return_type("Result")
        """
        transformer = SetReturnType(self.class_name, self.name, return_type)
        result = self._transform(transformer)

        if result.success and transformer.changed:
            return Result(
                success=True,
                message=f"Set return type of {self.class_name}.{self.name} to {return_type}",
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
        >>> method.set_parameter_type("data", "dict[str, Any]")
        >>> method.set_parameter_type("timeout", "int")
        """
        transformer = SetParameterType(self.class_name, self.name, param_name, param_type)
        result = self._transform(transformer)

        if result.success and transformer.changed:
            return Result(
                success=True,
                message=f"Set type of {param_name} to {param_type} in {self.class_name}.{self.name}",
                files_changed=result.files_changed,
            )
        return result

    def remove_type_hints(self) -> Result:
        """Remove all type hints from this method.

        Removes return type annotations and parameter type annotations.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> method.remove_type_hints()
        """
        transformer = RemoveTypeHints(self.class_name, self.name)
        result = self._transform(transformer)

        if result.success and transformer.changed:
            return Result(
                success=True,
                message=f"Removed type hints from {self.class_name}.{self.name}",
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
        >>> method.infer_type_hints()
        >>> method.infer_type_hints(overwrite=True)
        """
        transformer = InferTypeHints(self.class_name, self.name, overwrite)
        result = self._transform(transformer)

        if result.success and transformer.changed:
            return Result(
                success=True,
                message=f"Inferred type hints for {self.class_name}.{self.name}",
                files_changed=result.files_changed,
            )
        return result
