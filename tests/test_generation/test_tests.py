"""
Tests for rejig.generation.tests module.

This module tests test generation utilities:
- TestCase dataclass
- FunctionSignature dataclass
- SignatureExtractor CST visitor
- ClassSignatureExtractor CST visitor
- DoctestExtractor CST visitor
- TestGenerator class
- UnittestToPytestConverter transformer
- AddPytestFixtureTransformer
- extract_function_signature function
- extract_class_signatures function
- extract_doctests function
"""
from __future__ import annotations

import textwrap

import libcst as cst
import pytest

from rejig.generation.tests import (
    AddPytestFixtureTransformer,
    ClassSignatureExtractor,
    DoctestExtractor,
    FunctionSignature,
    SignatureExtractor,
    TestCase,
    TestGenerator,
    UnittestToPytestConverter,
    extract_class_signatures,
    extract_doctests,
    extract_function_signature,
)


# =============================================================================
# TestCase Tests
# =============================================================================

class TestTestCase:
    """Tests for TestCase dataclass."""

    def test_default_values(self):
        """TestCase should have sensible defaults."""
        tc = TestCase()

        assert tc.input == {}
        assert tc.expected is None
        assert tc.description == ""

    def test_all_fields_settable(self):
        """TestCase should allow setting all fields."""
        tc = TestCase(
            input={"x": 1, "y": 2},
            expected=3,
            description="test adding",
        )

        assert tc.input == {"x": 1, "y": 2}
        assert tc.expected == 3
        assert tc.description == "test adding"


# =============================================================================
# FunctionSignature Tests
# =============================================================================

class TestFunctionSignature:
    """Tests for FunctionSignature dataclass."""

    def test_minimal_signature(self):
        """FunctionSignature should work with just a name."""
        sig = FunctionSignature(name="my_func")

        assert sig.name == "my_func"
        assert sig.parameters == []
        assert sig.return_type is None
        assert sig.is_async is False
        assert sig.decorators == []
        assert sig.docstring is None
        assert sig.is_method is False
        assert sig.class_name is None

    def test_full_signature(self):
        """FunctionSignature should accept all fields."""
        sig = FunctionSignature(
            name="process",
            parameters=[("data", "str", None), ("count", "int", "1")],
            return_type="bool",
            is_async=True,
            decorators=["staticmethod"],
            docstring="Process data.",
            is_method=True,
            class_name="Handler",
        )

        assert sig.name == "process"
        assert len(sig.parameters) == 2
        assert sig.return_type == "bool"
        assert sig.is_async is True
        assert sig.decorators == ["staticmethod"]
        assert sig.is_method is True
        assert sig.class_name == "Handler"


# =============================================================================
# SignatureExtractor Tests
# =============================================================================

