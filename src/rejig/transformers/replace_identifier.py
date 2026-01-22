"""Transformer to replace identifier references within methods."""
from __future__ import annotations

import libcst as cst


class ReplaceIdentifier(cst.CSTTransformer):
    """Replace identifier references within a specific class method.

    Useful for renaming variables or replacing simple identifiers with
    attribute accesses (e.g., replacing `data` with `cls.data`).

    Parameters
    ----------
    class_name : str
        Name of the class containing the method.
    method_name : str
        Name of the method to search within.
    old_name : str
        Identifier name to replace.
    new_name : str
        New expression to replace with (can be "cls.attr" style).

    Attributes
    ----------
    replaced_count : int
        Number of replacements made.

    Examples
    --------
    >>> # Replace all 'data' references with 'cls.data' in a method
    >>> transformer = ReplaceIdentifier(
    ...     "DataService",
    ...     "process",
    ...     "data",
    ...     "cls.data"
    ... )
    >>> new_tree = tree.visit(transformer)
    """

    def __init__(self, class_name: str, method_name: str, old_name: str, new_name: str):
        super().__init__()
        self.class_name = class_name
        self.method_name = method_name
        self.old_name = old_name
        self.new_name = new_name
        self.in_target_class = False
        self.in_target_method = False
        self.replaced_count = 0

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

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        if self.in_target_class and node.name.value == self.method_name:
            self.in_target_method = True
        return True

    def leave_FunctionDef(
        self,
        original_node: cst.FunctionDef,
        updated_node: cst.FunctionDef,
    ) -> cst.FunctionDef:
        if self.in_target_class and original_node.name.value == self.method_name:
            self.in_target_method = False
        return updated_node

    def leave_Name(
        self,
        original_node: cst.Name,
        updated_node: cst.Name,
    ) -> cst.Name | cst.Attribute | cst.BaseExpression:
        if not self.in_target_method:
            return updated_node

        if updated_node.value == self.old_name:
            self.replaced_count += 1
            # Parse the new name (could be "cls.attr_name" style)
            return cst.parse_expression(self.new_name)

        return updated_node
