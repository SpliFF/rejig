"""Directive finder for searching across codebases."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rejig.directives.parser import DirectiveParser, DirectiveType, ParsedDirective
from rejig.directives.targets import DirectiveTarget, DirectiveTargetList

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class DirectiveFinder:
    """Find linting directives across a codebase.

    Provides methods to search for linting directive comments with various
    filtering options.

    Parameters
    ----------
    rejig : Rejig
        The Rejig instance to use for finding files.

    Examples
    --------
    >>> finder = DirectiveFinder(rj)
    >>> all_directives = finder.find_all()
    >>> type_ignores = finder.find_type_ignores()
    >>> bare_ignores = finder.find_bare_type_ignores()
    """

    def __init__(self, rejig: Rejig) -> None:
        self._rejig = rejig
        self._parser = DirectiveParser()

    def find_all(self) -> DirectiveTargetList:
        """Find all linting directives in the codebase.

        Returns
        -------
        DirectiveTargetList
            All directives found.
        """
        targets: list[DirectiveTarget] = []

        for file_path in self._rejig.files:
            results = self._parser.parse_file(file_path)
            for line_number, directive in results:
                targets.append(
                    DirectiveTarget(self._rejig, file_path, line_number, directive)
                )

        return DirectiveTargetList(self._rejig, targets)

    def find_in_file(self, file_path: Path) -> DirectiveTargetList:
        """Find all directives in a specific file.

        Parameters
        ----------
        file_path : Path
            Path to the file to search.

        Returns
        -------
        DirectiveTargetList
            Directives found in the file.
        """
        results = self._parser.parse_file(file_path)
        targets = [
            DirectiveTarget(self._rejig, file_path, line_number, directive)
            for line_number, directive in results
        ]
        return DirectiveTargetList(self._rejig, targets)

    def find_by_type(self, directive_type: DirectiveType) -> DirectiveTargetList:
        """Find directives of a specific type.

        Parameters
        ----------
        directive_type : DirectiveType
            Type of directive to find.

        Returns
        -------
        DirectiveTargetList
            Directives of the specified type.
        """
        return self.find_all().by_type(directive_type)

    def find_type_ignores(self) -> DirectiveTargetList:
        """Find all type: ignore comments.

        Returns
        -------
        DirectiveTargetList
            All type: ignore directives.
        """
        return self.find_by_type("type_ignore")

    def find_bare_type_ignores(self) -> DirectiveTargetList:
        """Find type: ignore comments without specific error codes.

        Returns
        -------
        DirectiveTargetList
            Bare type: ignore directives (without [error-code]).
        """
        return self.find_type_ignores().bare()

    def find_specific_type_ignores(self) -> DirectiveTargetList:
        """Find type: ignore comments with specific error codes.

        Returns
        -------
        DirectiveTargetList
            Type: ignore directives with specific codes.
        """
        return self.find_type_ignores().specific()

    def find_noqa_comments(self) -> DirectiveTargetList:
        """Find all noqa comments.

        Returns
        -------
        DirectiveTargetList
            All noqa directives.
        """
        return self.find_by_type("noqa")

    def find_bare_noqa(self) -> DirectiveTargetList:
        """Find noqa comments without specific error codes.

        Returns
        -------
        DirectiveTargetList
            Bare noqa directives (without specific codes).
        """
        return self.find_noqa_comments().bare()

    def find_pylint_disables(self) -> DirectiveTargetList:
        """Find all pylint: disable comments.

        Returns
        -------
        DirectiveTargetList
            All pylint: disable directives.
        """
        return self.find_by_type("pylint_disable")

    def find_fmt_directives(self) -> DirectiveTargetList:
        """Find all fmt directives (skip, off, on).

        Returns
        -------
        DirectiveTargetList
            All fmt directives.
        """
        targets: list[DirectiveTarget] = []

        for file_path in self._rejig.files:
            results = self._parser.parse_file(file_path)
            for line_number, directive in results:
                if directive.directive_type in ("fmt_skip", "fmt_off", "fmt_on"):
                    targets.append(
                        DirectiveTarget(self._rejig, file_path, line_number, directive)
                    )

        return DirectiveTargetList(self._rejig, targets)

    def find_no_cover(self) -> DirectiveTargetList:
        """Find all pragma: no cover comments.

        Returns
        -------
        DirectiveTargetList
            All no cover directives.
        """
        return self.find_by_type("no_cover")

    def find_without_reason(self) -> DirectiveTargetList:
        """Find all directives without a reason comment.

        Returns
        -------
        DirectiveTargetList
            Directives without reason comments.
        """
        return self.find_all().without_reason()

    def find_with_code(self, code: str) -> DirectiveTargetList:
        """Find all directives containing a specific error code.

        Parameters
        ----------
        code : str
            Error code to search for.

        Returns
        -------
        DirectiveTargetList
            Directives containing the specified code.
        """
        return self.find_all().with_code(code)
