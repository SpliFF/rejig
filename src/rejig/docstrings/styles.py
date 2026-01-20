"""Docstring style definitions and formatters.

Supports Google, NumPy, and Sphinx docstring styles.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


DocstringStyleType = Literal["google", "numpy", "sphinx"]


class DocstringStyle(str, Enum):
    """Supported docstring styles."""

    GOOGLE = "google"
    NUMPY = "numpy"
    SPHINX = "sphinx"


@dataclass
class DocstringParam:
    """A parameter documented in a docstring."""

    name: str
    description: str = ""
    type_hint: str = ""


@dataclass
class DocstringRaises:
    """An exception documented in a docstring."""

    exception: str
    description: str = ""


@dataclass
class DocstringReturns:
    """Return value documented in a docstring."""

    description: str
    type_hint: str = ""


@dataclass
class DocstringExample:
    """An example in a docstring."""

    code: str
    description: str = ""


@dataclass
class ParsedDocstring:
    """Parsed representation of a docstring.

    This is a style-agnostic representation that can be converted
    to/from any supported docstring style.
    """

    summary: str = ""
    description: str = ""
    params: list[DocstringParam] = field(default_factory=list)
    returns: DocstringReturns | None = None
    raises: list[DocstringRaises] = field(default_factory=list)
    examples: list[DocstringExample] = field(default_factory=list)
    attributes: list[DocstringParam] = field(default_factory=list)
    yields: DocstringReturns | None = None
    notes: str = ""
    warnings: str = ""
    see_also: str = ""
    references: str = ""

    def has_param(self, name: str) -> bool:
        """Check if a parameter is documented."""
        return any(p.name == name for p in self.params)

    def get_param(self, name: str) -> DocstringParam | None:
        """Get a parameter by name."""
        for p in self.params:
            if p.name == name:
                return p
        return None

    def add_param(self, name: str, description: str = "", type_hint: str = "") -> None:
        """Add or update a parameter."""
        for p in self.params:
            if p.name == name:
                p.description = description
                p.type_hint = type_hint
                return
        self.params.append(DocstringParam(name, description, type_hint))

    def remove_param(self, name: str) -> bool:
        """Remove a parameter. Returns True if found and removed."""
        for i, p in enumerate(self.params):
            if p.name == name:
                del self.params[i]
                return True
        return False

    def has_raises(self, exception: str) -> bool:
        """Check if an exception is documented."""
        return any(r.exception == exception for r in self.raises)

    def add_raises(self, exception: str, description: str = "") -> None:
        """Add or update a raises entry."""
        for r in self.raises:
            if r.exception == exception:
                r.description = description
                return
        self.raises.append(DocstringRaises(exception, description))


class DocstringFormatter:
    """Base class for docstring formatters."""

    def format(self, docstring: ParsedDocstring, indent: str = "") -> str:
        """Format a parsed docstring to a string."""
        raise NotImplementedError

    def get_indent(self, base_indent: str) -> str:
        """Get the indentation for docstring content."""
        return base_indent + "    "


class GoogleDocstringFormatter(DocstringFormatter):
    """Google-style docstring formatter.

    Example output:
        '''Summary line.

        Extended description.

        Args:
            param1: Description of param1.
            param2 (int): Description with type.

        Returns:
            Description of return value.

        Raises:
            ValueError: If input is invalid.
        '''
    """

    def format(self, docstring: ParsedDocstring, indent: str = "") -> str:
        """Format a ParsedDocstring to Google style."""
        lines: list[str] = []
        content_indent = indent + "    "

        # Summary
        if docstring.summary:
            lines.append(f'{indent}"""')
            # Check if summary fits on one line and there's nothing else
            is_simple = (
                not docstring.description
                and not docstring.params
                and docstring.returns is None
                and not docstring.raises
                and not docstring.examples
            )
            if is_simple and len(docstring.summary) < 70:
                lines[-1] = f'{indent}"""{docstring.summary}"""'
                return lines[0]

            lines.append(f"{indent}{docstring.summary}")
        else:
            lines.append(f'{indent}"""')

        # Description
        if docstring.description:
            lines.append("")
            for desc_line in docstring.description.splitlines():
                lines.append(f"{indent}{desc_line}" if desc_line else "")

        # Args/Parameters
        if docstring.params:
            lines.append("")
            lines.append(f"{indent}Args:")
            for param in docstring.params:
                if param.type_hint:
                    lines.append(f"{content_indent}{param.name} ({param.type_hint}): {param.description}")
                else:
                    lines.append(f"{content_indent}{param.name}: {param.description}")

        # Returns
        if docstring.returns:
            lines.append("")
            lines.append(f"{indent}Returns:")
            if docstring.returns.type_hint:
                lines.append(f"{content_indent}{docstring.returns.type_hint}: {docstring.returns.description}")
            else:
                lines.append(f"{content_indent}{docstring.returns.description}")

        # Yields
        if docstring.yields:
            lines.append("")
            lines.append(f"{indent}Yields:")
            if docstring.yields.type_hint:
                lines.append(f"{content_indent}{docstring.yields.type_hint}: {docstring.yields.description}")
            else:
                lines.append(f"{content_indent}{docstring.yields.description}")

        # Raises
        if docstring.raises:
            lines.append("")
            lines.append(f"{indent}Raises:")
            for r in docstring.raises:
                lines.append(f"{content_indent}{r.exception}: {r.description}")

        # Examples
        if docstring.examples:
            lines.append("")
            lines.append(f"{indent}Examples:")
            for example in docstring.examples:
                if example.description:
                    lines.append(f"{content_indent}{example.description}")
                for code_line in example.code.splitlines():
                    lines.append(f"{content_indent}{code_line}")

        # Notes
        if docstring.notes:
            lines.append("")
            lines.append(f"{indent}Note:")
            for note_line in docstring.notes.splitlines():
                lines.append(f"{content_indent}{note_line}" if note_line else "")

        # Close
        lines.append(f'{indent}"""')

        return "\n".join(lines)