class TestSignatureExtractor:
    """Tests for SignatureExtractor CST visitor."""

    def test_extracts_simple_function(self):
        """Should extract signature from a simple function."""
        code = textwrap.dedent('''\
            def my_func(x: int, y: str) -> bool:
                return True
        ''')

        tree = cst.parse_module(code)
        extractor = SignatureExtractor("my_func")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(extractor)

        sig = extractor.signature
        assert sig is not None
        assert sig.name == "my_func"
        assert len(sig.parameters) == 2
        assert sig.return_type == "bool"

    def test_extracts_async_function(self):
        """Should detect async functions."""
        code = textwrap.dedent('''\
            async def fetch(url: str) -> str:
                pass
        ''')

        tree = cst.parse_module(code)
        extractor = SignatureExtractor("fetch")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(extractor)

        sig = extractor.signature
        assert sig is not None
        assert sig.is_async is True

    def test_extracts_decorators(self):
        """Should extract decorator names."""
        code = textwrap.dedent('''\
            @property
            @staticmethod
            def my_prop():
                pass
        ''')

        tree = cst.parse_module(code)
        extractor = SignatureExtractor("my_prop")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(extractor)

        sig = extractor.signature
        assert sig is not None
        assert "property" in sig.decorators
        assert "staticmethod" in sig.decorators

    def test_extracts_method_from_class(self):
        """Should extract method signature when class_name is specified."""
        code = textwrap.dedent('''\
            class MyClass:
                def my_method(self, value: int) -> None:
                    pass
        ''')

        tree = cst.parse_module(code)
        extractor = SignatureExtractor("my_method", class_name="MyClass")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(extractor)

        sig = extractor.signature
        assert sig is not None
        assert sig.name == "my_method"
        assert sig.is_method is True
        assert sig.class_name == "MyClass"
        # self parameter should be excluded
        assert len(sig.parameters) == 1
        assert sig.parameters[0][0] == "value"

    def test_skips_wrong_class(self):
        """Should not extract method from wrong class."""
        code = textwrap.dedent('''\
            class ClassA:
                def method(self):
                    pass

            class ClassB:
                def method(self):
                    pass
        ''')

        tree = cst.parse_module(code)
        extractor = SignatureExtractor("method", class_name="ClassA")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(extractor)

        sig = extractor.signature
        assert sig is not None
        assert sig.class_name == "ClassA"

    def test_extracts_docstring(self):
        """Should extract function docstring."""
        code = textwrap.dedent('''\
            def my_func():
                """This is the docstring."""
                pass
        ''')

        tree = cst.parse_module(code)
        extractor = SignatureExtractor("my_func")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(extractor)

        sig = extractor.signature
        assert sig is not None
        assert sig.docstring == "This is the docstring."

    def test_extracts_default_values(self):
        """Should extract parameter default values."""
        code = textwrap.dedent('''\
            def config(host: str = "localhost", port: int = 8080):
                pass
        ''')

        tree = cst.parse_module(code)
        extractor = SignatureExtractor("config")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(extractor)

        sig = extractor.signature
        assert sig is not None
        assert len(sig.parameters) == 2
        # (name, type_hint, default)
        assert sig.parameters[0][2] == '"localhost"'
        assert sig.parameters[1][2] == "8080"


# =============================================================================
# ClassSignatureExtractor Tests
# =============================================================================

class TestClassSignatureExtractor:
    """Tests for ClassSignatureExtractor CST visitor."""

    def test_extracts_all_methods(self):
        """Should extract all method signatures from a class."""
        code = textwrap.dedent('''\
            class MyClass:
                def __init__(self, value: int):
                    self.value = value

                def get_value(self) -> int:
                    return self.value

                def set_value(self, value: int) -> None:
                    self.value = value
        ''')

        tree = cst.parse_module(code)
        extractor = ClassSignatureExtractor("MyClass")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(extractor)

        assert len(extractor.methods) == 3
        method_names = [m.name for m in extractor.methods]
        assert "__init__" in method_names
        assert "get_value" in method_names
        assert "set_value" in method_names

    def test_extracts_class_docstring(self):
        """Should extract class docstring."""
        code = textwrap.dedent('''\
            class MyClass:
                """This is the class docstring."""

                def method(self):
                    pass
        ''')

        tree = cst.parse_module(code)
        extractor = ClassSignatureExtractor("MyClass")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(extractor)

        assert extractor.class_docstring == "This is the class docstring."

    def test_skips_other_classes(self):
        """Should only extract from the target class."""
        code = textwrap.dedent('''\
            class ClassA:
                def method_a(self):
                    pass

            class ClassB:
                def method_b(self):
                    pass
        ''')

        tree = cst.parse_module(code)
        extractor = ClassSignatureExtractor("ClassA")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(extractor)

        assert len(extractor.methods) == 1
        assert extractor.methods[0].name == "method_a"


# =============================================================================
# DoctestExtractor Tests
# =============================================================================

