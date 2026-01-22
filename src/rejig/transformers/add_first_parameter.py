"""Transformer to add a first parameter to methods/functions."""
from __future__ import annotations

import libcst as cst


class AddFirstParameter(cst.CSTTransformer):
    """Add a first parameter (like 'cls' or 'self') to a method.

    Useful for converting static methods to class methods or instance methods.

    Parameters
    ----------
    class_name : str | None
        Name of the class containing the method. Use None for module-level functions.
    method_name : str
        Name of the method or function to modify.
    param_name : str
        Name of the parameter to add. Defaults to "cls".

    Attributes
    ----------
    added : bool
        True if the parameter was added.

    Examples
    --------
    >>> transformer = AddFirstParameter("MyClass", "my_method", "cls")
    >>> new_tree = tree.visit(transformer)
    """

    def __init__(self, class_name: str | None, method_name: str, param_name: str = "cls") -> None:
        super().__init__()
        self.class_name = class_name
        self.method_name = method_name
        self.param_name = param_name
        self.in_target_class = class_name is None  # If no class, we're at module level
        self.added = False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        if self.class_name and node.name.value == self.class_name:
            self.in_target_class = True
        return True

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        if self.class_name and original_node.name.value == self.class_name:
            self.in_target_class = False
        return updated_node

    def leave_FunctionDef(
        self,
        original_node: cst.FunctionDef,
        updated_node: cst.FunctionDef,
    ) -> cst.FunctionDef:
        if not self.in_target_class or updated_node.name.value != self.method_name:
            return updated_node

        # Add the new parameter at the beginning
        new_param = cst.Param(name=cst.Name(self.param_name))
        existing_params = list(updated_node.params.params)

        # Check if first param is already cls/self
        if existing_params and existing_params[0].name.value in ("cls", "self"):
            return updated_node

        # Add comma after new param if there are existing params
        if existing_params:
            new_param = new_param.with_changes(comma=cst.MaybeSentinel.DEFAULT)

        new_params = [new_param] + existing_params
        self.added = True

        return updated_node.with_changes(
            params=updated_node.params.with_changes(params=new_params)
        )
