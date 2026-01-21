"""Pattern finding for code that needs attention.

Detects common code patterns that may indicate issues:
- Functions without type hints
- Classes/functions without docstrings
- Bare except clauses
- Hardcoded strings
- Magic numbers
"""
from __future__ import annotations

import re
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
class PatternMatch:
    """A pattern match found during analysis.

    Attributes
    ----------
    pattern_type : str
        Type of pattern matched.
    file_path : Path
        Path to the file.
    line_number : int
        Line number of the match.
    name : str | None
        Name of the element if applicable.
    value : str | None
        The matched value (e.g., the hardcoded string).
    """

    pattern_type: str
    file_path: Path
    line_number: int
    name: str | None = None
    value: str | None = None


class TypeHintCollector(cst.CSTVisitor):
    """Collect functions/methods without type hints."""

    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._functions_without_hints: list[tuple[str, int, str]] = []
        self._class_stack: list[str] = []

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        self._class_stack.append(node.name.value)
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        self._class_stack.pop()

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        # Check if function has any type hints
        has_return_hint = node.returns is not None
        has_param_hints = False

        for param in node.params.params:
            if param.annotation is not None:
                has_param_hints = True
                break

        # Also check *args, **kwargs, keyword-only params
        if node.params.star_arg and isinstance(node.params.star_arg, cst.Param):
            if node.params.star_arg.annotation is not None:
                has_param_hints = True
        if node.params.star_kwarg and node.params.star_kwarg.annotation is not None:
            has_param_hints = True

        # Determine the entity type
        if self._class_stack:
            entity_type = "method"
            full_name = f"{self._class_stack[-1]}.{node.name.value}"
        else:
            entity_type = "function"
            full_name = node.name.value

        # Skip special methods like __init__ if they only lack return hint
        if node.name.value.startswith("__") and node.name.value.endswith("__"):
            # For dunder methods, only flag if they have no param hints at all
            # (excluding self/cls which don't need hints)
            real_params = [
                p
                for p in node.params.params
                if p.name.value not in ("self", "cls")
            ]
            if not real_params and not has_return_hint:
                return True

        if not has_return_hint and not has_param_hints:
            self._functions_without_hints.append(
                (full_name, 0, entity_type)  # Line number filled in later
            )

        return True

    @property
    def results(self) -> list[tuple[str, int, str]]:
        return self._functions_without_hints


class DocstringCollector(cst.CSTVisitor):
    """Collect classes/functions without docstrings."""

    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._missing_docstrings: list[tuple[str, int, str]] = []
        self._class_stack: list[str] = []

    def _has_docstring(self, body: cst.BaseSuite) -> bool:
        """Check if a body starts with a docstring."""
        if isinstance(body, cst.IndentedBlock):
            if body.body:
                first_stmt = body.body[0]
                if isinstance(first_stmt, cst.SimpleStatementLine):
                    if first_stmt.body:
                        first_expr = first_stmt.body[0]
                        if isinstance(first_expr, cst.Expr):
                            if isinstance(first_expr.value, (cst.SimpleString, cst.ConcatenatedString)):
                                return True
        return False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        if not self._has_docstring(node.body):
            self._missing_docstrings.append((node.name.value, 0, "class"))
        self._class_stack.append(node.name.value)
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        self._class_stack.pop()

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        # Skip private methods/functions
        if node.name.value.startswith("_") and not node.name.value.startswith("__"):
            return True

        if not self._has_docstring(node.body):
            if self._class_stack:
                full_name = f"{self._class_stack[-1]}.{node.name.value}"
                entity_type = "method"
            else:
                full_name = node.name.value
                entity_type = "function"
            self._missing_docstrings.append((full_name, 0, entity_type))

        return True

    @property
    def results(self) -> list[tuple[str, int, str]]:
        return self._missing_docstrings


class BareExceptCollector(cst.CSTVisitor):
    """Collect bare except clauses."""

    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._bare_excepts: list[int] = []

    def visit_ExceptHandler(self, node: cst.ExceptHandler) -> bool:
        # A bare except has no type specified
        if node.type is None:
            self._bare_excepts.append(0)  # Line number filled later
        return True

    @property
    def results(self) -> list[int]:
        return self._bare_excepts


