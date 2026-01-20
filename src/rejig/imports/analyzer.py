"""Import analysis using LibCST.

Provides functionality to:
- Parse and extract import statements
- Track which names are used in a file
- Detect unused imports
- Detect missing imports (undefined names that could be imports)
"""
from __future__ import annotations

import builtins
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


@dataclass
class ImportInfo:
    """Information about an import statement.

    Attributes
    ----------
    module : str | None
        The module being imported (None for regular imports like 'import os').
    names : list[str]
        List of names being imported. For 'import os', this is ['os'].
        For 'from os import path, getcwd', this is ['path', 'getcwd'].
    aliases : dict[str, str]
        Map of alias to original name. For 'import os as operating_system',
        this is {'operating_system': 'os'}.
    is_from_import : bool
        True if this is a 'from x import y' statement.
    is_relative : bool
        True if this is a relative import (starts with .).
    relative_level : int
        Number of dots for relative imports (e.g., '.' = 1, '..' = 2).
    line_number : int
        1-based line number where this import appears.
    import_statement : str
        The full import statement as a string.
    is_future : bool
        True if this is a 'from __future__' import.
    is_type_checking : bool
        True if this import is inside an 'if TYPE_CHECKING:' block.
    """

    module: str | None
    names: list[str]
    aliases: dict[str, str] = field(default_factory=dict)
    is_from_import: bool = False
    is_relative: bool = False
    relative_level: int = 0
    line_number: int = 0
    import_statement: str = ""
    is_future: bool = False
    is_type_checking: bool = False

    def get_imported_names(self) -> list[str]:
        """Get all names that this import makes available.

        Returns the aliases if present, otherwise the original names.
        """
        result = []
        for name in self.names:
            if name in self.aliases.values():
                # Find the alias for this name
                for alias, original in self.aliases.items():
                    if original == name:
                        result.append(alias)
                        break
            else:
                result.append(name)
        return result

    def get_original_name(self, alias: str) -> str:
        """Get the original name for an alias, or return the name unchanged."""
        return self.aliases.get(alias, alias)


class ImportCollector(cst.CSTVisitor):
    """Collect all imports from a module."""

    def __init__(self) -> None:
        self.imports: list[ImportInfo] = []
        self._in_type_checking = False
        self._type_checking_depth = 0

    def visit_If(self, node: cst.If) -> bool:
        """Track if we're inside an if TYPE_CHECKING block."""
        # Check if this is 'if TYPE_CHECKING:'
        if isinstance(node.test, cst.Name) and node.test.value == "TYPE_CHECKING":
            self._in_type_checking = True
            self._type_checking_depth += 1
        return True

    def leave_If(self, node: cst.If) -> None:
        """Track leaving an if TYPE_CHECKING block."""
        if isinstance(node.test, cst.Name) and node.test.value == "TYPE_CHECKING":
            self._type_checking_depth -= 1
            if self._type_checking_depth == 0:
                self._in_type_checking = False

    def visit_Import(self, node: cst.Import) -> bool:
        """Process 'import x' statements."""
        names = []
        aliases = {}

        for name in node.names if isinstance(node.names, tuple) else []:
            if isinstance(name, cst.ImportAlias):
                if isinstance(name.name, cst.Attribute):
                    # import os.path
                    full_name = _get_full_name(name.name)
                    names.append(full_name)
                    if name.asname and isinstance(name.asname.name, cst.Name):
                        aliases[name.asname.name.value] = full_name
                elif isinstance(name.name, cst.Name):
                    names.append(name.name.value)
                    if name.asname and isinstance(name.asname.name, cst.Name):
                        aliases[name.asname.name.value] = name.name.value

        line_number = node.body[0].start_pos.line if hasattr(node, "body") else 0
        if hasattr(node, "_metadata"):
            pos_data = node._metadata.get(cst.metadata.PositionProvider, None)
            if pos_data:
                line_number = pos_data.start.line

        # For simple imports, get line number from the CST structure
        # We'll get accurate line numbers when we use the position provider wrapper

        self.imports.append(
            ImportInfo(
                module=None,
                names=names,
                aliases=aliases,
                is_from_import=False,
                is_relative=False,
                relative_level=0,
                import_statement=_node_to_code(node),
                is_future=False,
                is_type_checking=self._in_type_checking,
            )
        )
        return False

    def visit_ImportFrom(self, node: cst.ImportFrom) -> bool:
        """Process 'from x import y' statements."""
        # Get the module being imported from
        module = None
        is_relative = False
        relative_level = 0

        if node.relative:
            is_relative = True
            relative_level = len(node.relative)

        if node.module:
            module = _get_full_name(node.module)

        # Get names being imported
        names = []
        aliases = {}

        if isinstance(node.names, cst.ImportStar):
            names = ["*"]
        elif isinstance(node.names, tuple):
            for name in node.names:
                if isinstance(name, cst.ImportAlias):
                    if isinstance(name.name, cst.Name):
                        names.append(name.name.value)
                        if name.asname and isinstance(name.asname.name, cst.Name):
                            aliases[name.asname.name.value] = name.name.value

        is_future = module == "__future__"

        self.imports.append(
            ImportInfo(
                module=module,
                names=names,
                aliases=aliases,
                is_from_import=True,
                is_relative=is_relative,
                relative_level=relative_level,
                import_statement=_node_to_code(node),
                is_future=is_future,
                is_type_checking=self._in_type_checking,
            )
        )
        return False


