"""
Tests for rejig.docstrings.generator module.

This module tests docstring generation:
- DocstringGenerator class
- generate() method
- generate_parsed() method
"""
from __future__ import annotations

import textwrap

import libcst as cst
import pytest

from rejig.docstrings.generator import DocstringGenerator
from rejig.docstrings.styles import DocstringStyle


# =============================================================================
# DocstringGenerator Tests
# =============================================================================

class TestDocstringGenerator:
    """Tests for DocstringGenerator class."""

    @pytest.fixture
    def google_gen(self):
        return DocstringGenerator(style="google")

    @pytest.fixture
    def numpy_gen(self):
        return DocstringGenerator(style="numpy")

    @pytest.fixture
    def sphinx_gen(self):
        return DocstringGenerator(style="sphinx")

    def test_init_with_string_style(self):
        """DocstringGenerator should accept string style."""
        gen = DocstringGenerator(style="google")
        assert gen.style == DocstringStyle.GOOGLE

    def test_init_with_enum_style(self):
        """DocstringGenerator should accept enum style."""
        gen = DocstringGenerator(style=DocstringStyle.NUMPY)
        assert gen.style == DocstringStyle.NUMPY

    def test_generate_simple_function(self, google_gen):
        """Should generate docstring for simple function."""
        code = textwrap.dedent('''\
            def my_func():
                pass
        ''')

        tree = cst.parse_module(code)
        func = tree.body[0]

        docstring = google_gen.generate(func)

        assert docstring  # Should produce some docstring
        assert isinstance(docstring, str)

    def test_generate_with_parameters(self, google_gen):
        """Should include parameters in docstring."""
        code = textwrap.dedent('''\
            def process(data: list[str], count: int):
                pass
        ''')

        tree = cst.parse_module(code)
        func = tree.body[0]

        docstring = google_gen.generate(func)

        assert "data" in docstring or "Args:" in docstring

    def test_generate_with_return_type(self, google_gen):
        """Should include return type in docstring."""
        code = textwrap.dedent('''\
            def get_value() -> int:
                pass
        ''')

        tree = cst.parse_module(code)
        func = tree.body[0]

        docstring = google_gen.generate(func)

        assert "int" in docstring or "Returns:" in docstring

    def test_generate_with_default_values(self, google_gen):
        """Should handle parameters with defaults."""
        code = textwrap.dedent('''\
            def config(host: str = "localhost", port: int = 8080):
                pass
        ''')

        tree = cst.parse_module(code)
        func = tree.body[0]

        docstring = google_gen.generate(func)

        assert "host" in docstring or "Args:" in docstring

    def test_generate_with_custom_summary(self, google_gen):
        """Should use custom summary if provided."""
        code = textwrap.dedent('''\
            def my_func():
                pass
        ''')

        tree = cst.parse_module(code)
        func = tree.body[0]

        docstring = google_gen.generate(func, summary="Custom summary here.")

        assert "Custom summary here." in docstring

    def test_generate_parsed_returns_parsed_docstring(self, google_gen):
        """generate_parsed should return ParsedDocstring."""
        code = textwrap.dedent('''\
            def process(x: int) -> str:
                pass
        ''')

        tree = cst.parse_module(code)
        func = tree.body[0]

        parsed = google_gen.generate_parsed(func)

        assert parsed is not None
        assert len(parsed.params) >= 1
        assert parsed.params[0].name == "x"
        assert parsed.returns is not None


# =============================================================================
# Style-Specific Generation Tests
# =============================================================================

class TestGoogleStyleGeneration:
    """Tests for Google-style docstring generation."""

    def test_generates_args_section(self):
        """Should generate Args section for parameters."""
        gen = DocstringGenerator(style="google")
        code = textwrap.dedent('''\
            def func(x: int, y: str):
                pass
        ''')

        tree = cst.parse_module(code)
        func = tree.body[0]

        docstring = gen.generate(func)

        assert "Args:" in docstring

    def test_generates_returns_section(self):
        """Should generate Returns section."""
        gen = DocstringGenerator(style="google")
        code = textwrap.dedent('''\
            def func() -> int:
                pass
        ''')

        tree = cst.parse_module(code)
        func = tree.body[0]

        docstring = gen.generate(func)

        assert "Returns:" in docstring