class HardcodedStringCollector(cst.CSTVisitor):
    """Collect hardcoded strings that might need externalization."""

    def __init__(self, file_path: Path, min_length: int = 10) -> None:
        self._file_path = file_path
        self._min_length = min_length
        self._strings: list[tuple[str, int]] = []
        self._in_call = 0
        self._in_assignment = False
        self._assignment_name: str | None = None

    def visit_Call(self, node: cst.Call) -> bool:
        self._in_call += 1
        return True

    def leave_Call(self, node: cst.Call) -> None:
        self._in_call -= 1

    def visit_Assign(self, node: cst.Assign) -> bool:
        self._in_assignment = True
        # Track simple name assignments
        if len(node.targets) == 1:
            target = node.targets[0].target
            if isinstance(target, cst.Name):
                self._assignment_name = target.value
        return True

    def leave_Assign(self, node: cst.Assign) -> None:
        self._in_assignment = False
        self._assignment_name = None

    def visit_SimpleString(self, node: cst.SimpleString) -> bool:
        # Skip docstrings (handled separately)
        # Skip f-strings, byte strings
        raw_value = node.value
        if raw_value.startswith(('f"', "f'", 'b"', "b'", 'r"', "r'")):
            return False

        # Extract the actual string content
        # Handle triple-quoted strings
        if raw_value.startswith('"""') or raw_value.startswith("'''"):
            content = raw_value[3:-3]
        else:
            content = raw_value[1:-1]

        # Skip short strings
        if len(content) < self._min_length:
            return False

        # Skip strings that look like constants (all uppercase names)
        if self._assignment_name and self._assignment_name.isupper():
            return False

        # Skip strings that are likely paths, URLs, or patterns
        if any(
            pattern in content
            for pattern in ["/", "\\", "://", "{}", "{{", "}}", "%s", "%d"]
        ):
            return False

        # Skip strings in function calls (likely logging, errors, etc.)
        if self._in_call > 0:
            return False

        self._strings.append((content[:50] + "..." if len(content) > 50 else content, 0))
        return False

    @property
    def results(self) -> list[tuple[str, int]]:
        return self._strings


class MagicNumberCollector(cst.CSTVisitor):
    """Collect magic numbers that might need to be constants."""

    # Numbers that are commonly acceptable
    ALLOWED_NUMBERS = {0, 1, 2, -1, 10, 100, 1000, 60, 24, 365}

    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._magic_numbers: list[tuple[int | float, int]] = []
        self._in_assignment = False
        self._assignment_name: str | None = None

    def visit_Assign(self, node: cst.Assign) -> bool:
        self._in_assignment = True
        if len(node.targets) == 1:
            target = node.targets[0].target
            if isinstance(target, cst.Name):
                self._assignment_name = target.value
        return True

    def leave_Assign(self, node: cst.Assign) -> None:
        self._in_assignment = False
        self._assignment_name = None

    def visit_Integer(self, node: cst.Integer) -> bool:
        # Skip if this is a constant assignment (uppercase name)
        if self._assignment_name and self._assignment_name.isupper():
            return False

        try:
            value = int(node.value)
        except ValueError:
            return False

        # Skip common acceptable values
        if value in self.ALLOWED_NUMBERS:
            return False

        # Skip small numbers used in common patterns
        if abs(value) <= 2:
            return False

        self._magic_numbers.append((value, 0))
        return False

    def visit_Float(self, node: cst.Float) -> bool:
        # Skip if this is a constant assignment
        if self._assignment_name and self._assignment_name.isupper():
            return False

        try:
            value = float(node.value)
        except ValueError:
            return False

        # Skip common values
        if value in {0.0, 0.5, 1.0, 2.0}:
            return False

        self._magic_numbers.append((value, 0))
        return False

    @property
    def results(self) -> list[tuple[int | float, int]]:
        return self._magic_numbers


