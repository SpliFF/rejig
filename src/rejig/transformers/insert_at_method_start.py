"""Transformer to insert statements at method/function start."""
from __future__ import annotations

import libcst as cst


class InsertAtMethodStart(cst.CSTTransformer):
    """Insert a statement at the start of a method body."""

    def __init__(self, class_name: str | None, method_name: str, statement: str):
        super().__init__()
        self.class_name = class_name
        self.method_name = method_name
        self.statement = statement
        self.in_target_class = class_name is None  # If no class, we're at module level
        self.inserted = False

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

        # Parse the new statement
        new_stmt = cst.parse_statement(self.statement)

        # Get the existing body
        if isinstance(updated_node.body, cst.IndentedBlock):
            existing_body = list(updated_node.body.body)

            # Skip docstring if present
            insert_idx = 0
            if existing_body and isinstance(existing_body[0], cst.SimpleStatementLine):
                if len(existing_body[0].body) == 1 and isinstance(existing_body[0].body[0], cst.Expr):
                    expr = existing_body[0].body[0].value
                    if isinstance(expr, (cst.SimpleString, cst.ConcatenatedString, cst.FormattedString)):
                        insert_idx = 1

            existing_body.insert(insert_idx, new_stmt)
            self.inserted = True

            return updated_node.with_changes(
                body=updated_node.body.with_changes(body=existing_body)
            )

        return updated_node
