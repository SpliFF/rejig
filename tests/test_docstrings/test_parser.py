"""
Tests for rejig.docstrings.parser module.

This module tests DocstringParser for parsing docstrings:
- Detecting docstring style (Google, NumPy, Sphinx)
- Parsing parameters, returns, raises sections
- Handling different styles of documentation
- Edge cases and malformed docstrings

The DocstringParser automatically detects docstring style and
parses it into a style-agnostic ParsedDocstring object.

Coverage targets:
- detect_style() for different styles
- parse() for Google-style docstrings
- parse() for NumPy-style docstrings
- parse() for Sphinx-style docstrings
- extract_docstring() and has_docstring() helpers
- Edge cases (empty, malformed, unusual formatting)
"""
from __future__ import annotations

import textwrap

import pytest

from rejig.docstrings import DocstringParser, DocstringStyle, ParsedDocstring


# =============================================================================
# DocstringParser Style Detection Tests
# =============================================================================

class TestDocstringParserStyleDetection:
    """Tests for DocstringParser.detect_style()."""

    @pytest.fixture
    def parser(self) -> DocstringParser:
        """Create a parser instance."""
        return DocstringParser()

    def test_detect_google_style(self, parser: DocstringParser):
        """
        detect_style() should identify Google-style docstrings.

        Google style uses "Args:", "Returns:", etc. as section headers.
        """
        docstring = textwrap.dedent('''
            Short summary.

            Args:
                x: The x coordinate.
                y: The y coordinate.

            Returns:
                The computed distance.
        ''')

        style = parser.detect_style(docstring)
        assert style == DocstringStyle.GOOGLE

    def test_detect_numpy_style(self, parser: DocstringParser):
        """
        detect_style() should identify NumPy-style docstrings.

        NumPy style uses underlined section headers like:
        Parameters
        ----------
        """
        docstring = textwrap.dedent('''
            Short summary.

            Parameters
            ----------
            x : int
                The x coordinate.
            y : int
                The y coordinate.

            Returns
            -------
            float
                The computed distance.
        ''')

        style = parser.detect_style(docstring)
        assert style == DocstringStyle.NUMPY

    def test_detect_sphinx_style(self, parser: DocstringParser):
        """
        detect_style() should identify Sphinx-style docstrings.

        Sphinx style uses :param:, :type:, :returns:, etc.
        """
        docstring = textwrap.dedent('''
            Short summary.

            :param x: The x coordinate.
            :type x: int
            :param y: The y coordinate.
            :type y: int
            :returns: The computed distance.
            :rtype: float
        ''')

        style = parser.detect_style(docstring)
        assert style == DocstringStyle.SPHINX

    def test_default_to_google_style(self, parser: DocstringParser):
        """
        detect_style() should default to Google style for ambiguous docstrings.
        """
        docstring = "Just a simple summary with no sections."

        style = parser.detect_style(docstring)
        assert style == DocstringStyle.GOOGLE


# =============================================================================
# Google Style Parsing Tests
# =============================================================================

