"""Transformer to rename methods within classes."""
from __future__ import annotations

import libcst as cst


class RenameMethod(cst.CSTTransformer):
    """Rename a method within a class."""

    def __init__(self, class_name: str, old_name: str, new_name: str):
        super().__init__()
        self.class_name = class_name
        self.old_name = old_name
        self.new_name = new_name
        self.in_target_class = False
        self.renamed = False

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
        if self.in_target_class and updated_node.name.value == self.old_name:
            self.renamed = True
            return updated_node.with_changes(name=cst.Name(self.new_name))
        return updated_node
