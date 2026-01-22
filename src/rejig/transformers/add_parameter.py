"""Transformer to add parameters to methods/functions."""
from __future__ import annotations

import libcst as cst

from rejig.transformers.parameter_utils import find_insert_position, fix_param_commas


class AddParameter(cst.CSTTransformer):
    """Add a parameter to a method or function.

    Parameters
    ----------
    class_name : str | None
        Name of the class containing the method. Use None for module-level functions.
    method_name : str
        Name of the method or function.
    param_name : str
        Name of the parameter to add.
    type_annotation : str | None
        Optional type annotation for the parameter.
    default_value : str | None
        Optional default value for the parameter.
    position : str
        Where to add: "start" (after self/cls), "end".
        Defaults to "end".

    Examples
    --------
    >>> transformer = AddParameter("MyClass", "my_method", "foo", "str", '"default"', "end")
    >>> new_tree = tree.visit(transformer)
    """

    def __init__(
        self,
        class_name: str | None,
        method_name: str,
        param_name: str,
        type_annotation: str | None = None,
        default_value: str | None = None,
        position: str = "end",
    ):
        super().__init__()
        self.class_name = class_name
        self.method_name = method_name
        self.param_name = param_name
        self.type_annotation = type_annotation
        self.default_value = default_value
        self.position = position
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

        # Build the new parameter
        new_param = cst.Param(name=cst.Name(self.param_name))

        # Add type annotation if provided
        if self.type_annotation:
            new_param = new_param.with_changes(
                annotation=cst.Annotation(annotation=cst.parse_expression(self.type_annotation))
            )

        # Add default value if provided
        if self.default_value is not None:
            new_param = new_param.with_changes(
                default=cst.parse_expression(self.default_value)
            )

        existing_params = list(updated_node.params.params)
        params = updated_node.params

        # Find insert position using utility
        insert_idx = find_insert_position(existing_params, self.position)

        # Insert the new parameter
        existing_params.insert(insert_idx, new_param)

        # Fix all commas using utility
        has_star_arg = isinstance(params.star_arg, cst.ParamStar) or isinstance(params.star_arg, cst.Param)
        existing_params = fix_param_commas(
            existing_params,
            has_kwonly=bool(params.kwonly_params),
            has_star_kwarg=params.star_kwarg is not None,
            has_star_arg=has_star_arg,
        )

        self.added = True

        return updated_node.with_changes(
            params=updated_node.params.with_changes(params=existing_params)
        )
