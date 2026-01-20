"""Transformer to set the return type of a function or method."""
from __future__ import annotations

import libcst as cst


class SetReturnType(cst.CSTTransformer):
    """Set the return type annotation of a function or method.

    Parameters
    ----------
    class_name : str | None
        Name of the class containing the method. None for module-level functions.
    function_name : str
        Name of the function/method to modify.
    return_type : str
        The return type annotation to set (e.g., "list[str]", "None").

    Attributes
    ----------
    changed : bool
        True if the transformer made any changes.
    """

    def __init__(
        self,
        class_name: str | None,
        function_name: str,
        return_type: str,
    ) -> None:
        super().__init__()
        self.class_name = class_name
        self.function_name = function_name
        self.return_type = return_type
        self.changed = False
        self._in_target_class = False

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

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        # Check if this is the target function
        if original_node.name.value != self.function_name:
            return updated_node

        # For methods, must be in the target class
        if self.class_name is not None and not self._in_target_class:
            return updated_node

        # For module-level functions, must not be in any class
        if self.class_name is None and self._in_target_class:
            return updated_node

        # Parse the return type
        try:
            return_annotation = cst.parse_expression(self.return_type)
        except Exception:
            return updated_node

        self.changed = True
        return updated_node.with_changes(
            returns=cst.Annotation(annotation=return_annotation)
        )
