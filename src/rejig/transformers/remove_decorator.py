"""Transformer to remove decorators from classes or functions."""
from __future__ import annotations

import libcst as cst


class RemoveDecorator(cst.CSTTransformer):
    """Remove a decorator from a class or function."""

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
