"""ClassScope for operations on a specific class."""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst

from rejig.result import FindResult, Match, RefactorResult
from rejig.transformers import (
    AddClassAttribute,
    RemoveClassAttribute,
    RemoveDecorator,
    RenameClass,
)

from .base import BaseScope

if TYPE_CHECKING:
    from rejig.core import Manipylate
    from .method_scope import MethodScope


class ClassScope(BaseScope):
    """
    Scope for operations on a specific class.

    This class provides methods for finding and modifying a class
    across all files in the working set.

    Parameters
    ----------
    manipylate : Manipylate
        The parent Manipylate instance.
    class_name : str
        Name of the class to operate on.

    Examples
    --------
    >>> class_scope = pym.find_class("MyClass")
    >>> class_scope.add_attribute("count", "int", "0")
    >>> class_scope.find_method("process").insert_statement("self.count += 1")
    """

    def __init__(self, manipylate: Manipylate, class_name: str):
        super().__init__(manipylate)
        self.class_name = class_name
        self._file_path: Path | None = None

    def _find_class_file(self) -> Path | None:
        """Find the file containing the class."""
        if self._file_path is not None:
            return self._file_path

        pattern = rf"\bclass\s+{re.escape(self.class_name)}\b"
        for file_path in self.files:
            try:
                content = file_path.read_text()
                if re.search(pattern, content):
                    self._file_path = file_path
                    return file_path
            except Exception:
                continue
        return None

    @property
    def file_path(self) -> Path | None:
        """Path to the file containing this class."""
        return self._find_class_file()

    def exists(self) -> bool:
        """Check if the class exists in any file."""
        return self._find_class_file() is not None

    def find_method(self, method_name: str) -> MethodScope:
        """
        Find a method within this class.

        Parameters
        ----------
        method_name : str
            Name of the method to find.

        Returns
        -------
        MethodScope
            A scope object for performing operations on the matched method.

        Examples
        --------
        >>> method_scope = class_scope.find_method("process")
        >>> method_scope.add_parameter("timeout", "int", "30")
        """
        from .method_scope import MethodScope

        return MethodScope(
            manipylate=self.manipylate,
            class_name=self.class_name,
            method_name=method_name,
        )

    def find_methods(self, pattern: str | None = None) -> FindResult:
        """
        Find all methods in this class, optionally filtered by pattern.

        Parameters
        ----------
        pattern : str | None
            Optional regex pattern to filter method names.

        Returns
        -------
        FindResult
            Result containing all matching methods.
        """
        matches: list[Match] = []
        file_path = self._find_class_file()
        if not file_path:
            return FindResult(matches)

        regex = re.compile(pattern) if pattern else None

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
                    return False  # Don't recurse into nested functions

            finder = MethodFinder(self.class_name)
            tree.walk(finder)

            for method_name in finder.methods:
                if regex is None or regex.search(method_name):
                    # Find line number
                    method_pattern = rf"\bdef\s+{re.escape(method_name)}\b"
                    for i, line in enumerate(content.splitlines(), 1):
                        if re.search(method_pattern, line):
                            matches.append(Match(file_path, method_name, i))
                            break

        except Exception:
            pass

        return FindResult(matches)

    def add_attribute(
        self,
        attr_name: str,
        type_annotation: str,
        default_value: str = "None",
    ) -> RefactorResult:
        """
        Add a class-level attribute with type annotation.

        Parameters
        ----------
        attr_name : str
            Name of the attribute to add.
        type_annotation : str
            Type annotation for the attribute.
        default_value : str, optional
            Default value for the attribute. Defaults to "None".

        Returns
        -------
        RefactorResult
            Result of the operation.

        Examples
        --------
        >>> class_scope.add_attribute("count", "int", "0")
        >>> class_scope.add_attribute("cache", "dict[str, Any] | None", "None")
        """
        file_path = self._find_class_file()
        if not file_path:
            return RefactorResult(
                success=False,
                message=f"Class {self.class_name} not found",
            )

        transformer = AddClassAttribute(
            self.class_name, attr_name, type_annotation, default_value
        )
        result = self.manipylate.transform_file(file_path, transformer)

        if result.success and transformer.added:
            return RefactorResult(
                success=True,
                message=f"Added attribute {attr_name} to {self.class_name}",
                files_changed=[file_path],
            )
        return result

    def remove_attribute(self, attr_name: str) -> RefactorResult:
        """
        Remove a class-level attribute.

        Parameters
        ----------
        attr_name : str
            Name of the attribute to remove.

        Returns
        -------
        RefactorResult
            Result of the operation.
        """
        file_path = self._find_class_file()
        if not file_path:
            return RefactorResult(
                success=False,
                message=f"Class {self.class_name} not found",
            )

        transformer = RemoveClassAttribute(self.class_name, attr_name)
        return self.manipylate.transform_file(file_path, transformer)

    def rename(self, new_name: str) -> RefactorResult:
        """
        Rename the class.

        Note: This only renames the class definition. It does not update
        references to the class throughout the codebase. For comprehensive
        renaming with import updates, use rope-based refactoring.

        Parameters
        ----------
        new_name : str
            New name for the class.

        Returns
        -------
        RefactorResult
            Result of the operation.
        """
        file_path = self._find_class_file()
        if not file_path:
            return RefactorResult(
                success=False,
                message=f"Class {self.class_name} not found",
            )

        transformer = RenameClass(self.class_name, new_name)
        result = self.manipylate.transform_file(file_path, transformer)

        if result.success and transformer.renamed:
            self.class_name = new_name
            return RefactorResult(
                success=True,
                message=f"Renamed class to {new_name}",
                files_changed=[file_path],
            )
        return result

    def add_decorator(self, decorator: str) -> RefactorResult:
        """
        Add a decorator to the class.

        Parameters
        ----------
        decorator : str
            Decorator to add (without @ prefix).

        Returns
        -------
        RefactorResult
            Result of the operation.
        """
        file_path = self._find_class_file()
        if not file_path:
            return RefactorResult(
                success=False,
                message=f"Class {self.class_name} not found",
            )

        # Use a simple regex-based approach for class decorators
        content = file_path.read_text()
        pattern = rf"(^class\s+{re.escape(self.class_name)}\b)"
        replacement = f"@{decorator}\n\\1"
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        if new_content == content:
            return RefactorResult(
                success=False,
                message=f"Could not add decorator to {self.class_name}",
            )

        if self.dry_run:
            return RefactorResult(
                success=True,
                message=f"[DRY RUN] Would add @{decorator} to {self.class_name}",
                files_changed=[file_path],
            )

        file_path.write_text(new_content)
        return RefactorResult(
            success=True,
            message=f"Added @{decorator} to {self.class_name}",
            files_changed=[file_path],
        )

    def remove_decorator(self, decorator: str) -> RefactorResult:
        """
        Remove a decorator from the class.

        Parameters
        ----------
        decorator : str
            Decorator to remove (without @ prefix).

        Returns
        -------
        RefactorResult
            Result of the operation.
        """
        file_path = self._find_class_file()
        if not file_path:
            return RefactorResult(
                success=False,
                message=f"Class {self.class_name} not found",
            )

        transformer = RemoveDecorator(self.class_name, decorator, target_type="class")
        return self.manipylate.transform_file(file_path, transformer)

    def move_to(self, dest_module: str) -> RefactorResult:
        """
        Move this class to a different module using rope.

        Rope automatically updates all imports throughout the project.

        Parameters
        ----------
        dest_module : str
            Destination module path (e.g., 'myapp.models').

        Returns
        -------
        RefactorResult
            Result with success status.

        Examples
        --------
        >>> with Manipylate("src/") as pym:
        ...     pym.find_class("MyClass").move_to("new_module.models")
        """
        file_path = self._find_class_file()
        if not file_path:
            return RefactorResult(
                success=False,
                message=f"Class {self.class_name} not found",
            )

        return self.manipylate.move_class(file_path, self.class_name, dest_module)
