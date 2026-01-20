"""Test generation utilities for Python code.

This module provides utilities for generating test stubs, converting
between test frameworks, and managing pytest fixtures.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import libcst as cst

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


@dataclass
class TestCase:
    """Represents a single test case for parameterized testing.

    Attributes:
        input: Dictionary of parameter name to value mappings.
        expected: The expected return value or exception.
        description: Optional description for the test case.
    """

    input: dict[str, Any] = field(default_factory=dict)
    expected: Any = None
    description: str = ""


@dataclass
class FunctionSignature:
    """Extracted function signature information.

    Attributes:
        name: Function name.
        parameters: List of (name, type_hint, default) tuples.
        return_type: Return type annotation if present.
        is_async: Whether the function is async.
        decorators: List of decorator names.
        docstring: The function's docstring if present.
    """

    name: str
    parameters: list[tuple[str, str | None, str | None]] = field(default_factory=list)
    return_type: str | None = None
    is_async: bool = False
    decorators: list[str] = field(default_factory=list)
    docstring: str | None = None
    is_method: bool = False
    class_name: str | None = None


class SignatureExtractor(cst.CSTVisitor):
    """Extract function signature information from a CST node."""

    def __init__(self, function_name: str, class_name: str | None = None) -> None:
        self.function_name = function_name
        self.class_name = class_name
        self.signature: FunctionSignature | None = None
        self._current_class: str | None = None

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        self._current_class = node.name.value
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        self._current_class = None

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        if node.name.value != self.function_name:
            return True

        # Check class context
        if self.class_name is not None and self._current_class != self.class_name:
            return True
        if self.class_name is None and self._current_class is not None:
            return True

        sig = FunctionSignature(
            name=self.function_name,
            is_async=node.asynchronous is not None,
            is_method=self._current_class is not None,
            class_name=self._current_class,
        )

        # Extract decorators
        for dec in node.decorators:
            if isinstance(dec.decorator, cst.Name):
                sig.decorators.append(dec.decorator.value)
            elif isinstance(dec.decorator, cst.Call):
                if isinstance(dec.decorator.func, cst.Name):
                    sig.decorators.append(dec.decorator.func.value)

        # Extract parameters
        params = node.params
        for param in params.params:
            name = param.name.value
            if name in ("self", "cls"):
                continue

            type_hint = None
            if param.annotation:
                type_hint = cst.parse_module("").code_for_node(param.annotation.annotation)

            default = None
            if param.default:
                default = cst.parse_module("").code_for_node(param.default)

            sig.parameters.append((name, type_hint, default))

        # Keyword-only parameters
        for param in params.kwonly_params:
            name = param.name.value
            type_hint = None
            if param.annotation:
                type_hint = cst.parse_module("").code_for_node(param.annotation.annotation)
            default = None
            if param.default:
                default = cst.parse_module("").code_for_node(param.default)
            sig.parameters.append((name, type_hint, default))

        # Return type
        if node.returns:
            sig.return_type = cst.parse_module("").code_for_node(node.returns.annotation)

        # Extract docstring
        if isinstance(node.body, cst.IndentedBlock) and node.body.body:
            first_stmt = node.body.body[0]
            if isinstance(first_stmt, cst.SimpleStatementLine):
                if len(first_stmt.body) == 1 and isinstance(first_stmt.body[0], cst.Expr):
                    expr = first_stmt.body[0].value
                    if isinstance(expr, cst.SimpleString):
                        sig.docstring = expr.evaluated_value
                    elif isinstance(expr, cst.ConcatenatedString):
                        parts = []
                        for part in expr.left, expr.right:
                            if isinstance(part, cst.SimpleString):
                                parts.append(part.evaluated_value)
                        sig.docstring = "".join(str(p) for p in parts if p)

        self.signature = sig
        return False


class ClassSignatureExtractor(cst.CSTVisitor):
    """Extract all method signatures from a class."""

    def __init__(self, class_name: str) -> None:
        self.class_name = class_name
        self.methods: list[FunctionSignature] = []
        self._in_class = False
        self.class_docstring: str | None = None

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        if node.name.value == self.class_name:
            self._in_class = True
            # Extract class docstring
            if isinstance(node.body, cst.IndentedBlock) and node.body.body:
                first_stmt = node.body.body[0]
                if isinstance(first_stmt, cst.SimpleStatementLine):
                    if len(first_stmt.body) == 1 and isinstance(first_stmt.body[0], cst.Expr):
                        expr = first_stmt.body[0].value
                        if isinstance(expr, cst.SimpleString):
                            self.class_docstring = expr.evaluated_value
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        if node.name.value == self.class_name:
            self._in_class = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        if not self._in_class:
            return True

        sig = FunctionSignature(
            name=node.name.value,
            is_async=node.asynchronous is not None,
            is_method=True,
            class_name=self.class_name,
        )

        # Extract decorators
        for dec in node.decorators:
            if isinstance(dec.decorator, cst.Name):
                sig.decorators.append(dec.decorator.value)
            elif isinstance(dec.decorator, cst.Call):
                if isinstance(dec.decorator.func, cst.Name):
                    sig.decorators.append(dec.decorator.func.value)

        # Extract parameters
        params = node.params
        for param in params.params:
            name = param.name.value
            if name in ("self", "cls"):
                continue

            type_hint = None
            if param.annotation:
                type_hint = cst.parse_module("").code_for_node(param.annotation.annotation)

            default = None
            if param.default:
                default = cst.parse_module("").code_for_node(param.default)

            sig.parameters.append((name, type_hint, default))

        # Keyword-only parameters
        for param in params.kwonly_params:
            name = param.name.value
            type_hint = None
            if param.annotation:
                type_hint = cst.parse_module("").code_for_node(param.annotation.annotation)
            default = None
            if param.default:
                default = cst.parse_module("").code_for_node(param.default)
            sig.parameters.append((name, type_hint, default))

        # Return type
        if node.returns:
            sig.return_type = cst.parse_module("").code_for_node(node.returns.annotation)

        self.methods.append(sig)
        return False


class DoctestExtractor(cst.CSTVisitor):
    """Extract doctest examples from docstrings."""

    def __init__(self, function_name: str | None = None, class_name: str | None = None) -> None:
        self.function_name = function_name
        self.class_name = class_name
        self.examples: list[tuple[str, str, str | None]] = []  # (code, expected, function_name)
        self._current_class: str | None = None
        self._current_function: str | None = None

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        self._current_class = node.name.value
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        self._current_class = None

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        self._current_function = node.name.value

        # Check filters
        if self.function_name and node.name.value != self.function_name:
            return True
        if self.class_name and self._current_class != self.class_name:
            return True

        # Extract docstring
        docstring = None
        if isinstance(node.body, cst.IndentedBlock) and node.body.body:
            first_stmt = node.body.body[0]
            if isinstance(first_stmt, cst.SimpleStatementLine):
                if len(first_stmt.body) == 1 and isinstance(first_stmt.body[0], cst.Expr):
                    expr = first_stmt.body[0].value
                    if isinstance(expr, cst.SimpleString):
                        docstring = expr.evaluated_value

        if docstring:
            self._extract_doctests(docstring, node.name.value)

        return True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:
        self._current_function = None

    def _extract_doctests(self, docstring: str, function_name: str) -> None:
        """Extract doctests from a docstring."""
        # Match >>> lines and their expected output
        lines = docstring.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith(">>>"):
                code_lines = [line[4:]]  # Remove >>> prefix
                i += 1
                # Collect continuation lines
                while i < len(lines) and lines[i].strip().startswith("..."):
                    code_lines.append(lines[i].strip()[4:])  # Remove ... prefix
                    i += 1
                # Collect expected output
                expected_lines = []
                while i < len(lines):
                    next_line = lines[i].strip()
                    if next_line.startswith(">>>") or not next_line or next_line.startswith("..."):
                        break
                    expected_lines.append(next_line)
                    i += 1

                code = "\n".join(code_lines)
                expected = "\n".join(expected_lines) if expected_lines else None
                self.examples.append((code, expected or "", function_name))
            else:
                i += 1


class TestGenerator:
    """Generate test stubs and test files from source code.

    Provides methods for generating pytest test files from classes and
    functions, converting doctests to pytest, and generating parameterized
    tests.

    Parameters
    ----------
    indent : str
        The indentation string to use. Default is 4 spaces.

    Examples
    --------
    >>> gen = TestGenerator()
    >>> stub = gen.generate_function_test_stub(signature)
    >>> test_file = gen.generate_class_test_file(class_name, signatures)
    """

    def __init__(self, indent: str = "    ") -> None:
        self.indent = indent

    def generate_function_test_stub(
        self,
        signature: FunctionSignature,
        include_setup: bool = False,
    ) -> str:
        """Generate a test stub for a function.

        Parameters
        ----------
        signature : FunctionSignature
            The function signature to generate a test for.
        include_setup : bool
            Whether to include setup/teardown comments.

        Returns
        -------
        str
            The generated test function code.
        """
        func_name = signature.name
        test_name = f"test_{func_name}"

        # Handle async functions
        async_prefix = "async " if signature.is_async else ""

        # Generate parameter examples
        param_examples = self._generate_param_examples(signature.parameters)

        # Build test body
        body_lines = []
        if include_setup:
            body_lines.append(f"{self.indent}# Setup")
            body_lines.append(f"{self.indent}# ...")
            body_lines.append("")

        # Add parameter setup comments
        if param_examples:
            body_lines.append(f"{self.indent}# Arrange")
            for name, example in param_examples.items():
                body_lines.append(f"{self.indent}{name} = {example}")
            body_lines.append("")

        # Call the function
        body_lines.append(f"{self.indent}# Act")
        param_names = ", ".join(param_examples.keys()) if param_examples else ""

        if signature.is_method and signature.class_name:
            instance_var = self._to_snake_case(signature.class_name)
            body_lines.append(f"{self.indent}{instance_var} = {signature.class_name}()  # TODO: provide args")
            if signature.is_async:
                body_lines.append(f"{self.indent}result = await {instance_var}.{func_name}({param_names})")
            else:
                body_lines.append(f"{self.indent}result = {instance_var}.{func_name}({param_names})")
        else:
            if signature.is_async:
                body_lines.append(f"{self.indent}result = await {func_name}({param_names})")
            else:
                body_lines.append(f"{self.indent}result = {func_name}({param_names})")
        body_lines.append("")

        # Assert placeholder
        body_lines.append(f"{self.indent}# Assert")
        if signature.return_type:
            body_lines.append(f"{self.indent}assert result is not None  # TODO: add specific assertions")
        else:
            body_lines.append(f"{self.indent}assert True  # TODO: add assertions")

        body = "\n".join(body_lines)
        return f"{async_prefix}def {test_name}():\n{body}"

    def generate_class_test_file(
        self,
        class_name: str,
        methods: list[FunctionSignature],
        class_docstring: str | None = None,
        module_path: str | None = None,
        include_setup: bool = True,
        include_teardown: bool = False,
    ) -> str:
        """Generate a complete test file for a class.

        Parameters
        ----------
        class_name : str
            Name of the class being tested.
        methods : list[FunctionSignature]
            List of method signatures to generate tests for.
        class_docstring : str | None
            Optional class docstring for context.
        module_path : str | None
            Optional module path for imports.
        include_setup : bool
            Whether to include a setup method.
        include_teardown : bool
            Whether to include a teardown method.

        Returns
        -------
        str
            Complete test file content.
        """
        lines = ['"""Tests for {class_name}."""'.format(class_name=class_name)]
        lines.append("from __future__ import annotations")
        lines.append("")

        # Add pytest import
        lines.append("import pytest")
        lines.append("")

        # Add import for the class if module path provided
        if module_path:
            lines.append(f"from {module_path} import {class_name}")
            lines.append("")

        # Generate test class
        test_class_name = f"Test{class_name}"
        lines.append("")
        lines.append(f"class {test_class_name}:")
        if class_docstring:
            lines.append(f'{self.indent}"""Tests for {class_name}: {class_docstring}"""')
        else:
            lines.append(f'{self.indent}"""Tests for {class_name}."""')
        lines.append("")

        # Setup method
        if include_setup:
            lines.append(f"{self.indent}def setup_method(self):")
            lines.append(f"{self.indent}{self.indent}\"\"\"Set up test fixtures.\"\"\"")
            lines.append(f"{self.indent}{self.indent}# TODO: Initialize test fixtures")
            lines.append(f"{self.indent}{self.indent}pass")
            lines.append("")

        # Teardown method
        if include_teardown:
            lines.append(f"{self.indent}def teardown_method(self):")
            lines.append(f"{self.indent}{self.indent}\"\"\"Tear down test fixtures.\"\"\"")
            lines.append(f"{self.indent}{self.indent}# TODO: Clean up test fixtures")
            lines.append(f"{self.indent}{self.indent}pass")
            lines.append("")

        # Generate test methods for each public method
        for method in methods:
            if method.name.startswith("_") and method.name != "__init__":
                continue  # Skip private methods

            test_stub = self._generate_method_test(method, class_name)
            # Indent each line of the test stub
            indented_stub = "\n".join(
                f"{self.indent}{line}" if line else ""
                for line in test_stub.split("\n")
            )
            lines.append(indented_stub)
            lines.append("")

        return "\n".join(lines)

    def _generate_method_test(self, method: FunctionSignature, class_name: str) -> str:
        """Generate a test method for a class method."""
        # Handle special method names
        if method.name == "__init__":
            test_name = f"test_{self._to_snake_case(class_name)}_init"
        else:
            test_name = f"test_{method.name}"

        async_prefix = "async " if method.is_async else ""

        param_examples = self._generate_param_examples(method.parameters)

        body_lines = []

        # Arrange
        body_lines.append(f"{self.indent}# Arrange")
        for name, example in param_examples.items():
            body_lines.append(f"{self.indent}{name} = {example}")

        # Create instance
        instance_var = self._to_snake_case(class_name)
        body_lines.append(f"{self.indent}{instance_var} = {class_name}()  # TODO: provide args")
        body_lines.append("")

        # Act
        body_lines.append(f"{self.indent}# Act")
        param_names = ", ".join(param_examples.keys())

        if method.name == "__init__":
            body_lines.append(f"{self.indent}# Instance already created in Arrange")
        elif method.is_async:
            body_lines.append(f"{self.indent}result = await {instance_var}.{method.name}({param_names})")
        else:
            body_lines.append(f"{self.indent}result = {instance_var}.{method.name}({param_names})")
        body_lines.append("")

        # Assert
        body_lines.append(f"{self.indent}# Assert")
        if method.name == "__init__":
            body_lines.append(f"{self.indent}assert {instance_var} is not None")
        elif method.return_type and method.return_type not in ("None", "None"):
            body_lines.append(f"{self.indent}assert result is not None  # TODO: add specific assertions")
        else:
            body_lines.append(f"{self.indent}assert True  # TODO: add assertions")

        body = "\n".join(body_lines)
        return f"{async_prefix}def {test_name}(self):\n{body}"

    def generate_parameterized_test(
        self,
        signature: FunctionSignature,
        test_cases: list[TestCase],
    ) -> str:
        """Generate a parameterized pytest test.

        Parameters
        ----------
        signature : FunctionSignature
            The function signature to test.
        test_cases : list[TestCase]
            List of test cases with inputs and expected outputs.

        Returns
        -------
        str
            The generated parameterized test code.
        """
        func_name = signature.name
        test_name = f"test_{func_name}"

        # Build pytest.mark.parametrize arguments
        param_names = list(test_cases[0].input.keys()) if test_cases else []
        param_names.append("expected")

        # Build parameter string
        params_str = ", ".join(f'"{p}"' for p in param_names)

        # Build test cases
        case_lines = []
        for tc in test_cases:
            values = [repr(tc.input.get(p)) for p in param_names[:-1]]
            values.append(repr(tc.expected))
            case_str = f"({', '.join(values)})"
            if tc.description:
                case_str = f"pytest.param{case_str}, id={repr(tc.description)}"
            case_lines.append(case_str)

        cases_str = ",\n        ".join(case_lines)

        # Generate function signature
        async_prefix = "async " if signature.is_async else ""
        func_params = ", ".join(param_names)

        # Build test body
        body_lines = []
        body_lines.append(f"{self.indent}# Act")

        if signature.is_method and signature.class_name:
            instance_var = self._to_snake_case(signature.class_name)
            input_params = ", ".join(param_names[:-1])
            body_lines.append(f"{self.indent}{instance_var} = {signature.class_name}()  # TODO: provide args")
            if signature.is_async:
                body_lines.append(f"{self.indent}result = await {instance_var}.{func_name}({input_params})")
            else:
                body_lines.append(f"{self.indent}result = {instance_var}.{func_name}({input_params})")
        else:
            input_params = ", ".join(param_names[:-1])
            if signature.is_async:
                body_lines.append(f"{self.indent}result = await {func_name}({input_params})")
            else:
                body_lines.append(f"{self.indent}result = {func_name}({input_params})")

        body_lines.append("")
        body_lines.append(f"{self.indent}# Assert")
        body_lines.append(f"{self.indent}assert result == expected")

        body = "\n".join(body_lines)

        return f"""@pytest.mark.parametrize(
    [{params_str}],
    [
        {cases_str},
    ],
)
{async_prefix}def {test_name}({func_params}):
{body}"""

    def doctest_to_pytest(
        self,
        examples: list[tuple[str, str, str | None]],
        function_name: str | None = None,
    ) -> str:
        """Convert doctest examples to pytest tests.

        Parameters
        ----------
        examples : list[tuple[str, str, str | None]]
            List of (code, expected, function_name) tuples from DoctestExtractor.
        function_name : str | None
            Function name for naming the test.

        Returns
        -------
        str
            Generated pytest test code.
        """
        if not examples:
            return ""

        tests = []
        for i, (code, expected, func_name) in enumerate(examples):
            test_func_name = func_name or function_name or "unknown"
            test_name = f"test_{test_func_name}_doctest_{i + 1}"

            body_lines = []
            body_lines.append(f'{self.indent}"""Test from doctest example."""')

            # Check if the code is an expression or statement
            code = code.strip()
            if expected:
                expected = expected.strip()
                # Handle assertion from expected output
                body_lines.append(f"{self.indent}result = {code}")
                if expected.startswith("<") and expected.endswith(">"):
                    # Skip repr output like <MyClass at 0x...>
                    body_lines.append(f"{self.indent}assert result is not None")
                elif expected in ("True", "False", "None"):
                    body_lines.append(f"{self.indent}assert result is {expected}")
                else:
                    body_lines.append(f"{self.indent}assert result == {expected}")
            else:
                # Just execute the code
                body_lines.append(f"{self.indent}{code}")

            body = "\n".join(body_lines)
            tests.append(f"def {test_name}():\n{body}")

        return "\n\n\n".join(tests)

    def _generate_param_examples(
        self,
        parameters: list[tuple[str, str | None, str | None]],
    ) -> dict[str, str]:
        """Generate example values for parameters based on type hints."""
        examples = {}
        for name, type_hint, default in parameters:
            if default:
                examples[name] = default
            elif type_hint:
                examples[name] = self._type_to_example(type_hint)
            else:
                examples[name] = "None  # TODO: provide value"
        return examples

    def _type_to_example(self, type_hint: str) -> str:
        """Convert a type hint to an example value."""
        # Handle Optional
        if type_hint.startswith("Optional["):
            inner = type_hint[9:-1]
            return self._type_to_example(inner)
        if type_hint.endswith(" | None"):
            inner = type_hint[:-7]
            return self._type_to_example(inner)
        if type_hint.startswith("None | "):
            inner = type_hint[7:]
            return self._type_to_example(inner)

        # Handle common types
        type_lower = type_hint.lower()
        if "str" in type_lower:
            return '"test_string"'
        elif "int" in type_lower:
            return "1"
        elif "float" in type_lower:
            return "1.0"
        elif "bool" in type_lower:
            return "True"
        elif type_hint.startswith("list[") or type_hint.startswith("List["):
            return "[]"
        elif type_hint.startswith("dict[") or type_hint.startswith("Dict["):
            return "{}"
        elif type_hint.startswith("set[") or type_hint.startswith("Set["):
            return "set()"
        elif type_hint.startswith("tuple[") or type_hint.startswith("Tuple["):
            return "()"
        elif "Path" in type_hint:
            return 'Path("test")'
        elif "bytes" in type_lower:
            return 'b"test"'
        elif type_hint == "Any":
            return "None"
        else:
            # Assume it's a class type
            return f"{type_hint}()  # TODO: provide args"

    def _to_snake_case(self, name: str) -> str:
        """Convert CamelCase to snake_case."""
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


class UnittestToPytestConverter(cst.CSTTransformer):
    """Convert unittest test cases to pytest style.

    Transforms:
    - self.assertEqual(a, b) -> assert a == b
    - self.assertTrue(x) -> assert x
    - self.assertFalse(x) -> assert not x
    - self.assertIsNone(x) -> assert x is None
    - self.assertIsNotNone(x) -> assert x is not None
    - self.assertIn(a, b) -> assert a in b
    - self.assertRaises(X) -> pytest.raises(X)
    - etc.
    """

    def __init__(self) -> None:
        super().__init__()
        self.converted = False
        self._needs_pytest_import = False

    def leave_Call(
        self,
        original_node: cst.Call,
        updated_node: cst.Call,
    ) -> cst.BaseExpression:
        # Check if it's a self.assertX call
        if not isinstance(updated_node.func, cst.Attribute):
            return updated_node
        if not isinstance(updated_node.func.value, cst.Name):
            return updated_node
        if updated_node.func.value.value != "self":
            return updated_node

        method_name = updated_node.func.attr.value
        args = [arg.value for arg in updated_node.args if isinstance(arg, cst.Arg)]

        # Handle various assertion methods
        if method_name == "assertEqual" and len(args) >= 2:
            self.converted = True
            return cst.Comparison(
                left=args[0],
                comparisons=[
                    cst.ComparisonTarget(
                        operator=cst.Equal(),
                        comparator=args[1],
                    )
                ],
            )

        if method_name == "assertNotEqual" and len(args) >= 2:
            self.converted = True
            return cst.Comparison(
                left=args[0],
                comparisons=[
                    cst.ComparisonTarget(
                        operator=cst.NotEqual(),
                        comparator=args[1],
                    )
                ],
            )

        if method_name == "assertTrue" and len(args) >= 1:
            self.converted = True
            return args[0]

        if method_name == "assertFalse" and len(args) >= 1:
            self.converted = True
            return cst.UnaryOperation(operator=cst.Not(), expression=args[0])

        if method_name == "assertIsNone" and len(args) >= 1:
            self.converted = True
            return cst.Comparison(
                left=args[0],
                comparisons=[
                    cst.ComparisonTarget(
                        operator=cst.Is(),
                        comparator=cst.Name("None"),
                    )
                ],
            )

        if method_name == "assertIsNotNone" and len(args) >= 1:
            self.converted = True
            return cst.Comparison(
                left=args[0],
                comparisons=[
                    cst.ComparisonTarget(
                        operator=cst.IsNot(),
                        comparator=cst.Name("None"),
                    )
                ],
            )

        if method_name == "assertIn" and len(args) >= 2:
            self.converted = True
            return cst.Comparison(
                left=args[0],
                comparisons=[
                    cst.ComparisonTarget(
                        operator=cst.In(),
                        comparator=args[1],
                    )
                ],
            )

        if method_name == "assertNotIn" and len(args) >= 2:
            self.converted = True
            return cst.Comparison(
                left=args[0],
                comparisons=[
                    cst.ComparisonTarget(
                        operator=cst.NotIn(),
                        comparator=args[1],
                    )
                ],
            )

        if method_name == "assertIs" and len(args) >= 2:
            self.converted = True
            return cst.Comparison(
                left=args[0],
                comparisons=[
                    cst.ComparisonTarget(
                        operator=cst.Is(),
                        comparator=args[1],
                    )
                ],
            )

        if method_name == "assertIsNot" and len(args) >= 2:
            self.converted = True
            return cst.Comparison(
                left=args[0],
                comparisons=[
                    cst.ComparisonTarget(
                        operator=cst.IsNot(),
                        comparator=args[1],
                    )
                ],
            )

        if method_name == "assertGreater" and len(args) >= 2:
            self.converted = True
            return cst.Comparison(
                left=args[0],
                comparisons=[
                    cst.ComparisonTarget(
                        operator=cst.GreaterThan(),
                        comparator=args[1],
                    )
                ],
            )

        if method_name == "assertLess" and len(args) >= 2:
            self.converted = True
            return cst.Comparison(
                left=args[0],
                comparisons=[
                    cst.ComparisonTarget(
                        operator=cst.LessThan(),
                        comparator=args[1],
                    )
                ],
            )

        if method_name == "assertGreaterEqual" and len(args) >= 2:
            self.converted = True
            return cst.Comparison(
                left=args[0],
                comparisons=[
                    cst.ComparisonTarget(
                        operator=cst.GreaterThanEqual(),
                        comparator=args[1],
                    )
                ],
            )

        if method_name == "assertLessEqual" and len(args) >= 2:
            self.converted = True
            return cst.Comparison(
                left=args[0],
                comparisons=[
                    cst.ComparisonTarget(
                        operator=cst.LessThanEqual(),
                        comparator=args[1],
                    )
                ],
            )

        if method_name == "assertRaises" and len(args) >= 1:
            self.converted = True
            self._needs_pytest_import = True
            return cst.Call(
                func=cst.Attribute(
                    value=cst.Name("pytest"),
                    attr=cst.Name("raises"),
                ),
                args=[cst.Arg(value=args[0])],
            )

        return updated_node

    def leave_Expr(
        self,
        original_node: cst.Expr,
        updated_node: cst.Expr,
    ) -> cst.BaseSmallStatement:
        # Wrap converted comparisons in assert
        if isinstance(updated_node.value, (cst.Comparison, cst.UnaryOperation)):
            if self.converted:
                return cst.Assert(test=updated_node.value)
        return updated_node


class AddPytestFixtureTransformer(cst.CSTTransformer):
    """Add a pytest fixture to a conftest.py file."""

    def __init__(
        self,
        fixture_name: str,
        body: str,
        scope: str = "function",
        autouse: bool = False,
        params: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.fixture_name = fixture_name
        self.body = body
        self.scope = scope
        self.autouse = autouse
        self.params = params
        self.added = False

    def leave_Module(
        self,
        original_node: cst.Module,
        updated_node: cst.Module,
    ) -> cst.Module:
        # Check if fixture already exists
        for stmt in updated_node.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == self.fixture_name:
                return updated_node

        # Build decorator arguments
        decorator_args = [cst.Arg(
            keyword=cst.Name("scope"),
            value=cst.SimpleString(f'"{self.scope}"'),
        )]
        if self.autouse:
            decorator_args.append(cst.Arg(
                keyword=cst.Name("autouse"),
                value=cst.Name("True"),
            ))
        if self.params:
            params_list = cst.List([cst.Element(cst.SimpleString(f'"{p}"')) for p in self.params])
            decorator_args.append(cst.Arg(
                keyword=cst.Name("params"),
                value=params_list,
            ))

        # Build fixture function
        fixture_code = f"""@pytest.fixture(scope="{self.scope}")
