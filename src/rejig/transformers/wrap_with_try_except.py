"""Transformer to wrap function body with try/except."""
from __future__ import annotations

import libcst as cst


class WrapWithTryExcept(cst.CSTTransformer):
    """Wrap a function/method body with try/except block.

    Parameters
    ----------
    class_name : str | None
        Name of the class containing the method. Use None for module-level functions.
    function_name : str
        Name of the method or function.
    exceptions : list[str]
        List of exception types to catch (e.g., ["ValueError", "TypeError"]).
    handler : str
        Handler code to execute in except block.
        Use 'e' to reference the caught exception.

    Examples
    --------
    >>> transformer = WrapWithTryExcept(
    ...     None, "process",
    ...     ["ValueError", "TypeError"],
    ...     "logger.error(f'Error: {e}'); raise"
    ... )
    >>> new_tree = tree.visit(transformer)
    """

    def __init__(
        self,
        class_name: str | None,
        function_name: str,
        exceptions: list[str],
        handler: str,
    ):
        super().__init__()
        self.class_name = class_name
        self.function_name = function_name
        self.exceptions = exceptions
        self.handler = handler
        self.in_target_class = class_name is None
        self.wrapped = False

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

        body = updated_node.body
        if not isinstance(body, cst.IndentedBlock):
            return updated_node

        # Check if already wrapped in try
        if len(body.body) == 1 and isinstance(body.body[0], cst.Try):
            return updated_node

        # Build exception type(s)
        if len(self.exceptions) == 1:
            exc_type = cst.parse_expression(self.exceptions[0])
        else:
            # Multiple exceptions as tuple
            exc_tuple = "(" + ", ".join(self.exceptions) + ")"
            exc_type = cst.parse_expression(exc_tuple)

        # Parse handler statements
        handler_statements = self._parse_handler(self.handler)

        # Create the except handler
        except_handler = cst.ExceptHandler(
            type=exc_type,
            name=cst.AsName(
                whitespace_before_as=cst.SimpleWhitespace(" "),
                whitespace_after_as=cst.SimpleWhitespace(" "),
                name=cst.Name("e"),
            ),
            body=cst.IndentedBlock(body=handler_statements),
        )

        # Create try statement with original body
        try_stmt = cst.Try(
            body=body,
            handlers=[except_handler],
        )

        self.wrapped = True
        return updated_node.with_changes(
            body=cst.IndentedBlock(body=[try_stmt])
        )

    def _parse_handler(self, handler: str) -> list[cst.BaseStatement]:
        """Parse handler code into a list of statements."""
        # Handle semicolon-separated statements
        parts = [p.strip() for p in handler.split(";") if p.strip()]

        statements: list[cst.BaseStatement] = []
        for part in parts:
            try:
                stmt = cst.parse_statement(part)
                statements.append(stmt)
            except Exception:
                # If parsing fails, wrap in pass
                continue

        if not statements:
            statements = [cst.parse_statement("pass")]

        return statements