class NameUsageCollector(cst.CSTVisitor):
    """Collect all name usages in a module (excluding definitions and imports)."""

    def __init__(self) -> None:
        self.used_names: set[str] = set()
        self._in_import = False
        self._in_definition = False
        self._definition_depth = 0
        self._in_annotation = False

    def visit_Import(self, node: cst.Import) -> bool:
        self._in_import = True
        return False

    def leave_Import(self, node: cst.Import) -> None:
        self._in_import = False

    def visit_ImportFrom(self, node: cst.ImportFrom) -> bool:
        self._in_import = True
        return False

    def leave_ImportFrom(self, node: cst.ImportFrom) -> None:
        self._in_import = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        # Don't count the function name itself as a usage
        return True

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        # Don't count the class name itself as a usage
        return True

    def visit_Annotation(self, node: cst.Annotation) -> bool:
        self._in_annotation = True
        return True

    def leave_Annotation(self, node: cst.Annotation) -> None:
        self._in_annotation = False

    def visit_Name(self, node: cst.Name) -> bool:
        if not self._in_import:
            self.used_names.add(node.value)
        return False

    def visit_Attribute(self, node: cst.Attribute) -> bool:
        # For x.y.z, we need to track 'x' as used
        if not self._in_import:
            root = node
            while isinstance(root.value, cst.Attribute):
                root = root.value
            if isinstance(root.value, cst.Name):
                self.used_names.add(root.value.value)
        return True


class ImportAnalyzer:
    """Analyze imports in Python files.

    Provides functionality to:
    - Extract all imports from a file
    - Detect unused imports
    - Detect missing imports (undefined names)
    """

    def __init__(self, rejig: Rejig) -> None:
        self._rejig = rejig

    def get_imports(self, path: Path) -> list[ImportInfo]:
        """Get all imports from a file.

        Parameters
        ----------
        path : Path
            Path to the Python file.

        Returns
        -------
        list[ImportInfo]
            List of import information objects.
        """
        if not path.exists():
            return []

        try:
            content = path.read_text()
            tree = cst.parse_module(content)
            wrapper = cst.MetadataWrapper(tree)
            collector = ImportCollector()
            wrapper.visit(collector)

            # Update line numbers using position data
            for i, node in enumerate(_get_import_nodes(tree)):
                if hasattr(node, "__class__"):
                    pos = wrapper.resolve(cst.metadata.PositionProvider).get(node)
                    if pos and i < len(collector.imports):
                        collector.imports[i].line_number = pos.start.line

            return collector.imports
        except Exception:
            return []

    def get_used_names(self, path: Path) -> set[str]:
        """Get all names used in a file (excluding definitions and imports).

        Parameters
        ----------
        path : Path
            Path to the Python file.

        Returns
        -------
        set[str]
            Set of name strings used in the file.
        """
        if not path.exists():
            return set()

        try:
            content = path.read_text()
            tree = cst.parse_module(content)
            collector = NameUsageCollector()
            tree.walk(collector)
            return collector.used_names
        except Exception:
            return set()

    def find_unused_imports(self, path: Path) -> list[ImportInfo]:
        """Find imports that are not used in the file.

        Parameters
        ----------
        path : Path
            Path to the Python file.

        Returns
        -------
        list[ImportInfo]
            List of unused imports.
        """
        imports = self.get_imports(path)
        used_names = self.get_used_names(path)

        unused = []
        for imp in imports:
            # Skip __future__ imports (always needed if present)
            if imp.is_future:
                continue

            # Skip star imports (can't determine if unused)
            if "*" in imp.names:
                continue

            # Check if any of the imported names are used
            imported_names = imp.get_imported_names()
            is_used = False

            for name in imported_names:
                if name in used_names:
                    is_used = True
                    break

            if not is_used:
                unused.append(imp)

        return unused

    def find_potentially_missing_imports(self, path: Path) -> set[str]:
        """Find names that are used but not defined or imported.

        Note: This is a heuristic - it doesn't catch all cases (like
        names from star imports or exec/eval).

        Parameters
        ----------
        path : Path
            Path to the Python file.

        Returns
        -------
        set[str]
            Set of name strings that might need imports.
        """
        if not path.exists():
            return set()

        try:
            content = path.read_text()
            tree = cst.parse_module(content)

            # Get all used names
            usage_collector = NameUsageCollector()
            tree.walk(usage_collector)
            used_names = usage_collector.used_names

            # Get all imported names
            import_collector = ImportCollector()
            tree.walk(import_collector)

            imported_names: set[str] = set()
            for imp in import_collector.imports:
                imported_names.update(imp.get_imported_names())
                # Also add module names for regular imports
                if not imp.is_from_import:
                    for name in imp.names:
                        # For 'import os.path', add 'os'
                        imported_names.add(name.split(".")[0])

            # Get all defined names (classes, functions, assignments)
            defined_names = _get_defined_names(tree)

            # Get builtin names
            builtin_names = set(dir(builtins))

            # Find undefined names
            undefined = used_names - imported_names - defined_names - builtin_names

            # Filter out common false positives
            undefined -= {"self", "cls", "super", "type", "object"}

            return undefined
        except Exception:
            return set()


