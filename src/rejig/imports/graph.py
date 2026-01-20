"""Import graph analysis and circular import detection."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from rejig.imports.analyzer import ImportAnalyzer

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


@dataclass
class ImportEdge:
    """An edge in the import graph representing one import relationship.

    Attributes
    ----------
    from_module : str
        The module that contains the import.
    to_module : str
        The module being imported.
    is_from_import : bool
        Whether this is a 'from x import y' style import.
    names : list[str]
        Names being imported (for from imports).
    line_number : int
        Line number of the import in the source file.
    file_path : Path
        Path to the file containing the import.
    """

    from_module: str
    to_module: str
    is_from_import: bool = False
    names: list[str] = field(default_factory=list)
    line_number: int = 0
    file_path: Path | None = None


@dataclass
class CircularImport:
    """Represents a circular import chain.

    Attributes
    ----------
    cycle : list[str]
        List of module names in the cycle. The last module imports the first.
    edges : list[ImportEdge]
        The import edges that form this cycle.
    """

    cycle: list[str]
    edges: list[ImportEdge] = field(default_factory=list)

    def __str__(self) -> str:
        return " -> ".join(self.cycle + [self.cycle[0]])


class ImportGraph:
    """Build and analyze the import graph for a project.

    Provides functionality to:
    - Build a dependency graph of imports
    - Detect circular imports
    - Find all dependencies of a module
    - Find all modules that depend on a given module
    """

    def __init__(self, rejig: Rejig) -> None:
        self._rejig = rejig
        self._analyzer = ImportAnalyzer(rejig)
        self._graph: dict[str, set[str]] = defaultdict(set)
        self._reverse_graph: dict[str, set[str]] = defaultdict(set)
        self._edges: list[ImportEdge] = []
        self._module_to_path: dict[str, Path] = {}
        self._built = False

    def build(self) -> None:
        """Build the import graph from all files in the project."""
        self._graph.clear()
        self._reverse_graph.clear()
        self._edges.clear()
        self._module_to_path.clear()

        for file_path in self._rejig.files:
            module_name = self._path_to_module(file_path)
            if not module_name:
                continue

            self._module_to_path[module_name] = file_path
            imports = self._analyzer.get_imports(file_path)

            for imp in imports:
                # Skip __future__ imports
                if imp.is_future:
                    continue

                # Resolve the target module
                target_module = self._resolve_import_target(file_path, imp)
                if not target_module:
                    continue

                # Add to graph
                self._graph[module_name].add(target_module)
                self._reverse_graph[target_module].add(module_name)

                # Track edge details
                self._edges.append(
                    ImportEdge(
                        from_module=module_name,
                        to_module=target_module,
                        is_from_import=imp.is_from_import,
                        names=imp.names,
                        line_number=imp.line_number,
                        file_path=file_path,
                    )
                )

        self._built = True

    def _path_to_module(self, path: Path) -> str | None:
        """Convert a file path to a module name."""
        try:
            rel_path = path.relative_to(self._rejig.root)
            parts = list(rel_path.parts)

            # Remove .py extension
            if parts[-1].endswith(".py"):
                parts[-1] = parts[-1][:-3]

            # Handle __init__.py
            if parts[-1] == "__init__":
                parts = parts[:-1]

            if not parts:
                return None

            return ".".join(parts)
        except Exception:
            return None

    def _resolve_import_target(self, file_path: Path, imp) -> str | None:
        """Resolve an import to its target module name."""
        if imp.is_relative:
            # Resolve relative import
            try:
                file_dir = file_path.parent
                rel_path = file_dir.relative_to(self._rejig.root)
                parts = list(rel_path.parts)

                # Go up by relative_level - 1
                level = imp.relative_level
                if level > len(parts):
                    return None

                base_parts = parts[: len(parts) - level + 1]

                # Add the module path
                if imp.module:
                    module_parts = imp.module.split(".")
                    base_parts.extend(module_parts)

                return ".".join(base_parts) if base_parts else None
            except Exception:
                return None
        else:
            # Absolute import
            if imp.is_from_import and imp.module:
                return imp.module.split(".")[0]
            elif imp.names:
                return imp.names[0].split(".")[0]
            return None

    def get_dependencies(self, module: str) -> set[str]:
        """Get all modules that a given module imports.

        Parameters
        ----------
        module : str
            The module name to check.

        Returns
        -------
        set[str]
            Set of module names that this module imports.
        """
        if not self._built:
            self.build()
        return set(self._graph.get(module, set()))

    def get_dependents(self, module: str) -> set[str]:
        """Get all modules that import a given module.

        Parameters
        ----------
        module : str
            The module name to check.

        Returns
        -------
        set[str]
            Set of module names that import this module.
        """
        if not self._built:
            self.build()
        return set(self._reverse_graph.get(module, set()))

    def get_all_dependencies(self, module: str) -> set[str]:
        """Get all transitive dependencies of a module.

        Parameters
        ----------
        module : str
            The module name to check.

        Returns
        -------
        set[str]
            Set of all module names that this module depends on (directly or indirectly).
        """
        if not self._built:
            self.build()

        visited: set[str] = set()
        stack = [module]

        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)

            for dep in self._graph.get(current, set()):
                if dep not in visited:
                    stack.append(dep)

        visited.discard(module)  # Don't include the module itself
        return visited

    def find_circular_imports(self) -> list[CircularImport]:
        """Find all circular import chains in the project.

        Returns
        -------
        list[CircularImport]
            List of circular import chains found.
        """
        if not self._built:
            self.build()

        cycles: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()
        path: list[str] = []

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self._graph.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:]
                    cycles.append(cycle)

            path.pop()
            rec_stack.discard(node)

        for node in self._graph:
            if node not in visited:
                dfs(node)

        # Convert to CircularImport objects and deduplicate
        seen_cycles: set[frozenset[str]] = set()
        result: list[CircularImport] = []

        for cycle in cycles:
            # Normalize cycle (start from smallest element)
            min_idx = cycle.index(min(cycle))
            normalized = cycle[min_idx:] + cycle[:min_idx]
            cycle_set = frozenset(normalized)

            if cycle_set not in seen_cycles:
                seen_cycles.add(cycle_set)

                # Find the edges that form this cycle
                edges = []
                for i, mod in enumerate(normalized):
                    next_mod = normalized[(i + 1) % len(normalized)]
                    for edge in self._edges:
                        if edge.from_module == mod and edge.to_module == next_mod:
                            edges.append(edge)
                            break

                result.append(CircularImport(cycle=normalized, edges=edges))

        return result

    def get_edges(self) -> list[ImportEdge]:
        """Get all import edges in the graph.

        Returns
        -------
        list[ImportEdge]
            List of all import edges.
        """
        if not self._built:
            self.build()
        return list(self._edges)

    def get_modules(self) -> set[str]:
        """Get all modules in the graph.

        Returns
        -------
        set[str]
            Set of all module names.
        """
        if not self._built:
            self.build()
        return set(self._graph.keys()) | set(self._reverse_graph.keys())

    def to_dict(self) -> dict[str, list[str]]:
        """Export the graph as a dictionary.

        Returns
        -------
        dict[str, list[str]]
            Dictionary mapping module names to their dependencies.
        """
        if not self._built:
            self.build()
        return {k: sorted(v) for k, v in self._graph.items()}
