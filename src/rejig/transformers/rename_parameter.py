"""Transformer to rename parameters in methods/functions."""
from __future__ import annotations

import libcst as cst


class RenameParameter(cst.CSTTransformer):
    """Rename a parameter in a method or function.

    Renames the parameter in the function signature and updates all
    references to it within the function body.

    Parameters
    ----------
    class_name : str | None
        Name of the class containing the method. Use None for module-level functions.
    function_name : str
        Name of the method or function.
    old_name : str
        Current name of the parameter.
    new_name : str
        New name for the parameter.

    Examples
    --------
    >>> transformer = RenameParameter("MyClass", "my_method", "old_param", "new_param")
    >>> new_tree = tree.visit(transformer)
    """

    def __init__(
        self,
        class_name: str | None,
        function_name: str,
        old_name: str,
        new_name: str,
    ):
        super().__init__()
        self.class_name = class_name
        self.function_name = function_name
        self.old_name = old_name
        self.new_name = new_name
        self.in_target_class = class_name is None
        self.in_target_function = False
        self.renamed = False

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

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        if self.in_target_class and node.name.value == self.function_name:
            self.in_target_function = True
        return True

    def leave_FunctionDef(
        self,
        original_node: cst.FunctionDef,
        updated_node: cst.FunctionDef,
    ) -> cst.FunctionDef:
        if self.in_target_class and original_node.name.value == self.function_name:
            self.in_target_function = False
            # Now rename the parameter in the signature
            return self._rename_in_signature(updated_node)
        return updated_node

    def _rename_in_signature(self, node: cst.FunctionDef) -> cst.FunctionDef:
        """Rename the parameter in the function signature."""
        params = node.params
        changed = False

        # Rename in regular params
        new_params = []
        for p in params.params:
            if p.name.value == self.old_name:
                new_params.append(p.with_changes(name=cst.Name(self.new_name)))
                changed = True
            else:
                new_params.append(p)

        # Rename in kwonly_params
        new_kwonly = []
        for p in params.kwonly_params:
            if p.name.value == self.old_name:
                new_kwonly.append(p.with_changes(name=cst.Name(self.new_name)))
                changed = True
            else:
                new_kwonly.append(p)

        # Check star_arg
        new_star_arg = params.star_arg
        if isinstance(params.star_arg, cst.Param) and params.star_arg.name.value == self.old_name:
            new_star_arg = params.star_arg.with_changes(name=cst.Name(self.new_name))
            changed = True

        # Check star_kwarg
        new_star_kwarg = params.star_kwarg
        if params.star_kwarg and params.star_kwarg.name.value == self.old_name:
            new_star_kwarg = params.star_kwarg.with_changes(name=cst.Name(self.new_name))
            changed = True

        if changed:
            self.renamed = True
            new_parameters = params.with_changes(
                params=new_params,
                kwonly_params=new_kwonly,
                star_arg=new_star_arg,
                star_kwarg=new_star_kwarg,
            )
            return node.with_changes(params=new_parameters)

        return node

    def leave_Name(
        self,
        original_node: cst.Name,
        updated_node: cst.Name,
    ) -> cst.Name:
        """Rename references to the parameter within the function body."""
        if self.in_target_function and updated_node.value == self.old_name:
            return updated_node.with_changes(value=self.new_name)
        return updated_node