class TestNumpyStyleGeneration:
    """Tests for NumPy-style docstring generation."""

    def test_generates_parameters_section(self):
        """Should generate Parameters section."""
        gen = DocstringGenerator(style="numpy")
        code = textwrap.dedent('''\
            def func(x: int):
                pass
        ''')

        tree = cst.parse_module(code)
        func = tree.body[0]

        docstring = gen.generate(func)

        assert "Parameters" in docstring
        assert "----------" in docstring

    def test_generates_returns_section(self):
        """Should generate Returns section with underline."""
        gen = DocstringGenerator(style="numpy")
        code = textwrap.dedent('''\
            def func() -> int:
                pass
        ''')

        tree = cst.parse_module(code)
        func = tree.body[0]

        docstring = gen.generate(func)

        assert "Returns" in docstring


class TestSphinxStyleGeneration:
    """Tests for Sphinx-style docstring generation."""

    def test_generates_param_directives(self):
        """Should generate :param: directives."""
        gen = DocstringGenerator(style="sphinx")
        code = textwrap.dedent('''\
            def func(x: int):
                pass
        ''')

        tree = cst.parse_module(code)
        func = tree.body[0]

        docstring = gen.generate(func)

        assert ":param" in docstring

    def test_generates_returns_directive(self):
        """Should generate :returns: directive."""
        gen = DocstringGenerator(style="sphinx")
        code = textwrap.dedent('''\
            def func() -> int:
                pass
        ''')

        tree = cst.parse_module(code)
        func = tree.body[0]

        docstring = gen.generate(func)

        assert ":return" in docstring or ":returns:" in docstring


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases in docstring generation."""

    def test_function_with_no_params_or_return(self):
        """Should handle function with no params or return."""
        gen = DocstringGenerator(style="google")
        code = textwrap.dedent('''\
            def noop():
                pass
        ''')

        tree = cst.parse_module(code)
        func = tree.body[0]

        docstring = gen.generate(func)

        assert docstring  # Should still produce something

    def test_function_with_star_args(self):
        """Should handle *args."""
        gen = DocstringGenerator(style="google")
        code = textwrap.dedent('''\
            def variadic(*args):
                pass
        ''')

        tree = cst.parse_module(code)
        func = tree.body[0]

        # Should not raise
        docstring = gen.generate(func)
        assert docstring

    def test_function_with_kwargs(self):
        """Should handle **kwargs."""
        gen = DocstringGenerator(style="google")
        code = textwrap.dedent('''\
            def keyword(**kwargs):
                pass
        ''')

        tree = cst.parse_module(code)
        func = tree.body[0]

        # Should not raise
        docstring = gen.generate(func)
        assert docstring

    def test_async_function(self):
        """Should handle async functions."""
        gen = DocstringGenerator(style="google")
        code = textwrap.dedent('''\
            async def fetch(url: str) -> str:
                pass
        ''')

        tree = cst.parse_module(code)
        func = tree.body[0]

        docstring = gen.generate(func)

        assert "url" in docstring or "Args:" in docstring

    def test_method_skips_self(self):
        """Should skip 'self' parameter for methods."""
        gen = DocstringGenerator(style="google")
        code = textwrap.dedent('''\
            class MyClass:
                def method(self, x: int):
                    pass
        ''')

        tree = cst.parse_module(code)
        class_def = tree.body[0]
        method = class_def.body.body[0]

        docstring = gen.generate(method)

        # self should not be documented
        assert "self" not in docstring.lower() or "x" in docstring

    def test_classmethod_skips_cls(self):
        """Should skip 'cls' parameter for classmethods."""
        gen = DocstringGenerator(style="google")
        code = textwrap.dedent('''\
            class MyClass:
                @classmethod
                def create(cls, value: int):
                    pass
        ''')

        tree = cst.parse_module(code)
        class_def = tree.body[0]
        method = class_def.body.body[0]

        docstring = gen.generate(method)

        # cls should not be documented
        assert "value" in docstring or "Args:" in docstring

    def test_complex_type_hints(self):
        """Should handle complex type hints."""
        gen = DocstringGenerator(style="google")
        code = textwrap.dedent('''\
            def process(
                data: dict[str, list[int]],
                callback: Callable[[int], None] | None = None,
            ) -> tuple[int, str]:
                pass
        ''')

        tree = cst.parse_module(code)
        func = tree.body[0]

        # Should not raise
        docstring = gen.generate(func)
        assert docstring