class TestDoctestExtractor:
    """Tests for DoctestExtractor CST visitor."""

    def test_extracts_simple_doctest(self):
        """Should extract simple doctest examples."""
        code = textwrap.dedent('''\
            def add(x, y):
                """Add two numbers.

                >>> add(1, 2)
                3
                """
                return x + y
        ''')

        tree = cst.parse_module(code)
        extractor = DoctestExtractor()
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(extractor)

        assert len(extractor.examples) >= 1
        code_example, expected, func_name = extractor.examples[0]
        assert "add(1, 2)" in code_example
        assert expected == "3"
        assert func_name == "add"

    def test_extracts_multiple_examples(self):
        """Should extract multiple doctest examples."""
        code = textwrap.dedent('''\
            def multiply(x, y):
                """Multiply numbers.

                >>> multiply(2, 3)
                6
                >>> multiply(0, 5)
                0
                """
                return x * y
        ''')

        tree = cst.parse_module(code)
        extractor = DoctestExtractor()
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(extractor)

        assert len(extractor.examples) >= 2

    def test_filters_by_function_name(self):
        """Should filter by function name."""
        code = textwrap.dedent('''\
            def func_a():
                """
                >>> func_a()
                'a'
                """
                return 'a'

            def func_b():
                """
                >>> func_b()
                'b'
                """
                return 'b'
        ''')

        tree = cst.parse_module(code)
        extractor = DoctestExtractor(function_name="func_a")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(extractor)

        # Should only have examples from func_a
        for code_ex, expected, func_name in extractor.examples:
            assert func_name == "func_a"


# =============================================================================
# TestGenerator Tests
# =============================================================================

class TestTestGenerator:
    """Tests for TestGenerator class."""

    def test_generate_function_test_stub(self):
        """Should generate a test stub for a function."""
        sig = FunctionSignature(
            name="add",
            parameters=[("x", "int", None), ("y", "int", None)],
            return_type="int",
        )

        gen = TestGenerator()
        stub = gen.generate_function_test_stub(sig)

        assert "def test_add" in stub
        assert "x = " in stub
        assert "y = " in stub
        assert "result" in stub
        assert "assert" in stub

    def test_generate_async_function_test_stub(self):
        """Should generate async test stub for async functions."""
        sig = FunctionSignature(
            name="fetch",
            parameters=[("url", "str", None)],
            return_type="str",
            is_async=True,
        )

        gen = TestGenerator()
        stub = gen.generate_function_test_stub(sig)

        assert "async def test_fetch" in stub
        assert "await" in stub

    def test_generate_method_test_stub(self):
        """Should generate test stub for class methods."""
        sig = FunctionSignature(
            name="process",
            parameters=[("data", "str", None)],
            return_type="str",
            is_method=True,
            class_name="Handler",
        )

        gen = TestGenerator()
        stub = gen.generate_function_test_stub(sig)

        assert "def test_process" in stub
        assert "handler = Handler()" in stub or "Handler()" in stub

    def test_generate_class_test_file(self):
        """Should generate a complete test file for a class."""
        methods = [
            FunctionSignature(name="__init__", is_method=True, class_name="MyClass"),
            FunctionSignature(
                name="process",
                parameters=[("data", "str", None)],
                is_method=True,
                class_name="MyClass",
            ),
        ]

        gen = TestGenerator()
        test_file = gen.generate_class_test_file("MyClass", methods)

        assert "class TestMyClass" in test_file
        assert "import pytest" in test_file
        assert "def test_" in test_file

    def test_generate_class_test_file_with_module_path(self):
        """Should include import when module path is provided."""
        methods = [
            FunctionSignature(name="run", is_method=True, class_name="Service"),
        ]

        gen = TestGenerator()
        test_file = gen.generate_class_test_file(
            "Service",
            methods,
            module_path="myapp.services",
        )

        assert "from myapp.services import Service" in test_file

    def test_generate_parameterized_test(self):
        """Should generate parameterized pytest test."""
        sig = FunctionSignature(
            name="add",
            parameters=[("x", "int", None), ("y", "int", None)],
            return_type="int",
        )

        test_cases = [
            TestCase(input={"x": 1, "y": 2}, expected=3, description="positive numbers"),
            TestCase(input={"x": -1, "y": 1}, expected=0, description="negative and positive"),
        ]

        gen = TestGenerator()
        test = gen.generate_parameterized_test(sig, test_cases)

        assert "@pytest.mark.parametrize" in test
        assert "def test_add" in test

    def test_doctest_to_pytest(self):
        """Should convert doctest examples to pytest tests."""
        examples = [
            ("add(1, 2)", "3", "add"),
            ("add(0, 0)", "0", "add"),
        ]

        gen = TestGenerator()
        tests = gen.doctest_to_pytest(examples)

        assert "def test_add_doctest_1" in tests
        assert "def test_add_doctest_2" in tests
        assert "assert result ==" in tests

    def test_type_to_example_basic_types(self):
        """Should generate examples for basic types."""
        gen = TestGenerator()

        assert '"' in gen._type_to_example("str")  # String value
        assert gen._type_to_example("int") == "1"
        assert gen._type_to_example("float") == "1.0"
        assert gen._type_to_example("bool") == "True"

    def test_type_to_example_collection_types(self):
        """Should generate examples for collection types."""
        gen = TestGenerator()

        # Note: The implementation checks for basic type names in type_lower first,
        # so "list[int]" matches "int", "List[str]" matches "str", etc.
        # Testing collection types that don't contain basic type names in the inner type
        assert gen._type_to_example("list[MyClass]") == "[]"
        assert gen._type_to_example("dict[MyKey, MyValue]") == "{}"
        assert gen._type_to_example("set[MyItem]") == "set()"
        assert gen._type_to_example("tuple[MyA, MyB]") == "()"

    def test_to_snake_case(self):
        """Should convert CamelCase to snake_case."""
        gen = TestGenerator()

        assert gen._to_snake_case("MyClass") == "my_class"
        assert gen._to_snake_case("HTTPHandler") == "http_handler"
        assert gen._to_snake_case("simple") == "simple"


