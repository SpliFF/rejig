"""Transformer to add decorators to module-level functions."""
from __future__ import annotations

import libcst as cst


class AddFunctionDecorator(cst.CSTTransformer):
    """Add a decorator to a module-level function.

    Parameters
    ----------
    function_name : str
        Name of the function to add the decorator to.
    decorator : str
        Decorator to add (without @ prefix). Can include arguments,
        e.g., "lru_cache(maxsize=128)".

    Examples
    --------
    >>> transformer = AddFunctionDecorator("my_function", "lru_cache")
    >>> new_tree = tree.visit(transformer)
    """

    def __init__(self, function_name: str, decorator: str):
        super().__init__()
        self.function_name = function_name
        self.decorator = decorator
        self.added = False
        self._in_class = False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        self._in_class = True
        return True

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        self._in_class = False
        return updated_node

    def leave_FunctionDef(
        self,
        original_node: cst.FunctionDef,
        updated_node: cst.FunctionDef,
    ) -> cst.FunctionDef:
        # Only target module-level functions
        if self._in_class or updated_node.name.value != self.function_name:
            return updated_node

        # Parse the decorator - it might be a simple name or a call
        decorator_expr = cst.parse_expression(self.decorator)

        # Check if decorator already exists
        for dec in updated_node.decorators:
            # Get the decorator name (handle both Name and Call nodes)
            existing_name = None
            if isinstance(dec.decorator, cst.Name):
                existing_name = dec.decorator.value
            elif isinstance(dec.decorator, cst.Call) and isinstance(dec.decorator.func, cst.Name):
                existing_name = dec.decorator.func.value

            # Get the new decorator name
            new_name = None
            if isinstance(decorator_expr, cst.Name):
                new_name = decorator_expr.value
            elif isinstance(decorator_expr, cst.Call) and isinstance(decorator_expr.func, cst.Name):
                new_name = decorator_expr.func.value

            if existing_name and new_name and existing_name == new_name:
                # Decorator already exists, don't add duplicate
                return updated_node

        # Add new decorator at the beginning
        new_decorator = cst.Decorator(decorator=decorator_expr)
        new_decorators = [new_decorator] + list(updated_node.decorators)
        self.added = True

        return updated_node.with_changes(decorators=new_decorators)
