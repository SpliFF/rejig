"""ClassTarget for operations on Python class definitions."""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import libcst as cst

from rejig.core.position import find_class_line
from rejig.targets.base import ErrorResult, ErrorTarget, Result, Target, TargetList
from rejig.transformers import (
    AddClassAttribute,
    AddClassDecorator,
    RemoveClassAttribute,
    RemoveDecorator,
    RenameClass,
)

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig
    from rejig.targets.python.method import MethodTarget


class ClassTarget(Target):
    """Target for a Python class definition.

    Provides operations for modifying class attributes, methods,
    decorators, and more.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    name : str
        Name of the class.
    file_path : Path | None
        Optional path to the file containing the class.
        If not provided, the class will be searched across all files.

    Examples
    --------
    >>> cls = rj.file("models.py").find_class("User")
    >>> cls.add_attribute("email", "str", '""')
    >>> cls.find_method("save").insert_statement("self.validate()")
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
        """Path to the file containing this class."""
        if self._file_path is None:
            self._find_class()
        return self._file_path

    @property
    def line_number(self) -> int | None:
        """Line number where the class is defined."""
        if self._line_number is None:
            self._find_class()
        return self._line_number

    def __repr__(self) -> str:
        if self._file_path:
            return f"ClassTarget({self.name!r}, file={self._file_path})"
        return f"ClassTarget({self.name!r})"

    def _find_class(self) -> Path | None:
        """Find the file containing this class."""
        if self._file_path is not None:
            # Verify the class exists in the specified file
            if self._verify_class_in_file(self._file_path):
                return self._file_path
            return None

        # Search across all files in the project
        for fp in self._rejig.files:
            try:
                content = fp.read_text()
                line_number = find_class_line(content, self.name)
                if line_number is not None:
                    self._file_path = fp
                    self._line_number = line_number
                    return fp
            except Exception:
                continue
        return None

    def _verify_class_in_file(self, file_path: Path) -> bool:
        """Verify the class exists in the specified file."""
        try:
            content = file_path.read_text()
            line_number = find_class_line(content, self.name)
            if line_number is not None:
                self._line_number = line_number
                return True
        except Exception:
            pass
        return False

    def exists(self) -> bool:
        """Check if this class exists."""
        return self._find_class() is not None

    def get_content(self) -> Result:
        """Get the source code of this class.

        Returns
        -------
        Result
            Result with class source code in `data` field if successful.
        """
        file_path = self._find_class()
        if not file_path:
            return self._operation_failed("get_content", f"Class '{self.name}' not found")

        try:
            content = file_path.read_text()
            tree = cst.parse_module(content)

            for node in tree.body:
                if isinstance(node, cst.ClassDef) and node.name.value == self.name:
                    class_code = tree.code_for_node(node)
                    return Result(success=True, message="OK", data=class_code)

            return self._operation_failed("get_content", f"Class '{self.name}' not found in AST")
        except Exception as e:
            return self._operation_failed("get_content", f"Failed to get class content: {e}", e)

    def _transform(self, transformer: cst.CSTTransformer) -> Result:
        """Apply a LibCST transformer to the file containing this class."""
        file_path = self._find_class()
        if not file_path:
            return self._operation_failed("transform", f"Class '{self.name}' not found")

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
                    message=f"[DRY RUN] Would modify class {self.name}",
                    files_changed=[file_path],
                )

            file_path.write_text(new_content)
            return Result(
                success=True,
                message=f"Modified class {self.name}",
                files_changed=[file_path],
            )
        except Exception as e:
            return self._operation_failed("transform", f"Transformation failed: {e}", e)

    # ===== Navigation methods =====

    def find_method(self, name: str) -> Target:
        """Find a method within this class.

        Parameters
        ----------
        name : str
            Name of the method to find.

        Returns
        -------
        MethodTarget | ErrorTarget
            MethodTarget if found, ErrorTarget otherwise.
        """
        from rejig.targets.python.method import MethodTarget

        file_path = self._find_class()
        if not file_path:
            return ErrorTarget(self._rejig, f"Class '{self.name}' not found")

        target = MethodTarget(self._rejig, self.name, name, file_path=file_path)
        if target.exists():
            return target
        return ErrorTarget(self._rejig, f"Method '{name}' not found in class '{self.name}'")

    def find_methods(self, pattern: str | None = None) -> TargetList[Target]:
        """Find all methods in this class, optionally filtered by pattern.

        Parameters
        ----------
        pattern : str | None
            Optional regex pattern to filter method names.

        Returns
        -------
        TargetList[MethodTarget]
            List of matching MethodTarget objects.
        """
        from rejig.targets.python.method import MethodTarget

        file_path = self._find_class()
        if not file_path:
            return TargetList(self._rejig, [])

        regex = re.compile(pattern) if pattern else None
        targets: list[Target] = []

        try:
            content = file_path.read_text()
            tree = cst.parse_module(content)

            class MethodFinder(cst.CSTVisitor):
                def __init__(self, target_class: str):
                    self.target_class = target_class
                    self.in_target_class = False
                    self.methods: list[str] = []

                def visit_ClassDef(self, node: cst.ClassDef) -> bool:
                    if node.name.value == self.target_class:
                        self.in_target_class = True
                    return True

                def leave_ClassDef(self, node: cst.ClassDef) -> None:
                    if node.name.value == self.target_class:
                        self.in_target_class = False

                def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
                    if self.in_target_class:
                        self.methods.append(node.name.value)
                    return False

            finder = MethodFinder(self.name)
            tree.walk(finder)

            for method_name in finder.methods:
                if regex is None or regex.search(method_name):
                    targets.append(MethodTarget(self._rejig, self.name, method_name, file_path=file_path))

        except Exception:
            pass

        return TargetList(self._rejig, targets)

    # ===== Modification operations =====

    def add_attribute(self, name: str, type_hint: str, default: str = "None") -> Result:
        """Add a class-level attribute with type annotation.

        Parameters
        ----------
        name : str
            Name of the attribute to add.
        type_hint : str
            Type annotation for the attribute.
        default : str
            Default value for the attribute (default: "None").

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> cls.add_attribute("count", "int", "0")
        >>> cls.add_attribute("cache", "dict[str, Any] | None", "None")
        """
        transformer = AddClassAttribute(self.name, name, type_hint, default)
        result = self._transform(transformer)

        if result.success and transformer.added:
            return Result(
                success=True,
                message=f"Added attribute {name} to {self.name}",
                files_changed=result.files_changed,
            )
        return result

    def remove_attribute(self, attr_name: str) -> Result:
        """Remove a class-level attribute.

        Parameters
        ----------
        attr_name : str
            Name of the attribute to remove.

        Returns
        -------
        Result
            Result of the operation.
        """
        transformer = RemoveClassAttribute(self.name, attr_name)
        return self._transform(transformer)

    def add_method(self, name: str, body: str = "pass", **kwargs: Any) -> Result:
        """Add a method to this class.

        Parameters
        ----------
        name : str
            Name of the method to add.
        body : str
            Body of the method (default: "pass").
        **kwargs
            Additional options:
            - params: Parameter list after self (string)
            - return_type: Return type annotation
            - decorators: Decorators (list of strings without @)

        Returns
        -------
        Result
            Result of the operation.
        """
        file_path = self._find_class()
        if not file_path:
            return self._operation_failed("add_method", f"Class '{self.name}' not found")

        params = kwargs.get("params", "")
        return_type = kwargs.get("return_type", "")
        decorators = kwargs.get("decorators", [])

        # Build method definition
        method_def = ""
        if decorators:
            for dec in decorators:
                method_def += f"    @{dec}\n"

        if params:
            param_str = f"self, {params}"
        else:
            param_str = "self"

        if return_type:
            method_def += f"    def {name}({param_str}) -> {return_type}:\n"
        else:
            method_def += f"    def {name}({param_str}):\n"

        # Indent body
        for line in body.splitlines():
            method_def += f"        {line}\n"

        # Find the class and insert the method at the end
        try:
            content = file_path.read_text()

            # Find class definition and its end
            class_pattern = rf"^class\s+{re.escape(self.name)}\b[^:]*:"
            match = re.search(class_pattern, content, re.MULTILINE)
            if not match:
                return self._operation_failed("add_method", f"Could not find class {self.name}")

            # Find the end of the class (next class/function at same indentation or EOF)
            lines = content.splitlines(keepends=True)
            class_line_idx = content[: match.start()].count("\n")

            # Find the last line of the class
            insert_idx = len(lines)
            for i in range(class_line_idx + 1, len(lines)):
                line = lines[i]
                # Check if this is a new top-level definition
                if line and not line[0].isspace() and line.strip():
                    insert_idx = i
                    break

            # Insert the method before the next definition
            lines.insert(insert_idx, "\n" + method_def)
            new_content = "".join(lines)

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would add method {name} to {self.name}",
                    files_changed=[file_path],
                )

            file_path.write_text(new_content)
            return Result(
                success=True,
                message=f"Added method {name} to {self.name}",
                files_changed=[file_path],
            )
        except Exception as e:
            return self._operation_failed("add_method", f"Failed to add method: {e}", e)

    def rename(self, new_name: str) -> Result:
        """Rename this class.

        Note: This only renames the class definition. It does not update
        references to the class throughout the codebase.

        Parameters
        ----------
        new_name : str
            New name for the class.

        Returns
        -------
        Result
            Result of the operation.
        """
        transformer = RenameClass(self.name, new_name)
        result = self._transform(transformer)

        if result.success and transformer.renamed:
            old_name = self.name
            self.name = new_name
            return Result(
                success=True,
                message=f"Renamed class {old_name} to {new_name}",
                files_changed=result.files_changed,
            )
        return result

    def add_decorator(self, decorator: str) -> Result:
        """Add a decorator to this class.

        Parameters
        ----------
        decorator : str
            Decorator to add (without @ prefix). Can include arguments,
            e.g., "dataclass(frozen=True)".

        Returns
        -------
        Result
            Result of the operation.
        """
        transformer = AddClassDecorator(self.name, decorator)
        result = self._transform(transformer)

        if result.success and transformer.added:
            return Result(
                success=True,
                message=f"Added @{decorator} to {self.name}",
                files_changed=result.files_changed,
            )
        return result

    def remove_decorator(self, decorator: str) -> Result:
        """Remove a decorator from this class.

        Parameters
        ----------
        decorator : str
            Decorator to remove (without @ prefix).

        Returns
        -------
        Result
            Result of the operation.
        """
        transformer = RemoveDecorator(self.name, decorator, target_type="class")
        return self._transform(transformer)

    def move_to(self, destination: str | Target) -> Result:
        """Move this class to a different module using rope.

        Parameters
        ----------
        destination : str | Target
            Destination module path (e.g., 'myapp.models').

        Returns
        -------
        Result
            Result of the operation.
        """
        file_path = self._find_class()
        if not file_path:
            return self._operation_failed("move_to", f"Class '{self.name}' not found")

        dest_module = str(destination) if isinstance(destination, Target) else destination

        # Use the rejig's move_class method if available
        if hasattr(self._rejig, "move_class"):
            return self._rejig.move_class(file_path, self.name, dest_module)

        return self._unsupported_operation("move_to")

    def delete(self) -> Result:
        """Delete this class from the file.

        Returns
        -------
        Result
            Result of the operation.
        """
        file_path = self._find_class()
        if not file_path:
            return self._operation_failed("delete", f"Class '{self.name}' not found")

        try:
            content = file_path.read_text()
            tree = cst.parse_module(content)

            class ClassRemover(cst.CSTTransformer):
                def __init__(self, class_name: str):
                    self.class_name = class_name
                    self.removed = False

                def leave_ClassDef(
                    self, original_node: cst.ClassDef, updated_node: cst.ClassDef
                ) -> cst.ClassDef | cst.RemovalSentinel:
                    if original_node.name.value == self.class_name:
                        self.removed = True
                        return cst.RemovalSentinel.REMOVE
                    return updated_node

            remover = ClassRemover(self.name)
            new_tree = tree.visit(remover)

            if not remover.removed:
                return self._operation_failed("delete", f"Could not remove class {self.name}")

            new_content = new_tree.code

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would delete class {self.name}",
                    files_changed=[file_path],
                )

            file_path.write_text(new_content)
            return Result(
                success=True,
                message=f"Deleted class {self.name}",
                files_changed=[file_path],
            )
        except Exception as e:
            return self._operation_failed("delete", f"Failed to delete class: {e}", e)