class PatternFinder:
    """Find code patterns that may need attention.

    Detects:
    - Functions/methods without type hints
    - Classes/functions without docstrings
    - Bare except clauses
    - Hardcoded strings
    - Magic numbers
    """

    def __init__(self, rejig: Rejig) -> None:
        self._rejig = rejig

    def find_functions_without_type_hints(self) -> AnalysisTargetList:
        """Find functions and methods without type hints.

        Returns
        -------
        AnalysisTargetList
            Functions and methods lacking type annotations.
        """
        findings: list[AnalysisTarget] = []

        for file_path in self._rejig.files:
            try:
                content = file_path.read_text()
                tree = cst.parse_module(content)
                wrapper = cst.MetadataWrapper(tree)

                collector = TypeHintCollector(file_path)
                wrapper.visit(collector)

                # Get line numbers
                lines = content.splitlines()
                for name, _, entity_type in collector.results:
                    # Find the line where this function is defined
                    func_name = name.split(".")[-1]
                    line_num = 1
                    for i, line in enumerate(lines, 1):
                        if f"def {func_name}" in line:
                            line_num = i
                            break

                    finding = AnalysisFinding(
                        type=AnalysisType.MISSING_TYPE_HINT,
                        file_path=file_path,
                        line_number=line_num,
                        name=name,
                        message=f"{entity_type.capitalize()} '{name}' has no type hints",
                        severity="warning",
                    )
                    findings.append(AnalysisTarget(self._rejig, finding))
            except Exception:
                continue

        return AnalysisTargetList(self._rejig, findings)

    def find_classes_without_docstrings(self) -> AnalysisTargetList:
        """Find classes without docstrings.

        Returns
        -------
        AnalysisTargetList
            Classes lacking docstrings.
        """
        findings: list[AnalysisTarget] = []

        for file_path in self._rejig.files:
            try:
                content = file_path.read_text()
                tree = cst.parse_module(content)

                wrapper = cst.MetadataWrapper(tree)
                collector = DocstringCollector(file_path)
                wrapper.visit(collector)

                lines = content.splitlines()
                for name, _, entity_type in collector.results:
                    if entity_type != "class":
                        continue

                    # Find line number
                    line_num = 1
                    for i, line in enumerate(lines, 1):
                        if f"class {name}" in line:
                            line_num = i
                            break

                    finding = AnalysisFinding(
                        type=AnalysisType.MISSING_DOCSTRING,
                        file_path=file_path,
                        line_number=line_num,
                        name=name,
                        message=f"Class '{name}' has no docstring",
                        severity="info",
                    )
                    findings.append(AnalysisTarget(self._rejig, finding))
            except Exception:
                continue

        return AnalysisTargetList(self._rejig, findings)

    def find_functions_without_docstrings(self) -> AnalysisTargetList:
        """Find functions and methods without docstrings.

        Returns
        -------
        AnalysisTargetList
            Functions and methods lacking docstrings.
        """
        findings: list[AnalysisTarget] = []

        for file_path in self._rejig.files:
            try:
                content = file_path.read_text()
                tree = cst.parse_module(content)

                wrapper = cst.MetadataWrapper(tree)
                collector = DocstringCollector(file_path)
                wrapper.visit(collector)

                lines = content.splitlines()
                for name, _, entity_type in collector.results:
                    if entity_type == "class":
                        continue

                    # Find line number
                    func_name = name.split(".")[-1]
                    line_num = 1
                    for i, line in enumerate(lines, 1):
                        if f"def {func_name}" in line:
                            line_num = i
                            break

                    finding = AnalysisFinding(
                        type=AnalysisType.MISSING_DOCSTRING,
                        file_path=file_path,
                        line_number=line_num,
                        name=name,
                        message=f"{entity_type.capitalize()} '{name}' has no docstring",
                        severity="info",
                    )
                    findings.append(AnalysisTarget(self._rejig, finding))
            except Exception:
                continue

        return AnalysisTargetList(self._rejig, findings)

    def find_bare_excepts(self) -> AnalysisTargetList:
        """Find bare except clauses (except: without type).

        Returns
        -------
        AnalysisTargetList
            Bare except clauses found.
        """
        findings: list[AnalysisTarget] = []

        for file_path in self._rejig.files:
            try:
                content = file_path.read_text()
                lines = content.splitlines()

                # Use simple pattern matching for bare excepts
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if stripped == "except:" or stripped.startswith("except: "):
                        finding = AnalysisFinding(
                            type=AnalysisType.BARE_EXCEPT,
                            file_path=file_path,
                            line_number=i,
                            message="Bare 'except:' clause catches all exceptions",
                            severity="warning",
                        )
                        findings.append(AnalysisTarget(self._rejig, finding))
            except Exception:
                continue

        return AnalysisTargetList(self._rejig, findings)

    def find_hardcoded_strings(
        self, min_length: int = 10
    ) -> AnalysisTargetList:
        """Find hardcoded strings that might need externalization.

        Parameters
        ----------
        min_length : int
            Minimum string length to consider. Default 10.

        Returns
        -------
        AnalysisTargetList
            Hardcoded strings found.
        """
        findings: list[AnalysisTarget] = []

        for file_path in self._rejig.files:
            try:
                content = file_path.read_text()
                tree = cst.parse_module(content)

                wrapper = cst.MetadataWrapper(tree)
                collector = HardcodedStringCollector(file_path, min_length)
                wrapper.visit(collector)

                lines = content.splitlines()
                for string_value, _ in collector.results:
                    # Find the line containing this string
                    line_num = 1
                    search_val = string_value[:30] if len(string_value) > 30 else string_value
                    for i, line in enumerate(lines, 1):
                        if search_val in line:
                            line_num = i
                            break

                    finding = AnalysisFinding(
                        type=AnalysisType.HARDCODED_STRING,
                        file_path=file_path,
                        line_number=line_num,
                        message=f"Hardcoded string: '{string_value[:40]}...' " if len(string_value) > 40 else f"Hardcoded string: '{string_value}'",
                        severity="info",
                        value=string_value,
                    )
                    findings.append(AnalysisTarget(self._rejig, finding))
            except Exception:
                continue

        return AnalysisTargetList(self._rejig, findings)

    def find_magic_numbers(self) -> AnalysisTargetList:
        """Find magic numbers that might need to be constants.

        Returns
        -------
        AnalysisTargetList
            Magic numbers found.
        """
        findings: list[AnalysisTarget] = []

        for file_path in self._rejig.files:
            try:
                content = file_path.read_text()
                tree = cst.parse_module(content)

                wrapper = cst.MetadataWrapper(tree)
                collector = MagicNumberCollector(file_path)
                wrapper.visit(collector)

                lines = content.splitlines()
                for number_value, _ in collector.results:
                    # Find the line containing this number
                    line_num = 1
                    num_str = str(number_value)
                    for i, line in enumerate(lines, 1):
                        # Use word boundary to avoid partial matches
                        if re.search(rf"\b{re.escape(num_str)}\b", line):
                            line_num = i
                            break

                    finding = AnalysisFinding(
                        type=AnalysisType.MAGIC_NUMBER,
                        file_path=file_path,
                        line_number=line_num,
                        message=f"Magic number: {number_value}",
                        severity="info",
                        value=number_value,
                    )
                    findings.append(AnalysisTarget(self._rejig, finding))
            except Exception:
                continue

        return AnalysisTargetList(self._rejig, findings)

    def find_all_patterns(self) -> AnalysisTargetList:
        """Find all pattern issues.

        Returns
        -------
        AnalysisTargetList
            All pattern findings combined.
        """
        all_findings: list[AnalysisTarget] = []

        # Collect from all pattern finders
        all_findings.extend(self.find_functions_without_type_hints()._targets)
        all_findings.extend(self.find_classes_without_docstrings()._targets)
        all_findings.extend(self.find_functions_without_docstrings()._targets)
        all_findings.extend(self.find_bare_excepts()._targets)

        return AnalysisTargetList(self._rejig, all_findings)
