"""Cyclomatic complexity and code complexity analysis.

Measures various complexity metrics:
- Cyclomatic complexity (number of decision points)
- Nesting depth
- Function/class length
- Number of parameters
- Number of branches and returns
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
class ComplexityResult:
    """Result of complexity analysis for a function or method.

    Attributes
    ----------
    name : str
        Function or method name.
    file_path : Path
        Path to the file.
    line_number : int
        Starting line number.
    end_line : int
        Ending line number.
    cyclomatic_complexity : int
        Number of decision points + 1.
    line_count : int
        Number of lines in the function.
    parameter_count : int
        Number of parameters.
    branch_count : int
        Number of if/elif branches.
    return_count : int
        Number of return statements.
    is_method : bool
        True if this is a method in a class.
    class_name : str | None
        Name of containing class if a method.
    """

    name: str
    file_path: Path
    line_number: int
    end_line: int = 0
    cyclomatic_complexity: int = 1
    line_count: int = 0
    parameter_count: int = 0
    branch_count: int = 0
    return_count: int = 0
    is_method: bool = False
    class_name: str | None = None

    @property
    def full_name(self) -> str:
        """Full name including class if a method."""
        if self.class_name:
            return f"{self.class_name}.{self.name}"
        return self.name


@dataclass
class NestingResult:
    """Result of nesting depth analysis.

    Attributes
    ----------
    name : str
        Function or method name.
    file_path : Path
        Path to the file.
    line_number : int
        Line where deepest nesting occurs.
    max_depth : int
        Maximum nesting depth found.
    is_method : bool
        True if this is a method.
    class_name : str | None
        Name of containing class if a method.
    """

    name: str
    file_path: Path
    line_number: int
    max_depth: int = 0
    is_method: bool = False
    class_name: str | None = None

    @property
    def full_name(self) -> str:
        """Full name including class if a method."""
        if self.class_name:
            return f"{self.class_name}.{self.name}"
        return self.name


class ComplexityCollector(cst.CSTVisitor):
    """Collect complexity metrics from a module."""

    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._results: list[ComplexityResult] = []
        self._nesting_results: list[NestingResult] = []
        self._class_stack: list[str] = []
        self._current_result: ComplexityResult | None = None
        self._current_nesting: int = 0
        self._max_nesting: int = 0
        self._deepest_line: int = 0

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        self._class_stack.append(node.name.value)
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        self._class_stack.pop()

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        # Start tracking a new function
        is_method = len(self._class_stack) > 0
        class_name = self._class_stack[-1] if self._class_stack else None

        # Count parameters
        param_count = len(node.params.params)
        if node.params.star_arg and isinstance(node.params.star_arg, cst.Param):
            param_count += 1
        if node.params.star_kwarg:
            param_count += 1
        param_count += len(node.params.kwonly_params)

        # Subtract self/cls for methods
        if is_method and param_count > 0:
            if node.params.params:
                first_param = node.params.params[0].name.value
                if first_param in ("self", "cls"):
                    param_count -= 1

        self._current_result = ComplexityResult(
            name=node.name.value,
            file_path=self._file_path,
            line_number=0,  # Will be filled later
            cyclomatic_complexity=1,  # Base complexity
            parameter_count=param_count,
            is_method=is_method,
            class_name=class_name,
        )

        # Reset nesting tracking
        self._current_nesting = 0
        self._max_nesting = 0
        self._deepest_line = 0

        return True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:
        if self._current_result:
            self._results.append(self._current_result)

            # Add nesting result
            nesting_result = NestingResult(
                name=node.name.value,
                file_path=self._file_path,
                line_number=self._deepest_line or 0,
                max_depth=self._max_nesting,
                is_method=self._current_result.is_method,
                class_name=self._current_result.class_name,
            )
            self._nesting_results.append(nesting_result)

            self._current_result = None

    # Track complexity contributors
    def visit_If(self, node: cst.If) -> bool:
        if self._current_result:
            self._current_result.cyclomatic_complexity += 1
            self._current_result.branch_count += 1
            self._current_nesting += 1
            if self._current_nesting > self._max_nesting:
                self._max_nesting = self._current_nesting
        return True

    def leave_If(self, node: cst.If) -> None:
        if self._current_result:
            self._current_nesting -= 1

    def visit_For(self, node: cst.For) -> bool:
        if self._current_result:
            self._current_result.cyclomatic_complexity += 1
            self._current_nesting += 1
            if self._current_nesting > self._max_nesting:
                self._max_nesting = self._current_nesting
        return True

    def leave_For(self, node: cst.For) -> None:
        if self._current_result:
            self._current_nesting -= 1

    def visit_While(self, node: cst.While) -> bool:
        if self._current_result:
            self._current_result.cyclomatic_complexity += 1
            self._current_nesting += 1
            if self._current_nesting > self._max_nesting:
                self._max_nesting = self._current_nesting
        return True

    def leave_While(self, node: cst.While) -> None:
        if self._current_result:
            self._current_nesting -= 1

    def visit_Try(self, node: cst.Try) -> bool:
        if self._current_result:
            # Each except handler adds to complexity
            self._current_result.cyclomatic_complexity += len(node.handlers)
            self._current_nesting += 1
            if self._current_nesting > self._max_nesting:
                self._max_nesting = self._current_nesting
        return True

    def leave_Try(self, node: cst.Try) -> None:
        if self._current_result:
            self._current_nesting -= 1

    def visit_With(self, node: cst.With) -> bool:
        if self._current_result:
            self._current_nesting += 1
            if self._current_nesting > self._max_nesting:
                self._max_nesting = self._current_nesting
        return True

    def leave_With(self, node: cst.With) -> None:
        if self._current_result:
            self._current_nesting -= 1

    def visit_BooleanOperation(self, node: cst.BooleanOperation) -> bool:
        # and/or operators add complexity
        if self._current_result:
            self._current_result.cyclomatic_complexity += 1
        return True

    def visit_IfExp(self, node: cst.IfExp) -> bool:
        # Ternary expressions add complexity
        if self._current_result:
            self._current_result.cyclomatic_complexity += 1
        return True

    def visit_Return(self, node: cst.Return) -> bool:
        if self._current_result:
            self._current_result.return_count += 1
        return True

    @property
    def results(self) -> list[ComplexityResult]:
        return self._results

    @property
    def nesting_results(self) -> list[NestingResult]:
        return self._nesting_results


class ClassLengthCollector(cst.CSTVisitor):
    """Collect class length information."""

    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._results: list[tuple[str, int, int]] = []  # (name, start, end)

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        # We can't get line numbers directly from CST without metadata
        # We'll estimate from the code structure
        self._results.append((node.name.value, 0, 0))
        return True

    @property
    def results(self) -> list[tuple[str, int, int]]:
        return self._results


class ComplexityAnalyzer:
    """Analyze code complexity in Python files.

    Provides methods to find:
    - Functions exceeding cyclomatic complexity thresholds
    - Functions that are too long
    - Classes that are too long
    - Functions with excessive nesting
    - Functions with too many parameters
    """

    def __init__(self, rejig: Rejig) -> None:
        self._rejig = rejig
        self._cache: dict[Path, tuple[list[ComplexityResult], list[NestingResult]]] = {}

    def _analyze_file(
        self, file_path: Path
    ) -> tuple[list[ComplexityResult], list[NestingResult]]:
        """Analyze a single file for complexity."""
        if file_path in self._cache:
            return self._cache[file_path]

        try:
            content = file_path.read_text()
            tree = cst.parse_module(content)
            lines = content.splitlines()

            wrapper = cst.MetadataWrapper(tree)
            collector = ComplexityCollector(file_path)
            wrapper.visit(collector)

            # Update line numbers
            for result in collector.results:
                func_name = result.name
                for i, line in enumerate(lines, 1):
                    if f"def {func_name}" in line:
                        result.line_number = i
                        break

                # Estimate end line by counting lines in function
                # This is approximate - we'd need position metadata for accuracy
                if result.line_number > 0:
                    indent = len(lines[result.line_number - 1]) - len(
                        lines[result.line_number - 1].lstrip()
                    )
                    end_line = result.line_number
                    for i in range(result.line_number, len(lines)):
                        line = lines[i]
                        if line.strip() and not line.startswith(" " * (indent + 1)):
                            if i > result.line_number:
                                break
                        end_line = i + 1
                    result.end_line = end_line
                    result.line_count = end_line - result.line_number + 1

            # Update nesting results with line numbers
            for nesting in collector.nesting_results:
                for result in collector.results:
                    if (
                        result.name == nesting.name
                        and result.class_name == nesting.class_name
                    ):
                        nesting.line_number = result.line_number
                        break

            result_tuple = (collector.results, collector.nesting_results)
            self._cache[file_path] = result_tuple
            return result_tuple
        except Exception:
            return ([], [])

    def analyze_all(self) -> list[ComplexityResult]:
        """Analyze all files in the project.

        Returns
        -------
        list[ComplexityResult]
            Complexity results for all functions.
        """
        all_results: list[ComplexityResult] = []
        for file_path in self._rejig.files:
            results, _ = self._analyze_file(file_path)
            all_results.extend(results)
        return all_results

    def find_complex_functions(
        self, max_complexity: int = 10
    ) -> AnalysisTargetList:
        """Find functions exceeding cyclomatic complexity threshold.

        Parameters
        ----------
        max_complexity : int
            Maximum allowed cyclomatic complexity. Default 10.

        Returns
        -------
        AnalysisTargetList
            Functions exceeding the threshold.
        """
        findings: list[AnalysisTarget] = []

        for file_path in self._rejig.files:
            results, _ = self._analyze_file(file_path)

            for result in results:
                if result.cyclomatic_complexity > max_complexity:
                    entity = "Method" if result.is_method else "Function"
                    finding = AnalysisFinding(
                        type=AnalysisType.HIGH_CYCLOMATIC_COMPLEXITY,
                        file_path=file_path,
                        line_number=result.line_number,
                        name=result.full_name,
                        message=f"{entity} '{result.full_name}' has cyclomatic complexity {result.cyclomatic_complexity} (max: {max_complexity})",
                        severity="warning",
                        value=result.cyclomatic_complexity,
                        threshold=max_complexity,
                    )
                    findings.append(AnalysisTarget(self._rejig, finding))

        return AnalysisTargetList(self._rejig, findings)

    def find_long_functions(self, max_lines: int = 50) -> AnalysisTargetList:
        """Find functions exceeding line count threshold.

        Parameters
        ----------
        max_lines : int
            Maximum allowed lines in a function. Default 50.

        Returns
        -------
        AnalysisTargetList
            Functions exceeding the threshold.
        """
        findings: list[AnalysisTarget] = []

        for file_path in self._rejig.files:
            results, _ = self._analyze_file(file_path)

            for result in results:
                if result.line_count > max_lines:
                    entity = "Method" if result.is_method else "Function"
                    finding = AnalysisFinding(
                        type=AnalysisType.LONG_FUNCTION,
                        file_path=file_path,
                        line_number=result.line_number,
                        name=result.full_name,
                        message=f"{entity} '{result.full_name}' has {result.line_count} lines (max: {max_lines})",
                        severity="warning",
                        value=result.line_count,
                        threshold=max_lines,
                    )
                    findings.append(AnalysisTarget(self._rejig, finding))

        return AnalysisTargetList(self._rejig, findings)

    def find_long_classes(self, max_lines: int = 500) -> AnalysisTargetList:
        """Find classes exceeding line count threshold.

        Parameters
        ----------
        max_lines : int
            Maximum allowed lines in a class. Default 500.

        Returns
        -------
        AnalysisTargetList
            Classes exceeding the threshold.
        """
        findings: list[AnalysisTarget] = []

        for file_path in self._rejig.files:
            try:
                content = file_path.read_text()
                lines = content.splitlines()
                tree = cst.parse_module(content)

                wrapper = cst.MetadataWrapper(tree)
                collector = ClassLengthCollector(file_path)
                wrapper.visit(collector)

                for class_name, _, _ in collector.results:
                    # Find class boundaries
                    start_line = 0
                    for i, line in enumerate(lines, 1):
                        if f"class {class_name}" in line:
                            start_line = i
                            break

                    if start_line == 0:
                        continue

                    # Find end of class
                    indent = len(lines[start_line - 1]) - len(
                        lines[start_line - 1].lstrip()
                    )
                    end_line = start_line
                    for i in range(start_line, len(lines)):
                        line = lines[i]
                        if line.strip():
                            # Check if we've left the class indent
                            current_indent = len(line) - len(line.lstrip())
                            if current_indent <= indent and i > start_line:
                                if not line.strip().startswith("#"):
                                    break
                        end_line = i + 1

                    line_count = end_line - start_line + 1

                    if line_count > max_lines:
                        finding = AnalysisFinding(
                            type=AnalysisType.LONG_CLASS,
                            file_path=file_path,
                            line_number=start_line,
                            name=class_name,
                            message=f"Class '{class_name}' has {line_count} lines (max: {max_lines})",
                            severity="warning",
                            value=line_count,
                            threshold=max_lines,
                        )
                        findings.append(AnalysisTarget(self._rejig, finding))
            except Exception:
                continue

        return AnalysisTargetList(self._rejig, findings)

    def find_deeply_nested(self, max_depth: int = 4) -> AnalysisTargetList:
        """Find functions with excessive nesting depth.

        Parameters
        ----------
        max_depth : int
            Maximum allowed nesting depth. Default 4.

        Returns
        -------
        AnalysisTargetList
            Functions exceeding the threshold.
        """
        findings: list[AnalysisTarget] = []

        for file_path in self._rejig.files:
            _, nesting_results = self._analyze_file(file_path)

            for nesting in nesting_results:
                if nesting.max_depth > max_depth:
                    entity = "Method" if nesting.is_method else "Function"
                    finding = AnalysisFinding(
                        type=AnalysisType.DEEP_NESTING,
                        file_path=file_path,
                        line_number=nesting.line_number,
                        name=nesting.full_name,
                        message=f"{entity} '{nesting.full_name}' has nesting depth {nesting.max_depth} (max: {max_depth})",
                        severity="warning",
                        value=nesting.max_depth,
                        threshold=max_depth,
                    )
                    findings.append(AnalysisTarget(self._rejig, finding))

        return AnalysisTargetList(self._rejig, findings)

    def find_functions_with_many_parameters(
        self, max_params: int = 5
    ) -> AnalysisTargetList:
        """Find functions with too many parameters.

        Parameters
        ----------
        max_params : int
            Maximum allowed parameters. Default 5.

        Returns
        -------
        AnalysisTargetList
            Functions exceeding the threshold.
        """
        findings: list[AnalysisTarget] = []

        for file_path in self._rejig.files:
            results, _ = self._analyze_file(file_path)

            for result in results:
                if result.parameter_count > max_params:
                    entity = "Method" if result.is_method else "Function"
                    finding = AnalysisFinding(
                        type=AnalysisType.TOO_MANY_PARAMETERS,
                        file_path=file_path,
                        line_number=result.line_number,
                        name=result.full_name,
                        message=f"{entity} '{result.full_name}' has {result.parameter_count} parameters (max: {max_params})",
                        severity="info",
                        value=result.parameter_count,
                        threshold=max_params,
                    )
                    findings.append(AnalysisTarget(self._rejig, finding))

        return AnalysisTargetList(self._rejig, findings)

    def find_functions_with_many_branches(
        self, max_branches: int = 10
    ) -> AnalysisTargetList:
        """Find functions with too many branches (if/elif).

        Parameters
        ----------
        max_branches : int
            Maximum allowed branches. Default 10.

        Returns
        -------
        AnalysisTargetList
            Functions exceeding the threshold.
        """
        findings: list[AnalysisTarget] = []

        for file_path in self._rejig.files:
            results, _ = self._analyze_file(file_path)

            for result in results:
                if result.branch_count > max_branches:
                    entity = "Method" if result.is_method else "Function"
                    finding = AnalysisFinding(
                        type=AnalysisType.TOO_MANY_BRANCHES,
                        file_path=file_path,
                        line_number=result.line_number,
                        name=result.full_name,
                        message=f"{entity} '{result.full_name}' has {result.branch_count} branches (max: {max_branches})",
                        severity="info",
                        value=result.branch_count,
                        threshold=max_branches,
                    )
                    findings.append(AnalysisTarget(self._rejig, finding))

        return AnalysisTargetList(self._rejig, findings)

    def find_functions_with_many_returns(
        self, max_returns: int = 5
    ) -> AnalysisTargetList:
        """Find functions with too many return statements.

        Parameters
        ----------
        max_returns : int
            Maximum allowed return statements. Default 5.

        Returns
        -------
        AnalysisTargetList
            Functions exceeding the threshold.
        """
        findings: list[AnalysisTarget] = []

        for file_path in self._rejig.files:
            results, _ = self._analyze_file(file_path)

            for result in results:
                if result.return_count > max_returns:
                    entity = "Method" if result.is_method else "Function"
                    finding = AnalysisFinding(
                        type=AnalysisType.TOO_MANY_RETURNS,
                        file_path=file_path,
                        line_number=result.line_number,
                        name=result.full_name,
                        message=f"{entity} '{result.full_name}' has {result.return_count} return statements (max: {max_returns})",
                        severity="info",
                        value=result.return_count,
                        threshold=max_returns,
                    )
                    findings.append(AnalysisTarget(self._rejig, finding))

        return AnalysisTargetList(self._rejig, findings)

    def find_all_complexity_issues(
        self,
        max_complexity: int = 10,
        max_lines: int = 50,
        max_class_lines: int = 500,
        max_depth: int = 4,
        max_params: int = 5,
    ) -> AnalysisTargetList:
        """Find all complexity issues in the codebase.

        Parameters
        ----------
        max_complexity : int
            Maximum cyclomatic complexity. Default 10.
        max_lines : int
            Maximum lines per function. Default 50.
        max_class_lines : int
            Maximum lines per class. Default 500.
        max_depth : int
            Maximum nesting depth. Default 4.
        max_params : int
            Maximum parameters. Default 5.

        Returns
        -------
        AnalysisTargetList
            All complexity-related findings.
        """
        all_findings: list[AnalysisTarget] = []

        all_findings.extend(self.find_complex_functions(max_complexity)._targets)
        all_findings.extend(self.find_long_functions(max_lines)._targets)
        all_findings.extend(self.find_long_classes(max_class_lines)._targets)
        all_findings.extend(self.find_deeply_nested(max_depth)._targets)
        all_findings.extend(self.find_functions_with_many_parameters(max_params)._targets)

        return AnalysisTargetList(self._rejig, all_findings)
