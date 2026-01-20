"""Transformer to infer and add type hints based on defaults and name heuristics."""
from __future__ import annotations

import libcst as cst

from rejig.typehints.inference import TypeInference


class InferTypeHints(cst.CSTTransformer):
    """Infer and add type hints to a function or method.

    Uses heuristics based on:
    - Default values (e.g., = 0 → int)
    - Parameter names (e.g., count → int)
    - Common patterns

    Parameters
    ----------
    class_name : str | None
        Name of the class containing the method. None for module-level functions.
    function_name : str
        Name of the function/method to modify.
    overwrite : bool
        If True, overwrite existing type hints. Default False.

    Attributes
    ----------
    changed : bool
        True if the transformer made any changes.
    """

    def __init__(
        self,
        class_name: str | None,
        function_name: str,
        overwrite: bool = False,
    ) -> None:
        super().__init__()
        self.class_name = class_name
        self.function_name = function_name
        self.overwrite = overwrite
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

        # Skip if already annotated and not overwriting
        if updated_node.annotation is not None and not self.overwrite:
            return updated_node

        # Skip self/cls parameters
        param_name = original_node.name.value
        if param_name in ("self", "cls"):
            return updated_node

        # Try to infer type
        default_value = original_node.default
        inferred_type = TypeInference.infer_type(
            name=param_name,
            default_value=default_value,
        )

        if inferred_type is None:
            return updated_node

        # Parse and apply the type annotation
        try:
            type_annotation = cst.parse_expression(inferred_type)
            self.changed = True
            return updated_node.with_changes(
                annotation=cst.Annotation(annotation=type_annotation)
            )
        except Exception:
            return updated_node
