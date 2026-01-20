"""Type hint modernization utilities.

Converts old-style type hints to modern Python 3.10+ syntax:
- List[str] → list[str]
- Dict[str, int] → dict[str, int]
- Optional[str] → str | None
- Union[str, int] → str | int
"""
from __future__ import annotations

import libcst as cst
import libcst.matchers as m


class TypeHintModernizer(cst.CSTTransformer):
    """Transform old-style type hints to modern Python 3.10+ syntax."""

    # Mapping of typing module generics to built-in equivalents
    BUILTIN_GENERICS = {
        "List": "list",
        "Dict": "dict",
        "Set": "set",
        "FrozenSet": "frozenset",
        "Tuple": "tuple",
        "Type": "type",
    }

    def __init__(self) -> None:
        super().__init__()
        self.changed = False

    def _extract_slice_value(self, slice_elem: cst.BaseSlice) -> cst.BaseExpression:
        """Extract the expression from a slice element."""
        if isinstance(slice_elem, cst.Index):
            return slice_elem.value
        elif isinstance(slice_elem, cst.BaseExpression):
            return slice_elem
        else:
            # For cst.Slice and other types, return as-is (shouldn't happen for type hints)
            return slice_elem

    def _get_subscript_elements(
        self, subscript: cst.Subscript
    ) -> list[cst.BaseExpression]:
        """Extract all type expressions from a subscript's slice."""
        elements: list[cst.BaseExpression] = []
        slice_val = subscript.slice

        # In libcst, slice can be a sequence of SubscriptElement
        if isinstance(slice_val, (list, tuple)):
            for elem in slice_val:
                if isinstance(elem, cst.SubscriptElement):
                    elements.append(self._extract_slice_value(elem.slice))
                else:
                    elements.append(elem)
        elif isinstance(slice_val, cst.SubscriptElement):
            elements.append(self._extract_slice_value(slice_val.slice))
        else:
            # Direct slice (older libcst or simple case)
            elements.append(self._extract_slice_value(slice_val))

        return elements

    def leave_Subscript(
        self, original_node: cst.Subscript, updated_node: cst.Subscript
    ) -> cst.BaseExpression:
        """Transform subscripted types like List[str] → list[str]."""
        # Check if value is a Name from typing module
        if not isinstance(updated_node.value, cst.Name):
            return updated_node

        name = updated_node.value.value

        # Handle Optional[X] → X | None
        if name == "Optional":
            elements = self._get_subscript_elements(updated_node)
            if len(elements) != 1:
                return updated_node

            self.changed = True
            inner = elements[0]

            # Create X | None
            return cst.BinaryOperation(
                left=inner,
                operator=cst.BitOr(),
                right=cst.Name("None"),
            )

        # Handle Union[X, Y] → X | Y
        if name == "Union":
            elements = self._get_subscript_elements(updated_node)

            if len(elements) < 2:
                return updated_node

            self.changed = True

            # Build X | Y | Z chain
            result = elements[0]
            for t in elements[1:]:
                result = cst.BinaryOperation(
                    left=result,
                    operator=cst.BitOr(),
                    right=t,
                )
            return result

        # Handle builtin generics like List, Dict, etc.
        if name in self.BUILTIN_GENERICS:
            self.changed = True
            return updated_node.with_changes(
                value=cst.Name(self.BUILTIN_GENERICS[name])
            )

        return updated_node

    def leave_Attribute(
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.BaseExpression:
        """Handle typing.List, typing.Dict etc."""
        if isinstance(updated_node.value, cst.Name):
            if updated_node.value.value == "typing":
                attr_name = updated_node.attr.value
                if attr_name in self.BUILTIN_GENERICS:
                    self.changed = True
                    return cst.Name(self.BUILTIN_GENERICS[attr_name])
        return updated_node


class TypeCommentConverter(cst.CSTTransformer):
    """Convert type comments to inline annotations.

    Converts:
        x = 1  # type: int
    To:
        x: int = 1

    And:
        def f(x):  # type: (int) -> str
    To:
        def f(x: int) -> str:
    """

    def __init__(self) -> None:
        super().__init__()
        self.changed = False

    def leave_SimpleStatementLine(
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> cst.SimpleStatementLine:
        """Convert type comments on assignment lines."""
        # Check for trailing comment
        if not updated_node.trailing_comment:
            return updated_node

        comment = updated_node.trailing_comment.value
        if not comment.strip().startswith("# type:"):
            return updated_node

        # Extract the type from comment
        type_str = comment.split("# type:", 1)[1].strip()
        if type_str.startswith("ignore"):
            return updated_node

        # Check if this is an assignment
        if not updated_node.body or not isinstance(updated_node.body[0], cst.Assign):
            return updated_node

        assign = updated_node.body[0]
        if len(assign.targets) != 1:
            return updated_node

        target = assign.targets[0].target
        if not isinstance(target, cst.Name):
            return updated_node

        self.changed = True

        # Convert to annotated assignment
        try:
            annotation = cst.parse_expression(type_str)
            new_stmt = cst.AnnAssign(
                target=target,
                annotation=cst.Annotation(annotation=annotation),
                value=assign.value,
            )
            return updated_node.with_changes(
                body=[new_stmt],
                trailing_comment=None,
            )
        except Exception:
            # If we can't parse the type, leave it as is
            return updated_node

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Convert function type comments to annotations."""
        # Check for type comment in function body
        if not isinstance(updated_node.body, cst.IndentedBlock):
            return updated_node

        body = updated_node.body.body
        if not body:
            return updated_node

        # Check first statement for type comment
        first_stmt = body[0]
        if not isinstance(first_stmt, cst.SimpleStatementLine):
            return updated_node
        if not first_stmt.trailing_comment:
            return updated_node

        comment = first_stmt.trailing_comment.value
        if not comment.strip().startswith("# type:"):
            return updated_node

        type_str = comment.split("# type:", 1)[1].strip()
        if type_str.startswith("ignore"):
            return updated_node

        # Parse function type comment: (int, str) -> bool
        if "->" not in type_str:
            return updated_node

        try:
            params_str, return_str = type_str.split("->", 1)
            params_str = params_str.strip()
            return_str = return_str.strip()

            # Parse return type
            return_annotation = cst.parse_expression(return_str)

            # Parse parameter types
            if params_str.startswith("(") and params_str.endswith(")"):
                params_str = params_str[1:-1]

            param_types = [t.strip() for t in params_str.split(",") if t.strip()]

            # Update function parameters with types
            new_params = []
            param_list = list(updated_node.params.params)
            for i, param in enumerate(param_list):
                if i < len(param_types) and param_types[i] != "...":
                    try:
                        annotation = cst.parse_expression(param_types[i])
                        new_params.append(
                            param.with_changes(
                                annotation=cst.Annotation(annotation=annotation)
                            )
                        )
                    except Exception:
                        new_params.append(param)
                else:
                    new_params.append(param)

            self.changed = True

            # Remove the type comment from first statement
            new_first_stmt = first_stmt.with_changes(trailing_comment=None)
            new_body = [new_first_stmt] + list(body[1:])

            return updated_node.with_changes(
                params=updated_node.params.with_changes(params=new_params),
                returns=cst.Annotation(annotation=return_annotation),
                body=updated_node.body.with_changes(body=new_body),
            )
        except Exception:
            return updated_node