class TestDocstringParserGoogle:
    """Tests for parsing Google-style docstrings."""

    @pytest.fixture
    def parser(self) -> DocstringParser:
        """Create a parser instance."""
        return DocstringParser()

    def test_parse_summary_only(self, parser: DocstringParser):
        """
        parse() should extract summary from simple docstrings.
        """
        docstring = "This is a short summary."

        result = parser.parse(docstring)

        assert result.summary == "This is a short summary."
        assert result.description == ""
        assert result.params == []

    def test_parse_args_section(self, parser: DocstringParser):
        """
        parse() should extract parameters from Args section.
        """
        docstring = textwrap.dedent('''
            Calculate distance.

            Args:
                x: The x coordinate.
                y: The y coordinate.
        ''')

        result = parser.parse(docstring)

        assert len(result.params) == 2
        assert result.params[0].name == "x"
        assert result.params[0].description == "The x coordinate."
        assert result.params[1].name == "y"
        assert result.params[1].description == "The y coordinate."

    def test_parse_args_with_types(self, parser: DocstringParser):
        """
        parse() should extract type hints from Args section.

        Google style: name (type): description
        """
        docstring = textwrap.dedent('''
            Calculate distance.

            Args:
                x (int): The x coordinate.
                y (float): The y coordinate.
        ''')

        result = parser.parse(docstring)

        assert len(result.params) == 2
        assert result.params[0].name == "x"
        assert result.params[0].type_hint == "int"
        assert result.params[1].name == "y"
        assert result.params[1].type_hint == "float"

    def test_parse_returns_section(self, parser: DocstringParser):
        """
        parse() should extract return information.
        """
        docstring = textwrap.dedent('''
            Calculate distance.

            Returns:
                The computed distance value.
        ''')

        result = parser.parse(docstring)

        assert result.returns is not None
        assert "distance" in result.returns.description.lower()

    def test_parse_returns_with_type(self, parser: DocstringParser):
        """
        parse() should extract return type.

        Google style: type: description
        """
        docstring = textwrap.dedent('''
            Calculate distance.

            Returns:
                float: The computed distance value.
        ''')

        result = parser.parse(docstring)

        assert result.returns is not None
        assert result.returns.type_hint == "float"

    def test_parse_raises_section(self, parser: DocstringParser):
        """
        parse() should extract raised exceptions.
        """
        docstring = textwrap.dedent('''
            Calculate distance.

            Raises:
                ValueError: If coordinates are negative.
                TypeError: If arguments are not numeric.
        ''')

        result = parser.parse(docstring)

        assert len(result.raises) == 2
        assert result.raises[0].exception == "ValueError"
        assert "negative" in result.raises[0].description.lower()
        assert result.raises[1].exception == "TypeError"

    def test_parse_multiline_descriptions(self, parser: DocstringParser):
        """
        parse() should handle multi-line parameter descriptions.
        """
        docstring = textwrap.dedent('''
            Calculate distance.

            Args:
                x: The x coordinate. This can be any numeric
                    value including floats.
        ''')

        result = parser.parse(docstring)

        assert len(result.params) == 1
        assert "numeric" in result.params[0].description
        assert "floats" in result.params[0].description


# =============================================================================
# NumPy Style Parsing Tests
# =============================================================================

class TestDocstringParserNumPy:
    """Tests for parsing NumPy-style docstrings."""

    @pytest.fixture
    def parser(self) -> DocstringParser:
        """Create a parser instance."""
        return DocstringParser()

    def test_parse_numpy_parameters(self, parser: DocstringParser):
        """
        parse() should extract parameters from NumPy-style docstrings.

        NumPy style uses underlined section headers.
        """
        docstring = textwrap.dedent('''
            Calculate distance.

            Parameters
            ----------
            x : int
                The x coordinate.
            y : float
                The y coordinate.
        ''')

        result = parser.parse(docstring)

        assert len(result.params) == 2
        assert result.params[0].name == "x"
        assert result.params[0].type_hint == "int"
        assert result.params[1].name == "y"
        assert result.params[1].type_hint == "float"

    def test_parse_numpy_returns(self, parser: DocstringParser):
        """
        parse() should extract returns from NumPy-style docstrings.
        """
        docstring = textwrap.dedent('''
            Calculate distance.

            Returns
            -------
            float
                The computed distance.
        ''')

        result = parser.parse(docstring)

        assert result.returns is not None
        assert result.returns.type_hint == "float"
        assert "distance" in result.returns.description.lower()

    def test_parse_numpy_raises(self, parser: DocstringParser):
        """
        parse() should extract raises from NumPy-style docstrings.
        """
        docstring = textwrap.dedent('''
            Calculate distance.

            Raises
            ------
            ValueError
                If coordinates are negative.
        ''')

        result = parser.parse(docstring)

        assert len(result.raises) == 1
        assert result.raises[0].exception == "ValueError"


# =============================================================================
# Sphinx Style Parsing Tests
# =============================================================================

class TestDocstringParserSphinx:
    """Tests for parsing Sphinx-style docstrings."""

    @pytest.fixture
    def parser(self) -> DocstringParser:
        """Create a parser instance."""
        return DocstringParser()

    def test_parse_sphinx_params(self, parser: DocstringParser):
        """
        parse() should extract :param: directives.
        """
        docstring = textwrap.dedent('''
            Calculate distance.

            :param x: The x coordinate.
            :param y: The y coordinate.
        ''')

        result = parser.parse(docstring)

        assert len(result.params) == 2
        assert result.params[0].name == "x"
        assert result.params[1].name == "y"

    def test_parse_sphinx_types(self, parser: DocstringParser):
        """
        parse() should extract :type: directives.
        """
        docstring = textwrap.dedent('''
            Calculate distance.

            :param x: The x coordinate.
            :type x: int
            :param y: The y coordinate.
            :type y: float
        ''')

        result = parser.parse(docstring)

        assert len(result.params) == 2
        assert result.params[0].type_hint == "int"
        assert result.params[1].type_hint == "float"

    def test_parse_sphinx_returns(self, parser: DocstringParser):
        """
        parse() should extract :returns: and :rtype: directives.
        """
        docstring = textwrap.dedent('''
            Calculate distance.

            :returns: The computed distance.
            :rtype: float
        ''')

        result = parser.parse(docstring)

        assert result.returns is not None
        assert result.returns.type_hint == "float"
        assert "distance" in result.returns.description.lower()

    def test_parse_sphinx_raises(self, parser: DocstringParser):
        """
        parse() should extract :raises: directives.
        """
        docstring = textwrap.dedent('''
            Calculate distance.

            :raises ValueError: If coordinates are negative.
        ''')

        result = parser.parse(docstring)

        assert len(result.raises) == 1
        assert result.raises[0].exception == "ValueError"


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

