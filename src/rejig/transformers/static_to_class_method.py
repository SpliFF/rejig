"""Transformer to convert staticmethod to classmethod."""
from __future__ import annotations

import libcst as cst


class StaticToClassMethod(cst.CSTTransformer):
    """Convert @staticmethod to @classmethod for a specific method.

    Replaces the @staticmethod decorator with @classmethod. Note that this
    only changes the decorator; you should also add a 'cls' parameter using
    AddFirstParameter to make the method fully functional as a classmethod.

    Parameters
    ----------
    class_name : str
        Name of the class containing the method.
    method_name : str
        Name of the method to convert.

    Attributes
    ----------
    converted : bool
        True if the conversion was performed.

    Examples
    --------
    >>> transformer = StaticToClassMethod("Factory", "create")
    >>> new_tree = tree.visit(transformer)
    >>> # Then add 'cls' parameter with AddFirstParameter
    """

    def __init__(self, class_name: str, method_name: str):
        super().__init__()
        self.class_name = class_name
        self.method_name = method_name
        self.in_target_class = False
        self.converted = False

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

        # Check for @staticmethod decorator and replace with @classmethod
        new_decorators = []
        for decorator in updated_node.decorators:
            if isinstance(decorator.decorator, cst.Name) and decorator.decorator.value == "staticmethod":
                new_decorators.append(
                    decorator.with_changes(decorator=cst.Name("classmethod"))
                )
                self.converted = True
            else:
                new_decorators.append(decorator)

        return updated_node.with_changes(decorators=new_decorators)
