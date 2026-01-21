"""Code metrics collection and analysis.

Collects various metrics about the codebase:
- Lines of code (total, code, comments, blank)
- Number of classes, functions, methods
- Average complexity scores
- Test coverage gaps
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst

from rejig.analysis.complexity import ComplexityAnalyzer

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


@dataclass
class FileMetrics:
    """Metrics for a single file.

    Attributes
    ----------
    file_path : Path
        Path to the file.
    total_lines : int
        Total number of lines.
    code_lines : int
        Lines containing code.
    comment_lines : int
        Lines containing comments.
    blank_lines : int
        Empty lines.
    class_count : int
        Number of classes.
    function_count : int
        Number of functions.
    method_count : int
        Number of methods.
    import_count : int
        Number of import statements.
    avg_function_length : float
        Average lines per function.
    avg_complexity : float
        Average cyclomatic complexity.
    max_complexity : int
        Maximum cyclomatic complexity.
    has_docstring : bool
        Whether the module has a docstring.
    test_file : bool
        Whether this appears to be a test file.
    """

    file_path: Path
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    class_count: int = 0
    function_count: int = 0
    method_count: int = 0
    import_count: int = 0
    avg_function_length: float = 0.0
    avg_complexity: float = 0.0
    max_complexity: int = 0
    has_docstring: bool = False
    test_file: bool = False


@dataclass
class ModuleMetrics:
    """Aggregated metrics for a module/package.

    Attributes
    ----------
    name : str
        Module name.
    path : Path
        Path to the module directory.
    file_count : int
        Number of Python files.
    total_lines : int
        Total lines of code.
    class_count : int
        Total classes.
    function_count : int
        Total functions.
    method_count : int
        Total methods.
    avg_file_size : float
        Average lines per file.
    avg_complexity : float
        Average cyclomatic complexity.
    max_complexity : int
        Maximum cyclomatic complexity.
    test_coverage_estimate : float
        Estimated test coverage (ratio of test files).
    """

    name: str
    path: Path
    file_count: int = 0
    total_lines: int = 0
    class_count: int = 0
    function_count: int = 0
    method_count: int = 0
    avg_file_size: float = 0.0
    avg_complexity: float = 0.0
    max_complexity: int = 0
    test_coverage_estimate: float = 0.0


class MetricsCollector(cst.CSTVisitor):
    """Collect metrics from a module."""

    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._class_count = 0
        self._function_count = 0
        self._method_count = 0
        self._import_count = 0
        self._has_docstring = False
        self._class_stack: list[str] = []
        self._checked_docstring = False

    def visit_Module(self, node: cst.Module) -> bool:
        # Check for module docstring
        if node.body:
            first = node.body[0]
            if isinstance(first, cst.SimpleStatementLine):
                if first.body and isinstance(first.body[0], cst.Expr):
                    if isinstance(first.body[0].value, (cst.SimpleString, cst.ConcatenatedString)):
                        self._has_docstring = True
        self._checked_docstring = True
        return True

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        self._class_count += 1
        self._class_stack.append(node.name.value)
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        self._class_stack.pop()

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        if self._class_stack:
            self._method_count += 1
        else:
            self._function_count += 1
        return True

    def visit_Import(self, node: cst.Import) -> bool:
        self._import_count += 1
        return False

    def visit_ImportFrom(self, node: cst.ImportFrom) -> bool:
        self._import_count += 1
        return False

    @property
    def class_count(self) -> int:
        return self._class_count

    @property
    def function_count(self) -> int:
        return self._function_count

    @property
    def method_count(self) -> int:
        return self._method_count

    @property
    def import_count(self) -> int:
        return self._import_count

    @property
    def has_docstring(self) -> bool:
        return self._has_docstring


class CodeMetrics:
    """Collect and analyze code metrics for a project.

    Provides methods to:
    - Get metrics for individual files
    - Get aggregated metrics for modules/packages
    - Generate reports
    """

    def __init__(self, rejig: Rejig) -> None:
        self._rejig = rejig
        self._file_metrics_cache: dict[Path, FileMetrics] = {}
        self._complexity_analyzer = ComplexityAnalyzer(rejig)

    def _count_lines(self, content: str) -> tuple[int, int, int, int]:
        """Count different types of lines.

        Returns
        -------
        tuple[int, int, int, int]
            (total, code, comment, blank)
        """
        lines = content.splitlines()
        total = len(lines)
        blank = sum(1 for line in lines if not line.strip())
        comment = sum(1 for line in lines if line.strip().startswith("#"))

        # Code lines = total - blank - pure comment lines
        # (Lines with code and inline comments count as code)
        code = total - blank - comment

        return total, code, comment, blank

    def get_file_metrics(self, file_path: Path) -> FileMetrics:
        """Get metrics for a single file.

        Parameters
        ----------
        file_path : Path
            Path to the Python file.

        Returns
        -------
        FileMetrics
            Metrics for the file.
        """
        if file_path in self._file_metrics_cache:
            return self._file_metrics_cache[file_path]

        metrics = FileMetrics(file_path=file_path)

        try:
            content = file_path.read_text()

            # Count lines
            total, code, comment, blank = self._count_lines(content)
            metrics.total_lines = total
            metrics.code_lines = code
            metrics.comment_lines = comment
            metrics.blank_lines = blank

            # Parse and collect CST metrics
            tree = cst.parse_module(content)
            wrapper = cst.MetadataWrapper(tree)
            collector = MetricsCollector(file_path)
            wrapper.visit(collector)

            metrics.class_count = collector.class_count
            metrics.function_count = collector.function_count
            metrics.method_count = collector.method_count
            metrics.import_count = collector.import_count
            metrics.has_docstring = collector.has_docstring

            # Determine if test file
            metrics.test_file = (
                file_path.name.startswith("test_")
                or file_path.name.endswith("_test.py")
                or "tests" in file_path.parts
            )

            # Get complexity metrics
            complexity_results = self._complexity_analyzer.analyze_all()
            file_results = [
                r for r in complexity_results if r.file_path == file_path
            ]

            if file_results:
                metrics.avg_complexity = sum(
                    r.cyclomatic_complexity for r in file_results
                ) / len(file_results)
                metrics.max_complexity = max(
                    r.cyclomatic_complexity for r in file_results
                )
                metrics.avg_function_length = sum(
                    r.line_count for r in file_results
                ) / len(file_results)

        except Exception:
            pass

        self._file_metrics_cache[file_path] = metrics
        return metrics

    def get_all_file_metrics(self) -> list[FileMetrics]:
        """Get metrics for all files in the project.

        Returns
        -------
        list[FileMetrics]
            Metrics for all Python files.
        """
        return [self.get_file_metrics(f) for f in self._rejig.files]

    def get_module_metrics(self, module_path: Path) -> ModuleMetrics:
        """Get aggregated metrics for a module/package.

        Parameters
        ----------
        module_path : Path
            Path to the module directory.

        Returns
        -------
        ModuleMetrics
            Aggregated metrics for the module.
        """
        metrics = ModuleMetrics(
            name=module_path.name,
            path=module_path,
        )

        # Get all files in this module
        module_files = [
            f
            for f in self._rejig.files
            if f.is_relative_to(module_path)
        ]

        if not module_files:
            return metrics

        file_metrics_list = [self.get_file_metrics(f) for f in module_files]

        metrics.file_count = len(file_metrics_list)
        metrics.total_lines = sum(m.total_lines for m in file_metrics_list)
        metrics.class_count = sum(m.class_count for m in file_metrics_list)
        metrics.function_count = sum(m.function_count for m in file_metrics_list)
        metrics.method_count = sum(m.method_count for m in file_metrics_list)

        if metrics.file_count > 0:
            metrics.avg_file_size = metrics.total_lines / metrics.file_count

        # Calculate complexity averages
        complexities = [
            m.avg_complexity for m in file_metrics_list if m.avg_complexity > 0
        ]
        if complexities:
            metrics.avg_complexity = sum(complexities) / len(complexities)
            metrics.max_complexity = max(
                m.max_complexity for m in file_metrics_list
            )

        # Estimate test coverage (ratio of test files to source files)
        test_files = sum(1 for m in file_metrics_list if m.test_file)
        source_files = metrics.file_count - test_files
        if source_files > 0:
            metrics.test_coverage_estimate = test_files / source_files

        return metrics

    def get_project_summary(self) -> dict:
        """Get a summary of project metrics.

        Returns
        -------
        dict
            Summary metrics for the entire project.
        """
        all_metrics = self.get_all_file_metrics()

        if not all_metrics:
            return {}

        test_files = [m for m in all_metrics if m.test_file]
        source_files = [m for m in all_metrics if not m.test_file]

        summary = {
            "total_files": len(all_metrics),
            "source_files": len(source_files),
            "test_files": len(test_files),
            "total_lines": sum(m.total_lines for m in all_metrics),
            "code_lines": sum(m.code_lines for m in all_metrics),
            "comment_lines": sum(m.comment_lines for m in all_metrics),
            "blank_lines": sum(m.blank_lines for m in all_metrics),
            "total_classes": sum(m.class_count for m in all_metrics),
            "total_functions": sum(m.function_count for m in all_metrics),
            "total_methods": sum(m.method_count for m in all_metrics),
            "files_with_docstrings": sum(1 for m in all_metrics if m.has_docstring),
        }

        # Averages
        if source_files:
            summary["avg_file_size"] = sum(
                m.total_lines for m in source_files
            ) / len(source_files)

            complexities = [m.avg_complexity for m in source_files if m.avg_complexity > 0]
            if complexities:
                summary["avg_complexity"] = sum(complexities) / len(complexities)
                summary["max_complexity"] = max(
                    m.max_complexity for m in source_files
                )

        # Test coverage estimate
        if source_files:
            summary["test_coverage_estimate"] = len(test_files) / len(source_files)

        return summary

    def find_coverage_gaps(self) -> list[Path]:
        """Find source files that don't appear to have corresponding test files.

        Returns
        -------
        list[Path]
            Source files without apparent test coverage.
        """
        all_metrics = self.get_all_file_metrics()

        # Get source files (not in tests directory, not test_*.py)
        source_files = [
            m.file_path
            for m in all_metrics
            if not m.test_file
            and not m.file_path.name.startswith("_")
            and m.file_path.name != "__init__.py"
        ]

        # Get test file names (without test_ prefix and _test.py suffix)
        test_file_names: set[str] = set()
        for m in all_metrics:
            if m.test_file:
                name = m.file_path.stem
                if name.startswith("test_"):
                    test_file_names.add(name[5:])  # Remove test_ prefix
                elif name.endswith("_test"):
                    test_file_names.add(name[:-5])  # Remove _test suffix

        # Find source files without corresponding tests
        coverage_gaps = []
        for source_path in source_files:
            source_name = source_path.stem
            if source_name not in test_file_names:
                coverage_gaps.append(source_path)

        return sorted(coverage_gaps)

    def generate_summary_report(self) -> str:
        """Generate a human-readable summary report.

        Returns
        -------
        str
            Formatted summary report.
        """
        summary = self.get_project_summary()
        if not summary:
            return "No files analyzed."

        lines = [
            "# Code Metrics Summary",
            "",
            "## File Statistics",
            f"- Total files: {summary.get('total_files', 0)}",
            f"- Source files: {summary.get('source_files', 0)}",
            f"- Test files: {summary.get('test_files', 0)}",
            "",
            "## Line Counts",
            f"- Total lines: {summary.get('total_lines', 0):,}",
            f"- Code lines: {summary.get('code_lines', 0):,}",
            f"- Comment lines: {summary.get('comment_lines', 0):,}",
            f"- Blank lines: {summary.get('blank_lines', 0):,}",
            "",
            "## Structure",
            f"- Classes: {summary.get('total_classes', 0)}",
            f"- Functions: {summary.get('total_functions', 0)}",
            f"- Methods: {summary.get('total_methods', 0)}",
            "",
        ]

        if "avg_file_size" in summary:
            lines.extend([
                "## Averages",
                f"- Avg file size: {summary['avg_file_size']:.1f} lines",
            ])
            if "avg_complexity" in summary:
                lines.append(
                    f"- Avg complexity: {summary['avg_complexity']:.1f}"
                )
            if "max_complexity" in summary:
                lines.append(
                    f"- Max complexity: {summary['max_complexity']}"
                )

        if "test_coverage_estimate" in summary:
            lines.extend([
                "",
                "## Test Coverage (Estimate)",
                f"- Test/source ratio: {summary['test_coverage_estimate']:.1%}",
            ])

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Export all metrics as a dictionary.

        Returns
        -------
        dict
            Complete metrics data.
        """
        return {
            "summary": self.get_project_summary(),
            "files": [
                {
                    "path": str(m.file_path),
                    "total_lines": m.total_lines,
                    "code_lines": m.code_lines,
                    "comment_lines": m.comment_lines,
                    "blank_lines": m.blank_lines,
                    "classes": m.class_count,
                    "functions": m.function_count,
                    "methods": m.method_count,
                    "imports": m.import_count,
                    "avg_complexity": m.avg_complexity,
                    "max_complexity": m.max_complexity,
                    "has_docstring": m.has_docstring,
                    "is_test": m.test_file,
                }
                for m in self.get_all_file_metrics()
            ],
            "coverage_gaps": [str(p) for p in self.find_coverage_gaps()],
        }
