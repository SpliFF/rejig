"""Report generation for code analysis.

Generates various reports:
- API summaries
- Module structure documentation
- Complexity reports
- Coverage gap reports
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst

from rejig.analysis.complexity import ComplexityAnalyzer
from rejig.analysis.dead_code import DeadCodeAnalyzer
from rejig.analysis.metrics import CodeMetrics
from rejig.analysis.patterns import PatternFinder
from rejig.analysis.targets import AnalysisTargetList, AnalysisType
from rejig.core.results import Result

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


@dataclass
class AnalysisReport:
    """A comprehensive code analysis report.

    Attributes
    ----------
    generated_at : datetime
        When the report was generated.
    project_root : Path
        Root path of the analyzed project.
    summary : dict
        Summary statistics.
    complexity_issues : AnalysisTargetList
        Complexity-related findings.
    pattern_issues : AnalysisTargetList
        Pattern-related findings.
    dead_code : AnalysisTargetList
        Dead code findings.
    coverage_gaps : list[Path]
        Files without test coverage.
    """

    generated_at: datetime
    project_root: Path
    summary: dict = field(default_factory=dict)
    complexity_issues: AnalysisTargetList | None = None
    pattern_issues: AnalysisTargetList | None = None
    dead_code: AnalysisTargetList | None = None
    coverage_gaps: list[Path] = field(default_factory=list)

    def __str__(self) -> str:
        """Generate a human-readable report."""
        lines = [
            "# Code Analysis Report",
            f"Generated: {self.generated_at.isoformat()}",
            f"Project: {self.project_root}",
            "",
        ]

        # Summary
        if self.summary:
            lines.extend([
                "## Summary",
                f"- Files analyzed: {self.summary.get('total_files', 0)}",
                f"- Total lines: {self.summary.get('total_lines', 0):,}",
                f"- Classes: {self.summary.get('total_classes', 0)}",
                f"- Functions: {self.summary.get('total_functions', 0)}",
                "",
            ])

        # Issues
        if self.complexity_issues:
            lines.extend([
                "## Complexity Issues",
                f"Found {len(self.complexity_issues)} issues",
            ])
            for finding in self.complexity_issues[:10]:  # Show top 10
                lines.append(f"- {finding.location}: {finding.message}")
            if len(self.complexity_issues) > 10:
                lines.append(f"  ... and {len(self.complexity_issues) - 10} more")
            lines.append("")

        if self.pattern_issues:
            lines.extend([
                "## Pattern Issues",
                f"Found {len(self.pattern_issues)} issues",
            ])
            for finding in self.pattern_issues[:10]:
                lines.append(f"- {finding.location}: {finding.message}")
            if len(self.pattern_issues) > 10:
                lines.append(f"  ... and {len(self.pattern_issues) - 10} more")
            lines.append("")

        if self.dead_code:
            lines.extend([
                "## Dead Code",
                f"Found {len(self.dead_code)} potential issues",
            ])
            for finding in self.dead_code[:10]:
                lines.append(f"- {finding.location}: {finding.message}")
            if len(self.dead_code) > 10:
                lines.append(f"  ... and {len(self.dead_code) - 10} more")
            lines.append("")

        if self.coverage_gaps:
            lines.extend([
                "## Coverage Gaps",
                f"Found {len(self.coverage_gaps)} files without tests:",
            ])
            for path in self.coverage_gaps[:10]:
                lines.append(f"- {path}")
            if len(self.coverage_gaps) > 10:
                lines.append(f"  ... and {len(self.coverage_gaps) - 10} more")

        return "\n".join(lines)

    @property
    def total_issues(self) -> int:
        """Total number of issues found."""
        total = 0
        if self.complexity_issues:
            total += len(self.complexity_issues)
        if self.pattern_issues:
            total += len(self.pattern_issues)
        if self.dead_code:
            total += len(self.dead_code)
        return total


class APICollector(cst.CSTVisitor):
    """Collect public API elements from a module."""

    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._classes: list[dict] = []
        self._functions: list[dict] = []
        self._constants: list[dict] = []
        self._current_class: dict | None = None
        self._class_stack: list[str] = []

    def _get_docstring(self, body: cst.BaseSuite) -> str | None:
        """Extract docstring from a body."""
        if isinstance(body, cst.IndentedBlock) and body.body:
            first = body.body[0]
            if isinstance(first, cst.SimpleStatementLine) and first.body:
                if isinstance(first.body[0], cst.Expr):
                    val = first.body[0].value
                    if isinstance(val, cst.SimpleString):
                        # Remove quotes and clean up
                        s = val.value
                        if s.startswith('"""') or s.startswith("'''"):
                            return s[3:-3].strip()
                        return s[1:-1].strip()
        return None

    def _get_signature(self, node: cst.FunctionDef) -> str:
        """Get function signature as string."""
        params = []
        for param in node.params.params:
            p = param.name.value
            if param.annotation:
                p += ": " + cst.Module(body=[]).code_for_node(param.annotation.annotation)
            if param.default:
                p += " = ..."
            params.append(p)

        if node.params.star_arg and isinstance(node.params.star_arg, cst.Param):
            p = "*" + node.params.star_arg.name.value
            params.append(p)

        for param in node.params.kwonly_params:
            p = param.name.value
            if param.annotation:
                p += ": " + cst.Module(body=[]).code_for_node(param.annotation.annotation)
            if param.default:
                p += " = ..."
            params.append(p)

        if node.params.star_kwarg:
            p = "**" + node.params.star_kwarg.name.value
            params.append(p)

        ret = ""
        if node.returns:
            ret = " -> " + cst.Module(body=[]).code_for_node(node.returns.annotation)

        return f"({', '.join(params)}){ret}"

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        name = node.name.value
        # Skip private classes
        if name.startswith("_"):
            self._class_stack.append(name)
            return True

        docstring = self._get_docstring(node.body)

        # Get base classes
        bases = []
        for arg in node.bases:
            if isinstance(arg.value, cst.Name):
                bases.append(arg.value.value)
            elif isinstance(arg.value, cst.Attribute):
                bases.append(cst.Module(body=[]).code_for_node(arg.value))

        class_info = {
            "name": name,
            "bases": bases,
            "docstring": docstring,
            "methods": [],
            "attributes": [],
        }

        self._classes.append(class_info)
        self._current_class = class_info
        self._class_stack.append(name)
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        self._class_stack.pop()
        if not self._class_stack:
            self._current_class = None

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        name = node.name.value
        # Skip private functions (but allow dunder methods)
        if name.startswith("_") and not name.startswith("__"):
            return True

        docstring = self._get_docstring(node.body)
        signature = self._get_signature(node)

        func_info = {
            "name": name,
            "signature": signature,
            "docstring": docstring,
            "decorators": [
                cst.Module(body=[]).code_for_node(d.decorator)
                for d in node.decorators
            ],
        }

        if self._current_class:
            self._current_class["methods"].append(func_info)
        elif not self._class_stack:  # Top-level function
            self._functions.append(func_info)

        return True

    def visit_AnnAssign(self, node: cst.AnnAssign) -> bool:
        # Track class attributes or module constants
        if isinstance(node.target, cst.Name):
            name = node.target.value
            if name.startswith("_"):
                return False

            annotation = cst.Module(body=[]).code_for_node(node.annotation.annotation)

            if self._current_class:
                self._current_class["attributes"].append({
                    "name": name,
                    "type": annotation,
                })
            elif not self._class_stack and name.isupper():
                self._constants.append({
                    "name": name,
                    "type": annotation,
                })

        return False

    @property
    def classes(self) -> list[dict]:
        return self._classes

    @property
    def functions(self) -> list[dict]:
        return self._functions

    @property
    def constants(self) -> list[dict]:
        return self._constants


