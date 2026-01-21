"""DRY (Don't Repeat Yourself) analysis for Python code.

Detects duplicate code blocks, expressions, literals, and similar functions
that could be refactored to improve code quality.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from rejig.optimize.targets import (
    OptimizeFinding,
    OptimizeTarget,
    OptimizeTargetList,
    OptimizeType,
)

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


@dataclass
class CodeFragment:
    """Represents a fragment of code for comparison.

    Attributes
    ----------
    code : str
        The normalized code string.
    original_code : str
        The original code string with formatting.
    file_path : Path
        Path to the file containing this fragment.
    line_number : int
        Starting line number.
    end_line : int
        Ending line number.
    node_type : str
        Type of the CST node (for categorization).
    name : str | None
        Name of the containing function/class if applicable.
    """

    code: str
    original_code: str
    file_path: Path
    line_number: int
    end_line: int
    node_type: str
    name: str | None = None

    @property
    def hash(self) -> str:
        """Return a hash of the normalized code."""
        return hashlib.md5(self.code.encode()).hexdigest()

    @property
    def line_count(self) -> int:
        """Return the number of lines in this fragment."""
        return self.end_line - self.line_number + 1


@dataclass
class DuplicateGroup:
    """A group of duplicate code fragments.

    Attributes
    ----------
    fragments : list[CodeFragment]
        List of duplicate fragments.
    """

    fragments: list[CodeFragment] = field(default_factory=list)

    @property
    def count(self) -> int:
        """Number of duplicates."""
        return len(self.fragments)

    @property
    def representative(self) -> CodeFragment:
        """The first fragment as representative."""
        return self.fragments[0]


class CodeNormalizer(cst.CSTTransformer):
    """Normalizes code for comparison by removing variable-specific details."""

    def __init__(self) -> None:
        super().__init__()
        self._name_counter = 0
        self._name_map: dict[str, str] = {}

    def _get_normalized_name(self, name: str) -> str:
        """Get a normalized placeholder name."""
        if name not in self._name_map:
            self._name_map[name] = f"_var{self._name_counter}"
            self._name_counter += 1
        return self._name_map[name]

    def leave_Name(
        self, original_node: cst.Name, updated_node: cst.Name
    ) -> cst.Name:
        """Normalize variable names to generic placeholders."""
        # Keep built-in names as-is
        builtins = {
            "True", "False", "None", "print", "len", "range", "str", "int",
            "float", "list", "dict", "set", "tuple", "bool", "type", "isinstance",
            "hasattr", "getattr", "setattr", "delattr", "enumerate", "zip", "map",
            "filter", "sum", "min", "max", "abs", "sorted", "reversed", "any", "all",
            "open", "file", "input", "super", "self", "cls", "Exception", "ValueError",
            "TypeError", "KeyError", "IndexError", "AttributeError", "RuntimeError",
        }
        if original_node.value in builtins:
            return updated_node
        return updated_node.with_changes(
            value=self._get_normalized_name(original_node.value)
        )


class DuplicateCollector(cst.CSTVisitor):
    """Collects code fragments for duplicate detection."""

    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(
        self,
        file_path: Path,
        min_lines: int = 3,
        min_statements: int = 2,
    ) -> None:
        super().__init__()
        self.file_path = file_path
        self.min_lines = min_lines
        self.min_statements = min_statements
        self.fragments: list[CodeFragment] = []
        self.expressions: list[CodeFragment] = []
        self.literals: list[CodeFragment] = []
        self._current_function: str | None = None
        self._current_class: str | None = None

    def _get_position(self, node: cst.CSTNode) -> tuple[int, int]:
        """Get start and end line numbers for a node."""
        try:
            pos = self.get_metadata(PositionProvider, node)
            return pos.start.line, pos.end.line
        except KeyError:
            return 0, 0

    def _normalize_code(self, node: cst.CSTNode) -> str:
        """Normalize code for comparison."""
        try:
            normalizer = CodeNormalizer()
            normalized = node.visit(normalizer)
            return normalized.deep_replace(
                normalized, normalized
            ).code if hasattr(normalized, 'code') else str(normalized)
        except Exception:
            # Fallback to string representation
            return str(node)

    def _get_current_context(self) -> str | None:
        """Get the name of current function/class context."""
        if self._current_function:
            if self._current_class:
                return f"{self._current_class}.{self._current_function}"
            return self._current_function
        return self._current_class

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        """Track function context and collect function bodies."""
        self._current_function = node.name.value
        start_line, end_line = self._get_position(node)

        # Collect the function body if it meets size requirements
        if node.body and isinstance(node.body, cst.IndentedBlock):
            body_lines = end_line - start_line
            if body_lines >= self.min_lines:
                try:
                    normalized = self._normalize_code(node.body)
                    self.fragments.append(
                        CodeFragment(
                            code=normalized,
                            original_code=node.body.deep_replace(
                                node.body, node.body
                            ).code if hasattr(node.body, 'code') else str(node.body),
                            file_path=self.file_path,
                            line_number=start_line,
                            end_line=end_line,
                            node_type="function_body",
                            name=self._get_current_context(),
                        )
                    )
                except Exception:
                    pass

        return True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:
        """Clear function context."""
        self._current_function = None

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        """Track class context."""
        self._current_class = node.name.value
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        """Clear class context."""
        self._current_class = None

    def visit_If(self, node: cst.If) -> bool:
        """Collect if block bodies."""
        self._collect_compound_body(node, "if_body")
        return True

    def visit_For(self, node: cst.For) -> bool:
        """Collect for loop bodies."""
        self._collect_compound_body(node, "for_body")
        return True

    def visit_While(self, node: cst.While) -> bool:
        """Collect while loop bodies."""
        self._collect_compound_body(node, "while_body")
        return True

    def visit_Try(self, node: cst.Try) -> bool:
        """Collect try block bodies."""
        self._collect_compound_body(node, "try_body")
        return True

    def visit_With(self, node: cst.With) -> bool:
        """Collect with block bodies."""
        self._collect_compound_body(node, "with_body")
        return True

    def _collect_compound_body(
        self, node: cst.CSTNode, node_type: str
    ) -> None:
        """Collect body of compound statement."""
        if not hasattr(node, 'body'):
            return

        start_line, end_line = self._get_position(node)
        body = getattr(node, 'body')

        if isinstance(body, cst.IndentedBlock):
            statement_count = len(body.body)
            if statement_count >= self.min_statements:
                try:
                    normalized = self._normalize_code(body)
                    self.fragments.append(
                        CodeFragment(
                            code=normalized,
                            original_code=str(body),
                            file_path=self.file_path,
                            line_number=start_line,
                            end_line=end_line,
                            node_type=node_type,
                            name=self._get_current_context(),
                        )
                    )
                except Exception:
                    pass

    def visit_BinaryOperation(self, node: cst.BinaryOperation) -> bool:
        """Collect binary operations as potential duplicate expressions."""
        start_line, end_line = self._get_position(node)
        try:
            code = str(node)
            if len(code) > 20:  # Only track non-trivial expressions
                normalized = self._normalize_code(node)
                self.expressions.append(
                    CodeFragment(
                        code=normalized,
                        original_code=code,
                        file_path=self.file_path,
                        line_number=start_line,
                        end_line=end_line,
                        node_type="binary_operation",
                        name=self._get_current_context(),
                    )
                )
        except Exception:
            pass
        return True

    def visit_Call(self, node: cst.Call) -> bool:
        """Collect function calls as potential duplicate expressions."""
        start_line, end_line = self._get_position(node)
        try:
            code = str(node)
            if len(code) > 20:  # Only track non-trivial calls
                normalized = self._normalize_code(node)
                self.expressions.append(
                    CodeFragment(
                        code=normalized,
                        original_code=code,
                        file_path=self.file_path,
                        line_number=start_line,
                        end_line=end_line,
                        node_type="call",
                        name=self._get_current_context(),
                    )
                )
        except Exception:
            pass
        return True

    def visit_Integer(self, node: cst.Integer) -> bool:
        """Collect integer literals (magic numbers)."""
        # Skip common values like 0, 1, -1, 2
        try:
            value = int(node.value)
            if abs(value) > 2:
                start_line, end_line = self._get_position(node)
                self.literals.append(
                    CodeFragment(
                        code=node.value,
                        original_code=node.value,
                        file_path=self.file_path,
                        line_number=start_line,
                        end_line=end_line,
                        node_type="integer",
                        name=self._get_current_context(),
                    )
                )
        except (ValueError, TypeError):
            pass
        return True

    def visit_SimpleString(self, node: cst.SimpleString) -> bool:
        """Collect string literals."""
        try:
            value = node.value
            # Skip empty strings, single chars, and docstrings
            if len(value) > 5 and not value.startswith('"""') and not value.startswith("'''"):
                start_line, end_line = self._get_position(node)
                self.literals.append(
                    CodeFragment(
                        code=value,
                        original_code=value,
                        file_path=self.file_path,
                        line_number=start_line,
                        end_line=end_line,
                        node_type="string",
                        name=self._get_current_context(),
                    )
                )
        except Exception:
            pass
        return True


