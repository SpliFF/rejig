"""Transformer to remove decorators from classes or functions."""
from __future__ import annotations

import libcst as cst


class RemoveDecorator(cst.CSTTransformer):
    """Remove a decorator from a class or function.

    Removes a specific decorator from either a class or a module-level function.
    For removing decorators from methods within a class, use RemoveMethodDecorator.

    Parameters
    ----------
    name : str
        Name of the class or function to modify.
    decorator : str
        Name of the decorator to remove (without the @ symbol).
    target_type : str
        Type of target: "class" or "function". Defaults to "class".

    Attributes
    ----------
    removed : bool
        True if the decorator was found and removed.

    Examples
    --------
    >>> # Remove @dataclass from a class
    >>> transformer = RemoveDecorator("User", "dataclass", "class")
    >>> new_tree = tree.visit(transformer)

    >>> # Remove @cache from a function
    >>> transformer = RemoveDecorator("get_data", "cache", "function")
    >>> new_tree = tree.visit(transformer)
    """

    def __init__(self, name: str, decorator: str, target_type: str = "class"):
        super().__init__()
        self.name = name
        self.decorator = decorator
        self.target_type = target_type
        self.removed = False

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        if self.target_type != "class" or updated_node.name.value != self.name:
            return updated_node

        new_decorators = []
        for dec in updated_node.decorators:
            if isinstance(dec.decorator, cst.Name) and dec.decorator.value == self.decorator:
                self.removed = True
                continue
            new_decorators.append(dec)

        return updated_node.with_changes(decorators=new_decorators)

    def leave_FunctionDef(
        self,
        original_node: cst.FunctionDef,
        updated_node: cst.FunctionDef,
    ) -> cst.FunctionDef:
        if self.target_type != "function" or updated_node.name.value != self.name:
            return updated_node

        new_decorators = []
        for dec in updated_node.decorators:
            if isinstance(dec.decorator, cst.Name) and dec.decorator.value == self.decorator:
                self.removed = True
                continue
            new_decorators.append(dec)

        return updated_node.with_changes(decorators=new_decorators)