class AnalysisReporter:
    """Generate analysis reports for the codebase.

    Provides methods to generate various report formats.
    """

    def __init__(self, rejig: Rejig) -> None:
        self._rejig = rejig
        self._complexity_analyzer = ComplexityAnalyzer(rejig)
        self._pattern_finder = PatternFinder(rejig)
        self._dead_code_analyzer = DeadCodeAnalyzer(rejig)
        self._metrics = CodeMetrics(rejig)

    def generate_full_report(
        self,
        include_complexity: bool = True,
        include_patterns: bool = True,
        include_dead_code: bool = True,
        include_coverage: bool = True,
    ) -> AnalysisReport:
        """Generate a comprehensive analysis report.

        Parameters
        ----------
        include_complexity : bool
            Include complexity analysis. Default True.
        include_patterns : bool
            Include pattern analysis. Default True.
        include_dead_code : bool
            Include dead code analysis. Default True.
        include_coverage : bool
            Include coverage gap analysis. Default True.

        Returns
        -------
        AnalysisReport
            The complete analysis report.
        """
        report = AnalysisReport(
            generated_at=datetime.now(),
            project_root=self._rejig.root,
            summary=self._metrics.get_project_summary(),
        )

        if include_complexity:
            report.complexity_issues = self._complexity_analyzer.find_all_complexity_issues()

        if include_patterns:
            report.pattern_issues = self._pattern_finder.find_all_patterns()

        if include_dead_code:
            report.dead_code = self._dead_code_analyzer.find_all_dead_code()

        if include_coverage:
            report.coverage_gaps = self._metrics.find_coverage_gaps()

        return report

    def generate_api_summary(self, output_path: Path | str | None = None) -> Result:
        """Generate API documentation summary.

        Parameters
        ----------
        output_path : Path | str | None
            Path to write the summary. If None, returns in result.data.

        Returns
        -------
        Result
            Result containing the generated documentation.
        """
        lines = [
            "# API Summary",
            f"Generated: {datetime.now().isoformat()}",
            "",
        ]

        for file_path in sorted(self._rejig.files):
            try:
                content = file_path.read_text()
                tree = cst.parse_module(content)

                wrapper = cst.MetadataWrapper(tree)
                collector = APICollector(file_path)
                wrapper.visit(collector)

                if not collector.classes and not collector.functions:
                    continue

                # Get relative path
                try:
                    rel_path = file_path.relative_to(self._rejig.root)
                except ValueError:
                    rel_path = file_path

                lines.append(f"## {rel_path}")
                lines.append("")

                # Constants
                if collector.constants:
                    lines.append("### Constants")
                    for const in collector.constants:
                        lines.append(f"- `{const['name']}: {const['type']}`")
                    lines.append("")

                # Functions
                if collector.functions:
                    lines.append("### Functions")
                    for func in collector.functions:
                        lines.append(f"#### `{func['name']}{func['signature']}`")
                        if func["decorators"]:
                            lines.append(f"*Decorators: {', '.join(func['decorators'])}*")
                        if func["docstring"]:
                            lines.append(f"> {func['docstring'][:200]}...")
                        lines.append("")

                # Classes
                for cls in collector.classes:
                    bases = f"({', '.join(cls['bases'])})" if cls["bases"] else ""
                    lines.append(f"### Class `{cls['name']}{bases}`")
                    if cls["docstring"]:
                        lines.append(f"> {cls['docstring'][:200]}...")
                    lines.append("")

                    if cls["attributes"]:
                        lines.append("#### Attributes")
                        for attr in cls["attributes"]:
                            lines.append(f"- `{attr['name']}: {attr['type']}`")
                        lines.append("")

                    if cls["methods"]:
                        lines.append("#### Methods")
                        for method in cls["methods"]:
                            lines.append(f"- `{method['name']}{method['signature']}`")
                            if method["docstring"]:
                                doc = method["docstring"][:100]
                                lines.append(f"  > {doc}...")
                        lines.append("")

                lines.append("---")
                lines.append("")

            except Exception:
                continue

        content = "\n".join(lines)

        if output_path:
            output_path = Path(output_path)
            try:
                output_path.write_text(content)
                return Result(
                    success=True,
                    message=f"API summary written to {output_path}",
                    files_changed=[output_path],
                )
            except Exception as e:
                return Result(
                    success=False,
                    message=f"Failed to write API summary: {e}",
                )

        return Result(
            success=True,
            message="API summary generated",
            data=content,
        )

    def generate_module_structure(self, output_path: Path | str | None = None) -> Result:
        """Generate module structure documentation.

        Parameters
        ----------
        output_path : Path | str | None
            Path to write the structure. If None, returns in result.data.

        Returns
        -------
        Result
            Result containing the generated documentation.
        """
        lines = [
            "# Module Structure",
            f"Generated: {datetime.now().isoformat()}",
            "",
            "```",
        ]

        # Build tree structure
        tree: dict = {}
        for file_path in sorted(self._rejig.files):
            try:
                rel_path = file_path.relative_to(self._rejig.root)
            except ValueError:
                rel_path = file_path

            parts = rel_path.parts
            current = tree
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = None

        def format_tree(node: dict, prefix: str = "") -> list[str]:
            result = []
            items = sorted(node.items(), key=lambda x: (x[1] is not None, x[0]))
            for i, (name, subtree) in enumerate(items):
                is_last = i == len(items) - 1
                connector = "└── " if is_last else "├── "
                result.append(f"{prefix}{connector}{name}")
                if subtree is not None:
                    extension = "    " if is_last else "│   "
                    result.extend(format_tree(subtree, prefix + extension))
            return result

        lines.extend(format_tree(tree))
        lines.extend([
            "```",
            "",
            "## Statistics",
            "",
        ])

        # Add statistics per top-level directory
        summary = self._metrics.get_project_summary()
        lines.extend([
            f"- Total files: {summary.get('total_files', 0)}",
            f"- Total lines: {summary.get('total_lines', 0):,}",
            f"- Classes: {summary.get('total_classes', 0)}",
            f"- Functions: {summary.get('total_functions', 0)}",
        ])

        content = "\n".join(lines)

        if output_path:
            output_path = Path(output_path)
            try:
                output_path.write_text(content)
                return Result(
                    success=True,
                    message=f"Module structure written to {output_path}",
                    files_changed=[output_path],
                )
            except Exception as e:
                return Result(
                    success=False,
                    message=f"Failed to write module structure: {e}",
                )

        return Result(
            success=True,
            message="Module structure generated",
            data=content,
        )

    def generate_complexity_report(
        self, output_path: Path | str | None = None
    ) -> Result:
        """Generate a complexity analysis report as JSON.

        Parameters
        ----------
        output_path : Path | str | None
            Path to write the report. If None, returns in result.data.

        Returns
        -------
        Result
            Result containing the complexity data.
        """
        results = self._complexity_analyzer.analyze_all()

        data = {
            "generated_at": datetime.now().isoformat(),
            "project_root": str(self._rejig.root),
            "summary": {
                "total_functions": len(results),
                "avg_complexity": (
                    sum(r.cyclomatic_complexity for r in results) / len(results)
                    if results
                    else 0
                ),
                "max_complexity": max(
                    (r.cyclomatic_complexity for r in results), default=0
                ),
                "high_complexity_count": sum(
                    1 for r in results if r.cyclomatic_complexity > 10
                ),
            },
            "functions": [
                {
                    "name": r.full_name,
                    "file": str(r.file_path),
                    "line": r.line_number,
                    "cyclomatic_complexity": r.cyclomatic_complexity,
                    "line_count": r.line_count,
                    "parameter_count": r.parameter_count,
                    "branch_count": r.branch_count,
                    "return_count": r.return_count,
                }
                for r in results
            ],
        }

        if output_path:
            output_path = Path(output_path)
            try:
                output_path.write_text(json.dumps(data, indent=2))
                return Result(
                    success=True,
                    message=f"Complexity report written to {output_path}",
                    files_changed=[output_path],
                )
            except Exception as e:
                return Result(
                    success=False,
                    message=f"Failed to write complexity report: {e}",
                )

        return Result(
            success=True,
            message="Complexity report generated",
            data=data,
        )

    def generate_coverage_gaps_report(
        self, output_path: Path | str | None = None
    ) -> Result:
        """Generate a report of files without test coverage.

        Parameters
        ----------
        output_path : Path | str | None
            Path to write the report. If None, returns in result.data.

        Returns
        -------
        Result
            Result containing the coverage gap data.
        """
        gaps = self._metrics.find_coverage_gaps()

        lines = [
            "# Test Coverage Gaps",
            f"Generated: {datetime.now().isoformat()}",
            "",
            f"Found {len(gaps)} source files without corresponding test files:",
            "",
        ]

        for path in gaps:
            try:
                rel_path = path.relative_to(self._rejig.root)
            except ValueError:
                rel_path = path
            lines.append(f"- {rel_path}")

        content = "\n".join(lines)

        if output_path:
            output_path = Path(output_path)
            try:
                output_path.write_text(content)
                return Result(
                    success=True,
                    message=f"Coverage gaps report written to {output_path}",
                    files_changed=[output_path],
                )
            except Exception as e:
                return Result(
                    success=False,
                    message=f"Failed to write coverage gaps report: {e}",
                )

        return Result(
            success=True,
            message="Coverage gaps report generated",
            data={"gaps": [str(p) for p in gaps]},
        )
