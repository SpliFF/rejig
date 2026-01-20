"""Utilities for accurate position/line number tracking using LibCST metadata."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass
class NodePosition:
    """Position information for a CST node.

    Attributes
    ----------
    name : str
        Name of the node (class name, function name, etc.).
    start_line : int
        1-indexed starting line number.
    end_line : int
        1-indexed ending line number.
    """

    name: str
    start_line: int
    end_line: int


class PositionFinder(cst.CSTVisitor):
    """Visitor to find node positions using metadata.

    Uses LibCST's PositionProvider to get accurate line numbers
    that account for decorators and leading whitespace.
    """

    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self) -> None:
        self.classes: list[NodePosition] = []
        self.functions: list[NodePosition] = []
        self.methods: dict[str, list[NodePosition]] = {}
        self._current_class: str | None = None

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        pos = self.get_metadata(PositionProvider, node)
        self.classes.append(
            NodePosition(
                name=node.name.value,
                start_line=pos.start.line,
                end_line=pos.end.line,
            )
        )
        self._current_class = node.name.value
        self.methods[node.name.value] = []
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        self._current_class = None

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        pos = self.get_metadata(PositionProvider, node)
        node_pos = NodePosition(
            name=node.name.value,
            start_line=pos.start.line,
            end_line=pos.end.line,
        )

        if self._current_class is not None:
            self.methods[self._current_class].append(node_pos)
        else:
            self.functions.append(node_pos)

        # Don't descend into nested functions
        return False


def get_node_positions(source: str) -> PositionFinder:
    """Parse source and extract positions of all classes, functions, and methods.

    Parameters
    ----------
    source : str
        Python source code to parse.

    Returns
    -------
    PositionFinder
        Visitor with populated position information.

    Examples
    --------
    >>> finder = get_node_positions(source_code)
    >>> for cls in finder.classes:
    ...     print(f"Class {cls.name} at line {cls.start_line}")
    """
    tree = cst.parse_module(source)
    wrapper = MetadataWrapper(tree)
    finder = PositionFinder()
    wrapper.visit(finder)
    return finder


def find_class_line(source: str, class_name: str) -> int | None:
    """Find the line number where a class is defined.

    Parameters
    ----------
    source : str
        Python source code.
    class_name : str
        Name of the class to find.

    Returns
    -------
    int | None
        1-indexed line number, or None if not found.
    """
    finder = get_node_positions(source)
    for cls in finder.classes:
        if cls.name == class_name:
            return cls.start_line
    return None


def find_function_line(source: str, function_name: str) -> int | None:
    """Find the line number where a module-level function is defined.

    Parameters
    ----------
    source : str
        Python source code.
    function_name : str
        Name of the function to find.

    Returns
    -------
    int | None
        1-indexed line number, or None if not found.
    """
    finder = get_node_positions(source)
    for func in finder.functions:
        if func.name == function_name:
            return func.start_line
    return None


def find_method_line(source: str, class_name: str, method_name: str) -> int | None:
    """Find the line number where a method is defined.

    Parameters
    ----------
    source : str
        Python source code.
    class_name : str
        Name of the class containing the method.
    method_name : str
        Name of the method to find.

    Returns
    -------
    int | None
        1-indexed line number, or None if not found.
    """
    finder = get_node_positions(source)
    if class_name in finder.methods:
        for method in finder.methods[class_name]:
            if method.name == method_name:
                return method.start_line
    return None


def find_all_classes(source: str) -> Sequence[NodePosition]:
    """Find all classes in the source code with their positions.

    Parameters
    ----------
    source : str
        Python source code.

    Returns
    -------
    Sequence[NodePosition]
        List of class positions.
    """
    finder = get_node_positions(source)
    return finder.classes


def find_all_functions(source: str) -> Sequence[NodePosition]:
    """Find all module-level functions in the source code with their positions.

    Parameters
    ----------
    source : str
        Python source code.

    Returns
    -------
    Sequence[NodePosition]
        List of function positions.
    """
    finder = get_node_positions(source)
    return finder.functions


def find_class_lines(source: str, class_name: str) -> tuple[int, int] | None:
    """Find the start and end line numbers where a class is defined.

    Parameters
    ----------
    source : str
        Python source code.
    class_name : str
        Name of the class to find.

    Returns
    -------
    tuple[int, int] | None
        (start_line, end_line) as 1-indexed line numbers, or None if not found.
    """
    finder = get_node_positions(source)
    for cls in finder.classes:
        if cls.name == class_name:
            return (cls.start_line, cls.end_line)
    return None


def find_function_lines(source: str, function_name: str) -> tuple[int, int] | None:
    """Find the start and end line numbers where a module-level function is defined.

    Parameters
    ----------
    source : str
        Python source code.
    function_name : str
        Name of the function to find.

    Returns
    -------
    tuple[int, int] | None
        (start_line, end_line) as 1-indexed line numbers, or None if not found.
    """
    finder = get_node_positions(source)
    for func in finder.functions:
        if func.name == function_name:
            return (func.start_line, func.end_line)
    return None


def find_method_lines(source: str, class_name: str, method_name: str) -> tuple[int, int] | None:
    """Find the start and end line numbers where a method is defined.

    Parameters
    ----------
    source : str
        Python source code.
    class_name : str
        Name of the class containing the method.
    method_name : str
        Name of the method to find.

    Returns
    -------
    tuple[int, int] | None
        (start_line, end_line) as 1-indexed line numbers, or None if not found.
    """
    finder = get_node_positions(source)
    if class_name in finder.methods:
        for method in finder.methods[class_name]:
            if method.name == method_name:
                return (method.start_line, method.end_line)
    return None
