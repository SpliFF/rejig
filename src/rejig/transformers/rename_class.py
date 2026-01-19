"""Transformer to rename classes."""
from __future__ import annotations

import libcst as cst


class RenameClass(cst.CSTTransformer):
    """Rename a class."""

    def __init__(self, old_name: str, new_name: str):
        super().__init__()
        self.old_name = old_name
        self.new_name = new_name
        self.renamed = False

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        if updated_node.name.value == self.old_name:
            self.renamed = True
            return updated_node.with_changes(name=cst.Name(self.new_name))
        return updated_node
