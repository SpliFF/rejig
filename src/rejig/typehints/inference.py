"""Type inference utilities for Python code.

Provides heuristic type inference from:
- Default values
- Usage patterns
- Common naming conventions
"""
from __future__ import annotations

import libcst as cst


class TypeInference:
    """Utility class for inferring types from code patterns."""

    # Mapping of common variable name patterns to types
    NAME_PATTERNS = {
        "count": "int",
        "size": "int",
        "length": "int",
        "index": "int",
        "num": "int",
        "number": "int",
        "total": "int",
        "id": "int",
        "idx": "int",
        "age": "int",
        "year": "int",
        "month": "int",
        "day": "int",
        "hour": "int",
        "minute": "int",
        "second": "int",
        "price": "float",
        "amount": "float",
        "rate": "float",
        "ratio": "float",
        "percent": "float",
        "percentage": "float",
        "score": "float",
        "weight": "float",
        "height": "float",
        "width": "float",
        "name": "str",
        "title": "str",
        "description": "str",
        "text": "str",
        "message": "str",
        "label": "str",
        "key": "str",
        "value": "str",
        "path": "str | Path",
        "url": "str",
        "uri": "str",
        "email": "str",
        "username": "str",
        "password": "str",
        "content": "str",
        "data": "bytes",
        "enabled": "bool",
        "disabled": "bool",
        "active": "bool",
        "valid": "bool",
        "is_": "bool",
        "has_": "bool",
        "can_": "bool",
        "should_": "bool",
        "items": "list",
        "values": "list",
        "results": "list",
        "elements": "list",
        "entries": "list",
        "records": "list",
        "rows": "list",
        "mapping": "dict",
        "config": "dict",
        "settings": "dict",
        "options": "dict",
        "params": "dict",
        "kwargs": "dict",
        "args": "tuple",
        "callback": "Callable",
        "handler": "Callable",
        "func": "Callable",
        "function": "Callable",
    }

    @classmethod
    def infer_from_default(cls, default_value: cst.BaseExpression) -> str | None:
        """Infer type from a default value.

        Parameters
        ----------
        default_value : cst.BaseExpression
            The default value expression from the AST.

        Returns
        -------
        str | None
            Inferred type string, or None if cannot infer.
        """
        if isinstance(default_value, cst.Integer):
            return "int"
        if isinstance(default_value, cst.Float):
            return "float"
        if isinstance(default_value, (cst.SimpleString, cst.FormattedString, cst.ConcatenatedString)):
            # Check if it's a bytes literal
            if isinstance(default_value, cst.SimpleString):
                if default_value.value.startswith(("b'", 'b"', "B'", 'B"')):
                    return "bytes"
            return "str"
        if isinstance(default_value, cst.Name):
            if default_value.value == "True" or default_value.value == "False":
                return "bool"
            if default_value.value == "None":
                return "None"
        if isinstance(default_value, cst.List):
            if not default_value.elements:
                return "list"
            # Try to infer element type from first element
            first_elem = default_value.elements[0]
            if isinstance(first_elem, cst.Element):
                elem_type = cls.infer_from_default(first_elem.value)
                if elem_type:
                    return f"list[{elem_type}]"
            return "list"
        if isinstance(default_value, cst.Tuple):
            if not default_value.elements:
                return "tuple"
            return "tuple"
        if isinstance(default_value, cst.Dict):
            if not default_value.elements:
                return "dict"
            # Try to infer key/value types from first element
            first_elem = default_value.elements[0]
            if isinstance(first_elem, cst.DictElement):
                key_type = cls.infer_from_default(first_elem.key)
                val_type = cls.infer_from_default(first_elem.value)
                if key_type and val_type:
                    return f"dict[{key_type}, {val_type}]"
            return "dict"
        if isinstance(default_value, cst.Set):
            if not default_value.elements:
                return "set"
            first_elem = default_value.elements[0]
            if isinstance(first_elem, cst.Element):
                elem_type = cls.infer_from_default(first_elem.value)
                if elem_type:
                    return f"set[{elem_type}]"
            return "set"
        if isinstance(default_value, cst.Call):
            # Handle common constructor calls
            if isinstance(default_value.func, cst.Name):
                name = default_value.func.value
                if name in ("list", "dict", "set", "tuple", "frozenset"):
                    return name
                if name == "Path":
                    return "Path"
                if name == "datetime":
                    return "datetime"
                if name == "date":
                    return "date"
                if name == "time":
                    return "time"
                if name == "timedelta":
                    return "timedelta"
            elif isinstance(default_value.func, cst.Attribute):
                if isinstance(default_value.func.value, cst.Name):
                    # Handle things like datetime.now()
                    obj_name = default_value.func.value.value
                    attr_name = default_value.func.attr.value
                    if obj_name == "datetime" and attr_name in ("now", "utcnow", "today"):
                        return "datetime"
                    if obj_name == "date" and attr_name == "today":
                        return "date"
        if isinstance(default_value, cst.Lambda):
            return "Callable"
        if isinstance(default_value, cst.UnaryOperation):
            # Handle negative numbers
            if isinstance(default_value.operator, cst.Minus):
                inner_type = cls.infer_from_default(default_value.expression)
                return inner_type
        return None

    @classmethod
    def infer_from_name(cls, name: str) -> str | None:
        """Infer type from parameter/variable name.

        Parameters
        ----------
        name : str
            The parameter or variable name.

        Returns
        -------
        str | None
            Inferred type string, or None if cannot infer.
        """
        name_lower = name.lower()

        # Direct matches
        if name_lower in cls.NAME_PATTERNS:
            return cls.NAME_PATTERNS[name_lower]

        # Prefix matches
        for prefix in ("is_", "has_", "can_", "should_"):
            if name_lower.startswith(prefix):
                return "bool"

        # Suffix matches
        if name_lower.endswith("_id") or name_lower.endswith("_idx"):
            return "int"
        if name_lower.endswith("_count") or name_lower.endswith("_num"):
            return "int"
        if name_lower.endswith("_name") or name_lower.endswith("_text"):
            return "str"
        if name_lower.endswith("_path"):
            return "str | Path"
        if name_lower.endswith("_url") or name_lower.endswith("_uri"):
            return "str"
        if name_lower.endswith("_list") or name_lower.endswith("_items"):
            return "list"
        if name_lower.endswith("_dict") or name_lower.endswith("_map"):
            return "dict"
        if name_lower.endswith("_set"):
            return "set"
        if name_lower.endswith("_callback") or name_lower.endswith("_handler"):
            return "Callable"
        if name_lower.endswith("_enabled") or name_lower.endswith("_active"):
            return "bool"

        return None

    @classmethod
    def infer_type(
        cls,
        name: str | None = None,
        default_value: cst.BaseExpression | None = None,
    ) -> str | None:
        """Infer type from available information.

        Tries default value first, then falls back to name heuristics.

        Parameters
        ----------
        name : str | None
            The parameter or variable name.
        default_value : cst.BaseExpression | None
            The default value expression.

        Returns
        -------
        str | None
            Inferred type string, or None if cannot infer.
        """
        # Default value is most reliable
        if default_value is not None:
            inferred = cls.infer_from_default(default_value)
            if inferred:
                return inferred

        # Fall back to name heuristics
        if name is not None:
            inferred = cls.infer_from_name(name)
            if inferred:
                return inferred

        return None
