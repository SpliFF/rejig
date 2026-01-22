"""Shared utilities for parameter manipulation transformers.

This module provides common functionality for adding, removing, and
reordering function/method parameters, particularly comma handling.
"""
from __future__ import annotations

import libcst as cst


def fix_param_commas(
    params: list[cst.Param],
    has_kwonly: bool = False,
    has_star_kwarg: bool = False,
    has_star_arg: bool = False,
) -> list[cst.Param]:
    """Fix comma placement on a list of parameters.

    Ensures proper comma placement after parameter modifications:
    - All params except the last need commas if followed by more params
    - Last param needs comma only if followed by kwonly_params, star_arg, or star_kwarg

    Parameters
    ----------
    params : list[cst.Param]
        List of parameters to fix commas on.
    has_kwonly : bool
        Whether there are keyword-only parameters after these params.
    has_star_kwarg : bool
        Whether there is a **kwargs parameter after these params.
    has_star_arg : bool
        Whether there is a *args or bare * after these params.

    Returns
    -------
    list[cst.Param]
        Parameters with corrected comma placement.

    Examples
    --------
    >>> fixed = fix_param_commas(params, has_kwonly=True)
    """
    if not params:
        return params

    fixed_params: list[cst.Param] = []
    has_more_after = has_kwonly or has_star_kwarg or has_star_arg

    for i, param in enumerate(params):
        is_last = i == len(params) - 1

        if not is_last:
            # Not the last param - ensure it has a comma
            if isinstance(param.comma, cst.MaybeSentinel):
                param = param.with_changes(
                    comma=cst.Comma(whitespace_after=cst.SimpleWhitespace(" "))
                )
        else:
            # Last param - add comma only if something follows
            if has_more_after:
                if isinstance(param.comma, cst.MaybeSentinel):
                    param = param.with_changes(
                        comma=cst.Comma(whitespace_after=cst.SimpleWhitespace(" "))
                    )
            else:
                # Remove comma from last param
                param = param.with_changes(comma=cst.MaybeSentinel.DEFAULT)

        fixed_params.append(param)

    return fixed_params


def fix_kwonly_commas(
    kwonly_params: list[cst.Param],
    has_star_kwarg: bool = False,
) -> list[cst.Param]:
    """Fix comma placement on keyword-only parameters.

    Parameters
    ----------
    kwonly_params : list[cst.Param]
        List of keyword-only parameters.
    has_star_kwarg : bool
        Whether there is a **kwargs parameter after these params.

    Returns
    -------
    list[cst.Param]
        Parameters with corrected comma placement.
    """
    if not kwonly_params:
        return kwonly_params

    fixed_params: list[cst.Param] = []

    for i, param in enumerate(kwonly_params):
        is_last = i == len(kwonly_params) - 1

        if not is_last:
            # Not the last param - ensure it has a comma
            if isinstance(param.comma, cst.MaybeSentinel):
                param = param.with_changes(
                    comma=cst.Comma(whitespace_after=cst.SimpleWhitespace(" "))
                )
        else:
            # Last param - add comma only if star_kwarg follows
            if has_star_kwarg:
                if isinstance(param.comma, cst.MaybeSentinel):
                    param = param.with_changes(
                        comma=cst.Comma(whitespace_after=cst.SimpleWhitespace(" "))
                    )
            else:
                param = param.with_changes(comma=cst.MaybeSentinel.DEFAULT)

        fixed_params.append(param)

    return fixed_params


def ensure_trailing_comma(param: cst.Param) -> cst.Param:
    """Ensure a parameter has a trailing comma.

    Parameters
    ----------
    param : cst.Param
        The parameter to modify.

    Returns
    -------
    cst.Param
        Parameter with trailing comma.
    """
    if isinstance(param.comma, cst.MaybeSentinel):
        return param.with_changes(
            comma=cst.Comma(whitespace_after=cst.SimpleWhitespace(" "))
        )
    return param


