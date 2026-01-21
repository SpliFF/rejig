"""
Tests for rejig.docstrings.styles module.

This module tests docstring style definitions and formatters:
- DocstringStyle enum
- DocstringParam, DocstringRaises, DocstringReturns dataclasses
- ParsedDocstring dataclass and methods
- DocstringFormatter base class and implementations
"""
from __future__ import annotations

import pytest

from rejig.docstrings.styles import (
    DocstringExample,
    DocstringParam,
    DocstringRaises,
    DocstringReturns,
    DocstringStyle,
    GoogleDocstringFormatter,
    NumpyDocstringFormatter,
    ParsedDocstring,
    SphinxDocstringFormatter,
    get_formatter,
)


# =============================================================================
# DocstringStyle Tests
# =============================================================================

class TestDocstringStyle:
    """Tests for DocstringStyle enum."""

    def test_google_style(self):
        """DocstringStyle should have GOOGLE value."""
        assert DocstringStyle.GOOGLE == "google"

    def test_numpy_style(self):
        """DocstringStyle should have NUMPY value."""
        assert DocstringStyle.NUMPY == "numpy"

    def test_sphinx_style(self):
        """DocstringStyle should have SPHINX value."""
        assert DocstringStyle.SPHINX == "sphinx"

    def test_from_string(self):
        """DocstringStyle should be creatable from string."""
        style = DocstringStyle("google")
        assert style == DocstringStyle.GOOGLE


# =============================================================================
# DocstringParam Tests
# =============================================================================

class TestDocstringParam:
    """Tests for DocstringParam dataclass."""

    def test_minimal_param(self):
        """DocstringParam should work with just name."""
        param = DocstringParam(name="x")

        assert param.name == "x"
        assert param.description == ""
        assert param.type_hint == ""

    def test_full_param(self):
        """DocstringParam should accept all fields."""
        param = DocstringParam(
            name="data",
            description="The input data",
            type_hint="list[str]",
        )

        assert param.name == "data"
        assert param.description == "The input data"
        assert param.type_hint == "list[str]"


# =============================================================================
# DocstringRaises Tests
# =============================================================================

class TestDocstringRaises:
    """Tests for DocstringRaises dataclass."""

    def test_minimal_raises(self):
        """DocstringRaises should work with just exception."""
        raises = DocstringRaises(exception="ValueError")

        assert raises.exception == "ValueError"
        assert raises.description == ""

    def test_full_raises(self):
        """DocstringRaises should accept all fields."""
        raises = DocstringRaises(
            exception="TypeError",
            description="If argument is not a string",
        )

        assert raises.exception == "TypeError"
        assert raises.description == "If argument is not a string"


# =============================================================================
# DocstringReturns Tests
# =============================================================================

class TestDocstringReturns:
    """Tests for DocstringReturns dataclass."""

    def test_minimal_returns(self):
        """DocstringReturns should work with just description."""
        returns = DocstringReturns(description="The result")

        assert returns.description == "The result"
        assert returns.type_hint == ""

    def test_full_returns(self):
        """DocstringReturns should accept all fields."""
        returns = DocstringReturns(
            description="The computed value",
            type_hint="int",
        )

        assert returns.description == "The computed value"
        assert returns.type_hint == "int"


# =============================================================================
# DocstringExample Tests
# =============================================================================

class TestDocstringExample:
    """Tests for DocstringExample dataclass."""

    def test_minimal_example(self):
        """DocstringExample should work with just code."""
        example = DocstringExample(code=">>> func(1)")

        assert example.code == ">>> func(1)"
        assert example.description == ""

    def test_full_example(self):
        """DocstringExample should accept all fields."""
        example = DocstringExample(
            code=">>> add(1, 2)\n3",
            description="Adding two numbers",
        )

        assert example.code == ">>> add(1, 2)\n3"
        assert example.description == "Adding two numbers"


# =============================================================================
# ParsedDocstring Tests
# =============================================================================

