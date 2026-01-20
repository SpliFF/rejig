"""Docstring parser for extracting and parsing existing docstrings.

Supports parsing Google, NumPy, and Sphinx docstring styles.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

import libcst as cst

from rejig.docstrings.styles import (
    DocstringExample,
    DocstringParam,
    DocstringRaises,
    DocstringReturns,
    DocstringStyle,
    DocstringStyleType,
    ParsedDocstring,
)

if TYPE_CHECKING:
    from pathlib import Path


class DocstringParser:
    """Parse docstrings from Python code.

    Automatically detects docstring style (Google, NumPy, or Sphinx)
    and parses into a style-agnostic ParsedDocstring object.

    Examples
    --------
    >>> parser = DocstringParser()
    >>> docstring = '''Short summary.
    ...
    ... Args:
    ...     x: The x coordinate.
    ...     y: The y coordinate.
    ...
    ... Returns:
    ...     The computed distance.
    ... '''
    >>> parsed = parser.parse(docstring)
    >>> print(parsed.summary)
    Short summary.
    >>> print(parsed.params[0].name)
    x
    """

    # Google-style section headers
    GOOGLE_SECTIONS = {
        "args", "arguments", "parameters", "params",
        "returns", "return",
        "yields", "yield",
        "raises", "raise", "except", "exceptions",
        "example", "examples",
        "note", "notes",
        "warning", "warnings",
        "see also",
        "references",
        "attributes", "attrs",
    }

    # NumPy-style section underlines
    NUMPY_UNDERLINE = re.compile(r"^-+$")

    # Sphinx-style field patterns
    SPHINX_PARAM = re.compile(r":param\s+(\w+):\s*(.*)")
    SPHINX_TYPE = re.compile(r":type\s+(\w+):\s*(.*)")
    SPHINX_RETURNS = re.compile(r":returns?:\s*(.*)")
    SPHINX_RTYPE = re.compile(r":rtype:\s*(.*)")
    SPHINX_RAISES = re.compile(r":raises?\s+(\w+):\s*(.*)")

    def parse(self, docstring: str) -> ParsedDocstring:
        """Parse a docstring into a ParsedDocstring object.

        Automatically detects the docstring style.

        Parameters
        ----------
        docstring : str
            The raw docstring text.

        Returns
        -------
        ParsedDocstring
            The parsed docstring.
        """
        if not docstring:
            return ParsedDocstring()

        # Clean up the docstring
        docstring = self._clean_docstring(docstring)

        # Detect style and parse
        style = self.detect_style(docstring)

        if style == DocstringStyle.NUMPY:
            return self._parse_numpy(docstring)
        elif style == DocstringStyle.SPHINX:
            return self._parse_sphinx(docstring)
        else:
            return self._parse_google(docstring)

    def detect_style(self, docstring: str) -> DocstringStyle:
        """Detect the docstring style.

        Parameters
        ----------
        docstring : str
            The raw docstring text.

        Returns
        -------
        DocstringStyle
            The detected style.
        """
        lines = docstring.strip().splitlines()

        # Check for NumPy-style (sections with underlines)
        for i, line in enumerate(lines):
            if self.NUMPY_UNDERLINE.match(line.strip()):
                # Check if previous line is a section header
                if i > 0 and lines[i - 1].strip().lower() in {
                    "parameters", "returns", "yields", "raises",
                    "examples", "notes", "attributes",
                }:
                    return DocstringStyle.NUMPY

        # Check for Sphinx-style (:param, :type, :returns:)
        for line in lines:
            stripped = line.strip()
            if (
                stripped.startswith(":param ")
                or stripped.startswith(":type ")
                or stripped.startswith(":returns:")
                or stripped.startswith(":return:")
                or stripped.startswith(":rtype:")
                or stripped.startswith(":raises ")
            ):
                return DocstringStyle.SPHINX

        # Check for Google-style (Args:, Returns:, etc.)
        for line in lines:
            stripped = line.strip().lower()
            if stripped.rstrip(":") in self.GOOGLE_SECTIONS and stripped.endswith(":"):
                return DocstringStyle.GOOGLE

        # Default to Google
        return DocstringStyle.GOOGLE

    def _clean_docstring(self, docstring: str) -> str:
        """Clean up a docstring by removing leading/trailing quotes and normalizing."""
        docstring = docstring.strip()

        # Remove triple quotes
        if docstring.startswith('"""') or docstring.startswith("'''"):
            docstring = docstring[3:]
        if docstring.endswith('"""') or docstring.endswith("'''"):
            docstring = docstring[:-3]

        return docstring.strip()

    def _parse_google(self, docstring: str) -> ParsedDocstring:
        """Parse a Google-style docstring."""
        result = ParsedDocstring()
        lines = docstring.splitlines()

        if not lines:
            return result

        # Find section boundaries
        sections: dict[str, tuple[int, int]] = {}
        current_section: str | None = None
        section_start = 0

        # First, extract summary (everything before first section)
        summary_lines: list[str] = []
        description_lines: list[str] = []
        in_summary = True

        for i, line in enumerate(lines):
            stripped = line.strip().lower()
            section_name = stripped.rstrip(":")

            if section_name in self.GOOGLE_SECTIONS and stripped.endswith(":"):
                if current_section:
                    sections[current_section] = (section_start, i)
                current_section = section_name
                section_start = i + 1
            elif current_section is None:
                if in_summary and line.strip():
                    summary_lines.append(line.strip())
                    # Check if next line is empty (end of summary)
                    if i + 1 < len(lines) and not lines[i + 1].strip():
                        in_summary = False
                elif not in_summary and line.strip():
                    description_lines.append(line.strip())

        # Close last section
        if current_section:
            sections[current_section] = (section_start, len(lines))

        result.summary = " ".join(summary_lines)
        result.description = "\n".join(description_lines)

        # Parse each section
        for section, (start, end) in sections.items():
            section_lines = lines[start:end]
            section_text = "\n".join(section_lines)

            if section in ("args", "arguments", "parameters", "params"):
                result.params = self._parse_google_params(section_lines)
            elif section in ("returns", "return"):
                result.returns = self._parse_google_returns(section_lines)
            elif section in ("yields", "yield"):
                result.yields = self._parse_google_returns(section_lines)
            elif section in ("raises", "raise", "except", "exceptions"):
                result.raises = self._parse_google_raises(section_lines)
            elif section in ("example", "examples"):
                result.examples = self._parse_google_examples(section_lines)
            elif section in ("note", "notes"):
                result.notes = self._strip_section_content(section_lines)
            elif section in ("attributes", "attrs"):
                result.attributes = self._parse_google_params(section_lines)

        return result

    def _parse_google_params(self, lines: list[str]) -> list[DocstringParam]:
        """Parse Google-style parameter entries."""
        params: list[DocstringParam] = []
        current_param: DocstringParam | None = None

        # Pattern: name (type): description OR name: description
        param_pattern = re.compile(r"^\s*(\w+)\s*(?:\(([^)]+)\))?\s*:\s*(.*)")

        for line in lines:
            match = param_pattern.match(line)
            if match:
                if current_param:
                    params.append(current_param)
                name, type_hint, desc = match.groups()
                current_param = DocstringParam(
                    name=name,
                    type_hint=type_hint or "",
                    description=desc.strip(),
                )
            elif current_param and line.strip():
                # Continuation line
                current_param.description += " " + line.strip()

        if current_param:
            params.append(current_param)

        return params

    def _parse_google_returns(self, lines: list[str]) -> DocstringReturns | None:
        """Parse Google-style returns section."""
        if not lines:
            return None

        # Pattern: type: description OR just description
        first_line = lines[0].strip()
        type_pattern = re.compile(r"^(\w+(?:\[.*\])?)\s*:\s*(.*)")
        match = type_pattern.match(first_line)

        if match:
            type_hint, desc = match.groups()
            description_parts = [desc]
        else:
            type_hint = ""
            description_parts = [first_line]

        # Add continuation lines
        for line in lines[1:]:
            if line.strip():
                description_parts.append(line.strip())

        return DocstringReturns(
            description=" ".join(description_parts),
            type_hint=type_hint,
        )

    def _parse_google_raises(self, lines: list[str]) -> list[DocstringRaises]:
        """Parse Google-style raises section."""
        raises: list[DocstringRaises] = []
        current: DocstringRaises | None = None

        # Pattern: ExceptionType: description
        raises_pattern = re.compile(r"^\s*(\w+)\s*:\s*(.*)")

        for line in lines:
            match = raises_pattern.match(line)
            if match:
                if current:
                    raises.append(current)
                exception, desc = match.groups()
                current = DocstringRaises(
                    exception=exception,
                    description=desc.strip(),
                )
            elif current and line.strip():
                current.description += " " + line.strip()

        if current:
            raises.append(current)

        return raises

    def _parse_google_examples(self, lines: list[str]) -> list[DocstringExample]:
        """Parse Google-style examples section."""
        examples: list[DocstringExample] = []
        current_code: list[str] = []
        current_desc = ""

        for line in lines:
            stripped = line.strip()
            if stripped.startswith(">>>"):
                current_code.append(stripped)
            elif current_code:
                # End of code block
                if stripped:
                    current_code.append(stripped)
                else:
                    examples.append(DocstringExample(
                        code="\n".join(current_code),
                        description=current_desc,
                    ))
                    current_code = []
                    current_desc = ""
            elif stripped:
                current_desc = stripped

        if current_code:
            examples.append(DocstringExample(
                code="\n".join(current_code),
                description=current_desc,
            ))

        return examples

    def _strip_section_content(self, lines: list[str]) -> str:
        """Strip and join section content lines."""
        return "\n".join(line.strip() for line in lines if line.strip())

    def _parse_numpy(self, docstring: str) -> ParsedDocstring:
        """Parse a NumPy-style docstring."""
        result = ParsedDocstring()
        lines = docstring.splitlines()

        if not lines:
            return result

        # Find sections
        sections: dict[str, list[str]] = {}
        current_section: str | None = None
        current_lines: list[str] = []
        summary_lines: list[str] = []
        description_lines: list[str] = []

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Check for section header
            if i + 1 < len(lines) and self.NUMPY_UNDERLINE.match(lines[i + 1].strip()):
                # Save previous section
                if current_section:
                    sections[current_section] = current_lines
                current_section = stripped.lower()
                current_lines = []
                i += 2  # Skip header and underline
                continue

            if current_section:
                current_lines.append(line)
            else:
                # Before any section - summary/description
                if stripped:
                    if not summary_lines:
                        summary_lines.append(stripped)
                    elif summary_lines and not description_lines:
                        # Empty line after summary indicates description
                        description_lines.append(stripped)
                    else:
                        description_lines.append(stripped)
                elif summary_lines and not description_lines:
                    # First empty line after summary
                    pass

            i += 1

        # Save last section
        if current_section:
            sections[current_section] = current_lines

        result.summary = " ".join(summary_lines)
        result.description = "\n".join(description_lines)

        # Parse sections
        if "parameters" in sections:
            result.params = self._parse_numpy_params(sections["parameters"])
        if "returns" in sections:
            result.returns = self._parse_numpy_returns(sections["returns"])
        if "yields" in sections:
            result.yields = self._parse_numpy_returns(sections["yields"])
        if "raises" in sections:
            result.raises = self._parse_numpy_raises(sections["raises"])
        if "examples" in sections:
            result.examples = self._parse_numpy_examples(sections["examples"])
        if "notes" in sections:
            result.notes = self._strip_section_content(sections["notes"])
        if "attributes" in sections:
            result.attributes = self._parse_numpy_params(sections["attributes"])

        return result

    def _parse_numpy_params(self, lines: list[str]) -> list[DocstringParam]:
        """Parse NumPy-style parameter entries."""
        params: list[DocstringParam] = []
        current_param: DocstringParam | None = None

        # Pattern: name : type OR name
        param_pattern = re.compile(r"^(\w+)\s*(?::\s*(.+))?$")

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Check if this is a parameter definition (not indented or first line)
            if not line.startswith(" ") or not current_param:
                match = param_pattern.match(stripped)
                if match:
                    if current_param:
                        params.append(current_param)
                    name, type_hint = match.groups()
                    current_param = DocstringParam(
                        name=name,
                        type_hint=type_hint or "",
                        description="",
                    )
            elif current_param:
                # Description line (indented)
                if current_param.description:
                    current_param.description += " " + stripped
                else:
                    current_param.description = stripped

        if current_param:
            params.append(current_param)

        return params

    def _parse_numpy_returns(self, lines: list[str]) -> DocstringReturns | None:
        """Parse NumPy-style returns section."""
        if not lines:
            return None

        type_hint = ""
        description_parts: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if not type_hint and not line.startswith(" "):
                # First non-indented line is the type
                type_hint = stripped
            else:
                description_parts.append(stripped)

        return DocstringReturns(
            description=" ".join(description_parts),
            type_hint=type_hint,
        )

    def _parse_numpy_raises(self, lines: list[str]) -> list[DocstringRaises]:
        """Parse NumPy-style raises section."""
        raises: list[DocstringRaises] = []
        current: DocstringRaises | None = None

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if not line.startswith(" "):
                # Exception type
                if current:
                    raises.append(current)
                current = DocstringRaises(exception=stripped, description="")
            elif current:
                if current.description:
                    current.description += " " + stripped
                else:
                    current.description = stripped

        if current:
            raises.append(current)

        return raises

    def _parse_numpy_examples(self, lines: list[str]) -> list[DocstringExample]:
        """Parse NumPy-style examples section."""
        return self._parse_google_examples(lines)

    def _parse_sphinx(self, docstring: str) -> ParsedDocstring:
        """Parse a Sphinx-style docstring."""
        result = ParsedDocstring()
        lines = docstring.splitlines()

        if not lines:
            return result

        summary_lines: list[str] = []
        description_lines: list[str] = []
        params: dict[str, DocstringParam] = {}
        in_summary = True

        for line in lines:
            stripped = line.strip()

            # Check for Sphinx directives
            param_match = self.SPHINX_PARAM.match(stripped)
            type_match = self.SPHINX_TYPE.match(stripped)
            returns_match = self.SPHINX_RETURNS.match(stripped)
            rtype_match = self.SPHINX_RTYPE.match(stripped)
            raises_match = self.SPHINX_RAISES.match(stripped)

            if param_match:
                name, desc = param_match.groups()
                if name not in params:
                    params[name] = DocstringParam(name=name)
                params[name].description = desc
                in_summary = False
            elif type_match:
                name, type_hint = type_match.groups()
                if name not in params:
                    params[name] = DocstringParam(name=name)
                params[name].type_hint = type_hint
                in_summary = False
            elif returns_match:
                if result.returns is None:
                    result.returns = DocstringReturns(description="")
                result.returns.description = returns_match.group(1)
                in_summary = False
            elif rtype_match:
                if result.returns is None:
                    result.returns = DocstringReturns(description="")
                result.returns.type_hint = rtype_match.group(1)
                in_summary = False
            elif raises_match:
                exc, desc = raises_match.groups()
                result.raises.append(DocstringRaises(exception=exc, description=desc))
                in_summary = False
            elif stripped:
                if in_summary:
                    summary_lines.append(stripped)
                    # Check if next non-empty line starts a directive
                else:
                    description_lines.append(stripped)
            elif summary_lines:
                in_summary = False

        result.summary = " ".join(summary_lines)
        result.description = "\n".join(description_lines)
        result.params = list(params.values())

        return result