def remove_trailing_comma(param: cst.Param) -> cst.Param:
    """Remove trailing comma from a parameter.

    Parameters
    ----------
    param : cst.Param
        The parameter to modify.

    Returns
    -------
    cst.Param
        Parameter without trailing comma.
    """
    return param.with_changes(comma=cst.MaybeSentinel.DEFAULT)


def is_self_or_cls(param: cst.Param) -> bool:
    """Check if a parameter is 'self' or 'cls'.

    Parameters
    ----------
    param : cst.Param
        The parameter to check.

    Returns
    -------
    bool
        True if the parameter is 'self' or 'cls'.
    """
    return param.name.value in ("self", "cls")


def find_insert_position(
    params: list[cst.Param],
    position: str = "end",
) -> int:
    """Find the position to insert a new parameter.

    Parameters
    ----------
    params : list[cst.Param]
        Existing parameters.
    position : str
        Where to insert: "start" (after self/cls) or "end".

    Returns
    -------
    int
        Index position for insertion.
    """
    if position == "start":
        # Insert after self/cls if present
        if params and is_self_or_cls(params[0]):
            return 1
        return 0
    else:
        return len(params)


class ClassContextTracker:
    """Track nested class context in CST transformers.

    Use this helper to properly handle nested classes with the same name.
    Instead of a boolean flag, this uses a depth counter.

    Examples
    --------
    >>> class MyTransformer(cst.CSTTransformer):
    ...     def __init__(self, target_class: str):
    ...         self._tracker = ClassContextTracker(target_class)
    ...
    ...     def visit_ClassDef(self, node):
    ...         self._tracker.enter(node.name.value)
    ...         return True
    ...
    ...     def leave_ClassDef(self, original, updated):
    ...         self._tracker.exit(original.name.value)
    ...         return updated
    ...
    ...     @property
    ...     def in_target_class(self):
    ...         return self._tracker.is_in_target
    """

    def __init__(self, target_name: str) -> None:
        self.target_name = target_name
        self._depth = 0

    def enter(self, class_name: str) -> None:
        """Call when entering a class definition."""
        if class_name == self.target_name:
            self._depth += 1

    def exit(self, class_name: str) -> None:
        """Call when leaving a class definition."""
        if class_name == self.target_name:
            self._depth -= 1

    @property
    def is_in_target(self) -> bool:
        """Check if currently in the target class (depth == 1)."""
        return self._depth == 1

    @property
    def depth(self) -> int:
        """Current nesting depth."""
        return self._depth


class FunctionContextTracker:
    """Track nested function context in CST transformers.

    Similar to ClassContextTracker but for functions, with support
    for tracking a specific target function.

    Examples
    --------
    >>> tracker = FunctionContextTracker("my_function")
    >>> # In visit_FunctionDef:
    >>> tracker.enter(node.name.value)
    >>> # In leave_FunctionDef:
    >>> tracker.exit(original.name.value)
    """

    def __init__(self, target_name: str) -> None:
        self.target_name = target_name
        self._depth = 0
        self._target_depth = 0

    def enter(self, function_name: str) -> None:
        """Call when entering a function definition."""
        self._depth += 1
        if function_name == self.target_name and self._target_depth == 0:
            self._target_depth = self._depth

    def exit(self, function_name: str) -> None:
        """Call when leaving a function definition."""
        if self._depth == self._target_depth:
            self._target_depth = 0
        self._depth -= 1

    @property
    def is_in_target(self) -> bool:
        """Check if currently directly in target function (not nested)."""
        return self._target_depth > 0 and self._depth == self._target_depth

    @property
    def is_in_any_nested(self) -> bool:
        """Check if currently in any function within the target."""
        return self._target_depth > 0 and self._depth >= self._target_depth

    @property
    def depth(self) -> int:
        """Current function nesting depth."""
        return self._depth
