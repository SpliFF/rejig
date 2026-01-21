"""Docstring generator for creating docstrings from function signatures.

Generates docstrings in Google, NumPy, or Sphinx style from function/method
signatures, including parameters, return types, and raised exceptions.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import libcst as cst

from rejig.docstrings.styles import (
    DocstringParam,
    DocstringRaises,
    DocstringReturns,
    DocstringStyle,
    DocstringStyleType,
    ParsedDocstring,
    get_formatter,
)

if TYPE_CHECKING:
    from pathlib import Path


class DocstringGenerator:
    """Generate docstrings from function/method signatures.

    Analyzes function parameters, return type annotations, and raised
    exceptions to generate complete docstrings.

    Parameters
    ----------
    style : DocstringStyle | str
        The docstring style to generate ("google", "numpy", or "sphinx").

    Examples
    --------
    >>> gen = DocstringGenerator(style="google")
    >>> code = '''
    ... def process(data: list[str], timeout: int = 30) -> dict:
    ...     pass
    ... '''
    >>> tree = cst.parse_module(code)
    >>> func = tree.body[0]
    >>> docstring = gen.generate(func)
    """

    def __init__(self, style: DocstringStyle | DocstringStyleType = "google") -> None:
        """Initialize the generator.

        Parameters
        ----------
        style : DocstringStyle | str
            The docstring style to generate.
        """
        self.style = DocstringStyle(style) if isinstance(style, str) else style
        self._formatter = get_formatter(self.style)

    def generate(
        self,
        node: cst.FunctionDef,
        include_raises: bool = True,
        summary: str = "",
    ) -> str:
        """Generate a docstring for a function/method.

        Parameters
        ----------
        node : cst.FunctionDef
            The function node to generate a docstring for.
        include_raises : bool
            Whether to analyze the function body for raised exceptions.
        summary : str
            Custom summary line. If empty, generates from function name.

        Returns
        -------
        str
            The generated docstring.
        """
        parsed = self.generate_parsed(node, include_raises, summary)
        return self._formatter.format(parsed)

    def generate_parsed(
        self,
        node: cst.FunctionDef,
        include_raises: bool = True,
        summary: str = "",
    ) -> ParsedDocstring:
        """Generate a ParsedDocstring for a function/method.

        Parameters
        ----------
        node : cst.FunctionDef
            The function node to generate a docstring for.
        include_raises : bool
            Whether to analyze the function body for raised exceptions.
        summary : str
            Custom summary line. If empty, generates from function name.

        Returns
        -------
        ParsedDocstring
            The parsed docstring structure.
        """
        result = ParsedDocstring()

        # Generate summary if not provided
        if summary:
            result.summary = summary
        else:
            result.summary = self._generate_summary(node.name.value)

        # Extract parameters
        result.params = self._extract_params(node.params)

        # Extract return type
        if node.returns:
            result.returns = self._extract_return_type(node.returns)

        # Extract raised exceptions
        if include_raises:
            result.raises = self._extract_raises(node.body)

        return result

    def _generate_summary(self, func_name: str) -> str:
        """Generate a summary line from the function name.

        Parameters
        ----------
        func_name : str
            The function name.

        Returns
        -------
        str
            A summary line.
        """
        # Convert snake_case to words
        words = func_name.replace("_", " ").strip()

        # Handle common prefixes
        if func_name.startswith("get_"):
            return f"Get {words[4:]}."
        elif func_name.startswith("set_"):
            return f"Set {words[4:]}."
        elif func_name.startswith("is_"):
            return f"Check if {words[3:]}."
        elif func_name.startswith("has_"):
            return f"Check if has {words[4:]}."
        elif func_name.startswith("create_"):
            return f"Create {words[7:]}."
        elif func_name.startswith("delete_"):
            return f"Delete {words[7:]}."
        elif func_name.startswith("update_"):
            return f"Update {words[7:]}."
        elif func_name.startswith("find_"):
            return f"Find {words[5:]}."
        elif func_name.startswith("add_"):
            return f"Add {words[4:]}."
        elif func_name.startswith("remove_"):
            return f"Remove {words[7:]}."
        elif func_name.startswith("validate_"):
            return f"Validate {words[9:]}."
        elif func_name.startswith("parse_"):
            return f"Parse {words[6:]}."
        elif func_name.startswith("convert_"):
            return f"Convert {words[8:]}."
        elif func_name.startswith("calculate_"):
            return f"Calculate {words[10:]}."
        elif func_name.startswith("compute_"):
            return f"Compute {words[8:]}."
        elif func_name.startswith("_"):
            # Private methods
            return f"Internal: {words.lstrip()}."
        elif func_name == "__init__":
            return "Initialize the instance."
        elif func_name == "__repr__":
            return "Return string representation."
        elif func_name == "__str__":
            return "Return string representation."
        elif func_name == "__eq__":
            return "Check equality."
        elif func_name == "__hash__":
            return "Return hash value."
        elif func_name == "__len__":
            return "Return the length."
        elif func_name == "__iter__":
            return "Return an iterator."
        elif func_name == "__next__":
            return "Return the next value."
        elif func_name == "__enter__":
            return "Enter the context manager."
        elif func_name == "__exit__":
            return "Exit the context manager."

        # Default: capitalize and add period
        return f"{words.capitalize()}."

    def _extract_params(self, params: cst.Parameters) -> list[DocstringParam]:
        """Extract parameters from function signature.

        Parameters
        ----------
        params : cst.Parameters
            The parameters node.

        Returns
        -------
        list[DocstringParam]
            List of extracted parameters.
        """
        result: list[DocstringParam] = []

        # Regular parameters
        for param in params.params:
            name = param.name.value

            # Skip self and cls
            if name in ("self", "cls"):
                continue

            type_hint = ""
            if param.annotation:
                type_hint = self._annotation_to_str(param.annotation.annotation)

            # Generate description from parameter name
            description = self._generate_param_description(name, type_hint)

            result.append(DocstringParam(
                name=name,
                type_hint=type_hint,
                description=description,
            ))

        # *args
        if params.star_arg and isinstance(params.star_arg, cst.Param):
            name = params.star_arg.name.value
            type_hint = ""
            if params.star_arg.annotation:
                type_hint = self._annotation_to_str(params.star_arg.annotation.annotation)
            result.append(DocstringParam(
                name=f"*{name}",
                type_hint=type_hint,
                description="Variable positional arguments.",
            ))

        # Keyword-only parameters
        for param in params.kwonly_params:
            name = param.name.value
            type_hint = ""
            if param.annotation:
                type_hint = self._annotation_to_str(param.annotation.annotation)

            description = self._generate_param_description(name, type_hint)

            result.append(DocstringParam(
                name=name,
                type_hint=type_hint,
                description=description,
            ))

        # **kwargs
        if params.star_kwarg:
            name = params.star_kwarg.name.value
            type_hint = ""
            if params.star_kwarg.annotation:
                type_hint = self._annotation_to_str(params.star_kwarg.annotation.annotation)
            result.append(DocstringParam(
                name=f"**{name}",
                type_hint=type_hint,
                description="Variable keyword arguments.",
            ))

        return result

    def _generate_param_description(self, name: str, type_hint: str) -> str:
        """Generate a description from parameter name and type.

        Parameters
        ----------
        name : str
            Parameter name.
        type_hint : str
            Type hint string.

        Returns
        -------
        str
            Generated description.
        """
        # Convert snake_case to words
        words = name.replace("_", " ").strip()

        # Handle common naming patterns
        if name.startswith("is_") or name.startswith("has_"):
            return f"Whether {words[3:]}."
        elif name.startswith("num_") or name.startswith("n_"):
            return f"Number of {words.split(' ', 1)[-1]}."
        elif name.startswith("max_"):
            return f"Maximum {words[4:]}."
        elif name.startswith("min_"):
            return f"Minimum {words[4:]}."
        elif name == "timeout":
            return "Timeout in seconds."
        elif name == "path" or name.endswith("_path"):
            return f"Path to {words.replace(' path', '')}." if "_" in name else "The path."
        elif name == "file" or name.endswith("_file"):
            return f"File {words.replace(' file', '')}." if "_" in name else "The file."
        elif name == "name":
            return "The name."
        elif name == "value":
            return "The value."
        elif name == "data":
            return "The data."
        elif name == "config":
            return "Configuration settings."
        elif name == "options":
            return "Options to configure behavior."
        elif name == "callback":
            return "Callback function."
        elif name == "index" or name == "idx":
            return "The index."
        elif name == "key":
            return "The key."
        elif name == "keys":
            return "The keys."

        # Use type hint for description if available
        if type_hint:
            if "Callable" in type_hint:
                return f"A callable {words}."
            elif "list" in type_hint.lower() or "List" in type_hint:
                return f"List of {words}."
            elif "dict" in type_hint.lower() or "Dict" in type_hint:
                return f"Dictionary of {words}."
            elif "bool" in type_hint.lower():
                return f"Whether to {words}."

        # Default
        return f"The {words}."

    def _extract_return_type(self, annotation: cst.Annotation) -> DocstringReturns:
        """Extract return type from annotation.

        Parameters
        ----------
        annotation : cst.Annotation
            The return annotation node.

        Returns
        -------
        DocstringReturns
            The return type information.
        """
        type_hint = self._annotation_to_str(annotation.annotation)
        description = self._generate_return_description(type_hint)

        return DocstringReturns(
            description=description,
            type_hint=type_hint,
        )

    def _generate_return_description(self, type_hint: str) -> str:
        """Generate a description from return type.

        Parameters
        ----------
        type_hint : str
            The return type hint.

        Returns
        -------
        str
            Generated description.
        """
        type_lower = type_hint.lower()

        if type_hint == "None":
            return "None"
        elif "bool" in type_lower:
            return "True if successful, False otherwise."
        elif "list" in type_lower or "List" in type_hint:
            return "List of results."
        elif "dict" in type_lower or "Dict" in type_hint:
            return "Dictionary of results."
        elif "str" in type_lower:
            return "The resulting string."
        elif "int" in type_lower:
            return "The computed value."
        elif "float" in type_lower:
            return "The computed value."
        elif "Path" in type_hint:
            return "The path."
        elif "Result" in type_hint:
            return "Result of the operation."
        elif type_hint.startswith("tuple"):
            return "Tuple of results."
        elif type_hint.startswith("set"):
            return "Set of results."

        return "The result."

    def _extract_raises(self, body: cst.BaseSuite) -> list[DocstringRaises]:
        """Extract raised exceptions from function body.

        Parameters
        ----------
        body : cst.BaseSuite
            The function body.

        Returns
        -------
        list[DocstringRaises]
            List of exceptions that may be raised.
        """
        result: list[DocstringRaises] = []
        seen: set[str] = set()

        class RaiseVisitor(cst.CSTVisitor):
            def visit_Raise(self, node: cst.Raise) -> bool:
                if node.exc:
                    exc_name = self._get_exception_name(node.exc)
                    if exc_name and exc_name not in seen:
                        seen.add(exc_name)
                        desc = self._generate_raise_description(exc_name)
                        result.append(DocstringRaises(exception=exc_name, description=desc))
                return True

            def _get_exception_name(self, node: cst.BaseExpression) -> str | None:
                if isinstance(node, cst.Name):
                    return node.value
                elif isinstance(node, cst.Call):
                    return self._get_exception_name(node.func)
                elif isinstance(node, cst.Attribute):
                    return node.attr.value
                return None

            def _generate_raise_description(self, exc_name: str) -> str:
                common = {
                    "ValueError": "If the input value is invalid.",
                    "TypeError": "If the input type is incorrect.",
                    "KeyError": "If the key is not found.",
                    "IndexError": "If the index is out of range.",
                    "AttributeError": "If the attribute is not found.",
                    "FileNotFoundError": "If the file is not found.",
                    "RuntimeError": "If a runtime error occurs.",
                    "IOError": "If an I/O error occurs.",
                    "OSError": "If an OS error occurs.",
                    "NotImplementedError": "If the method is not implemented.",
                }
                return common.get(exc_name, f"If {exc_name} condition is met.")

        def find_raises_recursive(node):
            """Recursively find all Raise statements in a CST node."""
            if isinstance(node, cst.Raise) and node.exc:
                exc_name = None
                if isinstance(node.exc, cst.Name):
                    exc_name = node.exc.value
                elif isinstance(node.exc, cst.Call):
                    if isinstance(node.exc.func, cst.Name):
                        exc_name = node.exc.func.value
                    elif isinstance(node.exc.func, cst.Attribute):
                        exc_name = node.exc.func.attr.value
                if exc_name and exc_name not in seen:
                    seen.add(exc_name)
                    common = {
                        "ValueError": "If the input value is invalid.",
                        "TypeError": "If the input type is incorrect.",
                        "KeyError": "If the key is not found.",
                        "IndexError": "If the index is out of range.",
                        "AttributeError": "If the attribute is not found.",
                        "FileNotFoundError": "If the file is not found.",
                        "RuntimeError": "If a runtime error occurs.",
                        "IOError": "If an I/O error occurs.",
                        "OSError": "If an OS error occurs.",
                        "NotImplementedError": "If the method is not implemented.",
                    }
                    desc = common.get(exc_name, f"If {exc_name} condition is met.")
                    result.append(DocstringRaises(exception=exc_name, description=desc))
                return

            # Recursively search children
            for child in node.children:
                if isinstance(child, cst.CSTNode):
                    find_raises_recursive(child)

        if isinstance(body, cst.IndentedBlock):
            find_raises_recursive(body)

        return result

    def _annotation_to_str(self, node: cst.BaseExpression) -> str:
        """Convert an annotation node to a string.

        Parameters
        ----------
        node : cst.BaseExpression
            The annotation node.

        Returns
        -------
        str
            The string representation of the annotation.
        """
        if isinstance(node, cst.Name):
            return node.value
        elif isinstance(node, cst.Attribute):
            return f"{self._annotation_to_str(node.value)}.{node.attr.value}"
        elif isinstance(node, cst.Subscript):
            base = self._annotation_to_str(node.value)
            slices = []
            for element in node.slice:
                if isinstance(element, cst.SubscriptElement):
                    slices.append(self._annotation_to_str(element.slice.value))
            return f"{base}[{', '.join(slices)}]"
        elif isinstance(node, cst.BinaryOperation):
            left = self._annotation_to_str(node.left)
            right = self._annotation_to_str(node.right)
            if isinstance(node.operator, cst.BitOr):
                return f"{left} | {right}"
            return f"{left} | {right}"
        elif isinstance(node, cst.SimpleString):
            # String annotation (forward reference)
            value = node.value
            if value.startswith('"') or value.startswith("'"):
                return value[1:-1]
            return value
        elif isinstance(node, cst.Ellipsis):
            return "..."
        elif isinstance(node, cst.Tuple):
            elements = [self._annotation_to_str(e.value) for e in node.elements]
            return f"tuple[{', '.join(elements)}]"

        # Fallback: try to get the raw code
        try:
            module = cst.parse_expression("")
            return cst.Module(body=[]).code_for_node(node).strip()
        except Exception:
            return str(node)


def generate_docstring_for_function(
    source: str,
    func_name: str,
    style: DocstringStyle | DocstringStyleType = "google",
    summary: str = "",
) -> str | None:
    """Generate a docstring for a function in source code.

    Parameters
    ----------
    source : str
        The source code containing the function.
    func_name : str
        Name of the function to generate docstring for.
    style : DocstringStyle | str
        The docstring style to generate.
    summary : str
        Custom summary line.

    Returns
    -------
    str | None
        The generated docstring, or None if function not found.
    """
    try:
        tree = cst.parse_module(source)
        generator = DocstringGenerator(style)

        for node in tree.body:
            if isinstance(node, cst.FunctionDef) and node.name.value == func_name:
                return generator.generate(node, summary=summary)

        return None
    except Exception:
        return None


def generate_docstring_for_method(
    source: str,
    class_name: str,
    method_name: str,
    style: DocstringStyle | DocstringStyleType = "google",
    summary: str = "",
) -> str | None:
    """Generate a docstring for a method in source code.

    Parameters
    ----------
    source : str
        The source code containing the class.
    class_name : str
        Name of the class containing the method.
    method_name : str
        Name of the method to generate docstring for.
    style : DocstringStyle | str
        The docstring style to generate.
    summary : str
        Custom summary line.

    Returns
    -------
    str | None
        The generated docstring, or None if method not found.
    """
    try:
        tree = cst.parse_module(source)
        generator = DocstringGenerator(style)

        class MethodFinder(cst.CSTVisitor):
            def __init__(self):
                self.result: str | None = None
                self.in_target_class = False

            def visit_ClassDef(self, node: cst.ClassDef) -> bool:
                if node.name.value == class_name:
                    self.in_target_class = True
                return True

            def leave_ClassDef(self, node: cst.ClassDef) -> None:
                if node.name.value == class_name:
                    self.in_target_class = False

            def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
                if self.in_target_class and node.name.value == method_name:
                    self.result = generator.generate(node, summary=summary)
                return False

        finder = MethodFinder()
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(finder)
        return finder.result
    except Exception:
        return None
