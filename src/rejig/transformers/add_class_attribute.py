"""Transformer to add class-level attributes."""
from __future__ import annotations

import libcst as cst


class AddClassAttribute(cst.CSTTransformer):
    """Add a class-level attribute with type annotation.

    Inserts a new annotated assignment at the class level, typically after
    the class docstring if one exists.

    Parameters
    ----------
    class_name : str
        Name of the class to add the attribute to.
    attr_name : str
        Name of the attribute to add.
    type_annotation : str
        Type annotation as a string (e.g., "str", "int | None", "list[str]").
    default_value : str
        Default value as a string. Defaults to "None".

    Attributes
    ----------
    added : bool
        True if the attribute was added.

    Examples
    --------
    >>> transformer = AddClassAttribute("User", "email", "str | None", "None")
    >>> new_tree = tree.visit(transformer)
    >>> # Adds: email: str | None = None
    """

    def __init__(
        self,
        class_name: str,
        attr_name: str,
        type_annotation: str,
        default_value: str = "None",
    ):
        super().__init__()
        self.class_name = class_name
        self.attr_name = attr_name
        self.type_annotation = type_annotation
        self.default_value = default_value
        self.added = False

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        if updated_node.name.value != self.class_name:
            return updated_node

        # Create the new attribute line: attr_name: Type = default_value
        new_attr = cst.SimpleStatementLine(
            body=[
                cst.AnnAssign(
                    target=cst.Name(self.attr_name),
                    annotation=cst.Annotation(
                        annotation=cst.parse_expression(self.type_annotation)
                    ),
                    value=cst.parse_expression(self.default_value),
                )
            ],
            leading_lines=[cst.EmptyLine()],
        )

        # Insert after the class docstring (if any) or at the beginning
        new_body = list(updated_node.body.body)
        insert_idx = 0

        # Skip past docstring if present
        if new_body and isinstance(new_body[0], cst.SimpleStatementLine):
            if len(new_body[0].body) == 1 and isinstance(new_body[0].body[0], cst.Expr):
                expr = new_body[0].body[0].value
                if isinstance(expr, (cst.SimpleString, cst.ConcatenatedString, cst.FormattedString)):
                    insert_idx = 1

        new_body.insert(insert_idx, new_attr)
        self.added = True

        return updated_node.with_changes(
            body=updated_node.body.with_changes(body=new_body)
        )
