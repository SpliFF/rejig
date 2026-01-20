"""RuffConfigTarget - Target for [tool.ruff] configuration."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rejig.core.results import Result
from rejig.project.targets.tools.base import ToolConfigTarget

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class RuffConfigTarget(ToolConfigTarget):
    """Target for Ruff linter configuration.

    Manages [tool.ruff] section in pyproject.toml.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    path : Path
        Path to pyproject.toml.

    Examples
    --------
    >>> ruff = pyproject.ruff()
    >>> ruff.set(line_length=110, target_version="py310")
    >>> ruff.select(["E", "F", "W"])
    >>> ruff.ignore(["E501"])
    """

    TOOL_NAME = "ruff"

    def __init__(self, rejig: Rejig, path: Path) -> None:
        super().__init__(rejig, path, "ruff")

    def __repr__(self) -> str:
        return f"RuffConfigTarget({self.path})"

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def line_length(self) -> int:
        """Get the line length setting."""
        return self.get_option("line-length", 88)

    @property
    def target_version(self) -> str | None:
        """Get the target Python version."""
        return self.get_option("target-version")

    @property
    def selected_rules(self) -> list[str]:
        """Get the selected lint rules."""
        return self.get_option("lint.select", self.get_option("select", []))

    @property
    def ignored_rules(self) -> list[str]:
        """Get the ignored lint rules."""
        return self.get_option("lint.ignore", self.get_option("ignore", []))

    @property
    def extend_exclude(self) -> list[str]:
        """Get the extend-exclude patterns."""
        return self.get_option("extend-exclude", [])

    # =========================================================================
    # Setters
    # =========================================================================

    def set_line_length(self, length: int) -> Result:
        """Set the maximum line length.

        Parameters
        ----------
        length : int
            Maximum line length.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set_option("line-length", length)

    def set_target_version(self, version: str) -> Result:
        """Set the target Python version.

        Parameters
        ----------
        version : str
            Python version (e.g., "py310").

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set_option("target-version", version)

    def select(self, rules: list[str]) -> Result:
        """Set the selected lint rules.

        Parameters
        ----------
        rules : list[str]
            Rule codes to enable (e.g., ["E", "F", "W"]).

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> ruff.select(["E", "F", "W", "I"])
        """
        return self.set_option("lint.select", rules)

    def ignore(self, rules: list[str]) -> Result:
        """Set the ignored lint rules.

        Parameters
        ----------
        rules : list[str]
            Rule codes to ignore (e.g., ["E501"]).

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> ruff.ignore(["E501", "E402"])
        """
        return self.set_option("lint.ignore", rules)

    def add_select(self, rule: str) -> Result:
        """Add a rule to the selected rules.

        Parameters
        ----------
        rule : str
            Rule code to add.

        Returns
        -------
        Result
            Result of the operation.
        """
        rules = self.selected_rules
        if rule not in rules:
            rules.append(rule)
            return self.select(rules)
        return Result(success=True, message=f"Rule {rule} already selected")

    def add_ignore(self, rule: str) -> Result:
        """Add a rule to the ignored rules.

        Parameters
        ----------
        rule : str
            Rule code to ignore.

        Returns
        -------
        Result
            Result of the operation.
        """
        rules = self.ignored_rules
        if rule not in rules:
            rules.append(rule)
            return self.ignore(rules)
        return Result(success=True, message=f"Rule {rule} already ignored")

    def set_extend_exclude(self, patterns: list[str]) -> Result:
        """Set the extend-exclude patterns.

        Parameters
        ----------
        patterns : list[str]
            Patterns to exclude.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.set_option("extend-exclude", patterns)

    # =========================================================================
    # Isort Configuration (Ruff has built-in isort)
    # =========================================================================

    def configure_isort(
        self,
        known_first_party: list[str] | None = None,
        known_third_party: list[str] | None = None,
        force_single_line: bool | None = None,
    ) -> Result:
        """Configure Ruff's isort-equivalent settings.

        Parameters
        ----------
        known_first_party : list[str] | None
            First-party package names.
        known_third_party : list[str] | None
            Third-party package names.
        force_single_line : bool | None
            Force single line imports.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> ruff.configure_isort(known_first_party=["mypackage"])
        """
        data = self._load()
        if data is None:
            return self._operation_failed("configure_isort", "Failed to load pyproject.toml")

        if "tool" not in data:
            data["tool"] = {}
        if "ruff" not in data["tool"]:
            data["tool"]["ruff"] = {}
        if "lint" not in data["tool"]["ruff"]:
            data["tool"]["ruff"]["lint"] = {}
        if "isort" not in data["tool"]["ruff"]["lint"]:
            data["tool"]["ruff"]["lint"]["isort"] = {}

        isort = data["tool"]["ruff"]["lint"]["isort"]

        if known_first_party is not None:
            isort["known-first-party"] = known_first_party
        if known_third_party is not None:
            isort["known-third-party"] = known_third_party
        if force_single_line is not None:
            isort["force-single-line"] = force_single_line

        return self._save(data)
