"""
Tests for rejig.analysis.metrics module.

This module tests code metrics collection and analysis:
- FileMetrics for individual file statistics
- ModuleMetrics for aggregated module statistics
- CodeMetrics for project-wide analysis

CodeMetrics collects various measurements about code:
- Line counts (total, code, comment, blank)
- Structure counts (classes, functions, methods)
- Complexity averages
- Test coverage estimates

Coverage targets:
- Line counting and categorization
- MetricsCollector CST visitor
- File-level metrics collection
- Module-level aggregation
- Project summary generation
- Coverage gap detection
- Report generation
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig import Rejig
from rejig.analysis.metrics import CodeMetrics, FileMetrics, ModuleMetrics


# =============================================================================
# FileMetrics Tests
# =============================================================================

class TestFileMetrics:
    """Tests for FileMetrics dataclass.

    FileMetrics holds metrics for a single Python file.
    """

    def test_default_values(self):
        """
        FileMetrics should have sensible defaults.
        """
        metrics = FileMetrics(file_path=Path("test.py"))

        assert metrics.file_path == Path("test.py")
        assert metrics.total_lines == 0
        assert metrics.code_lines == 0
        assert metrics.comment_lines == 0
        assert metrics.blank_lines == 0
        assert metrics.class_count == 0
        assert metrics.function_count == 0
        assert metrics.method_count == 0
        assert metrics.has_docstring is False
        assert metrics.test_file is False

    def test_all_fields_settable(self):
        """
        FileMetrics should allow setting all fields.
        """
        metrics = FileMetrics(
            file_path=Path("app.py"),
            total_lines=100,
            code_lines=70,
            comment_lines=20,
            blank_lines=10,
            class_count=2,
            function_count=5,
            method_count=10,
            import_count=8,
            avg_function_length=15.0,
            avg_complexity=3.5,
            max_complexity=8,
            has_docstring=True,
            test_file=False,
        )

        assert metrics.total_lines == 100
        assert metrics.code_lines == 70
        assert metrics.avg_complexity == 3.5


# =============================================================================
# ModuleMetrics Tests
# =============================================================================

class TestModuleMetrics:
    """Tests for ModuleMetrics dataclass.

    ModuleMetrics holds aggregated metrics for a module/package.
    """

    def test_default_values(self):
        """
        ModuleMetrics should have sensible defaults.
        """
        metrics = ModuleMetrics(name="mymodule", path=Path("src/mymodule"))

        assert metrics.name == "mymodule"
        assert metrics.path == Path("src/mymodule")
        assert metrics.file_count == 0
        assert metrics.total_lines == 0
        assert metrics.avg_file_size == 0.0
        assert metrics.test_coverage_estimate == 0.0

    def test_all_fields_settable(self):
        """
        ModuleMetrics should allow setting all fields.
        """
        metrics = ModuleMetrics(
            name="mymodule",
            path=Path("src/mymodule"),
            file_count=10,
            total_lines=1000,
            class_count=20,
            function_count=50,
            method_count=100,
            avg_file_size=100.0,
            avg_complexity=4.0,
            max_complexity=15,
            test_coverage_estimate=0.8,
        )

        assert metrics.file_count == 10
        assert metrics.avg_complexity == 4.0


# =============================================================================
# CodeMetrics Tests
# =============================================================================

class TestCodeMetrics:
    """Tests for CodeMetrics class.

    CodeMetrics provides methods to collect metrics across a project.
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

    def test_line_counting(self, create_project):
        """
        CodeMetrics should correctly count different types of lines.
        """
        rj = create_project({
            "app.py": textwrap.dedent('''\
                # This is a comment
                x = 1

                # Another comment
                y = 2
            ''')
        })

        metrics = CodeMetrics(rj)
        file_metrics = metrics.get_file_metrics(rj.root / "app.py")

        # Total = 6 lines (including trailing)
        assert file_metrics.total_lines >= 5
        # 2 comment lines
        assert file_metrics.comment_lines >= 2
        # 1 blank line
        assert file_metrics.blank_lines >= 1

    def test_counts_classes(self, create_project):
        """
        CodeMetrics should count classes in a file.
        """
        rj = create_project({
            "app.py": textwrap.dedent('''\
                class First:
                    pass

                class Second:
                    pass

                class Third:
                    pass
            ''')
        })

        metrics = CodeMetrics(rj)
        file_metrics = metrics.get_file_metrics(rj.root / "app.py")

        assert file_metrics.class_count == 3

    def test_counts_functions(self, create_project):
        """
        CodeMetrics should count module-level functions.
        """
        rj = create_project({
            "app.py": textwrap.dedent('''\
                def func1():
                    pass

                def func2():
                    pass
            ''')
        })

        metrics = CodeMetrics(rj)
        file_metrics = metrics.get_file_metrics(rj.root / "app.py")

        assert file_metrics.function_count == 2

    def test_counts_methods(self, create_project):
        """
        CodeMetrics should count class methods separately.
        """
        rj = create_project({
            "app.py": textwrap.dedent('''\
                class MyClass:
                    def method1(self):
                        pass

                    def method2(self):
                        pass

                    def method3(self):
                        pass
            ''')
        })

        metrics = CodeMetrics(rj)
        file_metrics = metrics.get_file_metrics(rj.root / "app.py")

        assert file_metrics.method_count == 3
        # Methods should not be counted as functions
        assert file_metrics.function_count == 0

    def test_counts_imports(self, create_project):
        """
        CodeMetrics should count import statements.
        """
        rj = create_project({
            "app.py": textwrap.dedent('''\
                import os
                import sys
                from pathlib import Path
                from typing import List, Dict
            ''')
        })

        metrics = CodeMetrics(rj)
        file_metrics = metrics.get_file_metrics(rj.root / "app.py")

        assert file_metrics.import_count == 4

    def test_detects_module_docstring(self, create_project):
        """
        CodeMetrics should detect module-level docstrings.
        """
        rj = create_project({
            "with_doc.py": textwrap.dedent('''\
                """Module docstring."""

                x = 1
            '''),
            "without_doc.py": textwrap.dedent('''\
                # Just a comment
                x = 1
            ''')
        })

        metrics = CodeMetrics(rj)

        with_doc = metrics.get_file_metrics(rj.root / "with_doc.py")
        without_doc = metrics.get_file_metrics(rj.root / "without_doc.py")

        assert with_doc.has_docstring is True
        assert without_doc.has_docstring is False

    def test_identifies_test_files(self, create_project):
        """
        CodeMetrics should identify test files.

        Files matching test_*.py, *_test.py, or in tests/ directory
        should be marked as test files.
        """
        rj = create_project({
            "app.py": "x = 1\n",
            "test_app.py": "def test_x(): pass\n",
            "app_test.py": "def test_y(): pass\n",
            "tests/test_utils.py": "def test_z(): pass\n",
        })

        metrics = CodeMetrics(rj)

        app = metrics.get_file_metrics(rj.root / "app.py")
        test_app = metrics.get_file_metrics(rj.root / "test_app.py")
        app_test = metrics.get_file_metrics(rj.root / "app_test.py")
        tests_utils = metrics.get_file_metrics(rj.root / "tests" / "test_utils.py")

        assert app.test_file is False
        assert test_app.test_file is True
        assert app_test.test_file is True
        assert tests_utils.test_file is True

    def test_get_all_file_metrics(self, create_project):
        """
        get_all_file_metrics should return metrics for all files.
        """
        rj = create_project({
            "a.py": "x = 1\n",
            "b.py": "y = 2\n",
            "c.py": "z = 3\n",
        })

        metrics = CodeMetrics(rj)
        all_metrics = metrics.get_all_file_metrics()

        assert len(all_metrics) == 3
        assert all(isinstance(m, FileMetrics) for m in all_metrics)

    def test_get_module_metrics(self, create_project):
        """
        get_module_metrics should aggregate metrics for a directory.
        """
        rj = create_project({
            "mymodule/__init__.py": "",
            "mymodule/core.py": textwrap.dedent('''\
                class Core:
                    def process(self):
                        pass
            '''),
            "mymodule/utils.py": textwrap.dedent('''\
                def helper():
                    pass
            '''),
        })

        metrics = CodeMetrics(rj)
        module_metrics = metrics.get_module_metrics(rj.root / "mymodule")

        assert module_metrics.name == "mymodule"
        assert module_metrics.file_count >= 2  # At least core.py and utils.py
        assert module_metrics.class_count == 1  # Core class
        assert module_metrics.function_count == 1  # helper function
        assert module_metrics.method_count == 1  # process method

    def test_get_project_summary(self, create_project):
        """
        get_project_summary should return aggregated project statistics.
        """
        rj = create_project({
            "app.py": textwrap.dedent('''\
                """App module."""

                class App:
                    def run(self):
                        pass

                def main():
                    pass
            '''),
            "test_app.py": textwrap.dedent('''\
                def test_main():
                    pass
            '''),
        })

        metrics = CodeMetrics(rj)
        summary = metrics.get_project_summary()

        assert summary["total_files"] == 2
        assert summary["source_files"] == 1
        assert summary["test_files"] == 1
        assert summary["total_classes"] >= 1
        assert summary["total_functions"] >= 1
        assert summary["files_with_docstrings"] >= 1

    def test_find_coverage_gaps(self, create_project):
        """
        find_coverage_gaps should identify source files without tests.
        """
        rj = create_project({
            "app.py": "x = 1\n",
            "utils.py": "def helper(): pass\n",
            "__init__.py": "",
            "test_app.py": "def test_app(): pass\n",
        })

        metrics = CodeMetrics(rj)
        gaps = metrics.find_coverage_gaps()

        gap_names = [p.name for p in gaps]
        # utils.py has no test_utils.py
        assert "utils.py" in gap_names
        # app.py has test_app.py
        assert "app.py" not in gap_names
        # __init__.py is excluded
        assert "__init__.py" not in gap_names

    def test_generate_summary_report(self, create_project):
        """
        generate_summary_report should return formatted markdown.
        """
        rj = create_project({
            "app.py": textwrap.dedent('''\
                """App module."""

                def main():
                    pass
            '''),
        })

        metrics = CodeMetrics(rj)
        report = metrics.generate_summary_report()

        assert "# Code Metrics Summary" in report
        assert "File Statistics" in report
        assert "Line Counts" in report

    def test_to_dict(self, create_project):
        """
        to_dict should export all metrics as a dictionary.
        """
        rj = create_project({
            "app.py": "x = 1\n",
        })

        metrics = CodeMetrics(rj)
        data = metrics.to_dict()

        assert "summary" in data
        assert "files" in data
        assert "coverage_gaps" in data
        assert isinstance(data["files"], list)

    def test_empty_project(self, tmp_path: Path):
        """
        CodeMetrics should handle empty projects gracefully.
        """
        rj = Rejig(str(tmp_path))
        metrics = CodeMetrics(rj)

        summary = metrics.get_project_summary()
        report = metrics.generate_summary_report()

        # Empty project should work without errors
        assert summary == {} or summary.get("total_files", 0) == 0

    def test_caches_file_metrics(self, create_project):
        """
        CodeMetrics should cache file metrics for performance.
        """
        rj = create_project({
            "app.py": textwrap.dedent('''\
                def func():
                    pass
            '''),
        })

        metrics = CodeMetrics(rj)

        # First call
        result1 = metrics.get_file_metrics(rj.root / "app.py")
        # Second call should return cached result
        result2 = metrics.get_file_metrics(rj.root / "app.py")

        # Should be the same object (cached)
        assert result1 is result2

    def test_handles_syntax_errors(self, create_project):
        """
        CodeMetrics should handle files with syntax errors.
        """
        rj = create_project({
            "good.py": "x = 1\n",
            "bad.py": "def broken(:\n    pass",
        })

        metrics = CodeMetrics(rj)
        # Should not raise
        all_metrics = metrics.get_all_file_metrics()

        # Should have metrics for both files
        assert len(all_metrics) == 2


