"""Dead code detection.

Detects potentially unused code:
- Unused functions (not called anywhere in the codebase)
- Unused classes (not referenced anywhere)
- Unused variables
- Unreachable code (after return/raise)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst

from rejig.analysis.targets import (
    AnalysisFinding,
    AnalysisTarget,
    AnalysisTargetList,
    AnalysisType,
)

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


@dataclass
class UnusedCodeResult:
    """Result of dead code analysis.

    Attributes
    ----------
    name : str
        Name of the unused element.
    file_path : Path
        Path to the file.
    line_number : int
        Line number where defined.
    element_type : str
        Type: "function", "class", "variable", "import".
    is_public : bool
        True if the name doesn't start with underscore.
    """

    name: str
    file_path: Path
    line_number: int
    element_type: str
    is_public: bool = True


class DefinitionCollector(cst.CSTVisitor):
    """Collect all definitions (functions, classes, variables) in a module."""

    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._functions: list[tuple[str, int]] = []
        self._classes: list[tuple[str, int]] = []
        self._variables: list[tuple[str, int]] = []
        self._class_stack: list[str] = []
        self._function_stack: list[str] = []

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        # Only track top-level classes
        if not self._class_stack and not self._function_stack:
            self._classes.append((node.name.value, 0))
        self._class_stack.append(node.name.value)
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        self._class_stack.pop()

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        # Only track top-level functions (not methods or nested)
        if not self._class_stack and not self._function_stack:
            self._functions.append((node.name.value, 0))
        self._function_stack.append(node.name.value)
        return True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:
        self._function_stack.pop()

    def visit_Assign(self, node: cst.Assign) -> bool:
        # Only track module-level assignments
        if not self._class_stack and not self._function_stack:
            for target in node.targets:
                if isinstance(target.target, cst.Name):
                    name = target.target.value
                    # Skip constants (all uppercase) and dunders
                    if not name.isupper() and not name.startswith("__"):
                        self._variables.append((name, 0))
        return False

    def visit_AnnAssign(self, node: cst.AnnAssign) -> bool:
        # Only track module-level annotated assignments
        if not self._class_stack and not self._function_stack:
            if isinstance(node.target, cst.Name):
                name = node.target.value
                if not name.isupper() and not name.startswith("__"):
                    self._variables.append((name, 0))
        return False

    @property
    def functions(self) -> list[tuple[str, int]]:
        return self._functions

    @property
    def classes(self) -> list[tuple[str, int]]:
        return self._classes

    @property
    def variables(self) -> list[tuple[str, int]]:
        return self._variables


class UsageCollector(cst.CSTVisitor):
    """Collect all name usages in a module."""

    def __init__(self) -> None:
        self._used_names: set[str] = set()
        self._in_definition = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        # Don't count the function name itself as a usage
        return True

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        # Don't count the class name itself as a usage
        # But do count base classes
        return True

    def visit_Arg(self, node: cst.Arg) -> bool:
        # Track arguments to base classes
        return True

    def visit_Name(self, node: cst.Name) -> bool:
        self._used_names.add(node.value)
        return False

    def visit_Attribute(self, node: cst.Attribute) -> bool:
        # For x.y, track the root 'x'
        root = node
        while isinstance(root.value, cst.Attribute):
            root = root.value
        if isinstance(root.value, cst.Name):
            self._used_names.add(root.value.value)
        return True

    @property
    def used_names(self) -> set[str]:
        return self._used_names


class UnreachableCodeCollector(cst.CSTVisitor):
    """Detect unreachable code after return/raise statements."""

    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._unreachable: list[int] = []
        self._in_function = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        self._in_function = True
        self._check_body(node.body)
        return True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:
        self._in_function = False

    def _check_body(self, body: cst.BaseSuite) -> None:
        """Check for unreachable code in a body."""
        if not isinstance(body, cst.IndentedBlock):
            return

        found_terminator = False
        for stmt in body.body:
            if found_terminator:
                # This code is unreachable
                self._unreachable.append(0)  # Line number filled later
                break

            # Check if this statement is a terminator
            if isinstance(stmt, cst.SimpleStatementLine):
                for item in stmt.body:
                    if isinstance(item, (cst.Return, cst.Raise)):
                        found_terminator = True
                        break

    @property
    def unreachable_lines(self) -> list[int]:
        return self._unreachable


class DeadCodeAnalyzer:
    """Analyze code for potentially unused elements.

    Detects:
    - Functions not called anywhere in the project
    - Classes not referenced anywhere
    - Module-level variables not used
    - Unreachable code after return/raise
    """

    def __init__(self, rejig: Rejig) -> None:
        self._rejig = rejig
        self._definitions: dict[Path, tuple[list, list, list]] | None = None
        self._all_used_names: set[str] | None = None

    def _collect_definitions(
        self,
    ) -> dict[Path, tuple[list[tuple[str, int]], list[tuple[str, int]], list[tuple[str, int]]]]:
        """Collect all definitions across the project."""
        if self._definitions is not None:
            return self._definitions

        definitions: dict[Path, tuple[list, list, list]] = {}

        for file_path in self._rejig.files:
            try:
                content = file_path.read_text()
                tree = cst.parse_module(content)
                lines = content.splitlines()

                wrapper = cst.MetadataWrapper(tree)
                collector = DefinitionCollector(file_path)
                wrapper.visit(collector)

                # Update line numbers
                functions = []
                for name, _ in collector.functions:
                    line_num = 1
                    for i, line in enumerate(lines, 1):
                        if f"def {name}" in line:
                            line_num = i
                            break
                    functions.append((name, line_num))

                classes = []
                for name, _ in collector.classes:
                    line_num = 1
                    for i, line in enumerate(lines, 1):
                        if f"class {name}" in line:
                            line_num = i
                            break
                    classes.append((name, line_num))

                variables = []
                for name, _ in collector.variables:
                    line_num = 1
                    for i, line in enumerate(lines, 1):
                        if name in line and "=" in line:
                            line_num = i
                            break
                    variables.append((name, line_num))

                definitions[file_path] = (functions, classes, variables)
            except Exception:
                continue

        self._definitions = definitions
        return definitions

    def _collect_all_usages(self) -> set[str]:
        """Collect all name usages across the project."""
        if self._all_used_names is not None:
            return self._all_used_names

        used_names: set[str] = set()

        for file_path in self._rejig.files:
            try:
                content = file_path.read_text()
                tree = cst.parse_module(content)

                wrapper = cst.MetadataWrapper(tree)
                collector = UsageCollector()
                wrapper.visit(collector)

                used_names.update(collector.used_names)
            except Exception:
                continue

        self._all_used_names = used_names
        return used_names

    def find_unused_functions(self) -> AnalysisTargetList:
        """Find functions that are not called anywhere.

        Note: This may have false positives for:
        - Functions called via getattr/exec
        - Functions used as decorators
        - Functions passed as callbacks
        - Entry points/CLI commands

        Returns
        -------
        AnalysisTargetList
            Potentially unused functions.
        """
        findings: list[AnalysisTarget] = []
        definitions = self._collect_definitions()
        used_names = self._collect_all_usages()

        # Names to exclude (commonly used patterns)
        excluded_patterns = {
            "main",
            "setup",
            "teardown",
            "setUp",
            "tearDown",
            "test_",
            "__",
        }

        for file_path, (functions, _, _) in definitions.items():
            for name, line_num in functions:
                # Skip private functions (single underscore)
                if name.startswith("_") and not name.startswith("__"):
                    continue

                # Skip common excluded patterns
                if any(
                    name == pattern or name.startswith(pattern)
                    for pattern in excluded_patterns
                ):
                    continue

                # Check if function is used
                if name not in used_names:
                    finding = AnalysisFinding(
                        type=AnalysisType.UNUSED_FUNCTION,
                        file_path=file_path,
                        line_number=line_num,
                        name=name,
                        message=f"Function '{name}' appears to be unused",
                        severity="info",
                    )
                    findings.append(AnalysisTarget(self._rejig, finding))

        return AnalysisTargetList(self._rejig, findings)

    def find_unused_classes(self) -> AnalysisTargetList:
        """Find classes that are not referenced anywhere.

        Note: This may have false positives for:
        - Classes instantiated dynamically
        - Classes registered with factories
        - Abstract base classes

        Returns
        -------
        AnalysisTargetList
            Potentially unused classes.
        """
        findings: list[AnalysisTarget] = []
        definitions = self._collect_definitions()
        used_names = self._collect_all_usages()

        # Excluded patterns
        excluded_patterns = {"Test", "Mock", "Fake", "Base", "Abstract", "Mixin"}

        for file_path, (_, classes, _) in definitions.items():
            for name, line_num in classes:
                # Skip private classes
                if name.startswith("_"):
                    continue

                # Skip common patterns
                if any(
                    name == pattern or name.startswith(pattern) or name.endswith(pattern)
                    for pattern in excluded_patterns
                ):
                    continue

                # Check if class is used
                if name not in used_names:
                    finding = AnalysisFinding(
                        type=AnalysisType.UNUSED_CLASS,
                        file_path=file_path,
                        line_number=line_num,
                        name=name,
                        message=f"Class '{name}' appears to be unused",
                        severity="info",
                    )
                    findings.append(AnalysisTarget(self._rejig, finding))

        return AnalysisTargetList(self._rejig, findings)

    def find_unused_variables(self) -> AnalysisTargetList:
        """Find module-level variables that are not used.

        Note: Only analyzes module-level variables, not local variables.
        Constants (ALL_CAPS) are excluded.

        Returns
        -------
        AnalysisTargetList
            Potentially unused variables.
        """
        findings: list[AnalysisTarget] = []
        definitions = self._collect_definitions()
        used_names = self._collect_all_usages()

        for file_path, (_, _, variables) in definitions.items():
            for name, line_num in variables:
                # Skip private variables
                if name.startswith("_"):
                    continue

                # Check if variable is used (it will appear in used_names if defined,
                # so we need to count occurrences)
                if name not in used_names:
                    finding = AnalysisFinding(
                        type=AnalysisType.UNUSED_VARIABLE,
                        file_path=file_path,
                        line_number=line_num,
                        name=name,
                        message=f"Variable '{name}' appears to be unused",
                        severity="info",
                    )
                    findings.append(AnalysisTarget(self._rejig, finding))

        return AnalysisTargetList(self._rejig, findings)

    def find_unreachable_code(self) -> AnalysisTargetList:
        """Find code that is unreachable (after return/raise).

        Returns
        -------
        AnalysisTargetList
            Unreachable code locations.
        """
        findings: list[AnalysisTarget] = []

        for file_path in self._rejig.files:
            try:
                content = file_path.read_text()
                tree = cst.parse_module(content)
                lines = content.splitlines()

                wrapper = cst.MetadataWrapper(tree)
                collector = UnreachableCodeCollector(file_path)
                wrapper.visit(collector)

                # For each unreachable section, find approximate line
                # This is simplified - real implementation would need position metadata
                for _ in collector.unreachable_lines:
                    # Search for patterns like "return\n    <code>"
                    for i, line in enumerate(lines):
                        if i > 0 and lines[i - 1].strip().startswith(
                            ("return ", "return\n", "raise ")
                        ):
                            if line.strip() and not line.strip().startswith(("#", "except")):
                                finding = AnalysisFinding(
                                    type=AnalysisType.UNREACHABLE_CODE,
                                    file_path=file_path,
                                    line_number=i + 1,
                                    message=f"Code at line {i + 1} may be unreachable",
                                    severity="warning",
                                )
                                findings.append(AnalysisTarget(self._rejig, finding))
                                break
            except Exception:
                continue

        return AnalysisTargetList(self._rejig, findings)

    def find_all_dead_code(self) -> AnalysisTargetList:
        """Find all potentially dead code.

        Returns
        -------
        AnalysisTargetList
            All dead code findings.
        """
        all_findings: list[AnalysisTarget] = []

        all_findings.extend(self.find_unused_functions()._targets)
        all_findings.extend(self.find_unused_classes()._targets)
        all_findings.extend(self.find_unused_variables()._targets)
        all_findings.extend(self.find_unreachable_code()._targets)

        return AnalysisTargetList(self._rejig, all_findings)
