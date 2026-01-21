"""
Tests for rejig.analysis.reporter module.

This module tests report generation for code analysis:
- AnalysisReport dataclass for comprehensive reports
- AnalysisReporter for generating various report formats
- API documentation generation
- Module structure documentation
- Complexity reports
- Coverage gap reports

Coverage targets:
- AnalysisReport creation and properties
- Full report generation
- API summary generation
- Module structure generation
- Complexity report JSON generation
- Coverage gap report generation
"""
from __future__ import annotations

import json
import textwrap
from datetime import datetime
from pathlib import Path

import pytest

from rejig import Rejig
from rejig.analysis.reporter import AnalysisReport, AnalysisReporter
from rejig.analysis.targets import AnalysisTargetList
from rejig.core.results import Result


# =============================================================================
# AnalysisReport Tests
# =============================================================================

class TestAnalysisReport:
    """Tests for AnalysisReport dataclass.

    AnalysisReport holds the complete results of a code analysis run.
    """

    def test_required_fields(self, tmp_path: Path):
        """
        AnalysisReport should require timestamp and project root.
        """
        report = AnalysisReport(
            generated_at=datetime.now(),
            project_root=tmp_path,
        )

        assert report.generated_at is not None
        assert report.project_root == tmp_path

    def test_optional_fields_have_defaults(self, tmp_path: Path):
        """
        AnalysisReport optional fields should have sensible defaults.
        """
        report = AnalysisReport(
            generated_at=datetime.now(),
            project_root=tmp_path,
        )

        assert report.summary == {}
        assert report.complexity_issues is None
        assert report.pattern_issues is None
        assert report.dead_code is None
        assert report.coverage_gaps == []

    def test_total_issues_empty(self, tmp_path: Path):
        """
        total_issues should be 0 when no issues found.
        """
        report = AnalysisReport(
            generated_at=datetime.now(),
            project_root=tmp_path,
        )

        assert report.total_issues == 0

    def test_total_issues_with_findings(self, tmp_path: Path):
        """
        total_issues should sum all finding categories.
        """
        rj = Rejig(str(tmp_path))

        # Create mock target lists
        from rejig.analysis.targets import AnalysisFinding, AnalysisTarget, AnalysisType

        findings = [
            AnalysisFinding(
                type=AnalysisType.HIGH_CYCLOMATIC_COMPLEXITY,
                file_path=Path("test.py"),
                line_number=1,
            ),
            AnalysisFinding(
                type=AnalysisType.LONG_FUNCTION,
                file_path=Path("test.py"),
                line_number=2,
            ),
        ]
        complexity = AnalysisTargetList(
            rj, [AnalysisTarget(rj, f) for f in findings]
        )

        pattern_finding = AnalysisFinding(
            type=AnalysisType.BARE_EXCEPT,
            file_path=Path("test.py"),
            line_number=3,
        )
        patterns = AnalysisTargetList(
            rj, [AnalysisTarget(rj, pattern_finding)]
        )

        report = AnalysisReport(
            generated_at=datetime.now(),
            project_root=tmp_path,
            complexity_issues=complexity,
            pattern_issues=patterns,
        )

        assert report.total_issues == 3

    def test_str_format(self, tmp_path: Path):
        """
        __str__ should produce a readable report.
        """
        report = AnalysisReport(
            generated_at=datetime.now(),
            project_root=tmp_path,
            summary={"total_files": 10, "total_lines": 1000},
        )

        output = str(report)

        assert "# Code Analysis Report" in output
        assert "Generated:" in output
        assert "Project:" in output
        assert "Summary" in output

    def test_str_with_findings(self, tmp_path: Path):
        """
        __str__ should include findings when present.
        """
        rj = Rejig(str(tmp_path))

        from rejig.analysis.targets import AnalysisFinding, AnalysisTarget, AnalysisType

        finding = AnalysisFinding(
            type=AnalysisType.HIGH_CYCLOMATIC_COMPLEXITY,
            file_path=Path("test.py"),
            line_number=10,
            message="Complexity is too high",
        )
        complexity = AnalysisTargetList(
            rj, [AnalysisTarget(rj, finding)]
        )

        report = AnalysisReport(
            generated_at=datetime.now(),
            project_root=tmp_path,
            complexity_issues=complexity,
        )

        output = str(report)

        assert "Complexity Issues" in output
        assert "1 issues" in output