# =============================================================================
# Integration Tests
# =============================================================================

class TestCodeMetricsIntegration:
    """Integration tests for code metrics workflow."""

    def test_full_analysis_workflow(self, tmp_path: Path):
        """
        Complete workflow: collect metrics, get summary, find gaps.
        """
        # Create a small project
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()

        (tmp_path / "src" / "core.py").write_text(textwrap.dedent('''\
            """Core module."""

            class Engine:
                """Main processing engine."""

                def process(self, data):
                    """Process data."""
                    return data * 2

            def initialize():
                """Initialize the system."""
                return Engine()
        '''))

        (tmp_path / "tests" / "test_core.py").write_text(textwrap.dedent('''\
            def test_engine():
                pass
        '''))

        rj = Rejig(str(tmp_path))
        metrics = CodeMetrics(rj)

        # Collect all metrics
        all_file_metrics = metrics.get_all_file_metrics()
        assert len(all_file_metrics) == 2

        # Get summary
        summary = metrics.get_project_summary()
        assert summary["total_files"] == 2
        assert summary["source_files"] == 1
        assert summary["test_files"] == 1

        # Generate report
        report = metrics.generate_summary_report()
        assert "# Code Metrics Summary" in report

        # Export to dict
        data = metrics.to_dict()
        assert len(data["files"]) == 2
