"""Transformer to add decorators to methods."""
from __future__ import annotations

import libcst as cst


class AddMethodDecorator(cst.CSTTransformer):
    """Add a decorator to a method.

    Parameters
    ----------
    class_name : str
        Name of the class containing the method.
    method_name : str
        Name of the method to decorate.
    decorator : str
        Decorator name to add (without @).

    Attributes
    ----------
    added : bool
        True if the decorator was added.
    """

    def __init__(self, class_name: str, method_name: str, decorator: str):
        super().__init__()
        self.class_name = class_name
        self.method_name = method_name
        self.decorator = decorator
        self._class_depth = 0  # Track nested class depth
        self.added = False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        if node.name.value == self.class_name:
            self._class_depth += 1
        return True

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        if original_node.name.value == self.class_name:
            self._class_depth -= 1
        return updated_node

    @property
    def in_target_class(self) -> bool:
        """Check if we're currently in the target class (not nested)."""
        return self._class_depth == 1

    def leave_FunctionDef(
        self,
        original_node: cst.FunctionDef,
        updated_node: cst.FunctionDef,
    ) -> cst.FunctionDef:
        if not self.in_target_class or updated_node.name.value != self.method_name:
            return updated_node

        # Check if decorator already exists
        for dec in updated_node.decorators:
            if isinstance(dec.decorator, cst.Name) and dec.decorator.value == self.decorator:
                return updated_node

        # Add new decorator at the beginning
        new_decorator = cst.Decorator(decorator=cst.Name(self.decorator))
        new_decorators = [new_decorator] + list(updated_node.decorators)
        self.added = True

        return updated_node.with_changes(decorators=new_decorators)