# =============================================================================
# AnalysisReporter Tests
# =============================================================================

class TestAnalysisReporter:
    """Tests for AnalysisReporter class.

    AnalysisReporter generates various analysis reports.
    """

    @pytest.fixture
    def create_project(self, tmp_path: Path):
        """Factory fixture to create a project with specific files."""
        def _create(files: dict[str, str]):
            for name, content in files.items():
                file_path = tmp_path / name
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)
            return Rejig(str(tmp_path))
        return _create

    def test_generate_full_report(self, create_project):
        """
        generate_full_report should return an AnalysisReport.
        """
        rj = create_project({
            "app.py": textwrap.dedent('''\
                """App module."""

                def main():
                    pass
            '''),
        })

        reporter = AnalysisReporter(rj)
        report = reporter.generate_full_report()

        assert isinstance(report, AnalysisReport)
        assert report.generated_at is not None
        assert report.project_root == rj.root

    def test_generate_full_report_includes_all_categories(self, create_project):
        """
        generate_full_report should include all enabled categories.
        """
        rj = create_project({
            "app.py": textwrap.dedent('''\
                def func(x):
                    return x
            '''),
        })

        reporter = AnalysisReporter(rj)
        report = reporter.generate_full_report(
            include_complexity=True,
            include_patterns=True,
            include_dead_code=True,
            include_coverage=True,
        )

        assert report.complexity_issues is not None
        assert report.pattern_issues is not None
        assert report.dead_code is not None
        assert report.coverage_gaps is not None

    def test_generate_full_report_selective(self, create_project):
        """
        generate_full_report should respect disabled categories.
        """
        rj = create_project({
            "app.py": "x = 1\n",
        })

        reporter = AnalysisReporter(rj)
        report = reporter.generate_full_report(
            include_complexity=False,
            include_patterns=False,
            include_dead_code=True,
            include_coverage=False,
        )

        assert report.complexity_issues is None
        assert report.pattern_issues is None
        assert report.dead_code is not None
        assert report.coverage_gaps == []

    def test_generate_api_summary(self, create_project):
        """
        generate_api_summary should return API documentation.
        """
        rj = create_project({
            "mymodule.py": textwrap.dedent('''\
                """Module docstring."""

                class MyClass:
                    """A sample class."""

                    def method(self, x: int) -> int:
                        """Process x."""
                        return x * 2

                def standalone(a: str, b: str) -> str:
                    """Concatenate strings."""
                    return a + b
            '''),
        })

        reporter = AnalysisReporter(rj)
        result = reporter.generate_api_summary()

        assert result.success is True
        assert "API summary generated" in result.message
        assert result.data is not None
        assert "# API Summary" in result.data
        assert "MyClass" in result.data
        assert "standalone" in result.data

    def test_generate_api_summary_to_file(self, create_project, tmp_path: Path):
        """
        generate_api_summary should write to file when output_path given.
        """
        rj = create_project({
            "app.py": textwrap.dedent('''\
                def helper():
                    pass
            '''),
        })

        output_path = tmp_path / "api.md"
        reporter = AnalysisReporter(rj)
        result = reporter.generate_api_summary(output_path=output_path)

        assert result.success is True
        assert output_path.exists()
        content = output_path.read_text()
        assert "# API Summary" in content

    def test_generate_module_structure(self, create_project):
        """
        generate_module_structure should return module tree.
        """
        rj = create_project({
            "mypackage/__init__.py": "",
            "mypackage/core.py": "x = 1\n",
            "mypackage/utils.py": "y = 2\n",
        })

        reporter = AnalysisReporter(rj)
        result = reporter.generate_module_structure()

        assert result.success is True
        assert "Module structure generated" in result.message
        assert result.data is not None
        assert "# Module Structure" in result.data
        # Should contain file names
        assert "core.py" in result.data or "mypackage" in result.data

    def test_generate_module_structure_to_file(self, create_project, tmp_path: Path):
        """
        generate_module_structure should write to file when output_path given.
        """
        rj = create_project({
            "app.py": "x = 1\n",
        })

        output_path = tmp_path / "structure.md"
        reporter = AnalysisReporter(rj)
        result = reporter.generate_module_structure(output_path=output_path)

        assert result.success is True
        assert output_path.exists()

    def test_generate_complexity_report(self, create_project):
        """
        generate_complexity_report should return complexity data as JSON.
        """
        rj = create_project({
            "app.py": textwrap.dedent('''\
                def simple():
                    return 1

                def complex_func(x):
                    if x > 0:
                        if x > 10:
                            return "high"
                        return "low"
                    return "zero"
            '''),
        })

        reporter = AnalysisReporter(rj)
        result = reporter.generate_complexity_report()

        assert result.success is True
        assert result.data is not None
        assert "generated_at" in result.data
        assert "summary" in result.data
        assert "functions" in result.data

        # Summary should have statistics
        summary = result.data["summary"]
        assert "total_functions" in summary
        assert "avg_complexity" in summary

    def test_generate_complexity_report_to_file(self, create_project, tmp_path: Path):
        """
        generate_complexity_report should write JSON to file.
        """
        rj = create_project({
            "app.py": "def func(): pass\n",
        })

        output_path = tmp_path / "complexity.json"
        reporter = AnalysisReporter(rj)
        result = reporter.generate_complexity_report(output_path=output_path)

        assert result.success is True
        assert output_path.exists()

        # Verify JSON is valid
        data = json.loads(output_path.read_text())
        assert "summary" in data

    def test_generate_coverage_gaps_report(self, create_project):
        """
        generate_coverage_gaps_report should list untested files.
        """
        rj = create_project({
            "app.py": "x = 1\n",
            "utils.py": "y = 2\n",
            "test_app.py": "def test_x(): pass\n",
        })

        reporter = AnalysisReporter(rj)
        result = reporter.generate_coverage_gaps_report()

        assert result.success is True
        assert result.data is not None
        assert "gaps" in result.data
        # utils.py has no test
        gap_names = [Path(p).name for p in result.data["gaps"]]
        assert "utils.py" in gap_names

    def test_generate_coverage_gaps_report_to_file(self, create_project, tmp_path: Path):
        """
        generate_coverage_gaps_report should write to file.
        """
        rj = create_project({
            "app.py": "x = 1\n",
        })

        output_path = tmp_path / "gaps.md"
        reporter = AnalysisReporter(rj)
        result = reporter.generate_coverage_gaps_report(output_path=output_path)

        assert result.success is True
        assert output_path.exists()
        content = output_path.read_text()
        assert "Test Coverage Gaps" in content

    def test_empty_project(self, tmp_path: Path):
        """
        Reporter should handle empty projects gracefully.
        """
        rj = Rejig(str(tmp_path))
        reporter = AnalysisReporter(rj)

        # All methods should work without errors
        full_report = reporter.generate_full_report()
        assert isinstance(full_report, AnalysisReport)

        api_result = reporter.generate_api_summary()
        assert api_result.success is True

        structure_result = reporter.generate_module_structure()
        assert structure_result.success is True

    def test_handles_syntax_errors(self, create_project):
        """
        Reporter should handle files with syntax errors.
        """
        rj = create_project({
            "good.py": "x = 1\n",
            "bad.py": "def broken(:\n    pass",
        })

        reporter = AnalysisReporter(rj)
        # Should not raise
        report = reporter.generate_full_report()

        assert isinstance(report, AnalysisReport)