class FunctionSignatureCollector(cst.CSTVisitor):
    """Collects function signatures for similarity analysis."""

    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, file_path: Path) -> None:
        super().__init__()
        self.file_path = file_path
        self.functions: list[dict] = []
        self._current_class: str | None = None

    def _get_position(self, node: cst.CSTNode) -> tuple[int, int]:
        """Get start and end line numbers for a node."""
        try:
            pos = self.get_metadata(PositionProvider, node)
            return pos.start.line, pos.end.line
        except KeyError:
            return 0, 0

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        """Track class context."""
        self._current_class = node.name.value
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        """Clear class context."""
        self._current_class = None

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        """Collect function information."""
        start_line, end_line = self._get_position(node)

        # Count parameters
        param_count = len(node.params.params)
        if node.params.star_arg and isinstance(node.params.star_arg, cst.Param):
            param_count += 1
        if node.params.star_kwarg:
            param_count += 1

        # Count statements in body
        statement_count = 0
        if isinstance(node.body, cst.IndentedBlock):
            statement_count = len(node.body.body)

        # Get normalized body for comparison
        try:
            normalizer = CodeNormalizer()
            normalized_body = node.body.visit(normalizer) if node.body else ""
            body_hash = hashlib.md5(str(normalized_body).encode()).hexdigest()
        except Exception:
            body_hash = ""

        name = node.name.value
        if self._current_class:
            name = f"{self._current_class}.{name}"

        self.functions.append({
            "name": name,
            "file_path": self.file_path,
            "line_number": start_line,
            "end_line": end_line,
            "param_count": param_count,
            "statement_count": statement_count,
            "body_hash": body_hash,
            "original_code": str(node),
        })

        return True


