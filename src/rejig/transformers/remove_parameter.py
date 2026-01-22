"""Transformer to remove parameters from methods/functions."""
from __future__ import annotations

import libcst as cst

from rejig.transformers.parameter_utils import fix_kwonly_commas, fix_param_commas


class RemoveParameter(cst.CSTTransformer):
    """Remove a parameter from a method or function.

    Parameters
    ----------
    class_name : str | None
        Name of the class containing the method. Use None for module-level functions.
    function_name : str
        Name of the method or function.
    param_name : str
        Name of the parameter to remove.

    Examples
    --------
    >>> transformer = RemoveParameter("MyClass", "my_method", "deprecated_arg")
    >>> new_tree = tree.visit(transformer)
    """

    def __init__(
        self,
        class_name: str | None,
        function_name: str,
        param_name: str,
    ):
        super().__init__()
        self.class_name = class_name
        self.function_name = function_name
        self.param_name = param_name
        self.in_target_class = class_name is None
        self.removed = False

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
        if not self.in_target_class or updated_node.name.value != self.function_name:
            return updated_node

        params = updated_node.params

        # Filter out the parameter from regular params
        new_params = [p for p in params.params if p.name.value != self.param_name]
        if len(new_params) != len(params.params):
            self.removed = True

        # Filter from kwonly_params
        new_kwonly = [p for p in params.kwonly_params if p.name.value != self.param_name]
        if len(new_kwonly) != len(params.kwonly_params):
            self.removed = True

        # Check star_arg
        new_star_arg = params.star_arg
        if isinstance(params.star_arg, cst.Param) and params.star_arg.name.value == self.param_name:
            new_star_arg = cst.MaybeSentinel.DEFAULT
            self.removed = True

        # Check star_kwarg
        new_star_kwarg = params.star_kwarg
        if params.star_kwarg and params.star_kwarg.name.value == self.param_name:
            new_star_kwarg = None
            self.removed = True

        if not self.removed:
            return updated_node

        # Use utility functions for comma handling
        has_star_arg = isinstance(new_star_arg, cst.ParamStar) or isinstance(new_star_arg, cst.Param)
        new_params = fix_param_commas(
            new_params,
            has_kwonly=bool(new_kwonly),
            has_star_kwarg=new_star_kwarg is not None,
            has_star_arg=has_star_arg,
        )
        new_kwonly = fix_kwonly_commas(new_kwonly, has_star_kwarg=new_star_kwarg is not None)

        new_parameters = params.with_changes(
            params=new_params,
            kwonly_params=new_kwonly,
            star_arg=new_star_arg,
            star_kwarg=new_star_kwarg,
        )

        return updated_node.with_changes(params=new_parameters)
