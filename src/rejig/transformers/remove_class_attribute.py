"""Transformer to remove class-level attributes."""
from __future__ import annotations

import libcst as cst


class RemoveClassAttribute(cst.CSTTransformer):
    """Remove a class-level attribute.

    Removes both annotated assignments (attr: Type = value) and simple
    assignments (attr = value) from the specified class.

    Parameters
    ----------
    class_name : str
        Name of the class containing the attribute.
    attr_name : str
        Name of the attribute to remove.

    Attributes
    ----------
    removed : bool
        True if the attribute was found and removed.

    Examples
    --------
    >>> transformer = RemoveClassAttribute("User", "deprecated_field")
    >>> new_tree = tree.visit(transformer)
    """

    def __init__(self, class_name: str, attr_name: str):
        super().__init__()
        self.class_name = class_name
        self.attr_name = attr_name
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

    def leave_SimpleStatementLine(
        self,
        original_node: cst.SimpleStatementLine,
        updated_node: cst.SimpleStatementLine,
    ) -> cst.SimpleStatementLine | cst.RemovalSentinel:
        if not self.in_target_class:
            return updated_node

        if len(updated_node.body) == 1:
            stmt = updated_node.body[0]
            # Check for annotated assignment: attr: Type = value
            if isinstance(stmt, cst.AnnAssign):
                if isinstance(stmt.target, cst.Name) and stmt.target.value == self.attr_name:
                    self.removed = True
                    return cst.RemovalSentinel.REMOVE
            # Check for simple assignment: attr = value
            elif isinstance(stmt, cst.Assign):
                for target in stmt.targets:
                    if isinstance(target.target, cst.Name) and target.target.value == self.attr_name:
                        self.removed = True
                        return cst.RemovalSentinel.REMOVE
        return updated_node
