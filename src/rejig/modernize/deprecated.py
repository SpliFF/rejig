"""Deprecated code detection and replacement.

Finds and replaces deprecated API patterns:
- collections.MutableMapping → collections.abc.MutableMapping
- assertEquals → assertEqual
- asyncio.get_event_loop() → asyncio.get_running_loop() (in async context)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


@dataclass
class DeprecatedUsage:
    """Represents a deprecated API usage found in code."""

    file_path: Path
    line_number: int
    old_pattern: str
    suggested_replacement: str
    category: str  # "collections", "unittest", "asyncio", etc.


# Mapping of deprecated imports to their replacements
DEPRECATED_IMPORTS = {
    # collections module deprecations (Python 3.3+)
    "collections.Awaitable": "collections.abc.Awaitable",
    "collections.Coroutine": "collections.abc.Coroutine",
    "collections.AsyncIterable": "collections.abc.AsyncIterable",
    "collections.AsyncIterator": "collections.abc.AsyncIterator",
    "collections.AsyncGenerator": "collections.abc.AsyncGenerator",
    "collections.Hashable": "collections.abc.Hashable",
    "collections.Iterable": "collections.abc.Iterable",
    "collections.Iterator": "collections.abc.Iterator",
    "collections.Generator": "collections.abc.Generator",
    "collections.Reversible": "collections.abc.Reversible",
    "collections.Container": "collections.abc.Container",
    "collections.Collection": "collections.abc.Collection",
    "collections.Callable": "collections.abc.Callable",
    "collections.Set": "collections.abc.Set",
    "collections.MutableSet": "collections.abc.MutableSet",
    "collections.Mapping": "collections.abc.Mapping",
    "collections.MutableMapping": "collections.abc.MutableMapping",
    "collections.MappingView": "collections.abc.MappingView",
    "collections.KeysView": "collections.abc.KeysView",
    "collections.ItemsView": "collections.abc.ItemsView",
    "collections.ValuesView": "collections.abc.ValuesView",
    "collections.Sequence": "collections.abc.Sequence",
    "collections.MutableSequence": "collections.abc.MutableSequence",
    "collections.ByteString": "collections.abc.ByteString",
    # typing module deprecations (Python 3.9+)
    "typing.List": "list",
    "typing.Dict": "dict",
    "typing.Set": "set",
    "typing.FrozenSet": "frozenset",
    "typing.Tuple": "tuple",
    "typing.Type": "type",
    # Other common deprecations
    "imp": "importlib",
    "optparse": "argparse",
    "cgi.escape": "html.escape",
    "pipes.quote": "shlex.quote",
    "platform.linux_distribution": "distro.linux_distribution",
}

# Deprecated method names and their replacements
DEPRECATED_METHODS = {
    # unittest assertions
    "assertEquals": "assertEqual",
    "assertNotEquals": "assertNotEqual",
    "assertAlmostEquals": "assertAlmostEqual",
    "assertNotAlmostEquals": "assertNotAlmostEqual",
    "assertRegexpMatches": "assertRegex",
    "assertNotRegexpMatches": "assertNotRegex",
    "assertRaisesRegexp": "assertRaisesRegex",
    "assertItemsEqual": "assertCountEqual",
    "failUnlessEqual": "assertEqual",
    "failIfEqual": "assertNotEqual",
    "failUnless": "assertTrue",
    "failIf": "assertFalse",
    "failUnlessRaises": "assertRaises",
    "failUnlessAlmostEqual": "assertAlmostEqual",
    "failIfAlmostEqual": "assertNotAlmostEqual",
    # asyncio deprecations
    "asyncio.get_event_loop": "asyncio.get_running_loop",
    # logging deprecations
    "logger.warn": "logger.warning",
    "logging.warn": "logging.warning",
}


class DeprecatedUsageFinder(cst.CSTVisitor):
    """Find deprecated API usage in code."""

    def __init__(self, file_path: Path) -> None:
        super().__init__()
        self.file_path = file_path
        self.usages: list[DeprecatedUsage] = []
        self._metadata_wrapper = None

    def visit_Attribute(self, node: cst.Attribute) -> bool:
        """Check for deprecated attribute access."""
        # Build the full attribute path
        path = self._get_attribute_path(node)
        if path is None:
            return True

        # Check against deprecated imports
        if path in DEPRECATED_IMPORTS:
            self.usages.append(
                DeprecatedUsage(
                    file_path=self.file_path,
                    line_number=self._get_line_number(node),
                    old_pattern=path,
                    suggested_replacement=DEPRECATED_IMPORTS[path],
                    category="import",
                )
            )

        # Check for deprecated methods
        for old, new in DEPRECATED_METHODS.items():
            if path.endswith("." + old) or path == old:
                self.usages.append(
                    DeprecatedUsage(
                        file_path=self.file_path,
                        line_number=self._get_line_number(node),
                        old_pattern=old,
                        suggested_replacement=new,
                        category="method",
                    )
                )
                break

        return True

    def visit_Name(self, node: cst.Name) -> bool:
        """Check for deprecated function names."""
        name = node.value

        # Check method names directly
        if name in DEPRECATED_METHODS:
            self.usages.append(
                DeprecatedUsage(
                    file_path=self.file_path,
                    line_number=self._get_line_number(node),
                    old_pattern=name,
                    suggested_replacement=DEPRECATED_METHODS[name],
                    category="method",
                )
            )

        return True

    def _get_attribute_path(self, node: cst.Attribute) -> str | None:
        """Get the full dotted path of an attribute access."""
        parts = [node.attr.value]
        current = node.value

        while isinstance(current, cst.Attribute):
            parts.append(current.attr.value)
            current = current.value

        if isinstance(current, cst.Name):
            parts.append(current.value)
            return ".".join(reversed(parts))

        return None

    def _get_line_number(self, node: cst.CSTNode) -> int:
        """Get the line number for a node (placeholder - needs metadata)."""
        # Without metadata wrapper, we can't get accurate line numbers
        # Return 0 as placeholder
        return 0


class ReplaceDeprecatedTransformer(cst.CSTTransformer):
    """Replace deprecated API usage with modern equivalents."""

    def __init__(self, replacements: dict[str, str] | None = None) -> None:
        super().__init__()
        self.replacements = replacements or {**DEPRECATED_IMPORTS, **DEPRECATED_METHODS}
        self.changed = False

    def leave_Attribute(
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.BaseExpression:
        """Replace deprecated attribute access."""
        path = self._get_attribute_path(updated_node)
        if path is None:
            return updated_node

        if path in self.replacements:
            new_path = self.replacements[path]
            self.changed = True
            return self._build_attribute_from_path(new_path)

        return updated_node

    def leave_Name(
        self, original_node: cst.Name, updated_node: cst.Name
    ) -> cst.BaseExpression:
        """Replace deprecated function names."""
        name = updated_node.value

        if name in self.replacements:
            new_name = self.replacements[name]
            if "." not in new_name:
                self.changed = True
                return updated_node.with_changes(value=new_name)
            else:
                self.changed = True
                return self._build_attribute_from_path(new_name)

        return updated_node

    def _get_attribute_path(self, node: cst.Attribute) -> str | None:
        """Get the full dotted path of an attribute access."""
        parts = [node.attr.value]
        current = node.value

        while isinstance(current, cst.Attribute):
            parts.append(current.attr.value)
            current = current.value

        if isinstance(current, cst.Name):
            parts.append(current.value)
            return ".".join(reversed(parts))

        return None

    def _build_attribute_from_path(self, path: str) -> cst.BaseExpression:
        """Build an attribute access expression from a dotted path."""
        parts = path.split(".")
        result: cst.BaseExpression = cst.Name(parts[0])

        for part in parts[1:]:
            result = cst.Attribute(value=result, attr=cst.Name(part))

        return result


class OldStyleClassFinder(cst.CSTVisitor):
    """Find old-style class definitions (classes inheriting only from object)."""

    def __init__(self, file_path: Path) -> None:
        super().__init__()
        self.file_path = file_path
        self.old_style_classes: list[tuple[str, int]] = []

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        """Check if class has only object as base or no bases."""
        # Check if class has parens with only `object` as base
        if len(node.bases) == 1:
            base = node.bases[0]
            if isinstance(base.value, cst.Name) and base.value.value == "object":
                self.old_style_classes.append((node.name.value, 0))

        return True


def find_deprecated_usage(rejig: Rejig) -> list[DeprecatedUsage]:
    """Find all deprecated API usage in a project.

    Parameters
    ----------
    rejig : Rejig
        The Rejig instance to search.

    Returns
    -------
    list[DeprecatedUsage]
        List of deprecated usages found.
    """
    all_usages: list[DeprecatedUsage] = []

    for file_path in rejig.files:
        try:
            content = file_path.read_text()
            tree = cst.parse_module(content)
            wrapper = cst.MetadataWrapper(tree)

            finder = DeprecatedUsageFinder(file_path)
            wrapper.visit(finder)
            all_usages.extend(finder.usages)
        except Exception:
            continue

    return all_usages


def find_old_style_classes(rejig: Rejig) -> list[tuple[Path, str]]:
    """Find all old-style class definitions in a project.

    Parameters
    ----------
    rejig : Rejig
        The Rejig instance to search.

    Returns
    -------
    list[tuple[Path, str]]
        List of (file_path, class_name) tuples for old-style classes.
    """
    results: list[tuple[Path, str]] = []

    for file_path in rejig.files:
        try:
            content = file_path.read_text()
            tree = cst.parse_module(content)
            wrapper = cst.MetadataWrapper(tree)

            finder = OldStyleClassFinder(file_path)
            wrapper.visit(finder)

            for class_name, _ in finder.old_style_classes:
                results.append((file_path, class_name))
        except Exception:
            continue

    return results