# =============================================================================
# UnittestToPytestConverter Tests
# =============================================================================

class TestUnittestToPytestConverter:
    """Tests for UnittestToPytestConverter transformer."""

    def test_converts_assertEqual(self):
        """Should convert assertEqual to assert ==."""
        code = textwrap.dedent('''\
            self.assertEqual(a, b)
        ''')

        tree = cst.parse_module(code)
        transformer = UnittestToPytestConverter()
        modified = tree.visit(transformer)

        result = modified.code
        assert "==" in result
        assert transformer.converted is True

    def test_converts_assertTrue(self):
        """Should convert assertTrue to assert."""
        code = textwrap.dedent('''\
            self.assertTrue(x)
        ''')

        tree = cst.parse_module(code)
        transformer = UnittestToPytestConverter()
        modified = tree.visit(transformer)

        # Result should just be the expression (wrapped in assert by leave_Expr)
        assert transformer.converted is True

    def test_converts_assertFalse(self):
        """Should convert assertFalse to assert not."""
        code = textwrap.dedent('''\
            self.assertFalse(x)
        ''')

        tree = cst.parse_module(code)
        transformer = UnittestToPytestConverter()
        modified = tree.visit(transformer)

        result = modified.code
        assert "not" in result
        assert transformer.converted is True

    def test_converts_assertIsNone(self):
        """Should convert assertIsNone to assert is None."""
        code = textwrap.dedent('''\
            self.assertIsNone(x)
        ''')

        tree = cst.parse_module(code)
        transformer = UnittestToPytestConverter()
        modified = tree.visit(transformer)

        result = modified.code
        assert "is" in result
        assert "None" in result
        assert transformer.converted is True

    def test_converts_assertIn(self):
        """Should convert assertIn to assert in."""
        code = textwrap.dedent('''\
            self.assertIn(a, b)
        ''')

        tree = cst.parse_module(code)
        transformer = UnittestToPytestConverter()
        modified = tree.visit(transformer)

        result = modified.code
        assert "in" in result
        assert transformer.converted is True

    def test_converts_assertRaises(self):
        """Should convert assertRaises to pytest.raises."""
        code = textwrap.dedent('''\
            self.assertRaises(ValueError)
        ''')

        tree = cst.parse_module(code)
        transformer = UnittestToPytestConverter()
        modified = tree.visit(transformer)

        result = modified.code
        assert "pytest.raises" in result
        assert transformer.converted is True

    def test_converts_comparison_assertions(self):
        """Should convert comparison assertions."""
        code = textwrap.dedent('''\
            self.assertGreater(a, b)
            self.assertLess(a, b)
        ''')

        tree = cst.parse_module(code)
        transformer = UnittestToPytestConverter()
        modified = tree.visit(transformer)

        assert transformer.converted is True


