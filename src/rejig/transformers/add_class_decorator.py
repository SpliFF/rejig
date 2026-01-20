"""Transformer to add decorators to classes."""
from __future__ import annotations

import libcst as cst


class AddClassDecorator(cst.CSTTransformer):
    """Add a decorator to a class.

    Parameters
    ----------
    class_name : str
        Name of the class to add the decorator to.
    decorator : str
        Decorator to add (without @ prefix). Can include arguments,
        e.g., "dataclass(frozen=True)".

    Examples
    --------
    >>> transformer = AddClassDecorator("MyClass", "dataclass")
    >>> new_tree = tree.visit(transformer)
    """

    def __init__(self, class_name: str, decorator: str):
        super().__init__()
        self.class_name = class_name
        self.decorator = decorator
        self.added = False

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        if updated_node.name.value != self.class_name:
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
