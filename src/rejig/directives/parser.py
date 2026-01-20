"""Directive parser for extracting linting directives from Python code.

Parses:
- type: ignore[error-code]  # mypy
- noqa: E501, F401  # flake8, ruff
- pylint: disable=error-code  # pylint
- fmt: skip / fmt: off / fmt: on  # black
- pragma: no cover  # coverage
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig

DirectiveType = Literal[
    "type_ignore",
    "noqa",
    "pylint_disable",
    "pylint_enable",
    "fmt_skip",
    "fmt_off",
    "fmt_on",
    "no_cover",
]

# All recognized directive types
DIRECTIVE_TYPES: tuple[DirectiveType, ...] = (
    "type_ignore",
    "noqa",
    "pylint_disable",
    "pylint_enable",
    "fmt_skip",
    "fmt_off",
    "fmt_on",
    "no_cover",
)


@dataclass
class ParsedDirective:
    """A parsed linting directive from source code.

    Attributes
    ----------
    directive_type : DirectiveType
        Type of directive (type_ignore, noqa, etc.).
    codes : list[str]
        Error codes associated with the directive.
    reason : str | None
        Optional reason/comment for the directive.
    raw_text : str
        The raw directive text as found in the source.
    start_col : int
        Column offset where the directive starts in the line.
    end_col : int
        Column offset where the directive ends in the line.
    """

    directive_type: DirectiveType
    codes: list[str] = field(default_factory=list)
    reason: str | None = None
    raw_text: str = ""
    start_col: int = 0
    end_col: int = 0

    @property
    def is_bare(self) -> bool:
        """Check if this is a bare directive (no specific codes)."""
        return len(self.codes) == 0

    @property
    def is_specific(self) -> bool:
        """Check if this directive specifies error codes."""
        return len(self.codes) > 0


class DirectiveParser:
    """Parse linting directives from Python source code.

    Recognizes various directive formats:
    - # type: ignore
    - # type: ignore[arg-type]
    - # type: ignore[arg-type, return-value]  # reason
    - # noqa
    - # noqa: E501
    - # noqa: E501, F401
    - # pylint: disable=line-too-long
    - # pylint: disable=line-too-long,too-many-arguments
    - # fmt: skip
    - # fmt: off
    - # fmt: on
    - # pragma: no cover

    Examples
    --------
    >>> parser = DirectiveParser()
    >>> directive = parser.parse_line("x = 1  # type: ignore[arg-type]")
    >>> print(directive.directive_type)
    type_ignore
    >>> print(directive.codes)
    ['arg-type']
    """

    # Pattern for type: ignore comments
    TYPE_IGNORE_PATTERN = re.compile(
        r"#\s*type:\s*ignore"
        r"(?:\[(?P<codes>[^\]]+)\])?"
        r"(?:\s*#\s*(?P<reason>.+))?"
    )

    # Pattern for noqa comments
    NOQA_PATTERN = re.compile(
        r"#\s*noqa"
        r"(?::\s*(?P<codes>[A-Z0-9,\s]+))?"
        r"(?:\s*#\s*(?P<reason>.+))?",
        re.IGNORECASE,
    )

    # Pattern for pylint: disable comments
    PYLINT_DISABLE_PATTERN = re.compile(
        r"#\s*pylint:\s*disable\s*=\s*(?P<codes>[a-z0-9-,\s]+)"
        r"(?:\s*#\s*(?P<reason>.+))?",
        re.IGNORECASE,
    )

    # Pattern for pylint: enable comments
    PYLINT_ENABLE_PATTERN = re.compile(
        r"#\s*pylint:\s*enable\s*=\s*(?P<codes>[a-z0-9-,\s]+)",
        re.IGNORECASE,
    )

    # Pattern for fmt: skip comments
    FMT_SKIP_PATTERN = re.compile(r"#\s*fmt:\s*skip", re.IGNORECASE)

    # Pattern for fmt: off comments
    FMT_OFF_PATTERN = re.compile(r"#\s*fmt:\s*off", re.IGNORECASE)

    # Pattern for fmt: on comments
    FMT_ON_PATTERN = re.compile(r"#\s*fmt:\s*on", re.IGNORECASE)

    # Pattern for pragma: no cover comments
    NO_COVER_PATTERN = re.compile(r"#\s*pragma:\s*no\s*cover", re.IGNORECASE)

    def parse_line(self, line: str) -> list[ParsedDirective]:
        """Parse all directives from a single line.

        Parameters
        ----------
        line : str
            The line to parse.

        Returns
        -------
        list[ParsedDirective]
            List of parsed directives found in the line.
        """
        directives: list[ParsedDirective] = []

        # Check for type: ignore
        match = self.TYPE_IGNORE_PATTERN.search(line)
        if match:
            codes_str = match.group("codes")
            codes = [c.strip() for c in codes_str.split(",")] if codes_str else []
            reason = match.group("reason")
            directives.append(
                ParsedDirective(
                    directive_type="type_ignore",
                    codes=codes,
                    reason=reason.strip() if reason else None,
                    raw_text=match.group(0),
                    start_col=match.start(),
                    end_col=match.end(),
                )
            )

        # Check for noqa
        match = self.NOQA_PATTERN.search(line)
        if match:
            codes_str = match.group("codes")
            codes = [c.strip().upper() for c in codes_str.split(",")] if codes_str else []
            reason = match.group("reason")
            directives.append(
                ParsedDirective(
                    directive_type="noqa",
                    codes=codes,
                    reason=reason.strip() if reason else None,
                    raw_text=match.group(0),
                    start_col=match.start(),
                    end_col=match.end(),
                )
            )

        # Check for pylint: disable
        match = self.PYLINT_DISABLE_PATTERN.search(line)
        if match:
            codes_str = match.group("codes")
            codes = [c.strip() for c in codes_str.split(",")]
            reason = match.group("reason")
            directives.append(
                ParsedDirective(
                    directive_type="pylint_disable",
                    codes=codes,
                    reason=reason.strip() if reason else None,
                    raw_text=match.group(0),
                    start_col=match.start(),
                    end_col=match.end(),
                )
            )

        # Check for pylint: enable
        match = self.PYLINT_ENABLE_PATTERN.search(line)
        if match:
            codes_str = match.group("codes")
            codes = [c.strip() for c in codes_str.split(",")]
            directives.append(
                ParsedDirective(
                    directive_type="pylint_enable",
                    codes=codes,
                    raw_text=match.group(0),
                    start_col=match.start(),
                    end_col=match.end(),
                )
            )

        # Check for fmt: skip
        match = self.FMT_SKIP_PATTERN.search(line)
        if match:
            directives.append(
                ParsedDirective(
                    directive_type="fmt_skip",
                    raw_text=match.group(0),
                    start_col=match.start(),
                    end_col=match.end(),
                )
            )

        # Check for fmt: off
        match = self.FMT_OFF_PATTERN.search(line)
        if match:
            directives.append(
                ParsedDirective(
                    directive_type="fmt_off",
                    raw_text=match.group(0),
                    start_col=match.start(),
                    end_col=match.end(),
                )
            )

        # Check for fmt: on
        match = self.FMT_ON_PATTERN.search(line)
        if match:
            directives.append(
                ParsedDirective(
                    directive_type="fmt_on",
                    raw_text=match.group(0),
                    start_col=match.start(),
                    end_col=match.end(),
                )
            )

        # Check for pragma: no cover
        match = self.NO_COVER_PATTERN.search(line)
        if match:
            directives.append(
                ParsedDirective(
                    directive_type="no_cover",
                    raw_text=match.group(0),
                    start_col=match.start(),
                    end_col=match.end(),
                )
            )

        return directives

    def parse_file(self, file_path: Path) -> list[tuple[int, ParsedDirective]]:
        """Parse all directives from a file.

        Parameters
        ----------
        file_path : Path
            Path to the file to parse.

        Returns
        -------
        list[tuple[int, ParsedDirective]]
            List of (line_number, directive) tuples.
        """
        results: list[tuple[int, ParsedDirective]] = []

        if not file_path.exists():
            return results

        try:
            content = file_path.read_text()
            for line_number, line in enumerate(content.splitlines(), 1):
                directives = self.parse_line(line)
                for directive in directives:
                    results.append((line_number, directive))
        except Exception:
            pass

        return results

    def parse_content(self, content: str) -> list[tuple[int, ParsedDirective]]:
        """Parse all directives from content string.

        Parameters
        ----------
        content : str
            The content to parse.

        Returns
        -------
        list[tuple[int, ParsedDirective]]
            List of (line_number, directive) tuples.
        """
        results: list[tuple[int, ParsedDirective]] = []

        for line_number, line in enumerate(content.splitlines(), 1):
            directives = self.parse_line(line)
            for directive in directives:
                results.append((line_number, directive))

        return results

    @staticmethod
    def has_type_ignore(line: str) -> bool:
        """Check if a line has a type: ignore comment."""
        return "# type: ignore" in line or "#type: ignore" in line

    @staticmethod
    def has_noqa(line: str) -> bool:
        """Check if a line has a noqa comment."""
        return bool(re.search(r"#\s*noqa", line, re.IGNORECASE))

    @staticmethod
    def has_pylint_disable(line: str) -> bool:
        """Check if a line has a pylint: disable comment."""
        return bool(re.search(r"#\s*pylint:\s*disable", line, re.IGNORECASE))

    @staticmethod
    def has_fmt_skip(line: str) -> bool:
        """Check if a line has a fmt: skip comment."""
        return bool(re.search(r"#\s*fmt:\s*skip", line, re.IGNORECASE))

    @staticmethod
    def has_no_cover(line: str) -> bool:
        """Check if a line has a pragma: no cover comment."""
        return bool(re.search(r"#\s*pragma:\s*no\s*cover", line, re.IGNORECASE))

    @staticmethod
    def remove_directive(line: str, directive_type: DirectiveType) -> str:
        """Remove a specific directive from a line.

        Parameters
        ----------
        line : str
            The line to modify.
        directive_type : DirectiveType
            The type of directive to remove.

        Returns
        -------
        str
            The line with the directive removed.
        """
        patterns = {
            "type_ignore": r"\s*#\s*type:\s*ignore(?:\[[^\]]*\])?(?:\s*#\s*[^\n]*)?",
            "noqa": r"\s*#\s*noqa(?::\s*[A-Z0-9,\s]+)?(?:\s*#\s*[^\n]*)?",
            "pylint_disable": r"\s*#\s*pylint:\s*disable\s*=\s*[a-z0-9-,\s]+(?:\s*#\s*[^\n]*)?",
            "pylint_enable": r"\s*#\s*pylint:\s*enable\s*=\s*[a-z0-9-,\s]+",
            "fmt_skip": r"\s*#\s*fmt:\s*skip",
            "fmt_off": r"\s*#\s*fmt:\s*off",
            "fmt_on": r"\s*#\s*fmt:\s*on",
            "no_cover": r"\s*#\s*pragma:\s*no\s*cover",
        }

        pattern = patterns.get(directive_type)
        if pattern:
            return re.sub(pattern, "", line, flags=re.IGNORECASE).rstrip()

        return line
