"""Transformer to convert async functions to sync."""
from __future__ import annotations

import libcst as cst


class ConvertToSync(cst.CSTTransformer):
    """Convert an asynchronous function/method to synchronous.

    Removes the `async` keyword from the function definition and removes
    `await` expressions within the function body.

    Parameters
    ----------
    class_name : str | None
        Name of the class containing the method. Use None for module-level functions.
    function_name : str
        Name of the function or method to convert.

    Examples
    --------
    >>> transformer = ConvertToSync(None, "fetch_data")
    >>> new_tree = tree.visit(transformer)
    """

    def __init__(self, class_name: str | None, function_name: str):
        super().__init__()
        self.class_name = class_name
        self.function_name = function_name
        self.in_target_class = class_name is None
        self.in_target_function = False
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

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        if self.in_target_class and node.name.value == self.function_name:
            self.in_target_function = True
        return True

    def leave_FunctionDef(
        self,
        original_node: cst.FunctionDef,
        updated_node: cst.FunctionDef,
    ) -> cst.FunctionDef:
        if self.in_target_class and original_node.name.value == self.function_name:
            self.in_target_function = False

            # Skip if not async
            if updated_node.asynchronous is None:
                return updated_node

            # Remove async keyword
            self.converted = True
            return updated_node.with_changes(asynchronous=None)

        return updated_node

    def leave_Await(
        self,
        original_node: cst.Await,
        updated_node: cst.Await,
    ) -> cst.BaseExpression:
        """Remove await expressions within the target function."""
        if self.in_target_function:
            # Return the expression without await
            return updated_node.expression
        return updated_node