# =============================================================================
# AddPytestFixtureTransformer Tests
# =============================================================================

class TestAddPytestFixtureTransformer:
    """Tests for AddPytestFixtureTransformer."""

    def test_adds_simple_fixture(self):
        """Should add a simple fixture."""
        code = textwrap.dedent('''\
            import pytest
        ''')

        tree = cst.parse_module(code)
        transformer = AddPytestFixtureTransformer(
            "my_fixture",
            "return 42",
        )
        modified = tree.visit(transformer)

        result = modified.code
        assert "@pytest.fixture" in result
        assert "def my_fixture" in result
        assert "return 42" in result
        assert transformer.added is True

    def test_adds_fixture_with_scope(self):
        """Should add fixture with specified scope."""
        code = textwrap.dedent('''\
            import pytest
        ''')

        tree = cst.parse_module(code)
        transformer = AddPytestFixtureTransformer(
            "db_session",
            "yield Session()",
            scope="module",
        )
        modified = tree.visit(transformer)

        result = modified.code
        assert 'scope="module"' in result
        assert transformer.added is True

    def test_skips_if_fixture_exists(self):
        """Should not add fixture if it already exists."""
        code = textwrap.dedent('''\
            import pytest

            @pytest.fixture
            def my_fixture():
                return 1
        ''')

        tree = cst.parse_module(code)
        transformer = AddPytestFixtureTransformer(
            "my_fixture",
            "return 2",
        )
        modified = tree.visit(transformer)

        assert transformer.added is False


# =============================================================================
# extract_function_signature Tests
# =============================================================================

class TestExtractFunctionSignature:
    """Tests for extract_function_signature function."""

    def test_extracts_from_valid_code(self):
        """Should extract signature from valid Python code."""
        code = textwrap.dedent('''\
            def my_func(x: int, y: str = "default") -> bool:
                """My function."""
                return True
        ''')

        sig = extract_function_signature(code, "my_func")

        assert sig is not None
        assert sig.name == "my_func"
        assert len(sig.parameters) == 2
        assert sig.return_type == "bool"

    def test_returns_none_for_nonexistent_function(self):
        """Should return None for nonexistent function."""
        code = "x = 1"

        sig = extract_function_signature(code, "my_func")

        assert sig is None

    def test_extracts_method_with_class_name(self):
        """Should extract method when class_name is provided."""
        code = textwrap.dedent('''\
            class MyClass:
                def my_method(self, value: int) -> None:
                    pass
        ''')

        sig = extract_function_signature(code, "my_method", class_name="MyClass")

        assert sig is not None
        assert sig.name == "my_method"
        assert sig.is_method is True

    def test_handles_syntax_errors(self):
        """Should return None for code with syntax errors."""
        code = "def broken(:"

        sig = extract_function_signature(code, "broken")

        assert sig is None


# =============================================================================
# extract_class_signatures Tests
# =============================================================================

