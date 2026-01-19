"""Transformer to remove decorators from methods."""
from __future__ import annotations

import libcst as cst


class RemoveMethodDecorator(cst.CSTTransformer):
    """Remove a decorator from a method."""

    def __init__(self, class_name: str, method_name: str, decorator: str):
        super().__init__()
        self.class_name = class_name
        self.method_name = method_name
        self.decorator = decorator
        self.in_target_class = False
        self.removed = False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        if node.name.value == self.class_name:
            self.in_target_class = True
        return True

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        if original_node.name.value == self.class_name:
            self.in_target_class = False
        return updated_node

    def leave_FunctionDef(
        self,
        original_node: cst.FunctionDef,
        updated_node: cst.FunctionDef,
    ) -> cst.FunctionDef:
        if not self.in_target_class or updated_node.name.value != self.method_name:
            return updated_node

        new_decorators = []
        for dec in updated_node.decorators:
            if isinstance(dec.decorator, cst.Name) and dec.decorator.value == self.decorator:
                self.removed = True
                continue
            new_decorators.append(dec)

        return updated_node.with_changes(decorators=new_decorators)