class DRYAnalyzer:
    """Analyzer for detecting DRY (Don't Repeat Yourself) violations.

    Detects:
    - Duplicate code blocks (if, for, while, try, with bodies)
    - Duplicate expressions (complex operations, function calls)
    - Duplicate literals (magic numbers and strings)
    - Similar functions (functions with identical structure)
    - Repeated patterns

    Parameters
    ----------
    rejig : Rejig
        The Rejig instance for accessing project files.

    Example
    -------
    >>> from rejig import Rejig
    >>> from rejig.optimize import DRYAnalyzer
    >>> rj = Rejig("src/")
    >>> analyzer = DRYAnalyzer(rj)
    >>> issues = analyzer.find_all_issues()
    >>> print(issues.summary())
    """

    def __init__(self, rejig: Rejig) -> None:
        self._rejig = rejig

    def _get_python_files(self) -> list[Path]:
        """Get all Python files in the project."""
        return list(self._rejig.root.rglob("*.py"))

    def _analyze_file(
        self, file_path: Path, min_lines: int = 3, min_statements: int = 2
    ) -> tuple[list[CodeFragment], list[CodeFragment], list[CodeFragment]]:
        """Analyze a single file for duplicate code.

        Returns
        -------
        tuple
            (code_fragments, expressions, literals)
        """
        try:
            content = file_path.read_text()
            tree = cst.parse_module(content)
            wrapper = MetadataWrapper(tree)

            collector = DuplicateCollector(
                file_path, min_lines=min_lines, min_statements=min_statements
            )
            wrapper.visit(collector)

            return collector.fragments, collector.expressions, collector.literals
        except Exception:
            return [], [], []

    def _analyze_functions(self, file_path: Path) -> list[dict]:
        """Analyze functions in a file for similarity."""
        try:
            content = file_path.read_text()
            tree = cst.parse_module(content)
            wrapper = MetadataWrapper(tree)

            collector = FunctionSignatureCollector(file_path)
            wrapper.visit(collector)

            return collector.functions
        except Exception:
            return []

    def find_duplicate_code_blocks(
        self, min_lines: int = 3, min_occurrences: int = 2
    ) -> OptimizeTargetList:
        """Find duplicate code blocks across the codebase.

        Parameters
        ----------
        min_lines : int
            Minimum number of lines for a code block to be considered.
        min_occurrences : int
            Minimum number of occurrences to report as duplicate.

        Returns
        -------
        OptimizeTargetList
            List of duplicate code block findings.
        """
        all_fragments: list[CodeFragment] = []

        for file_path in self._get_python_files():
            fragments, _, _ = self._analyze_file(file_path, min_lines=min_lines)
            all_fragments.extend(fragments)

        # Group by hash
        groups: dict[str, list[CodeFragment]] = defaultdict(list)
        for fragment in all_fragments:
            groups[fragment.hash].append(fragment)

        # Create findings for duplicates
        findings: list[OptimizeTarget] = []
        for hash_val, fragments in groups.items():
            if len(fragments) >= min_occurrences:
                for fragment in fragments:
                    other_locations = [
                        f"{f.file_path}:{f.line_number}"
                        for f in fragments
                        if f != fragment
                    ]
                    finding = OptimizeFinding(
                        type=OptimizeType.DUPLICATE_CODE_BLOCK,
                        file_path=fragment.file_path,
                        line_number=fragment.line_number,
                        end_line=fragment.end_line,
                        name=fragment.name,
                        message=f"Duplicate code block found in {len(fragments)} locations",
                        severity="warning",
                        original_code=fragment.original_code[:200] + "..."
                        if len(fragment.original_code) > 200
                        else fragment.original_code,
                        suggested_code="Consider extracting to a shared function",
                        estimated_improvement="Maintainability, reduced code size",
                        context={
                            "occurrences": len(fragments),
                            "other_locations": other_locations[:5],
                            "line_count": fragment.line_count,
                        },
                    )
                    findings.append(OptimizeTarget(self._rejig, finding))

        return OptimizeTargetList(self._rejig, findings)

    def find_duplicate_expressions(
        self, min_occurrences: int = 3
    ) -> OptimizeTargetList:
        """Find duplicate complex expressions.

        Parameters
        ----------
        min_occurrences : int
            Minimum number of occurrences to report as duplicate.

        Returns
        -------
        OptimizeTargetList
            List of duplicate expression findings.
        """
        all_expressions: list[CodeFragment] = []

        for file_path in self._get_python_files():
            _, expressions, _ = self._analyze_file(file_path)
            all_expressions.extend(expressions)

        # Group by normalized code
        groups: dict[str, list[CodeFragment]] = defaultdict(list)
        for expr in all_expressions:
            groups[expr.code].append(expr)

        findings: list[OptimizeTarget] = []
        for code, expressions in groups.items():
            if len(expressions) >= min_occurrences:
                for expr in expressions:
                    finding = OptimizeFinding(
                        type=OptimizeType.DUPLICATE_EXPRESSION,
                        file_path=expr.file_path,
                        line_number=expr.line_number,
                        end_line=expr.end_line,
                        name=expr.name,
                        message=f"Expression repeated {len(expressions)} times",
                        severity="suggestion",
                        original_code=expr.original_code,
                        suggested_code="Consider extracting to a variable or function",
                        estimated_improvement="Readability, maintainability",
                        context={
                            "occurrences": len(expressions),
                            "expression_type": expr.node_type,
                        },
                    )
                    findings.append(OptimizeTarget(self._rejig, finding))

        return OptimizeTargetList(self._rejig, findings)

    def find_duplicate_literals(
        self, min_occurrences: int = 3
    ) -> OptimizeTargetList:
        """Find magic numbers and repeated string literals.

        Parameters
        ----------
        min_occurrences : int
            Minimum number of occurrences to report as duplicate.

        Returns
        -------
        OptimizeTargetList
            List of duplicate literal findings.
        """
        all_literals: list[CodeFragment] = []

        for file_path in self._get_python_files():
            _, _, literals = self._analyze_file(file_path)
            all_literals.extend(literals)

        # Group by value
        groups: dict[str, list[CodeFragment]] = defaultdict(list)
        for literal in all_literals:
            groups[literal.code].append(literal)

        findings: list[OptimizeTarget] = []
        for value, literals in groups.items():
            if len(literals) >= min_occurrences:
                literal_type = literals[0].node_type
                suggested = (
                    f"Define a constant: MY_CONSTANT = {value}"
                    if literal_type == "integer"
                    else f"Define a constant: MY_STRING = {value}"
                )

                for literal in literals:
                    finding = OptimizeFinding(
                        type=OptimizeType.DUPLICATE_LITERAL,
                        file_path=literal.file_path,
                        line_number=literal.line_number,
                        end_line=literal.end_line,
                        name=literal.name,
                        message=f"{'Magic number' if literal_type == 'integer' else 'String literal'} {value} used {len(literals)} times",
                        severity="suggestion",
                        original_code=value,
                        suggested_code=suggested,
                        estimated_improvement="Maintainability, single point of change",
                        context={
                            "occurrences": len(literals),
                            "literal_type": literal_type,
                        },
                    )
                    findings.append(OptimizeTarget(self._rejig, finding))

        return OptimizeTargetList(self._rejig, findings)

    def find_similar_functions(
        self, similarity_threshold: float = 0.9
    ) -> OptimizeTargetList:
        """Find functions with similar structure that could be consolidated.

        Parameters
        ----------
        similarity_threshold : float
            Threshold for body similarity (0.0 to 1.0).

        Returns
        -------
        OptimizeTargetList
            List of similar function findings.
        """
        all_functions: list[dict] = []

        for file_path in self._get_python_files():
            functions = self._analyze_functions(file_path)
            all_functions.extend(functions)

        # Group by body hash (exact matches)
        groups: dict[str, list[dict]] = defaultdict(list)
        for func in all_functions:
            if func["body_hash"]:
                groups[func["body_hash"]].append(func)

        findings: list[OptimizeTarget] = []
        for hash_val, functions in groups.items():
            if len(functions) >= 2:
                for func in functions:
                    other_names = [
                        f["name"] for f in functions if f != func
                    ]
                    finding = OptimizeFinding(
                        type=OptimizeType.SIMILAR_FUNCTION,
                        file_path=func["file_path"],
                        line_number=func["line_number"],
                        end_line=func["end_line"],
                        name=func["name"],
                        message=f"Function has identical structure to: {', '.join(other_names[:3])}",
                        severity="warning",
                        original_code=func["original_code"][:200] + "..."
                        if len(func["original_code"]) > 200
                        else func["original_code"],
                        suggested_code="Consider consolidating into a single parameterized function",
                        estimated_improvement="Reduced code duplication",
                        context={
                            "similar_functions": other_names,
                            "param_count": func["param_count"],
                            "statement_count": func["statement_count"],
                        },
                    )
                    findings.append(OptimizeTarget(self._rejig, finding))

        return OptimizeTargetList(self._rejig, findings)

    def find_all_issues(
        self,
        min_block_lines: int = 3,
        min_block_occurrences: int = 2,
        min_expression_occurrences: int = 3,
        min_literal_occurrences: int = 3,
    ) -> OptimizeTargetList:
        """Find all DRY violations in the codebase.

        Parameters
        ----------
        min_block_lines : int
            Minimum lines for duplicate code blocks.
        min_block_occurrences : int
            Minimum occurrences for duplicate blocks.
        min_expression_occurrences : int
            Minimum occurrences for duplicate expressions.
        min_literal_occurrences : int
            Minimum occurrences for duplicate literals.

        Returns
        -------
        OptimizeTargetList
            Combined list of all DRY findings.
        """
        all_findings: list[OptimizeTarget] = []

        # Collect all types of findings
        blocks = self.find_duplicate_code_blocks(
            min_lines=min_block_lines, min_occurrences=min_block_occurrences
        )
        all_findings.extend(blocks._targets)

        expressions = self.find_duplicate_expressions(
            min_occurrences=min_expression_occurrences
        )
        all_findings.extend(expressions._targets)

        literals = self.find_duplicate_literals(
            min_occurrences=min_literal_occurrences
        )
        all_findings.extend(literals._targets)

        similar = self.find_similar_functions()
        all_findings.extend(similar._targets)

        return OptimizeTargetList(self._rejig, all_findings)
