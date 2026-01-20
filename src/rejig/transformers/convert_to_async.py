"""Transformer to convert sync functions to async."""
from __future__ import annotations

import libcst as cst


class ConvertToAsync(cst.CSTTransformer):
    """Convert a synchronous function/method to asynchronous.

    Adds the `async` keyword to the function definition.

    Parameters
    ----------
    class_name : str | None
        Name of the class containing the method. Use None for module-level functions.
    function_name : str
        Name of the function or method to convert.

    Examples
    --------
    >>> transformer = ConvertToAsync(None, "fetch_data")
    >>> new_tree = tree.visit(transformer)
    """

    def __init__(self, class_name: str | None, function_name: str):
        super().__init__()
        self.class_name = class_name
        self.function_name = function_name
        self.in_target_class = class_name is None
        self.converted = False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        if self.class_name and node.name.value == self.class_name:
            self.in_target_class = True
        return True

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        if self.class_name and original_node.name.value == self.class_name:
            self.in_target_class = False
        return updated_node

    def leave_FunctionDef(
        self,
        original_node: cst.FunctionDef,
        updated_node: cst.FunctionDef,
    ) -> cst.FunctionDef:
        if not self.in_target_class or updated_node.name.value != self.function_name:
            return updated_node

        # Skip if already async
        if updated_node.asynchronous is not None:
            return updated_node

        # Add async keyword
        self.converted = True
        return updated_node.with_changes(
            asynchronous=cst.Asynchronous(
                whitespace_after=cst.SimpleWhitespace(" ")
            )
        )
