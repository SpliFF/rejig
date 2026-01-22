"""Transformer to convert async functions to sync."""
from __future__ import annotations

import libcst as cst


class ConvertToSync(cst.CSTTransformer):
    """Convert an asynchronous function/method to synchronous.

    Removes the `async` keyword from the function definition and removes
    `await` expressions within the function body (but not in nested functions).

    Parameters
    ----------
    class_name : str | None
        Name of the class containing the method. Use None for module-level functions.
    function_name : str
        Name of the function or method to convert.

    Attributes
    ----------
    converted : bool
        True if the function was converted from async to sync.

    Examples
    --------
    >>> transformer = ConvertToSync(None, "fetch_data")
    >>> new_tree = tree.visit(transformer)
    """

    def __init__(self, class_name: str | None, function_name: str):
        super().__init__()
        self.class_name = class_name
        self.function_name = function_name
        self._class_depth = 1 if class_name is None else 0
        self._function_depth = 0  # Track nested function depth
        self._target_function_depth = 0  # Depth at which target function was found
        self.converted = False

    @property
    def in_target_class(self) -> bool:
        """Check if we're in the target class context."""
        return self._class_depth == 1 if self.class_name else self._class_depth >= 0

    @property
    def in_target_function(self) -> bool:
        """Check if we're directly in the target function (not nested)."""
        return self._target_function_depth > 0 and self._function_depth == self._target_function_depth

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        if self.class_name and node.name.value == self.class_name:
            self._class_depth += 1
        return True

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        if self.class_name and original_node.name.value == self.class_name:
            self._class_depth -= 1
        return updated_node

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        self._function_depth += 1
        if self.in_target_class and node.name.value == self.function_name and self._target_function_depth == 0:
            self._target_function_depth = self._function_depth
        return True

    def leave_FunctionDef(
        self,
        original_node: cst.FunctionDef,
        updated_node: cst.FunctionDef,
    ) -> cst.FunctionDef:
        result = updated_node

        # Check if this is the target function being exited
        if self._function_depth == self._target_function_depth:
            self._target_function_depth = 0

            # Skip if not async
            if updated_node.asynchronous is not None:
                # Remove async keyword
                self.converted = True
                result = updated_node.with_changes(asynchronous=None)

        self._function_depth -= 1
        return result

    def leave_Await(
        self,
        original_node: cst.Await,
        updated_node: cst.Await,
    ) -> cst.BaseExpression:
        """Remove await expressions within the target function (not in nested functions)."""
        if self.in_target_function:
            # Return the expression without await
            return updated_node.expression
        return updated_node