class NumpyDocstringFormatter(DocstringFormatter):
    """NumPy-style docstring formatter.

    Example output:
        '''Summary line.

        Extended description.

        Parameters
        ----------
        param1 : type
            Description of param1.
        param2 : int
            Description with type.

        Returns
        -------
        type
            Description of return value.

        Raises
        ------
        ValueError
            If input is invalid.
        '''
    """

    def format(self, docstring: ParsedDocstring, indent: str = "") -> str:
        """Format a ParsedDocstring to NumPy style."""
        lines: list[str] = []
        content_indent = indent + "    "

        # Summary
        if docstring.summary:
            lines.append(f'{indent}"""')
            # Check if summary fits on one line and there's nothing else
            is_simple = (
                not docstring.description
                and not docstring.params
                and docstring.returns is None
                and not docstring.raises
                and not docstring.examples
            )
            if is_simple and len(docstring.summary) < 70:
                lines[-1] = f'{indent}"""{docstring.summary}"""'
                return lines[0]

            lines.append(f"{indent}{docstring.summary}")
        else:
            lines.append(f'{indent}"""')

        # Description
        if docstring.description:
            lines.append("")
            for desc_line in docstring.description.splitlines():
                lines.append(f"{indent}{desc_line}" if desc_line else "")

        # Parameters
        if docstring.params:
            lines.append("")
            lines.append(f"{indent}Parameters")
            lines.append(f"{indent}----------")
            for param in docstring.params:
                type_str = f" : {param.type_hint}" if param.type_hint else ""
                lines.append(f"{indent}{param.name}{type_str}")
                if param.description:
                    lines.append(f"{content_indent}{param.description}")

        # Returns
        if docstring.returns:
            lines.append("")
            lines.append(f"{indent}Returns")
            lines.append(f"{indent}-------")
            if docstring.returns.type_hint:
                lines.append(f"{indent}{docstring.returns.type_hint}")
            if docstring.returns.description:
                lines.append(f"{content_indent}{docstring.returns.description}")

        # Yields
        if docstring.yields:
            lines.append("")
            lines.append(f"{indent}Yields")
            lines.append(f"{indent}------")
            if docstring.yields.type_hint:
                lines.append(f"{indent}{docstring.yields.type_hint}")
            if docstring.yields.description:
                lines.append(f"{content_indent}{docstring.yields.description}")

        # Raises
        if docstring.raises:
            lines.append("")
            lines.append(f"{indent}Raises")
            lines.append(f"{indent}------")
            for r in docstring.raises:
                lines.append(f"{indent}{r.exception}")
                if r.description:
                    lines.append(f"{content_indent}{r.description}")

        # Examples
        if docstring.examples:
            lines.append("")
            lines.append(f"{indent}Examples")
            lines.append(f"{indent}--------")
            for example in docstring.examples:
                if example.description:
                    lines.append(f"{indent}{example.description}")
                for code_line in example.code.splitlines():
                    lines.append(f"{indent}{code_line}")

        # Notes
        if docstring.notes:
            lines.append("")
            lines.append(f"{indent}Notes")
            lines.append(f"{indent}-----")
            for note_line in docstring.notes.splitlines():
                lines.append(f"{indent}{note_line}" if note_line else "")

        # Close
        lines.append(f'{indent}"""')

        return "\n".join(lines)


