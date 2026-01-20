"""Docstring management for Python codebases.

This package provides tools for generating, parsing, updating, and converting
docstrings in Python source code. Supports Google, NumPy, and Sphinx styles.

Classes
-------
DocstringStyle
    Enum of supported docstring styles.

DocstringParser
    Parse existing docstrings into a style-agnostic representation.

DocstringGenerator
    Generate docstrings from function/method signatures.

ParsedDocstring
    Style-agnostic representation of a docstring.

DocstringParam
    A parameter documented in a docstring.

DocstringRaises
    An exception documented in a docstring.

DocstringReturns
    Return value documented in a docstring.

Examples
--------
>>> from rejig import Rejig
>>> from rejig.docstrings import DocstringGenerator, DocstringParser
>>>
>>> # Generate docstrings for functions without them
>>> rj = Rejig("src/")
>>> func = rj.find_function("process")
>>> func.generate_docstring(style="google")
>>>
>>> # Parse existing docstrings
>>> parser = DocstringParser()
>>> parsed = parser.parse(existing_docstring)
>>> print(parsed.params)
>>>
>>> # Convert docstring styles
>>> file = rj.file("mymodule.py")
>>> file.convert_docstring_style("sphinx", "google")
"""

from rejig.docstrings.generator import (
    DocstringGenerator,
    generate_docstring_for_function,
    generate_docstring_for_method,
)
from rejig.docstrings.parser import (
    DocstringParser,
    extract_docstring,
    has_docstring,
)
from rejig.docstrings.styles import (
    DocstringExample,
    DocstringFormatter,
    DocstringParam,
    DocstringRaises,
    DocstringReturns,
    DocstringStyle,
    DocstringStyleType,
    GoogleDocstringFormatter,
    NumpyDocstringFormatter,
    ParsedDocstring,
    SphinxDocstringFormatter,
    get_formatter,
)
from rejig.docstrings.updater import (
    AddDocstringTransformer,
    ConvertDocstringStyleTransformer,
    DocstringValidator,
    UpdateDocstringTransformer,
    find_missing_docstrings,
    find_outdated_docstrings,
)

__all__ = [
    # Styles
    "DocstringStyle",
    "DocstringStyleType",
    "DocstringParam",
    "DocstringRaises",
    "DocstringReturns",
    "DocstringExample",
    "ParsedDocstring",
    "DocstringFormatter",
    "GoogleDocstringFormatter",
    "NumpyDocstringFormatter",
    "SphinxDocstringFormatter",
    "get_formatter",
    # Parser
    "DocstringParser",
    "extract_docstring",
    "has_docstring",
    # Generator
    "DocstringGenerator",
    "generate_docstring_for_function",
    "generate_docstring_for_method",
    # Updater
    "AddDocstringTransformer",
    "UpdateDocstringTransformer",
    "ConvertDocstringStyleTransformer",
    "DocstringValidator",
    "find_outdated_docstrings",
    "find_missing_docstrings",
]