# =============================================================================
# APICollector Tests
# =============================================================================

class TestAPICollector:
    """Tests for APICollector CST visitor.

    APICollector extracts public API elements from a module.
    """

    def test_collects_public_classes(self, tmp_path: Path):
        """
        APICollector should find public classes.
        """
        import libcst as cst
        from rejig.analysis.reporter import APICollector

        code = textwrap.dedent('''\
            class PublicClass:
                """A public class."""
                pass

            class _PrivateClass:
                pass
        ''')

        tree = cst.parse_module(code)
        collector = APICollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        class_names = [c["name"] for c in collector.classes]
        assert "PublicClass" in class_names
        assert "_PrivateClass" not in class_names

    def test_collects_public_functions(self, tmp_path: Path):
        """
        APICollector should find public module-level functions.
        """
        import libcst as cst
        from rejig.analysis.reporter import APICollector

        code = textwrap.dedent('''\
            def public_func():
                """A public function."""
                pass

            def _private_func():
                pass
        ''')

        tree = cst.parse_module(code)
        collector = APICollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        func_names = [f["name"] for f in collector.functions]
        assert "public_func" in func_names
        assert "_private_func" not in func_names

    def test_extracts_docstrings(self, tmp_path: Path):
        """
        APICollector should extract docstrings.
        """
        import libcst as cst
        from rejig.analysis.reporter import APICollector

        code = textwrap.dedent('''\
            class MyClass:
                """This is the class docstring."""
                pass
        ''')

        tree = cst.parse_module(code)
        collector = APICollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        assert len(collector.classes) == 1
        assert "class docstring" in collector.classes[0]["docstring"]

    def test_extracts_function_signatures(self, tmp_path: Path):
        """
        APICollector should extract function signatures.
        """
        import libcst as cst
        from rejig.analysis.reporter import APICollector

        code = textwrap.dedent('''\
            def my_func(a: int, b: str = "default") -> bool:
                pass
        ''')

        tree = cst.parse_module(code)
        collector = APICollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        assert len(collector.functions) == 1
        sig = collector.functions[0]["signature"]
        assert "a" in sig
        assert "int" in sig
        # Default values shown as ...
        assert "..." in sig or "default" in sig

    def test_extracts_class_methods(self, tmp_path: Path):
        """
        APICollector should extract public methods from classes.
        """
        import libcst as cst
        from rejig.analysis.reporter import APICollector

        code = textwrap.dedent('''\
            class MyClass:
                def public_method(self):
                    pass

                def _private_method(self):
                    pass

                def __init__(self):
                    pass
        ''')

        tree = cst.parse_module(code)
        collector = APICollector(tmp_path / "test.py")
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(collector)

        method_names = [m["name"] for m in collector.classes[0]["methods"]]
        assert "public_method" in method_names
        assert "_private_method" not in method_names
        # Dunder methods should be included
        assert "__init__" in method_names


