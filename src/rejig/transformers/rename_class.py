"""Transformer to rename classes."""
from __future__ import annotations

import libcst as cst


class RenameClass(cst.CSTTransformer):
    """Rename a class definition.

    Note: This only renames the class definition itself. It does not update
    references to the class elsewhere in the code. For semantic renaming with
    automatic reference updates, use Rope integration.

    Parameters
    ----------
    old_name : str
        Current name of the class.
    new_name : str
        New name for the class.

    Attributes
    ----------
    renamed : bool
        True if the class was found and renamed.

    Examples
    --------
    >>> transformer = RenameClass("OldName", "NewName")
    >>> new_tree = tree.visit(transformer)
    """

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
