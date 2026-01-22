"""Transformer to remove module-level assignments."""
from __future__ import annotations

import libcst as cst


class RemoveModuleLevelAssignment(cst.CSTTransformer):
    """Remove a module-level assignment by variable name.

    Removes simple assignments at module level (not inside classes or functions).
    Handles standard assignments like `VAR = value`.

    Parameters
    ----------
    var_name : str
        Name of the variable to remove.

    Attributes
    ----------
    removed : bool
        True if the assignment was found and removed.

    Examples
    --------
    >>> # Remove deprecated module constant
    >>> transformer = RemoveModuleLevelAssignment("DEPRECATED_SETTING")
    >>> new_tree = tree.visit(transformer)
    """

    def __init__(self, var_name: str):
        super().__init__()
        self.var_name = var_name
        self.removed = False

    def leave_SimpleStatementLine(
        self,
        original_node: cst.SimpleStatementLine,
        updated_node: cst.SimpleStatementLine,
    ) -> cst.SimpleStatementLine | cst.RemovalSentinel:
        if len(updated_node.body) == 1:
            stmt = updated_node.body[0]
            if isinstance(stmt, cst.Assign):
                for target in stmt.targets:
                    if isinstance(target.target, cst.Name) and target.target.value == self.var_name:
                        self.removed = True
                        return cst.RemovalSentinel.REMOVE
        return updated_node
