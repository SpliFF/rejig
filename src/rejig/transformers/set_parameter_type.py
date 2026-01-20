"""Transformer to set the type annotation of a parameter."""
from __future__ import annotations

import libcst as cst


class SetParameterType(cst.CSTTransformer):
    """Set the type annotation of a parameter in a function or method.

    Parameters
    ----------
    class_name : str | None
        Name of the class containing the method. None for module-level functions.
    function_name : str
        Name of the function/method to modify.
    param_name : str
        Name of the parameter to annotate.
    param_type : str
        The type annotation to set (e.g., "dict[str, Any]").

    Attributes
    ----------
    changed : bool
        True if the transformer made any changes.
    """

    def __init__(
        self,
        class_name: str | None,
        function_name: str,
        param_name: str,
        param_type: str,
    ) -> None:
        super().__init__()
        self.class_name = class_name
        self.function_name = function_name
        self.param_name = param_name
        self.param_type = param_type
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
        if original_node.name.value == self.function_name:
            self._in_target_function = False
        return updated_node

    def leave_Param(
        self, original_node: cst.Param, updated_node: cst.Param
    ) -> cst.Param:
        if not self._in_target_function:
            return updated_node

        if original_node.name.value != self.param_name:
            return updated_node

        # Parse the type annotation
        try:
            type_annotation = cst.parse_expression(self.param_type)
        except Exception:
            return updated_node

        self.changed = True
        return updated_node.with_changes(
            annotation=cst.Annotation(annotation=type_annotation)
        )