def {self.fixture_name}():
    {self.body}
"""
        fixture_node = cst.parse_statement(fixture_code)

        # Add at end of module
        new_body = list(updated_node.body) + [fixture_node]
        self.added = True

        return updated_node.with_changes(body=new_body)


def extract_function_signature(
    content: str,
    function_name: str,
    class_name: str | None = None,
) -> FunctionSignature | None:
    """Extract a function signature from source code.

    Parameters
    ----------
    content : str
        Source code to analyze.
    function_name : str
        Name of the function to extract.
    class_name : str | None
        If provided, look for the function as a method of this class.

    Returns
    -------
    FunctionSignature | None
        The extracted signature, or None if not found.
    """
    try:
        tree = cst.parse_module(content)
        extractor = SignatureExtractor(function_name, class_name)
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(extractor)
        return extractor.signature
    except Exception:
        return None


def extract_class_signatures(
    content: str,
    class_name: str,
) -> tuple[list[FunctionSignature], str | None]:
    """Extract all method signatures from a class.

    Parameters
    ----------
    content : str
        Source code to analyze.
    class_name : str
        Name of the class to analyze.

    Returns
    -------
    tuple[list[FunctionSignature], str | None]
        A tuple of (list of method signatures, class docstring).
    """
    try:
        tree = cst.parse_module(content)
        extractor = ClassSignatureExtractor(class_name)
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(extractor)
        return extractor.methods, extractor.class_docstring
    except Exception:
        return [], None


def extract_doctests(
    content: str,
    function_name: str | None = None,
    class_name: str | None = None,
) -> list[tuple[str, str, str | None]]:
    """Extract doctest examples from source code.

    Parameters
    ----------
    content : str
        Source code to analyze.
    function_name : str | None
        If provided, only extract from this function.
    class_name : str | None
        If provided, only extract from methods of this class.

    Returns
    -------
    list[tuple[str, str, str | None]]
        List of (code, expected_output, function_name) tuples.
    """
    try:
        tree = cst.parse_module(content)
        extractor = DoctestExtractor(function_name, class_name)
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(extractor)
        return extractor.examples
    except Exception:
        return []