class TestDocstringParserEdgeCases:
    """Tests for edge cases in docstring parsing."""

    @pytest.fixture
    def parser(self) -> DocstringParser:
        """Create a parser instance."""
        return DocstringParser()

    def test_empty_docstring(self, parser: DocstringParser):
        """
        parse() should handle empty docstrings gracefully.
        """
        result = parser.parse("")

        assert result.summary == ""
        assert result.params == []
        assert result.returns is None

    def test_whitespace_only_docstring(self, parser: DocstringParser):
        """
        parse() should handle whitespace-only docstrings.
        """
        result = parser.parse("   \n\n   ")

        assert result.summary == ""

    def test_docstring_with_triple_quotes(self, parser: DocstringParser):
        """
        parse() should strip triple quotes from docstrings.

        The parser receives raw docstrings that may still have quotes.
        """
        docstring = '"""Short summary."""'

        result = parser.parse(docstring)

        assert result.summary == "Short summary."
        assert '"""' not in result.summary

    def test_parameters_section_alias(self, parser: DocstringParser):
        """
        parse() should recognize different section header variants.

        Google-style allows "Args:", "Arguments:", "Parameters:", etc.
        """
        docstring = textwrap.dedent('''
            Function summary.

            Parameters:
                x: The parameter.
        ''')

        result = parser.parse(docstring)

        assert len(result.params) == 1
        assert result.params[0].name == "x"


# =============================================================================
# Helper Functions Tests
# =============================================================================

class TestDocstringHelpers:
    """Tests for extract_docstring() and has_docstring() helpers."""

    def test_extract_docstring_from_function(self):
        """
        extract_docstring() should extract docstrings from function nodes.
        """
        import libcst as cst
        from rejig.docstrings import extract_docstring

        code = textwrap.dedent('''
            def my_function():
                """This is the docstring."""
                pass
        ''')

        module = cst.parse_module(code)
        func = module.body[0]

        result = extract_docstring(func)

        assert result == "This is the docstring."

    def test_extract_docstring_none_if_missing(self):
        """
        extract_docstring() should return None if no docstring.
        """
        import libcst as cst
        from rejig.docstrings import extract_docstring

        code = textwrap.dedent('''
            def my_function():
                pass
        ''')

        module = cst.parse_module(code)
        func = module.body[0]

        result = extract_docstring(func)

        assert result is None

    def test_has_docstring_true(self):
        """
        has_docstring() should return True when docstring exists.
        """
        import libcst as cst
        from rejig.docstrings import has_docstring

        code = textwrap.dedent('''
            def my_function():
                """Docstring here."""
                pass
        ''')

        module = cst.parse_module(code)
        func = module.body[0]

        assert has_docstring(func) is True

    def test_has_docstring_false(self):
        """
        has_docstring() should return False when no docstring.
        """
        import libcst as cst
        from rejig.docstrings import has_docstring

        code = textwrap.dedent('''
            def my_function():
                pass
        ''')

        module = cst.parse_module(code)
        func = module.body[0]

        assert has_docstring(func) is False


# =============================================================================
# ParsedDocstring Data Class Tests
# =============================================================================

class TestParsedDocstring:
    """Tests for ParsedDocstring data class."""

    def test_default_values(self):
        """
        ParsedDocstring should have sensible defaults.
        """
        parsed = ParsedDocstring()

        assert parsed.summary == ""
        assert parsed.description == ""
        assert parsed.params == []
        assert parsed.returns is None
        assert parsed.yields is None
        assert parsed.raises == []
        assert parsed.examples == []
        assert parsed.notes == ""
        assert parsed.attributes == []