class TestParsedDocstring:
    """Tests for ParsedDocstring dataclass."""

    def test_empty_docstring(self):
        """ParsedDocstring should have sensible defaults."""
        doc = ParsedDocstring()

        assert doc.summary == ""
        assert doc.description == ""
        assert doc.params == []
        assert doc.returns is None
        assert doc.raises == []
        assert doc.examples == []

    def test_full_docstring(self):
        """ParsedDocstring should accept all fields."""
        doc = ParsedDocstring(
            summary="Short summary.",
            description="Longer description.",
            params=[DocstringParam("x", "The input", "int")],
            returns=DocstringReturns("The output", "str"),
            raises=[DocstringRaises("ValueError", "If invalid")],
            examples=[DocstringExample(">>> func()")],
        )

        assert doc.summary == "Short summary."
        assert len(doc.params) == 1
        assert doc.returns is not None
        assert len(doc.raises) == 1
        assert len(doc.examples) == 1

    def test_has_param(self):
        """has_param should check if parameter is documented."""
        doc = ParsedDocstring(
            params=[
                DocstringParam("x"),
                DocstringParam("y"),
            ]
        )

        assert doc.has_param("x") is True
        assert doc.has_param("y") is True
        assert doc.has_param("z") is False

    def test_get_param(self):
        """get_param should return parameter by name."""
        doc = ParsedDocstring(
            params=[
                DocstringParam("x", "First param"),
                DocstringParam("y", "Second param"),
            ]
        )

        x_param = doc.get_param("x")
        assert x_param is not None
        assert x_param.description == "First param"

        z_param = doc.get_param("z")
        assert z_param is None

    def test_add_param_new(self):
        """add_param should add a new parameter."""
        doc = ParsedDocstring()

        doc.add_param("x", "The input", "int")

        assert len(doc.params) == 1
        assert doc.params[0].name == "x"
        assert doc.params[0].description == "The input"

    def test_add_param_update(self):
        """add_param should update an existing parameter."""
        doc = ParsedDocstring(
            params=[DocstringParam("x", "Old description")]
        )

        doc.add_param("x", "New description", "int")

        assert len(doc.params) == 1
        assert doc.params[0].description == "New description"

    def test_remove_param(self):
        """remove_param should remove a parameter."""
        doc = ParsedDocstring(
            params=[
                DocstringParam("x"),
                DocstringParam("y"),
            ]
        )

        result = doc.remove_param("x")

        assert result is True
        assert len(doc.params) == 1
        assert doc.params[0].name == "y"

    def test_remove_param_not_found(self):
        """remove_param should return False if not found."""
        doc = ParsedDocstring(params=[DocstringParam("x")])

        result = doc.remove_param("z")

        assert result is False
        assert len(doc.params) == 1


# =============================================================================
# get_formatter Tests
# =============================================================================

class TestGetFormatter:
    """Tests for get_formatter function."""

    def test_google_formatter(self):
        """get_formatter should return Google formatter."""
        formatter = get_formatter(DocstringStyle.GOOGLE)
        assert isinstance(formatter, GoogleDocstringFormatter)

    def test_numpy_formatter(self):
        """get_formatter should return NumPy formatter."""
        formatter = get_formatter(DocstringStyle.NUMPY)
        assert isinstance(formatter, NumpyDocstringFormatter)

    def test_sphinx_formatter(self):
        """get_formatter should return Sphinx formatter."""
        formatter = get_formatter(DocstringStyle.SPHINX)
        assert isinstance(formatter, SphinxDocstringFormatter)

    def test_from_string(self):
        """get_formatter should accept string style."""
        formatter = get_formatter("google")
        assert isinstance(formatter, GoogleDocstringFormatter)


# =============================================================================
# GoogleDocstringFormatter Tests
# =============================================================================

