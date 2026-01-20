"""Transformer to add parameters to methods/functions."""
from __future__ import annotations

import libcst as cst


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

        if self.position == "start":
            # Insert after self/cls if present
            insert_idx = 0
            if existing_params and existing_params[0].name.value in ("cls", "self"):
                insert_idx = 1

            # Add comma after new param if there are more params after it
            if insert_idx < len(existing_params):
                new_param = new_param.with_changes(comma=cst.MaybeSentinel.DEFAULT)

            existing_params.insert(insert_idx, new_param)
        else:
            # Add at the end
            # Ensure previous param has a comma if there are existing params
            if existing_params:
                # The last param needs a comma to separate from our new param
                last_idx = len(existing_params) - 1
                existing_params[last_idx] = existing_params[last_idx].with_changes(
                    comma=cst.MaybeSentinel.DEFAULT
                )
            existing_params.append(new_param)

        self.added = True

        return updated_node.with_changes(
            params=updated_node.params.with_changes(params=existing_params)
        )