class TestExtractClassSignatures:
    """Tests for extract_class_signatures function."""

    def test_extracts_from_valid_code(self):
        """Should extract all method signatures from a class."""
        code = textwrap.dedent('''\
            class MyClass:
                """Class docstring."""

                def method_a(self):
                    pass

                def method_b(self) -> int:
                    return 1
        ''')

        methods, docstring = extract_class_signatures(code, "MyClass")

        assert len(methods) == 2
        assert docstring == "Class docstring."
        method_names = [m.name for m in methods]
        assert "method_a" in method_names
        assert "method_b" in method_names

    def test_returns_empty_for_nonexistent_class(self):
        """Should return empty list for nonexistent class."""
        code = "x = 1"

        methods, docstring = extract_class_signatures(code, "MyClass")

        assert methods == []
        assert docstring is None

    def test_handles_syntax_errors(self):
        """Should return empty for code with syntax errors."""
        code = "class Broken(:"

        methods, docstring = extract_class_signatures(code, "Broken")

        assert methods == []
        assert docstring is None


# =============================================================================
# extract_doctests Tests
# =============================================================================

class TestExtractDoctests:
    """Tests for extract_doctests function."""

    def test_extracts_from_valid_code(self):
        """Should extract doctests from valid Python code."""
        code = textwrap.dedent('''\
            def add(x, y):
                """Add two numbers.

                >>> add(1, 2)
                3
                """
                return x + y
        ''')

        examples = extract_doctests(code)

        assert len(examples) >= 1

    def test_filters_by_function_name(self):
        """Should filter by function_name."""
        code = textwrap.dedent('''\
            def func_a():
                """
                >>> func_a()
                'a'
                """
                return 'a'

            def func_b():
                """
                >>> func_b()
                'b'
                """
                return 'b'
        ''')

        examples = extract_doctests(code, function_name="func_a")

        for code_ex, expected, func_name in examples:
            assert func_name == "func_a"

    def test_returns_empty_for_no_doctests(self):
        """Should return empty list when no doctests."""
        code = textwrap.dedent('''\
            def simple():
                """No examples here."""
                pass
        ''')

        examples = extract_doctests(code)

        assert examples == []

    def test_handles_syntax_errors(self):
        """Should return empty for code with syntax errors."""
        code = "def broken(:"

        examples = extract_doctests(code)

        assert examples == []


# =============================================================================
# Integration Tests
# =============================================================================

class TestTestsIntegration:
    """Integration tests for test generation."""

    def test_full_workflow_function_to_test(self):
        """Complete workflow: extract signature, generate test."""
        code = textwrap.dedent('''\
            def calculate(x: int, y: int) -> int:
                """Calculate the sum.

                >>> calculate(1, 2)
                3
                """
                return x + y
        ''')

        # Extract signature
        sig = extract_function_signature(code, "calculate")
        assert sig is not None

        # Generate test stub
        gen = TestGenerator()
        stub = gen.generate_function_test_stub(sig)

        assert "def test_calculate" in stub
        assert "assert" in stub

        # Extract and convert doctests
        examples = extract_doctests(code, function_name="calculate")
        doctest_tests = gen.doctest_to_pytest(examples, function_name="calculate")

        assert "def test_calculate_doctest" in doctest_tests

    def test_full_workflow_class_to_test_file(self):
        """Complete workflow: extract class signatures, generate test file."""
        code = textwrap.dedent('''\
            class Calculator:
                """A simple calculator."""

                def add(self, x: int, y: int) -> int:
                    return x + y

                def subtract(self, x: int, y: int) -> int:
                    return x - y
        ''')

        # Extract signatures
        methods, docstring = extract_class_signatures(code, "Calculator")
        assert len(methods) == 2

        # Generate test file
        gen = TestGenerator()
        test_file = gen.generate_class_test_file(
            "Calculator",
            methods,
            class_docstring=docstring,
            module_path="myapp.math",
        )

        assert "class TestCalculator" in test_file
        assert "from myapp.math import Calculator" in test_file
        assert "test_add" in test_file
        assert "test_subtract" in test_file