class TestGoogleDocstringFormatter:
    """Tests for GoogleDocstringFormatter."""

    @pytest.fixture
    def formatter(self):
        return GoogleDocstringFormatter()

    def test_format_summary_only(self, formatter):
        """Should format docstring with only summary."""
        doc = ParsedDocstring(summary="A simple function.")

        result = formatter.format(doc)

        assert "A simple function." in result

    def test_format_with_params(self, formatter):
        """Should format docstring with parameters."""
        doc = ParsedDocstring(
            summary="Process data.",
            params=[
                DocstringParam("x", "The input value", "int"),
                DocstringParam("y", "The second value", "str"),
            ],
        )

        result = formatter.format(doc)

        assert "Args:" in result
        assert "x (int):" in result or "x:" in result
        assert "y (str):" in result or "y:" in result

    def test_format_with_returns(self, formatter):
        """Should format docstring with returns."""
        doc = ParsedDocstring(
            summary="Get value.",
            returns=DocstringReturns("The computed value", "int"),
        )

        result = formatter.format(doc)

        assert "Returns:" in result
        assert "int" in result or "computed value" in result

    def test_format_with_raises(self, formatter):
        """Should format docstring with raises."""
        doc = ParsedDocstring(
            summary="Validate input.",
            raises=[
                DocstringRaises("ValueError", "If input is invalid"),
            ],
        )

        result = formatter.format(doc)

        assert "Raises:" in result
        assert "ValueError" in result


# =============================================================================
# NumpyDocstringFormatter Tests
# =============================================================================

class TestNumpyDocstringFormatter:
    """Tests for NumpyDocstringFormatter."""

    @pytest.fixture
    def formatter(self):
        return NumpyDocstringFormatter()

    def test_format_summary_only(self, formatter):
        """Should format docstring with only summary."""
        doc = ParsedDocstring(summary="A numpy-style docstring.")

        result = formatter.format(doc)

        assert "A numpy-style docstring." in result

    def test_format_with_params(self, formatter):
        """Should format parameters with underline."""
        doc = ParsedDocstring(
            summary="Process data.",
            params=[
                DocstringParam("x", "The input", "int"),
            ],
        )

        result = formatter.format(doc)

        assert "Parameters" in result
        assert "----------" in result
        assert "x" in result

    def test_format_with_returns(self, formatter):
        """Should format returns with underline."""
        doc = ParsedDocstring(
            summary="Get value.",
            returns=DocstringReturns("The result", "int"),
        )

        result = formatter.format(doc)

        assert "Returns" in result
        assert "-------" in result


# =============================================================================
# SphinxDocstringFormatter Tests
# =============================================================================

class TestSphinxDocstringFormatter:
    """Tests for SphinxDocstringFormatter."""

    @pytest.fixture
    def formatter(self):
        return SphinxDocstringFormatter()

    def test_format_summary_only(self, formatter):
        """Should format docstring with only summary."""
        doc = ParsedDocstring(summary="A sphinx-style docstring.")

        result = formatter.format(doc)

        assert "A sphinx-style docstring." in result

    def test_format_with_params(self, formatter):
        """Should format parameters with :param: directive."""
        doc = ParsedDocstring(
            summary="Process data.",
            params=[
                DocstringParam("x", "The input", "int"),
            ],
        )

        result = formatter.format(doc)

        assert ":param" in result
        assert "x" in result

    def test_format_with_type(self, formatter):
        """Should include :type: directive."""
        doc = ParsedDocstring(
            summary="Get value.",
            params=[
                DocstringParam("x", "The input", "int"),
            ],
        )

        result = formatter.format(doc)

        assert ":type" in result or ":param int" in result

    def test_format_with_returns(self, formatter):
        """Should format returns with :returns: directive."""
        doc = ParsedDocstring(
            summary="Get value.",
            returns=DocstringReturns("The result", "int"),
        )

        result = formatter.format(doc)

        assert ":returns:" in result or ":return:" in result

    def test_format_with_raises(self, formatter):
        """Should format raises with :raises: directive."""
        doc = ParsedDocstring(
            summary="Validate.",
            raises=[DocstringRaises("ValueError", "If invalid")],
        )

        result = formatter.format(doc)

        assert ":raises" in result
        assert "ValueError" in result
