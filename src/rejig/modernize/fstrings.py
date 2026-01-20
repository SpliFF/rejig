"""F-string conversion transformers.

Converts old-style string formatting to f-strings:
- "Hello {}".format(name) → f"Hello {name}"
- "Hello %s" % name → f"Hello {name}"
"""
from __future__ import annotations

import re
from typing import Sequence

import libcst as cst


class FormatToFstringTransformer(cst.CSTTransformer):
    """Transform .format() calls to f-strings.

    Converts:
        "Hello {}".format(name) → f"Hello {name}"
        "Hello {0}".format(name) → f"Hello {name}"
        "Hello {name}".format(name=value) → f"Hello {value}"
        "{} + {} = {}".format(a, b, c) → f"{a} + {b} = {c}"
    """

    def __init__(self) -> None:
        super().__init__()
        self.changed = False

    def leave_Call(
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> cst.BaseExpression:
        """Transform .format() calls to f-strings."""
        # Check if this is a .format() call on a string
        if not self._is_format_call(updated_node):
            return updated_node

        # Get the string being formatted
        string_node = self._get_string_value(updated_node.func)
        if string_node is None:
            return updated_node

        # Get the format arguments
        args = self._get_format_args(updated_node.args)
        if args is None:
            return updated_node

        # Try to convert to f-string
        try:
            fstring = self._convert_to_fstring(string_node, args)
            if fstring is not None:
                self.changed = True
                return fstring
        except Exception:
            pass

        return updated_node

    def _is_format_call(self, node: cst.Call) -> bool:
        """Check if this is a .format() call on a string literal."""
        if not isinstance(node.func, cst.Attribute):
            return False
        if node.func.attr.value != "format":
            return False
        return True

    def _get_string_value(self, func: cst.BaseExpression) -> cst.SimpleString | None:
        """Extract the string literal being formatted."""
        if not isinstance(func, cst.Attribute):
            return None
        value = func.value
        if isinstance(value, cst.SimpleString):
            return value
        return None

    def _get_format_args(
        self, args: Sequence[cst.Arg]
    ) -> tuple[list[cst.BaseExpression], dict[str, cst.BaseExpression]] | None:
        """Extract positional and keyword arguments from .format() call."""
        positional: list[cst.BaseExpression] = []
        keyword: dict[str, cst.BaseExpression] = {}

        for arg in args:
            if arg.keyword is None:
                # Skip *args and **kwargs
                if arg.star == "" or arg.star is None:
                    positional.append(arg.value)
                else:
                    return None  # Can't convert *args/**kwargs
            else:
                keyword[arg.keyword.value] = arg.value

        return positional, keyword

    def _convert_to_fstring(
        self,
        string_node: cst.SimpleString,
        args: tuple[list[cst.BaseExpression], dict[str, cst.BaseExpression]],
    ) -> cst.FormattedString | None:
        """Convert the string and arguments to an f-string."""
        positional, keyword = args

        # Get the string content without quotes
        string_value = string_node.value
        quote_char = string_value[0]

        # Handle raw strings
        prefix = ""
        if string_value.startswith(("r", "R")):
            prefix = string_value[0]
            string_value = string_value[1:]
            quote_char = string_value[0]

        # Determine quote style (single, double, triple)
        if string_value.startswith('"""') or string_value.startswith("'''"):
            quote = string_value[:3]
            content = string_value[3:-3]
        else:
            quote = string_value[0]
            content = string_value[1:-1]

        # Parse the format string and build f-string parts
        parts: list[cst.BaseFormattedStringContent] = []
        pos_idx = 0
        i = 0

        while i < len(content):
            # Look for format placeholders
            if content[i] == "{":
                if i + 1 < len(content) and content[i + 1] == "{":
                    # Escaped brace {{
                    parts.append(cst.FormattedStringText("{"))
                    i += 2
                    continue

                # Find the closing brace
                end = content.find("}", i)
                if end == -1:
                    return None  # Malformed format string

                placeholder = content[i + 1 : end]

                # Parse placeholder: could be "", "0", "name", "0:spec", "name:spec"
                format_spec = ""
                conversion = ""

                if "!" in placeholder:
                    placeholder, rest = placeholder.split("!", 1)
                    if ":" in rest:
                        conversion, format_spec = rest.split(":", 1)
                    else:
                        conversion = rest
                elif ":" in placeholder:
                    placeholder, format_spec = placeholder.split(":", 1)

                # Get the expression to substitute
                if placeholder == "" or placeholder.isdigit():
                    # Positional argument
                    idx = int(placeholder) if placeholder else pos_idx
                    if idx >= len(positional):
                        return None  # Not enough positional args
                    expr = positional[idx]
                    if placeholder == "":
                        pos_idx += 1
                else:
                    # Check for attribute access like {foo.bar}
                    if "." in placeholder or "[" in placeholder:
                        # Complex expression - need to look up base name
                        base_name = placeholder.split(".")[0].split("[")[0]
                        if base_name not in keyword:
                            return None
                        # Build the expression with attribute access
                        expr = keyword[base_name]
                        # Add the attribute/index accesses
                        rest_of_placeholder = placeholder[len(base_name):]
                        if rest_of_placeholder:
                            # Can't easily handle complex attribute access
                            return None
                    elif placeholder not in keyword:
                        return None
                    else:
                        expr = keyword[placeholder]

                # Build the f-string expression
                format_spec_parts = None
                if format_spec:
                    format_spec_parts = [cst.FormattedStringText(format_spec)]

                conversion_char = None
                if conversion:
                    conversion_char = conversion

                parts.append(
                    cst.FormattedStringExpression(
                        expression=expr,
                        conversion=conversion_char,
                        format_spec=format_spec_parts,
                    )
                )

                i = end + 1
            elif content[i] == "}":
                if i + 1 < len(content) and content[i + 1] == "}":
                    # Escaped brace }}
                    parts.append(cst.FormattedStringText("}"))
                    i += 2
                    continue
                else:
                    return None  # Unmatched brace
            else:
                # Regular text - collect until next brace
                text_start = i
                while i < len(content) and content[i] not in "{}":
                    i += 1
                if text_start < i:
                    parts.append(cst.FormattedStringText(content[text_start:i]))

        # Determine the quote style for the f-string
        if len(quote) == 3:
            start_quote = f'f{prefix}{quote}'
            end_quote = quote
        else:
            start_quote = f'f{prefix}{quote}'
            end_quote = quote

        return cst.FormattedString(
            parts=parts,
            start=start_quote,
            end=end_quote,
        )


class PercentToFstringTransformer(cst.CSTTransformer):
    """Transform % formatting to f-strings.

    Converts:
        "Hello %s" % name → f"Hello {name}"
        "Hello %s %s" % (a, b) → f"Hello {a} {b}"
        "%(name)s" % {"name": value} → f"{value}"
    """

    def __init__(self) -> None:
        super().__init__()
        self.changed = False

    def leave_BinaryOperation(
        self, original_node: cst.BinaryOperation, updated_node: cst.BinaryOperation
    ) -> cst.BaseExpression:
        """Transform % string formatting to f-strings."""
        # Check if this is a % operation with a string on the left
        if not isinstance(updated_node.operator, cst.Modulo):
            return updated_node

        if not isinstance(updated_node.left, cst.SimpleString):
            return updated_node

        string_node = updated_node.left
        right = updated_node.right

        try:
            fstring = self._convert_to_fstring(string_node, right)
            if fstring is not None:
                self.changed = True
                return fstring
        except Exception:
            pass

        return updated_node

    def _convert_to_fstring(
        self,
        string_node: cst.SimpleString,
        right: cst.BaseExpression,
    ) -> cst.FormattedString | None:
        """Convert % formatting to f-string."""
        # Get the string content
        string_value = string_node.value

        # Handle raw strings
        prefix = ""
        if string_value.startswith(("r", "R")):
            prefix = string_value[0]
            string_value = string_value[1:]

        # Determine quote style
        if string_value.startswith('"""') or string_value.startswith("'''"):
            quote = string_value[:3]
            content = string_value[3:-3]
        else:
            quote = string_value[0]
            content = string_value[1:-1]

        # Parse the format specifiers
        # Pattern matches: %s, %d, %f, %r, %(name)s, %10s, %.2f, etc.
        pattern = r"%(\((\w+)\))?([#0\- +]*)(\*|\d+)?(\.\d+)?([diouxXeEfFgGcrsba%])"

        parts: list[cst.BaseFormattedStringContent] = []
        values = self._get_values(right)
        if values is None:
            return None

        pos_idx = 0
        last_end = 0

        for match in re.finditer(pattern, content):
            # Add text before this placeholder
            if match.start() > last_end:
                text = content[last_end : match.start()]
                parts.append(cst.FormattedStringText(text))

            last_end = match.end()

            # Parse the format specifier
            key = match.group(2)  # Named key like %(name)s
            flags = match.group(3)
            width = match.group(4)
            precision = match.group(5)
            conversion_type = match.group(6)

            # Handle %% escape
            if conversion_type == "%":
                parts.append(cst.FormattedStringText("%"))
                continue

            # Get the value expression
            if key:
                # Named parameter
                if not isinstance(values, dict):
                    return None
                if key not in values:
                    return None
                expr = values[key]
            else:
                # Positional parameter
                if isinstance(values, dict):
                    return None
                if pos_idx >= len(values):
                    return None
                expr = values[pos_idx]
                pos_idx += 1

            # Build format spec
            format_spec = ""

            # Handle flags
            if flags:
                if "-" in flags:
                    format_spec += "<"
                elif "0" in flags:
                    format_spec += "0"
                if "+" in flags:
                    format_spec += "+"
                elif " " in flags:
                    format_spec += " "

            # Handle width
            if width and width != "*":
                format_spec += width
            elif width == "*":
                return None  # Can't handle dynamic width

            # Handle precision
            if precision:
                format_spec += precision

            # Handle conversion type
            conversion = None
            if conversion_type in ("s", "a"):
                pass  # Default string conversion
            elif conversion_type == "r":
                conversion = "r"
            elif conversion_type in ("d", "i"):
                format_spec += "d"
            elif conversion_type == "o":
                format_spec += "o"
            elif conversion_type in ("x", "X"):
                format_spec += conversion_type
            elif conversion_type in ("e", "E"):
                format_spec += conversion_type
            elif conversion_type in ("f", "F"):
                format_spec += conversion_type
            elif conversion_type in ("g", "G"):
                format_spec += conversion_type
            elif conversion_type == "c":
                format_spec += "c"
            elif conversion_type == "b":
                format_spec += "b"

            # Create format spec parts if needed
            format_spec_parts = None
            if format_spec:
                format_spec_parts = [cst.FormattedStringText(format_spec)]

            parts.append(
                cst.FormattedStringExpression(
                    expression=expr,
                    conversion=conversion,
                    format_spec=format_spec_parts,
                )
            )

        # Add any remaining text
        if last_end < len(content):
            parts.append(cst.FormattedStringText(content[last_end:]))

        # Create the f-string
        if len(quote) == 3:
            start_quote = f'f{prefix}{quote}'
            end_quote = quote
        else:
            start_quote = f'f{prefix}{quote}'
            end_quote = quote

        return cst.FormattedString(
            parts=parts,
            start=start_quote,
            end=end_quote,
        )

    def _get_values(
        self, right: cst.BaseExpression
    ) -> list[cst.BaseExpression] | dict[str, cst.BaseExpression] | None:
        """Extract values from the right side of % operator."""
        # Single value
        if isinstance(right, cst.Name):
            return [right]

        # Parenthesized single value or tuple
        if isinstance(right, cst.Tuple):
            return [elem.value for elem in right.elements]

        # Dictionary for named parameters
        if isinstance(right, cst.Dict):
            result = {}
            for elem in right.elements:
                if isinstance(elem, cst.DictElement):
                    if isinstance(elem.key, cst.SimpleString):
                        # Get the string value without quotes
                        key_str = elem.key.value[1:-1]
                        result[key_str] = elem.value
                    else:
                        return None  # Non-string key
                else:
                    return None  # StarredDictElement not supported
            return result

        # Other expressions (function calls, attribute access, etc.)
        if isinstance(right, (cst.Call, cst.Attribute, cst.Subscript)):
            return [right]

        return None