# =============================================================================
# Integration Tests
# =============================================================================

class TestAnalysisReporterIntegration:
    """Integration tests for analysis reporting workflow."""

    def test_full_analysis_workflow(self, tmp_path: Path):
        """
        Complete workflow: generate report, export to files.
        """
        # Create a small project
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "core.py").write_text(textwrap.dedent('''\
            """Core module."""

            class Engine:
                """Main engine class."""

                def process(self, data: list) -> list:
                    """Process data."""
                    result = []
                    for item in data:
                        if item > 0:
                            result.append(item * 2)
                    return result

            def initialize() -> Engine:
                """Create an engine."""
                return Engine()
        '''))

        rj = Rejig(str(tmp_path))
        reporter = AnalysisReporter(rj)

        # Generate full report
        report = reporter.generate_full_report()
        assert isinstance(report, AnalysisReport)
        report_str = str(report)
        assert "# Code Analysis Report" in report_str

        # Generate API summary
        api_result = reporter.generate_api_summary()
        assert api_result.success is True
        assert "Engine" in api_result.data

        # Generate complexity report
        complexity_result = reporter.generate_complexity_report()
        assert complexity_result.success is True
        assert len(complexity_result.data["functions"]) >= 1

        # Export all to files
        output_dir = tmp_path / "reports"
        output_dir.mkdir()

        reporter.generate_api_summary(output_path=output_dir / "api.md")
        reporter.generate_module_structure(output_path=output_dir / "structure.md")
        reporter.generate_complexity_report(output_path=output_dir / "complexity.json")
        reporter.generate_coverage_gaps_report(output_path=output_dir / "coverage.md")

        assert (output_dir / "api.md").exists()
        assert (output_dir / "structure.md").exists()
        assert (output_dir / "complexity.json").exists()
        assert (output_dir / "coverage.md").exists()
