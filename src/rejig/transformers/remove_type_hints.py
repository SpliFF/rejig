"""Transformer to remove type hints from a function or method."""
from __future__ import annotations

import libcst as cst


class RemoveTypeHints(cst.CSTTransformer):
    """Remove all type hints from a function or method.

    Removes:
    - Return type annotations
    - Parameter type annotations

    Parameters
    ----------
    class_name : str | None
        Name of the class containing the method. None for module-level functions.
    function_name : str
        Name of the function/method to modify.

    Attributes
    ----------
    changed : bool
        True if the transformer made any changes.
    """

    def __init__(
        self,
        class_name: str | None,
        function_name: str,
    ) -> None:
        super().__init__()
        self.class_name = class_name
        self.function_name = function_name
        self.changed = False
        self._in_target_class = False
        self._in_target_function = False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        if self.class_name and node.name.value == self.class_name:
            self._in_target_class = True
        return True

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        if self.class_name and original_node.name.value == self.class_name:
            self._in_target_class = False
        return updated_node

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        if node.name.value == self.function_name:
            # Check class context
            if self.class_name is not None and self._in_target_class:
                self._in_target_function = True
            elif self.class_name is None and not self._in_target_class:
                self._in_target_function = True
        return True

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        # Check if this is the target function
        if original_node.name.value != self.function_name:
            return updated_node

        # For methods, must be in the target class
        if self.class_name is not None and not self._in_target_class:
            self._in_target_function = False
            return updated_node

        # For module-level functions, must not be in any class
        if self.class_name is None and self._in_target_class:
            self._in_target_function = False
            return updated_node

        self._in_target_function = False

        # Remove return type annotation if present
        if updated_node.returns is not None:
            self.changed = True
            updated_node = updated_node.with_changes(returns=None)

        return updated_node

    def leave_Param(
        self, original_node: cst.Param, updated_node: cst.Param
    ) -> cst.Param:
        if not self._in_target_function:
            return updated_node

        if updated_node.annotation is not None:
            self.changed = True
            return updated_node.with_changes(annotation=None)

        return updated_node