def _get_full_name(node: cst.BaseExpression) -> str:
    """Get the full dotted name from an attribute or name node."""
    if isinstance(node, cst.Name):
        return node.value
    elif isinstance(node, cst.Attribute):
        return f"{_get_full_name(node.value)}.{node.attr.value}"
    return ""


def _node_to_code(node: cst.CSTNode) -> str:
    """Convert a CST node back to source code."""
    return cst.Module(body=[cst.SimpleStatementLine(body=[node])]).code.strip()


def _get_import_nodes(tree: cst.Module) -> list[cst.CSTNode]:
    """Get all import nodes from a module."""
    nodes = []
    for node in tree.body:
        if isinstance(node, cst.SimpleStatementLine):
            for stmt in node.body:
                if isinstance(stmt, (cst.Import, cst.ImportFrom)):
                    nodes.append(stmt)
    return nodes


class DefinitionCollector(cst.CSTVisitor):
    """Collect all defined names in a module."""

    def __init__(self) -> None:
        self.defined_names: set[str] = set()

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        self.defined_names.add(node.name.value)
        return True

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        self.defined_names.add(node.name.value)
        return True

    def visit_Assign(self, node: cst.Assign) -> bool:
        for target in node.targets:
            if isinstance(target.target, cst.Name):
                self.defined_names.add(target.target.value)
            elif isinstance(target.target, cst.Tuple):
                for elt in target.target.elements:
                    if isinstance(elt.value, cst.Name):
                        self.defined_names.add(elt.value.value)
        return False

    def visit_AnnAssign(self, node: cst.AnnAssign) -> bool:
        if isinstance(node.target, cst.Name):
            self.defined_names.add(node.target.value)
        return False

    def visit_For(self, node: cst.For) -> bool:
        if isinstance(node.target, cst.Name):
            self.defined_names.add(node.target.value)
        elif isinstance(node.target, cst.Tuple):
            for elt in node.target.elements:
                if isinstance(elt.value, cst.Name):
                    self.defined_names.add(elt.value.value)
        return True

    def visit_With(self, node: cst.With) -> bool:
        for item in node.items:
            if item.asname and isinstance(item.asname.name, cst.Name):
                self.defined_names.add(item.asname.name.value)
        return True

    def visit_ExceptHandler(self, node: cst.ExceptHandler) -> bool:
        if node.name and isinstance(node.name.name, cst.Name):
            self.defined_names.add(node.name.name.value)
        return True

    def visit_Param(self, node: cst.Param) -> bool:
        if isinstance(node.name, cst.Name):
            self.defined_names.add(node.name.value)
        return False

    def visit_NamedExpr(self, node: cst.NamedExpr) -> bool:
        if isinstance(node.target, cst.Name):
            self.defined_names.add(node.target.value)
        return True


def _get_defined_names(tree: cst.Module) -> set[str]:
    """Get all names defined in a module."""
    collector = DefinitionCollector()
    tree.walk(collector)
    return collector.defined_names
