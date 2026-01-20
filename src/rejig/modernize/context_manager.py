"""Context manager conversion transformer.

Converts classes to context managers by adding __enter__/__exit__ methods.
"""
from __future__ import annotations

import libcst as cst


class ConvertToContextManagerTransformer(cst.CSTTransformer):
    """Add __enter__ and __exit__ methods to make a class a context manager.

    If the class has:
    - open/connect method: use it in __enter__, add close/disconnect in __exit__
    - resource attribute: return it in __enter__, clean up in __exit__
    - otherwise: return self in __enter__, pass in __exit__
    """

    def __init__(
        self,
        class_name: str,
        enter_body: str | None = None,
        exit_body: str | None = None,
    ) -> None:
        super().__init__()
        self.class_name = class_name
        self.enter_body = enter_body
        self.exit_body = exit_body
        self.converted = False
        self._has_enter = False
        self._has_exit = False
        self._has_open = False
        self._has_close = False
        self._has_connect = False
        self._has_disconnect = False
        self._in_target_class = False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        """Check what methods the class has."""
        if node.name.value == self.class_name:
            self._in_target_class = True
            # Scan for existing methods
            for stmt in node.body.body if isinstance(node.body, cst.IndentedBlock) else []:
                if isinstance(stmt, cst.FunctionDef):
                    method_name = stmt.name.value
                    if method_name == "__enter__":
                        self._has_enter = True
                    elif method_name == "__exit__":
                        self._has_exit = True
                    elif method_name == "open":
                        self._has_open = True
                    elif method_name == "close":
                        self._has_close = True
                    elif method_name == "connect":
                        self._has_connect = True
                    elif method_name == "disconnect":
                        self._has_disconnect = True
        return True

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Add context manager methods."""
        if original_node.name.value != self.class_name:
            return updated_node

        self._in_target_class = False

        # Don't add if already a context manager
        if self._has_enter and self._has_exit:
            return updated_node

        methods_to_add: list[cst.FunctionDef] = []

        # Generate __enter__ method
        if not self._has_enter:
            enter_method = self._create_enter_method()
            # Add blank line before method
            enter_method = enter_method.with_changes(
                leading_lines=[cst.EmptyLine()]
            )
            methods_to_add.append(enter_method)

        # Generate __exit__ method
        if not self._has_exit:
            exit_method = self._create_exit_method()
            # Add blank line before method
            exit_method = exit_method.with_changes(
                leading_lines=[cst.EmptyLine()]
            )
            methods_to_add.append(exit_method)

        if not methods_to_add:
            return updated_node

        # Add methods to class body
        body = updated_node.body
        if isinstance(body, cst.IndentedBlock):
            new_body_items = list(body.body) + methods_to_add
            new_body = body.with_changes(body=new_body_items)
            self.converted = True
            return updated_node.with_changes(body=new_body)

        return updated_node

    def _create_enter_method(self) -> cst.FunctionDef:
        """Create __enter__ method."""
        if self.enter_body:
            body_code = self.enter_body
        elif self._has_open:
            body_code = "self.open()\nreturn self"
        elif self._has_connect:
            body_code = "self.connect()\nreturn self"
        else:
            body_code = "return self"

        # Parse the body
        body_stmts = self._parse_body(body_code)

        return cst.FunctionDef(
            name=cst.Name("__enter__"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
            body=cst.IndentedBlock(body=body_stmts),
            returns=cst.Annotation(annotation=cst.Name("Self")),
            decorators=[],
        )

    def _create_exit_method(self) -> cst.FunctionDef:
        """Create __exit__ method."""
        if self.exit_body:
            body_code = self.exit_body
        elif self._has_close:
            body_code = "self.close()\nreturn None"
        elif self._has_disconnect:
            body_code = "self.disconnect()\nreturn None"
        else:
            body_code = "return None"

        # Parse the body
        body_stmts = self._parse_body(body_code)

        # Standard __exit__ signature
        params = cst.Parameters(
            params=[
                cst.Param(name=cst.Name("self")),
                cst.Param(
                    name=cst.Name("exc_type"),
                    annotation=cst.Annotation(
                        annotation=cst.Subscript(
                            value=cst.Name("type"),
                            slice=[
                                cst.SubscriptElement(
                                    slice=cst.Index(value=cst.Name("BaseException"))
                                )
                            ],
                        )
                    ),
                ),
                cst.Param(
                    name=cst.Name("exc_val"),
                    annotation=cst.Annotation(
                        annotation=cst.BinaryOperation(
                            left=cst.Name("BaseException"),
                            operator=cst.BitOr(),
                            right=cst.Name("None"),
                        )
                    ),
                ),
                cst.Param(
                    name=cst.Name("exc_tb"),
                    annotation=cst.Annotation(
                        annotation=cst.BinaryOperation(
                            left=cst.Name("TracebackType"),
                            operator=cst.BitOr(),
                            right=cst.Name("None"),
                        )
                    ),
                ),
            ]
        )

        return cst.FunctionDef(
            name=cst.Name("__exit__"),
            params=params,
            body=cst.IndentedBlock(body=body_stmts),
            returns=cst.Annotation(
                annotation=cst.BinaryOperation(
                    left=cst.Name("bool"),
                    operator=cst.BitOr(),
                    right=cst.Name("None"),
                )
            ),
            decorators=[],
        )

    def _parse_body(self, code: str) -> list[cst.BaseStatement]:
        """Parse a code string into a list of statements."""
        # Wrap in a function to parse, then extract body
        wrapped = f"def _():\n    {code.replace(chr(10), chr(10) + '    ')}"
        try:
            module = cst.parse_module(wrapped)
            func = module.body[0]
            if isinstance(func, cst.FunctionDef) and isinstance(func.body, cst.IndentedBlock):
                return list(func.body.body)
        except Exception:
            pass

        # Fallback: simple return statement
        return [
            cst.SimpleStatementLine(
                body=[cst.Return(value=cst.Name("self"))]
            )
        ]
