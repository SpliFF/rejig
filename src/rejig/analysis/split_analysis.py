"""Module split analysis for identifying files that can be refactored into packages.

This module provides tools for analyzing Python files to determine if they
are good candidates for splitting into multiple files or packages.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig
    from rejig.targets.python.file import FileTarget


@dataclass
class SplitAnalysisResult:
    """Result of analyzing a file for potential splitting.

    Attributes
    ----------
    file_path : Path
        Path to the analyzed file.
    total_lines : int
        Total number of lines in the file.
    class_count : int
        Number of top-level classes.
    function_count : int
        Number of top-level functions.
    can_split : bool
        Whether the file can be meaningfully split.
    split_by : str | None
        Recommended split strategy: "class", "function", or None.
    reason : str
        Explanation of why the file can or cannot be split.
    """

    file_path: Path
    total_lines: int
    class_count: int
    function_count: int
    can_split: bool
    split_by: Literal["class", "function"] | None
    reason: str

    def __repr__(self) -> str:
        status = "splittable" if self.can_split else "not splittable"
        return f"SplitAnalysisResult({self.file_path.name}, {self.total_lines} lines, {status})"


class SplitAnalyzer:
    """Analyzer for identifying files that can be split into modules.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    min_lines : int
        Minimum lines to consider a file for splitting. Default 500.
    min_classes_to_split : int
        Minimum number of classes to consider splitting by class. Default 2.
    min_functions_to_split : int
        Minimum number of functions to consider splitting by function. Default 3.
    """

    def __init__(
        self,
        rejig: Rejig,
        min_lines: int = 500,
        min_classes_to_split: int = 2,
        min_functions_to_split: int = 3,
    ) -> None:
        self._rejig = rejig
        self.min_lines = min_lines
        self.min_classes_to_split = min_classes_to_split
        self.min_functions_to_split = min_functions_to_split

    def analyze_file(self, file_path: Path) -> SplitAnalysisResult:
        """Analyze a single file to determine if it can be split.

        Parameters
        ----------
        file_path : Path
            Path to the Python file to analyze.

        Returns
        -------
        SplitAnalysisResult
            Analysis result with split recommendation.
        """
        metrics = self._rejig.get_code_metrics().get_file_metrics(file_path)
        file_target = self._rejig.file(file_path)

        classes = file_target.find_classes()
        functions = file_target.find_functions()

        class_count = len(classes)
        function_count = len(functions)

        result = SplitAnalysisResult(
            file_path=file_path,
            total_lines=metrics.total_lines,
            class_count=class_count,
            function_count=function_count,
            can_split=False,
            split_by=None,
            reason="",
        )

        # Determine if file can be split
        if class_count >= self.min_classes_to_split:
            result.can_split = True
            result.split_by = "class"
            result.reason = f"Has {class_count} classes that can be split into separate files"
        elif class_count == 1 and function_count >= self.min_functions_to_split:
            # Single class with many functions - could split functions out
            result.can_split = True
            result.split_by = "function"
            result.reason = f"Has 1 class and {function_count} top-level functions"
        elif function_count >= self.min_functions_to_split:
            result.can_split = True
            result.split_by = "function"
            result.reason = f"Has {function_count} top-level functions that can be grouped"
        elif class_count == 1:
            result.reason = "Single large class - consider breaking into smaller classes first"
        else:
            result.reason = "Not enough distinct elements to split meaningfully"

        return result

    def analyze_file_target(self, file_target: FileTarget) -> SplitAnalysisResult:
        """Analyze a FileTarget to determine if it can be split.

        Parameters
        ----------
        file_target : FileTarget
            The file target to analyze.

        Returns
        -------
        SplitAnalysisResult
            Analysis result with split recommendation.
        """
        return self.analyze_file(file_target.path)

    def find_splittable_files(self) -> list[SplitAnalysisResult]:
        """Find all files that can be split.

        Returns
        -------
        list[SplitAnalysisResult]
            List of analysis results for splittable files, sorted by line count descending.
        """
        long_files = self._rejig.find_long_files(min_lines=self.min_lines)
        results = []

        for file_target in long_files:
            analysis = self.analyze_file(file_target.path)
            if analysis.can_split:
                results.append(analysis)

        # Sort by line count descending
        results.sort(key=lambda x: x.total_lines, reverse=True)
        return results

    def find_long_files_analysis(self) -> list[SplitAnalysisResult]:
        """Analyze all long files, whether splittable or not.

        Returns
        -------
        list[SplitAnalysisResult]
            List of analysis results for all long files, sorted by line count descending.
        """
        long_files = self._rejig.find_long_files(min_lines=self.min_lines)
        results = []

        for file_target in long_files:
            analysis = self.analyze_file(file_target.path)
            results.append(analysis)

        # Sort by line count descending
        results.sort(key=lambda x: x.total_lines, reverse=True)
        return results

    def get_summary(self) -> dict:
        """Get a summary of split analysis for the project.

        Returns
        -------
        dict
            Summary with counts and totals.
        """
        analyses = self.find_long_files_analysis()
        splittable = [a for a in analyses if a.can_split]
        not_splittable = [a for a in analyses if not a.can_split]

        return {
            "total_long_files": len(analyses),
            "splittable_count": len(splittable),
            "not_splittable_count": len(not_splittable),
            "total_lines_in_long_files": sum(a.total_lines for a in analyses),
            "splittable_by_class": len([a for a in splittable if a.split_by == "class"]),
            "splittable_by_function": len([a for a in splittable if a.split_by == "function"]),
        }