class SphinxDocstringFormatter(DocstringFormatter):
    """Sphinx-style (reStructuredText) docstring formatter.

    Example output:
        '''Summary line.

        Extended description.

        :param param1: Description of param1.
        :type param1: type
        :param param2: Description with type.
        :type param2: int
        :returns: Description of return value.
        :rtype: type
        :raises ValueError: If input is invalid.
        '''
    """

    def format(self, docstring: ParsedDocstring, indent: str = "") -> str:
        """Format a ParsedDocstring to Sphinx style."""
        lines: list[str] = []

        # Summary
        if docstring.summary:
            lines.append(f'{indent}"""')
            # Check if summary fits on one line and there's nothing else
            is_simple = (
                not docstring.description
                and not docstring.params
                and docstring.returns is None
                and not docstring.raises
                and not docstring.examples
            )
            if is_simple and len(docstring.summary) < 70:
                lines[-1] = f'{indent}"""{docstring.summary}"""'
                return lines[0]

            lines.append(f"{indent}{docstring.summary}")
        else:
            lines.append(f'{indent}"""')

        # Description
        if docstring.description:
            lines.append("")
            for desc_line in docstring.description.splitlines():
                lines.append(f"{indent}{desc_line}" if desc_line else "")

        # Parameters
        if docstring.params:
            lines.append("")
            for param in docstring.params:
                lines.append(f"{indent}:param {param.name}: {param.description}")
                if param.type_hint:
                    lines.append(f"{indent}:type {param.name}: {param.type_hint}")

        # Returns
        if docstring.returns:
            lines.append(f"{indent}:returns: {docstring.returns.description}")
            if docstring.returns.type_hint:
                lines.append(f"{indent}:rtype: {docstring.returns.type_hint}")

        # Raises
        if docstring.raises:
            for r in docstring.raises:
                lines.append(f"{indent}:raises {r.exception}: {r.description}")

        # Examples
        if docstring.examples:
            lines.append("")
            lines.append(f"{indent}.. rubric:: Examples")
            lines.append("")
            for example in docstring.examples:
                if example.description:
                    lines.append(f"{indent}{example.description}")
                lines.append(f"{indent}::")
                lines.append("")
                for code_line in example.code.splitlines():
                    lines.append(f"{indent}    {code_line}")
                lines.append("")

        # Close
        lines.append(f'{indent}"""')

        return "\n".join(lines)


def get_formatter(style: DocstringStyle | DocstringStyleType) -> DocstringFormatter:
    """Get the appropriate formatter for a docstring style.

    Parameters
    ----------
    style : DocstringStyle | str
        The docstring style ("google", "numpy", or "sphinx").

    Returns
    -------
    DocstringFormatter
        The formatter for the specified style.
    """
    if isinstance(style, str):
        style = DocstringStyle(style.lower())

    formatters = {
        DocstringStyle.GOOGLE: GoogleDocstringFormatter,
        DocstringStyle.NUMPY: NumpyDocstringFormatter,
        DocstringStyle.SPHINX: SphinxDocstringFormatter,
    }

    return formatters[style]()