def extract_docstring(node: cst.FunctionDef | cst.ClassDef) -> str | None:
    """Extract the docstring from a function or class node.

    Parameters
    ----------
    node : cst.FunctionDef | cst.ClassDef
        The CST node to extract from.

    Returns
    -------
    str | None
        The docstring text, or None if no docstring.
    """
    body = node.body
    if isinstance(body, cst.IndentedBlock):
        first_stmt = body.body[0] if body.body else None
        if isinstance(first_stmt, cst.SimpleStatementLine):
            if first_stmt.body and isinstance(first_stmt.body[0], cst.Expr):
                expr = first_stmt.body[0].value
                if isinstance(expr, (cst.SimpleString, cst.ConcatenatedString)):
                    return _extract_string_value(expr)
    return None


def _extract_string_value(node: cst.SimpleString | cst.ConcatenatedString) -> str:
    """Extract the string value from a string node."""
    if isinstance(node, cst.SimpleString):
        # Remove quotes
        value = node.value
        if value.startswith('"""') or value.startswith("'''"):
            return value[3:-3]
        elif value.startswith('"') or value.startswith("'"):
            return value[1:-1]
        return value
    elif isinstance(node, cst.ConcatenatedString):
        parts = []
        for part in node.left, node.right:
            if isinstance(part, cst.SimpleString):
                parts.append(_extract_string_value(part))
            elif isinstance(part, cst.ConcatenatedString):
                parts.append(_extract_string_value(part))
        return "".join(parts)
    return ""


def has_docstring(node: cst.FunctionDef | cst.ClassDef) -> bool:
    """Check if a function or class has a docstring.

    Parameters
    ----------
    node : cst.FunctionDef | cst.ClassDef
        The CST node to check.

    Returns
    -------
    bool
        True if the node has a docstring.
    """
    return extract_docstring(node) is not None
