"""ClassTarget for operations on Python class definitions."""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import libcst as cst

from rejig.core.position import find_class_line, find_class_lines
from rejig.targets.base import ErrorResult, ErrorTarget, Result, Target, TargetList
from rejig.transformers import (
    AddClassAttribute,
    AddClassDecorator,
    InferTypeHints,
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
        """Line number where the class is defined (alias for start_line)."""
        return self.start_line

    @property
    def start_line(self) -> int | None:
        """Starting line number of this class definition (1-indexed)."""
        if self._line_number is None:
            self._find_class()
        return self._line_number

    @property
    def end_line(self) -> int | None:
        """Ending line number of this class definition (1-indexed)."""
        file_path = self._find_class()
        if not file_path:
            return None
        try:
            content = file_path.read_text()
            lines = find_class_lines(content, self.name)
            return lines[1] if lines else None
        except Exception:
            return None

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

    def get_source(self) -> Result:
        """Get just the class signature (without body).

        Returns
        -------
        Result
            Result with class signature in `data` field if successful.
            The signature includes decorators, class name, and base classes.

        Examples
        --------
        >>> sig = cls.get_source()
        >>> if sig.success:
        ...     print(sig.data)  # "class MyClass(BaseClass):"
        """
        file_path = self._find_class()
        if not file_path:
            return self._operation_failed("get_source", f"Class '{self.name}' not found")

        try:
            content = file_path.read_text()
            tree = cst.parse_module(content)

            for node in tree.body:
                if isinstance(node, cst.ClassDef) and node.name.value == self.name:
                    # Build signature from decorators and class header
                    signature_parts: list[str] = []

                    # Add decorators
                    for decorator in node.decorators:
                        dec_code = tree.code_for_node(decorator)
                        signature_parts.append(dec_code.strip())

                    # Build class header: "class Name(bases):"
                    bases_code = ""
                    if node.bases:
                        # Extract just the value from each Arg, not including trailing commas
                        bases_list = [tree.code_for_node(base.value).strip() for base in node.bases]
                        bases_code = f"({', '.join(bases_list)})"
                    elif isinstance(node.lpar, cst.LeftParen):
                        # Has empty parens: class Foo():
                        bases_code = "()"

                    class_header = f"class {self.name}{bases_code}:"
                    signature_parts.append(class_header)

                    signature = "\n".join(signature_parts)
                    return Result(success=True, message="OK", data=signature)

            return self._operation_failed("get_source", f"Class '{self.name}' not found in AST")
        except Exception as e:
            return self._operation_failed("get_source", f"Failed to get class signature: {e}", e)

    def duplicate(self, new_name: str) -> Result:
        """Duplicate this class with a new name.

        Creates a copy of the class definition with the specified new name.
        The duplicate is inserted immediately after the original class.

        Parameters
        ----------
        new_name : str
            Name for the duplicated class.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> result = cls.duplicate("UserV2")
        >>> if result.success:
        ...     new_cls = rj.find_class("UserV2")
        """
        file_path = self._find_class()
        if not file_path:
            return self._operation_failed("duplicate", f"Class '{self.name}' not found")

        try:
            content = file_path.read_text()
            tree = cst.parse_module(content)

            class ClassDuplicator(cst.CSTTransformer):
                def __init__(self, original_name: str, new_name: str):
                    self.original_name = original_name
                    self.new_name = new_name
                    self.duplicated = False

                def leave_Module(
                    self, original_node: cst.Module, updated_node: cst.Module
                ) -> cst.Module:
                    new_body: list[cst.BaseStatement] = []
                    for stmt in updated_node.body:
                        new_body.append(stmt)
                        if isinstance(stmt, cst.ClassDef) and stmt.name.value == self.original_name:
                            # Create a duplicate with new name
                            new_class = stmt.with_changes(name=cst.Name(self.new_name))
                            new_body.append(cst.EmptyLine(whitespace=cst.SimpleWhitespace("")))
                            new_body.append(new_class)
                            self.duplicated = True
                    return updated_node.with_changes(body=new_body)

            duplicator = ClassDuplicator(self.name, new_name)
            new_tree = tree.visit(duplicator)

            if not duplicator.duplicated:
                return self._operation_failed("duplicate", f"Could not duplicate class {self.name}")

            new_content = new_tree.code

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would duplicate class {self.name} as {new_name}",
                    files_changed=[file_path],
                )

            file_path.write_text(new_content)
            return Result(
                success=True,
                message=f"Duplicated class {self.name} as {new_name}",
                files_changed=[file_path],
            )
        except Exception as e:
            return self._operation_failed("duplicate", f"Failed to duplicate class: {e}", e)

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
            wrapper = cst.MetadataWrapper(tree)
            wrapper.visit(finder)

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

    # ===== Type hint operations =====

    def add_type_hints_from_defaults(self, overwrite: bool = False) -> Result:
        """Add type hints to methods based on parameter defaults.

        Infers type hints from:
        - Default parameter values (e.g., = 0 → int)
        - Parameter names (e.g., count → int, is_valid → bool)

        This primarily targets the __init__ method to infer instance
        attribute types from default values.

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
        >>> cls.add_type_hints_from_defaults()
        >>> cls.add_type_hints_from_defaults(overwrite=True)
        """
        file_path = self._find_class()
        if not file_path:
            return self._operation_failed(
                "add_type_hints_from_defaults", f"Class '{self.name}' not found"
            )

        # Get all methods in this class
        methods = self.find_methods()
        if not methods:
            return Result(
                success=True,
                message=f"No methods found in {self.name}",
            )

        # Apply type inference to each method
        changed_count = 0
        for method in methods:
            transformer = InferTypeHints(self.name, method.name, overwrite)
            result = self._transform(transformer)
            if result.success and transformer.changed:
                changed_count += 1

        if changed_count == 0:
            return Result(
                success=True,
                message=f"No type hints inferred for {self.name}",
            )

        return Result(
            success=True,
            message=f"Inferred type hints for {changed_count} methods in {self.name}",
            files_changed=[file_path],
        )

    # ===== Docstring operations =====

    @property
    def has_docstring(self) -> bool:
        """Check if this class has a docstring.

        Returns
        -------
        bool
            True if the class has a docstring.

        Examples
        --------
        >>> if not cls.has_docstring:
        ...     cls.generate_docstring()
        """
        file_path = self._find_class()
        if not file_path:
            return False

        try:
            from rejig.docstrings.parser import has_docstring as check_docstring

            content = file_path.read_text()
            tree = cst.parse_module(content)

            for node in tree.body:
                if isinstance(node, cst.ClassDef) and node.name.value == self.name:
                    return check_docstring(node)
            return False
        except Exception:
            return False

    def get_docstring(self) -> Result:
        """Get the docstring of this class.

        Returns
        -------
        Result
            Result with docstring text in `data` field if successful.
            Returns empty string if no docstring exists.

        Examples
        --------
        >>> result = cls.get_docstring()
        >>> if result.success and result.data:
        ...     print(result.data)
        """
        file_path = self._find_class()
        if not file_path:
            return self._operation_failed("get_docstring", f"Class '{self.name}' not found")

        try:
            from rejig.docstrings.parser import extract_docstring

            content = file_path.read_text()
            tree = cst.parse_module(content)

            for node in tree.body:
                if isinstance(node, cst.ClassDef) and node.name.value == self.name:
                    docstring = extract_docstring(node)
                    return Result(success=True, message="OK", data=docstring or "")

            return self._operation_failed(
                "get_docstring", f"Class '{self.name}' not found in AST"
            )
        except Exception as e:
            return self._operation_failed("get_docstring", f"Failed to get docstring: {e}", e)

    def generate_docstrings(
        self,
        style: str = "google",
        overwrite: bool = False,
    ) -> Result:
        """Generate docstrings for all methods in this class.

        Parameters
        ----------
        style : str
            Docstring style: "google", "numpy", or "sphinx".
            Defaults to "google".
        overwrite : bool
            Whether to overwrite existing docstrings. Default False.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> cls.generate_docstrings()
        >>> cls.generate_docstrings(style="numpy")
        """
        file_path = self._find_class()
        if not file_path:
            return self._operation_failed("generate_docstrings", f"Class '{self.name}' not found")

        from rejig.docstrings.updater import AddDocstringTransformer

        methods = self.find_methods()
        if not methods:
            return Result(
                success=True,
                message=f"No methods found in {self.name}",
            )

        added_count = 0
        for method in methods:
            transformer = AddDocstringTransformer(
                target_class=self.name,
                target_func=method.name,
                style=style,
                overwrite=overwrite,
            )
            result = self._transform(transformer)
            if result.success and transformer.added:
                added_count += 1

        if added_count == 0:
            return Result(
                success=True,
                message=f"No docstrings added for {self.name} (all methods already have docstrings)",
            )

        return Result(
            success=True,
            message=f"Generated docstrings for {added_count} methods in {self.name}",
            files_changed=[file_path],
        )

    def find_methods_without_docstrings(self) -> TargetList[Target]:
        """Find all methods in this class that don't have docstrings.

        Returns
        -------
        TargetList[MethodTarget]
            List of methods without docstrings.

        Examples
        --------
        >>> missing = cls.find_methods_without_docstrings()
        >>> for method in missing:
        ...     method.generate_docstring()
        """
        from rejig.targets.python.method import MethodTarget

        file_path = self._find_class()
        if not file_path:
            return TargetList(self._rejig, [])

        try:
            from rejig.docstrings.parser import has_docstring as check_docstring

            content = file_path.read_text()
            tree = cst.parse_module(content)
            targets: list[Target] = []

            class MethodFinder(cst.CSTVisitor):
                def __init__(self, target_class: str):
                    self.target_class = target_class
                    self.in_target_class = False
                    self.methods_without_docs: list[str] = []

                def visit_ClassDef(self, node: cst.ClassDef) -> bool:
                    if node.name.value == self.target_class:
                        self.in_target_class = True
                    return True

                def leave_ClassDef(self, node: cst.ClassDef) -> None:
                    if node.name.value == self.target_class:
                        self.in_target_class = False

                def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
                    if self.in_target_class and not check_docstring(node):
                        self.methods_without_docs.append(node.name.value)
                    return False

            finder = MethodFinder(self.name)
            wrapper = cst.MetadataWrapper(tree)
            wrapper.visit(finder)

            for method_name in finder.methods_without_docs:
                targets.append(MethodTarget(self._rejig, self.name, method_name, file_path=file_path))

            return TargetList(self._rejig, targets)
        except Exception:
            return TargetList(self._rejig, [])

    # ===== Class transformation operations =====

    def convert_to_dataclass(
        self,
        frozen: bool = False,
        slots: bool = False,
    ) -> Result:
        """Convert this class to a dataclass.

        Adds @dataclass decorator and converts instance attributes to
        class-level annotated attributes. Removes __init__ if it only
        does attribute assignment.

        Parameters
        ----------
        frozen : bool
            If True, add frozen=True to decorator. Default False.
        slots : bool
            If True, add slots=True (Python 3.10+). Default False.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> cls.convert_to_dataclass()
        >>> cls.convert_to_dataclass(frozen=True, slots=True)
        """
        from rejig.generation import ConvertToDataclassTransformer

        transformer = ConvertToDataclassTransformer(
            self.name, frozen=frozen, slots=slots
        )
        result = self._transform(transformer)

        if result.success and transformer.converted:
            return Result(
                success=True,
                message=f"Converted {self.name} to dataclass",
                files_changed=result.files_changed,
            )
        return result

    def convert_from_dataclass(
        self,
        generate_repr: bool = True,
        generate_eq: bool = True,
        generate_hash: bool = False,
    ) -> Result:
        """Convert this dataclass back to a regular class.

        Removes @dataclass decorator and generates explicit dunder methods.

        Parameters
        ----------
        generate_repr : bool
            If True, generate __repr__ method. Default True.
        generate_eq : bool
            If True, generate __eq__ method. Default True.
        generate_hash : bool
            If True, generate __hash__ method. Default False.

        Returns
        -------
        Result
            Result of the operation.
        """
        from rejig.generation import ConvertFromDataclassTransformer

        transformer = ConvertFromDataclassTransformer(
            self.name,
            generate_repr=generate_repr,
            generate_eq=generate_eq,
            generate_hash=generate_hash,
        )
        result = self._transform(transformer)

        if result.success and transformer.converted:
            return Result(
                success=True,
                message=f"Converted {self.name} from dataclass to regular class",
                files_changed=result.files_changed,
            )
        return result

    def convert_to_typed_dict(self, total: bool = True) -> Result:
        """Convert this class to a TypedDict.

        Parameters
        ----------
        total : bool
            If True, all keys are required. Default True.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> cls.convert_to_typed_dict()
        >>> cls.convert_to_typed_dict(total=False)
        """
        from rejig.generation import ConvertToTypedDictTransformer

        transformer = ConvertToTypedDictTransformer(self.name, total=total)
        result = self._transform(transformer)

        if result.success and transformer.converted:
            return Result(
                success=True,
                message=f"Converted {self.name} to TypedDict",
                files_changed=result.files_changed,
            )
        return result

    def convert_to_named_tuple(self) -> Result:
        """Convert this class to a NamedTuple.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> cls.convert_to_named_tuple()
        """
        from rejig.generation import ConvertToNamedTupleTransformer

        transformer = ConvertToNamedTupleTransformer(self.name)
        result = self._transform(transformer)

        if result.success and transformer.converted:
            return Result(
                success=True,
                message=f"Converted {self.name} to NamedTuple",
                files_changed=result.files_changed,
            )
        return result

    def generate_init(self, overwrite: bool = False) -> Result:
        """Generate __init__ method from class attributes.

        Parameters
        ----------
        overwrite : bool
            If True, replace existing __init__. Default False.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> cls.generate_init()
        >>> cls.generate_init(overwrite=True)
        """
        from rejig.generation import GenerateInitTransformer

        transformer = GenerateInitTransformer(self.name, overwrite=overwrite)
        result = self._transform(transformer)

        if result.success and transformer.added:
            return Result(
                success=True,
                message=f"Generated __init__ for {self.name}",
                files_changed=result.files_changed,
            )
        return result

    def generate_repr(self, overwrite: bool = False) -> Result:
        """Generate __repr__ method from class attributes.

        Parameters
        ----------
        overwrite : bool
            If True, replace existing __repr__. Default False.

        Returns
        -------
        Result
            Result of the operation.
        """
        from rejig.generation import GenerateReprTransformer

        transformer = GenerateReprTransformer(self.name, overwrite=overwrite)
        result = self._transform(transformer)

        if result.success and transformer.added:
            return Result(
                success=True,
                message=f"Generated __repr__ for {self.name}",
                files_changed=result.files_changed,
            )
        return result

    def generate_eq(self, overwrite: bool = False) -> Result:
        """Generate __eq__ method from class attributes.

        Parameters
        ----------
        overwrite : bool
            If True, replace existing __eq__. Default False.

        Returns
        -------
        Result
            Result of the operation.
        """
        from rejig.generation import GenerateEqTransformer

        transformer = GenerateEqTransformer(self.name, overwrite=overwrite)
        result = self._transform(transformer)

        if result.success and transformer.added:
            return Result(
                success=True,
                message=f"Generated __eq__ for {self.name}",
                files_changed=result.files_changed,
            )
        return result

    def generate_hash(self, overwrite: bool = False) -> Result:
        """Generate __hash__ method from class attributes.

        Parameters
        ----------
        overwrite : bool
            If True, replace existing __hash__. Default False.

        Returns
        -------
        Result
            Result of the operation.
        """
        from rejig.generation import GenerateHashTransformer

        transformer = GenerateHashTransformer(self.name, overwrite=overwrite)
        result = self._transform(transformer)

        if result.success and transformer.added:
            return Result(
                success=True,
                message=f"Generated __hash__ for {self.name}",
                files_changed=result.files_changed,
            )
        return result

    def generate_all_dunders(self, overwrite: bool = False) -> Result:
        """Generate all common dunder methods (__init__, __repr__, __eq__, __hash__).

        Parameters
        ----------
        overwrite : bool
            If True, replace existing dunders. Default False.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> cls.generate_all_dunders()
        """
        from rejig.generation import (
            GenerateEqTransformer,
            GenerateHashTransformer,
            GenerateInitTransformer,
            GenerateReprTransformer,
        )

        file_path = self._find_class()
        if not file_path:
            return self._operation_failed("generate_all_dunders", f"Class '{self.name}' not found")

        added_methods: list[str] = []

        for TransformerClass, method_name in [
            (GenerateInitTransformer, "__init__"),
            (GenerateReprTransformer, "__repr__"),
            (GenerateEqTransformer, "__eq__"),
            (GenerateHashTransformer, "__hash__"),
        ]:
            transformer = TransformerClass(self.name, overwrite=overwrite)
            result = self._transform(transformer)
            if result.success and transformer.added:
                added_methods.append(method_name)

        if not added_methods:
            return Result(
                success=True,
                message=f"No dunder methods added to {self.name} (all already exist)",
            )

        return Result(
            success=True,
            message=f"Generated {', '.join(added_methods)} for {self.name}",
            files_changed=[file_path],
        )

    # ===== Test generation operations =====

    def generate_test_file(
        self,
        output_path: str | Path,
        include_setup: bool = True,
        include_teardown: bool = False,
    ) -> Result:
        """Generate a complete test file for this class.

        Creates a pytest test file with test stubs for all public methods.

        Parameters
        ----------
        output_path : str | Path
            Path where the test file should be written.
        include_setup : bool
            Whether to include a setup_method. Default True.
        include_teardown : bool
            Whether to include a teardown_method. Default False.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> cls.generate_test_file("tests/test_calculator.py")
        >>> cls.generate_test_file("tests/test_user.py", include_teardown=True)
        """
        from rejig.generation.tests import TestGenerator, extract_class_signatures

        file_path = self._find_class()
        if not file_path:
            return self._operation_failed("generate_test_file", f"Class '{self.name}' not found")

        try:
            content = file_path.read_text()
            methods, class_docstring = extract_class_signatures(content, self.name)

            if not methods:
                return Result(
                    success=True,
                    message=f"No methods found in class {self.name}",
                )

            # Determine module path for import
            module_path = None
            if self._rejig.root_path:
                try:
                    rel_path = file_path.relative_to(self._rejig.root_path)
                    # Convert path to module format
                    module_path = str(rel_path.with_suffix("")).replace("/", ".").replace("\\", ".")
                    # Remove leading src. if present
                    if module_path.startswith("src."):
                        module_path = module_path[4:]
                except ValueError:
                    pass

            generator = TestGenerator()
            test_content = generator.generate_class_test_file(
                self.name,
                methods,
                class_docstring=class_docstring,
                module_path=module_path,
                include_setup=include_setup,
                include_teardown=include_teardown,
            )

            output_path = Path(output_path)
            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would create test file at {output_path}",
                    data=test_content,
                )

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(test_content)

            return Result(
                success=True,
                message=f"Generated test file for {self.name} at {output_path}",
                files_changed=[output_path],
                data=test_content,
            )
        except Exception as e:
            return self._operation_failed("generate_test_file", f"Failed to generate test file: {e}", e)

    def generate_test_stub(self, test_dir: str | Path | None = None) -> Result:
        """Generate a test stub in the default location.

        Creates a test file in the tests/ directory mirroring the source structure.

        Parameters
        ----------
        test_dir : str | Path | None
            Base directory for tests. Defaults to "tests" in project root.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> cls.generate_test_stub()  # Creates tests/test_mymodule.py
        >>> cls.generate_test_stub("test_suite/unit")
        """
        file_path = self._find_class()
        if not file_path:
            return self._operation_failed("generate_test_stub", f"Class '{self.name}' not found")

        # Determine output path
        if test_dir is None:
            test_dir = self._rejig.root_path / "tests" if self._rejig.root_path else Path("tests")
        else:
            test_dir = Path(test_dir)

        # Generate test filename from source filename
        test_filename = f"test_{file_path.stem}.py"
        output_path = test_dir / test_filename

        return self.generate_test_file(output_path)

    def extract_protocol(
        self,
        protocol_name: str,
        methods: list[str] | None = None,
    ) -> Result:
        """Extract a Protocol from this class.

        Creates a new Protocol class with specified method signatures
        and inserts it before the original class.

        Parameters
        ----------
        protocol_name : str
            Name for the new Protocol class.
        methods : list[str] | None
            Method names to include. If None, includes all public methods.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> cls.extract_protocol("UserProtocol")
        >>> cls.extract_protocol("ValidatorProtocol", methods=["validate", "check"])
        """
        from rejig.generation import ExtractProtocolTransformer

        transformer = ExtractProtocolTransformer(
            self.name, protocol_name, methods=methods
        )
        result = self._transform(transformer)

        if result.success and transformer.extracted:
            return Result(
                success=True,
                message=f"Extracted Protocol '{protocol_name}' from {self.name}",
                files_changed=result.files_changed,
            )
        return result

    def extract_abstract_base(
        self,
        abc_name: str | None = None,
        methods: list[str] | None = None,
    ) -> Result:
        """Extract an Abstract Base Class from this class.

        Creates a new ABC with abstract method signatures and makes
        this class inherit from it.

        Parameters
        ----------
        abc_name : str | None
            Name for the new ABC. Defaults to "Base{ClassName}".
        methods : list[str] | None
            Method names to make abstract. If None, uses all public methods.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> cls.extract_abstract_base()
        >>> cls.extract_abstract_base("AbstractUser", methods=["save", "validate"])
        """
        from rejig.generation import ExtractAbstractBaseTransformer

        if abc_name is None:
            abc_name = f"Base{self.name}"

        transformer = ExtractAbstractBaseTransformer(
            self.name, abc_name, methods=methods
        )
        result = self._transform(transformer)

        if result.success and transformer.extracted:
            return Result(
                success=True,
                message=f"Extracted ABC '{abc_name}' from {self.name}",
                files_changed=result.files_changed,
            )
        return result

    def convert_attribute_to_property(
        self,
        attr_name: str,
        getter: bool = True,
        setter: bool = True,
    ) -> Result:
        """Convert a class attribute to a property with getter/setter.

        Parameters
        ----------
        attr_name : str
            Name of the attribute to convert.
        getter : bool
            If True, generate a getter property. Default True.
        setter : bool
            If True, generate a setter. Default True.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> cls.convert_attribute_to_property("_name")
        >>> cls.convert_attribute_to_property("value", setter=False)
        """
        from rejig.generation import ConvertAttributeToPropertyTransformer

        transformer = ConvertAttributeToPropertyTransformer(
            self.name, attr_name, getter=getter, setter=setter
        )
        result = self._transform(transformer)

        if result.success and transformer.converted:
            return Result(
                success=True,
                message=f"Converted attribute '{attr_name}' to property in {self.name}",
                files_changed=result.files_changed,
            )
        return result

    def add_property(
        self,
        prop_name: str,
        getter: str,
        setter: str | None = None,
        return_type: str | None = None,
    ) -> Result:
        """Add a property to this class.

        Parameters
        ----------
        prop_name : str
            Name of the property.
        getter : str
            Body of the getter (return statement or expression).
        setter : str | None
            Body of the setter. If None, property is read-only.
        return_type : str | None
            Return type annotation for the getter.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> cls.add_property("full_name", "f'{self.first} {self.last}'", return_type="str")
        >>> cls.add_property("age", "self._age", "self._age = value", "int")
        """
        from rejig.generation import AddPropertyTransformer

        transformer = AddPropertyTransformer(
            self.name, prop_name, getter, setter_body=setter, return_type=return_type
        )
        result = self._transform(transformer)

        if result.success and transformer.added:
            return Result(
                success=True,
                message=f"Added property '{prop_name}' to {self.name}",
                files_changed=result.files_changed,
            )
        return result

    def add_base_class(self, base_class: str, position: str = "last") -> Result:
        """Add a base class to this class.

        Parameters
        ----------
        base_class : str
            Name of the base class to add.
        position : str
            Where to add: "first" or "last". Default "last".

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> cls.add_base_class("BaseModel")
        >>> cls.add_base_class("ABC", position="first")
        """
        from rejig.generation import AddBaseClassTransformer

        transformer = AddBaseClassTransformer(
            self.name, base_class, position=position
        )
        result = self._transform(transformer)

        if result.success and transformer.added:
            return Result(
                success=True,
                message=f"Added base class '{base_class}' to {self.name}",
                files_changed=result.files_changed,
            )
        return result

    def remove_base_class(self, base_class: str) -> Result:
        """Remove a base class from this class.

        Parameters
        ----------
        base_class : str
            Name of the base class to remove.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> cls.remove_base_class("OldBase")
        """
        from rejig.generation import RemoveBaseClassTransformer

        transformer = RemoveBaseClassTransformer(self.name, base_class)
        result = self._transform(transformer)

        if result.success and transformer.removed:
            return Result(
                success=True,
                message=f"Removed base class '{base_class}' from {self.name}",
                files_changed=result.files_changed,
            )
        return result

    def add_mixin(self, mixin_class: str) -> Result:
        """Add a mixin class to this class.

        Mixins are added at the beginning of the base class list
        following Python MRO conventions.

        Parameters
        ----------
        mixin_class : str
            Name of the mixin class to add.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> cls.add_mixin("LoggingMixin")
        """
        from rejig.generation import AddMixinTransformer

        transformer = AddMixinTransformer(self.name, mixin_class)
        result = self._transform(transformer)

        if result.success and transformer.added:
            return Result(
                success=True,
                message=f"Added mixin '{mixin_class}' to {self.name}",
                files_changed=result.files_changed,
            )
        return result

    # ===== Code modernization operations =====

    def convert_to_context_manager(
        self,
        enter_body: str | None = None,
        exit_body: str | None = None,
    ) -> Result:
        """Convert this class to a context manager by adding __enter__/__exit__.

        If the class has open/connect methods, uses them in __enter__.
        If the class has close/disconnect methods, uses them in __exit__.
        Otherwise, returns self in __enter__ and passes in __exit__.

        Parameters
        ----------
        enter_body : str | None
            Custom body for __enter__ method. If None, auto-generates.
        exit_body : str | None
            Custom body for __exit__ method. If None, auto-generates.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> cls.convert_to_context_manager()
        >>> cls.convert_to_context_manager(
        ...     enter_body="self._conn = self.connect()\\nreturn self._conn",
        ...     exit_body="self._conn.close()"
        ... )
        """
        from rejig.modernize import ConvertToContextManagerTransformer

        transformer = ConvertToContextManagerTransformer(
            self.name, enter_body=enter_body, exit_body=exit_body
        )
        result = self._transform(transformer)

        if result.success and transformer.converted:
            return Result(
                success=True,
                message=f"Converted {self.name} to context manager",
                files_changed=result.files_changed,
            )
        elif result.success:
            return Result(
                success=True,
                message=f"{self.name} is already a context manager",
            )
        return result

    def remove_object_base(self) -> Result:
        """Remove unnecessary (object) base class from this class.

        In Python 3, all classes implicitly inherit from object, so
        explicitly inheriting from object is unnecessary.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> cls.remove_object_base()  # class Foo(object): → class Foo:
        """
        from rejig.generation import RemoveBaseClassTransformer

        transformer = RemoveBaseClassTransformer(self.name, "object")
        result = self._transform(transformer)

        if result.success and transformer.removed:
            return Result(
                success=True,
                message=f"Removed 'object' base class from {self.name}",
                files_changed=result.files_changed,
            )
        return Result(
            success=True,
            message=f"{self.name} does not inherit from object",
        )

    # ===== Directive operations =====

    def add_no_cover(self) -> Result:
        """Add pragma: no cover to exclude this class from coverage.

        Adds the pragma comment to the class definition line.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> cls.add_no_cover()
        """
        file_path = self._find_class()
        if not file_path:
            return self._operation_failed("add_no_cover", f"Class '{self.name}' not found")

        try:
            content = file_path.read_text()
            tree = cst.parse_module(content)

            for node in tree.body:
                if isinstance(node, cst.ClassDef) and node.name.value == self.name:
                    # Get the first line of the class definition
                    pos = tree.code_for_node(node).split("\n")[0]
                    line_num = content[:content.find(pos)].count("\n") + 1 if pos in content else None
                    if line_num:
                        from rejig.targets.python.line import LineTarget
                        return LineTarget(self._rejig, file_path, line_num).add_no_cover()

            return self._operation_failed("add_no_cover", f"Class '{self.name}' not found")
        except Exception as e:
            return self._operation_failed("add_no_cover", f"Failed to add no cover: {e}", e)

    def add_pylint_disable(self, codes: str | list[str]) -> Result:
        """Add pylint: disable comment to this class's definition line.

        Parameters
        ----------
        codes : str | list[str]
            Pylint error codes to disable.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> cls.add_pylint_disable("R0903")  # too-few-public-methods
        >>> cls.add_pylint_disable(["R0903", "R0901"])
        """
        file_path = self._find_class()
        if not file_path:
            return self._operation_failed("add_pylint_disable", f"Class '{self.name}' not found")

        try:
            content = file_path.read_text()
            tree = cst.parse_module(content)

            for node in tree.body:
                if isinstance(node, cst.ClassDef) and node.name.value == self.name:
                    pos = tree.code_for_node(node).split("\n")[0]
                    line_num = content[:content.find(pos)].count("\n") + 1 if pos in content else None
                    if line_num:
                        from rejig.targets.python.line import LineTarget
                        return LineTarget(self._rejig, file_path, line_num).add_pylint_disable(codes)

            return self._operation_failed("add_pylint_disable", f"Class '{self.name}' not found")
        except Exception as e:
            return self._operation_failed("add_pylint_disable", f"Failed to add pylint disable: {e}", e)
