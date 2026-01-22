"""Transformer to insert code at pattern matches."""
from __future__ import annotations

import re

import libcst as cst


class InsertAtMatch(cst.CSTTransformer):
    """Insert code before/after or replace a line matching a regex pattern.

    Supports scopes: module level, within a class, or within a method.

    Parameters
    ----------
    pattern : str
        Regex pattern to match against statement code.
    code : str
        Code to insert or use as replacement.
    position : str
        Where to insert: "before", "after", or "replace". Defaults to "before".
    scope : str | None
        Target scope: "module", "class", "method", or None (any). Defaults to None.
    class_name : str | None
        When scope is "class" or "method", the class to target.
    method_name : str | None
        When scope is "method", the method to target.

    Attributes
    ----------
    matched : bool
        True if the pattern was matched and code was inserted/replaced.

    Examples
    --------
    >>> # Insert logging after a specific line in a method
    >>> transformer = InsertAtMatch(
    ...     pattern=r"result = calculate\\(\\)",
    ...     code='logger.info(f"Result: {result}")',
    ...     position="after",
    ...     class_name="Calculator",
    ...     method_name="run"
    ... )
    >>> new_tree = tree.visit(transformer)
    """

    def __init__(
        self,
        pattern: str,
        code: str,
        position: str = "before",  # "before", "after", or "replace"
        scope: str | None = None,  # "module", "class", "method", or None (any)
        class_name: str | None = None,
        method_name: str | None = None,
    ):
        super().__init__()
        self.pattern = re.compile(pattern)
        self.code = code
        self.position = position
        self.scope = scope
        self.class_name = class_name
        self.method_name = method_name
        self.in_target_class = False
        self.in_target_method = False
        self.matched = False

    def _is_in_scope(self) -> bool:
        """Check if we're in the target scope."""
        if self.scope == "module":
            return not self.in_target_class and not self.in_target_method
        elif self.scope == "class":
            return self.in_target_class and not self.in_target_method
        elif self.scope == "method":
            return self.in_target_class and self.in_target_method
        else:
            # No scope restriction, but if class/method specified, must be in them
            if self.method_name and not self.in_target_method:
                return False
            if self.class_name and not self.in_target_class:
                return False
            return True

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
        if self.method_name and node.name.value == self.method_name:
            self.in_target_method = True
        return True

    def leave_FunctionDef(
        self,
        original_node: cst.FunctionDef,
        updated_node: cst.FunctionDef,
    ) -> cst.FunctionDef:
        if self.method_name and original_node.name.value == self.method_name:
            self.in_target_method = False
        return updated_node

    def _get_statement_code(self, node: cst.BaseStatement) -> str:
        """Get the code representation of a statement for regex matching."""
        return cst.parse_module("").code_for_node(node).strip()

    def leave_IndentedBlock(
        self,
        original_node: cst.IndentedBlock,
        updated_node: cst.IndentedBlock,
    ) -> cst.IndentedBlock:
        """Process statements within an indented block (method/class body)."""
        if self.matched or not self._is_in_scope():
            return updated_node

        new_body = []
        for stmt in updated_node.body:
            stmt_code = self._get_statement_code(stmt)

            if not self.matched and self.pattern.search(stmt_code):
                self.matched = True

                if self.position == "before":
                    new_stmt = cst.parse_statement(self.code)
                    new_body.append(new_stmt)
                    new_body.append(stmt)
                elif self.position == "after":
                    new_body.append(stmt)
                    new_stmt = cst.parse_statement(self.code)
                    new_body.append(new_stmt)
                elif self.position == "replace":
                    new_stmt = cst.parse_statement(self.code)
                    new_body.append(new_stmt)
            else:
                new_body.append(stmt)

        if new_body != list(updated_node.body):
            return updated_node.with_changes(body=new_body)
        return updated_node

    def leave_Module(
        self,
        original_node: cst.Module,
        updated_node: cst.Module,
    ) -> cst.Module:
        """Process module-level statements."""
        if self.matched or self.scope not in (None, "module"):
            return updated_node

        # Only process if we're looking at module scope
        if self.class_name or self.method_name:
            return updated_node

        new_body = []
        for stmt in updated_node.body:
            stmt_code = self._get_statement_code(stmt)

            if not self.matched and self.pattern.search(stmt_code):
                self.matched = True

                if self.position == "before":
                    new_stmt = cst.parse_statement(self.code)
                    new_body.append(new_stmt)
                    new_body.append(stmt)
                elif self.position == "after":
                    new_body.append(stmt)
                    new_stmt = cst.parse_statement(self.code)
                    new_body.append(new_stmt)
                elif self.position == "replace":
                    new_stmt = cst.parse_statement(self.code)
                    new_body.append(new_stmt)
            else:
                new_body.append(stmt)

        if new_body != list(updated_node.body):
            return updated_node.with_changes(body=new_body)
        return updated_node
