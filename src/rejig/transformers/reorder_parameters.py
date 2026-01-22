"""Transformer to reorder parameters in methods/functions."""
from __future__ import annotations

import libcst as cst

from rejig.transformers.parameter_utils import fix_param_commas


class ReorderParameters(cst.CSTTransformer):
    """Reorder parameters in a method or function signature.

    Parameters not in the order list are appended at the end in their
    original relative order.

    Parameters
    ----------
    class_name : str | None
        Name of the class containing the method. Use None for module-level functions.
    function_name : str
        Name of the method or function.
    param_order : list[str]
        Ordered list of parameter names defining the new order.

    Examples
    --------
    >>> transformer = ReorderParameters(None, "func", ["self", "required", "optional"])
    >>> new_tree = tree.visit(transformer)
    """

    def __init__(
        self,
        class_name: str | None,
        function_name: str,
        param_order: list[str],
    ):
        super().__init__()
        self.class_name = class_name
        self.function_name = function_name
        self.param_order = param_order
        self.in_target_class = class_name is None
        self.reordered = False

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

        # Build a lookup of params by name
        param_dict: dict[str, cst.Param] = {}
        for p in params.params:
            param_dict[p.name.value] = p

        # Reorder the params according to param_order
        reordered: list[cst.Param] = []
        seen: set[str] = set()

        # First, add params in the specified order
        for name in self.param_order:
            if name in param_dict:
                reordered.append(param_dict[name])
                seen.add(name)

        # Then append any params not in the order list
        for p in params.params:
            if p.name.value not in seen:
                reordered.append(p)

        # Check if order actually changed
        original_order = [p.name.value for p in params.params]
        new_order = [p.name.value for p in reordered]
        if original_order == new_order:
            return updated_node

        self.reordered = True

        # Use utility for comma fixing
        has_star_arg = isinstance(params.star_arg, cst.ParamStar) or isinstance(params.star_arg, cst.Param)
        fixed_params = fix_param_commas(
            reordered,
            has_kwonly=bool(params.kwonly_params),
            has_star_kwarg=params.star_kwarg is not None,
            has_star_arg=has_star_arg,
        )

        new_parameters = params.with_changes(params=fixed_params)
        return updated_node.with_changes(params=new_parameters)
