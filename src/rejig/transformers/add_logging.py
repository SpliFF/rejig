"""Transformer to add logging statements to functions."""
from __future__ import annotations

import libcst as cst


class AddLogging(cst.CSTTransformer):
    """Add logging statements to a function/method.

    Inserts a logging statement at the start of the function that logs
    entry with optional argument values.

    Parameters
    ----------
    class_name : str | None
        Name of the class containing the method. Use None for module-level functions.
    function_name : str
        Name of the method or function.
    level : str
        Logging level: "debug", "info", "warning", "error", "critical".
        Defaults to "debug".
    include_args : bool
        If True, include argument values in the log message.
        Defaults to False.
    logger_name : str
        Name of the logger variable. Defaults to "logger".

    Examples
    --------
    >>> transformer = AddLogging(None, "process", "debug", include_args=True)
    >>> new_tree = tree.visit(transformer)
    """

    def __init__(
        self,
        class_name: str | None,
        function_name: str,
        level: str = "debug",
        include_args: bool = False,
        logger_name: str = "logger",
    ):
        super().__init__()
        self.class_name = class_name
        self.function_name = function_name
        self.level = level.lower()
        self.include_args = include_args
        self.logger_name = logger_name
        self.in_target_class = class_name is None
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
        if not self.in_target_class or updated_node.name.value != self.function_name:
            return updated_node

        body = updated_node.body
        if not isinstance(body, cst.IndentedBlock):
            return updated_node

        # Build the logging statement
        log_stmt = self._build_log_statement(updated_node)

        # Find insertion point (after docstring if present)
        insert_idx = 0
        if body.body:
            first_stmt = body.body[0]
            if isinstance(first_stmt, cst.SimpleStatementLine):
                for expr in first_stmt.body:
                    if isinstance(expr, cst.Expr) and isinstance(expr.value, cst.SimpleString | cst.ConcatenatedString | cst.FormattedString):
                        # It's a docstring
                        insert_idx = 1
                        break

        # Insert the logging statement
        new_body = list(body.body)
        new_body.insert(insert_idx, log_stmt)

        self.added = True
        return updated_node.with_changes(
            body=body.with_changes(body=new_body)
        )

    def _build_log_statement(self, func_node: cst.FunctionDef) -> cst.SimpleStatementLine:
        """Build the logging statement."""
        func_name = func_node.name.value

        if self.include_args:
            # Build f-string with argument values
            param_names = self._get_param_names(func_node.params)
            # Skip self/cls
            if param_names and param_names[0] in ("self", "cls"):
                param_names = param_names[1:]

            if param_names:
                args_str = ", ".join(f"{p}={{{p}!r}}" for p in param_names)
                log_message = f'f"Entering {func_name}({args_str})"'
            else:
                log_message = f'"Entering {func_name}()"'
        else:
            log_message = f'"Entering {func_name}"'

        stmt_code = f"{self.logger_name}.{self.level}({log_message})"
        return cst.parse_statement(stmt_code)

    def _get_param_names(self, params: cst.Parameters) -> list[str]:
        """Get regular parameter names from a Parameters node."""
        names: list[str] = []
        for param in params.params:
            names.append(param.name.value)
        return names
