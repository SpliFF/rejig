"""Loop optimization analysis for Python code.

Detects slow loops that can be replaced with comprehensions, map, filter,
or other built-in functions for improved performance and readability.
"""
from __future__ import annotations

from dataclasses import dataclass
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
class LoopPattern:
    """Describes a detected loop pattern.

    Attributes
    ----------
    pattern_type : str
        The type of optimization possible.
    original_code : str
        The original loop code.
    suggested_code : str
        The suggested replacement.
    line_number : int
        Starting line number.
    end_line : int
        Ending line number.
    confidence : float
        Confidence level of the suggestion (0.0 to 1.0).
    """

    pattern_type: str
    original_code: str
    suggested_code: str
    line_number: int
    end_line: int
    confidence: float = 0.9


class LoopPatternVisitor(cst.CSTVisitor):
    """Visitor that detects loop patterns that can be optimized."""

    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, file_path: Path) -> None:
        super().__init__()
        self.file_path = file_path
        self.patterns: list[LoopPattern] = []
        self._current_function: str | None = None
        self._current_class: str | None = None

    def _get_position(self, node: cst.CSTNode) -> tuple[int, int]:
        """Get start and end line numbers for a node."""
        try:
            pos = self.get_metadata(PositionProvider, node)
            return pos.start.line, pos.end.line
        except KeyError:
            return 0, 0

    def _get_context_name(self) -> str | None:
        """Get the current function/class context name."""
        if self._current_function:
            if self._current_class:
                return f"{self._current_class}.{self._current_function}"
            return self._current_function
        return self._current_class

    def _node_to_code(self, node: cst.CSTNode) -> str:
        """Convert a CST node to its code representation."""
        try:
            module = cst.Module(body=[])
            return module.code_for_node(node)
        except Exception:
            return str(node)

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        """Track class context."""
        self._current_class = node.name.value
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        """Clear class context."""
        self._current_class = None

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        """Track function context."""
        self._current_function = node.name.value
        return True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:
        """Clear function context."""
        self._current_function = None

    def visit_For(self, node: cst.For) -> bool:
        """Analyze for loops for optimization opportunities."""
        start_line, end_line = self._get_position(node)

        # Check various patterns
        self._check_list_append_pattern(node, start_line, end_line)
        self._check_dict_assignment_pattern(node, start_line, end_line)
        self._check_set_add_pattern(node, start_line, end_line)
        self._check_sum_pattern(node, start_line, end_line)
        self._check_string_concat_pattern(node, start_line, end_line)
        self._check_any_all_pattern(node, start_line, end_line)
        self._check_enumerate_pattern(node, start_line, end_line)
        self._check_zip_pattern(node, start_line, end_line)
        self._check_map_pattern(node, start_line, end_line)
        self._check_filter_pattern(node, start_line, end_line)

        return True

    def _check_list_append_pattern(
        self, node: cst.For, start_line: int, end_line: int
    ) -> None:
        """Check for loops that append to a list (list comprehension candidate)."""
        if not isinstance(node.body, cst.IndentedBlock):
            return

        # Single statement in body
        if len(node.body.body) != 1:
            return

        stmt = node.body.body[0]
        if not isinstance(stmt, cst.SimpleStatementLine):
            return
        if len(stmt.body) != 1:
            return

        expr = stmt.body[0]
        if not isinstance(expr, cst.Expr):
            return

        call = expr.value
        if not isinstance(call, cst.Call):
            return

        # Check for .append() call
        if not isinstance(call.func, cst.Attribute):
            return
        if call.func.attr.value != "append":
            return
        if len(call.args) != 1:
            return

        # Get variable names
        target = self._node_to_code(node.target)
        iter_var = self._node_to_code(node.iter)
        list_name = self._node_to_code(call.func.value)
        append_value = self._node_to_code(call.args[0].value)

        # Check if it's a simple transformation or the item itself
        if append_value == target:
            suggested = f"{list_name} = list({iter_var})"
            pattern_type = "list_conversion"
        else:
            suggested = f"{list_name} = [{append_value} for {target} in {iter_var}]"
            pattern_type = "list_comprehension"

        original = self._node_to_code(node)
        self.patterns.append(
            LoopPattern(
                pattern_type=pattern_type,
                original_code=original,
                suggested_code=suggested,
                line_number=start_line,
                end_line=end_line,
                confidence=0.95,
            )
        )

    def _check_dict_assignment_pattern(
        self, node: cst.For, start_line: int, end_line: int
    ) -> None:
        """Check for loops that build a dict (dict comprehension candidate)."""
        if not isinstance(node.body, cst.IndentedBlock):
            return

        if len(node.body.body) != 1:
            return

        stmt = node.body.body[0]
        if not isinstance(stmt, cst.SimpleStatementLine):
            return
        if len(stmt.body) != 1:
            return

        assign = stmt.body[0]
        if not isinstance(assign, cst.Assign):
            return
        if len(assign.targets) != 1:
            return

        target = assign.targets[0].target
        if not isinstance(target, cst.Subscript):
            return

        # Get variable names
        iter_target = self._node_to_code(node.target)
        iter_var = self._node_to_code(node.iter)
        dict_name = self._node_to_code(target.value)
        key_expr = self._node_to_code(target.slice[0].slice.value) if target.slice else ""
        value_expr = self._node_to_code(assign.value)

        suggested = f"{dict_name} = {{{key_expr}: {value_expr} for {iter_target} in {iter_var}}}"
        original = self._node_to_code(node)

        self.patterns.append(
            LoopPattern(
                pattern_type="dict_comprehension",
                original_code=original,
                suggested_code=suggested,
                line_number=start_line,
                end_line=end_line,
                confidence=0.9,
            )
        )

    def _check_set_add_pattern(
        self, node: cst.For, start_line: int, end_line: int
    ) -> None:
        """Check for loops that add to a set (set comprehension candidate)."""
        if not isinstance(node.body, cst.IndentedBlock):
            return

        if len(node.body.body) != 1:
            return

        stmt = node.body.body[0]
        if not isinstance(stmt, cst.SimpleStatementLine):
            return
        if len(stmt.body) != 1:
            return

        expr = stmt.body[0]
        if not isinstance(expr, cst.Expr):
            return

        call = expr.value
        if not isinstance(call, cst.Call):
            return

        if not isinstance(call.func, cst.Attribute):
            return
        if call.func.attr.value != "add":
            return
        if len(call.args) != 1:
            return

        target = self._node_to_code(node.target)
        iter_var = self._node_to_code(node.iter)
        set_name = self._node_to_code(call.func.value)
        add_value = self._node_to_code(call.args[0].value)

        if add_value == target:
            suggested = f"{set_name} = set({iter_var})"
        else:
            suggested = f"{set_name} = {{{add_value} for {target} in {iter_var}}}"

        original = self._node_to_code(node)
        self.patterns.append(
            LoopPattern(
                pattern_type="set_comprehension",
                original_code=original,
                suggested_code=suggested,
                line_number=start_line,
                end_line=end_line,
                confidence=0.95,
            )
        )

    def _check_sum_pattern(
        self, node: cst.For, start_line: int, end_line: int
    ) -> None:
        """Check for loops that sum values (sum() candidate)."""
        if not isinstance(node.body, cst.IndentedBlock):
            return

        if len(node.body.body) != 1:
            return

        stmt = node.body.body[0]
        if not isinstance(stmt, cst.SimpleStatementLine):
            return
        if len(stmt.body) != 1:
            return

        aug_assign = stmt.body[0]
        if not isinstance(aug_assign, cst.AugAssign):
            return
        if not isinstance(aug_assign.operator, cst.AddAssign):
            return

        target = self._node_to_code(node.target)
        iter_var = self._node_to_code(node.iter)
        sum_var = self._node_to_code(aug_assign.target)
        add_value = self._node_to_code(aug_assign.value)

        if add_value == target:
            suggested = f"{sum_var} = sum({iter_var})"
        else:
            suggested = f"{sum_var} = sum({add_value} for {target} in {iter_var})"

        original = self._node_to_code(node)
        self.patterns.append(
            LoopPattern(
                pattern_type="sum_builtin",
                original_code=original,
                suggested_code=suggested,
                line_number=start_line,
                end_line=end_line,
                confidence=0.95,
            )
        )

    def _check_string_concat_pattern(
        self, node: cst.For, start_line: int, end_line: int
    ) -> None:
        """Check for loops that concatenate strings (join() candidate)."""
        if not isinstance(node.body, cst.IndentedBlock):
            return

        if len(node.body.body) != 1:
            return

        stmt = node.body.body[0]
        if not isinstance(stmt, cst.SimpleStatementLine):
            return
        if len(stmt.body) != 1:
            return

        aug_assign = stmt.body[0]
        if not isinstance(aug_assign, cst.AugAssign):
            return
        if not isinstance(aug_assign.operator, cst.AddAssign):
            return

        # Check if augmenting a string (heuristic: ends with += str or target var)
        target = self._node_to_code(node.target)
        iter_var = self._node_to_code(node.iter)
        result_var = self._node_to_code(aug_assign.target)
        add_value = self._node_to_code(aug_assign.value)

        # Detect string patterns like: result += item or result += str(item)
        if add_value == target:
            suggested = f'{result_var} = "".join({iter_var})'
        elif add_value.startswith("str("):
            suggested = f'{result_var} = "".join(str({target}) for {target} in {iter_var})'
        else:
            # Could be string concatenation with separator
            return

        original = self._node_to_code(node)
        self.patterns.append(
            LoopPattern(
                pattern_type="string_join",
                original_code=original,
                suggested_code=suggested,
                line_number=start_line,
                end_line=end_line,
                confidence=0.8,  # Lower confidence as we're guessing types
            )
        )

    def _check_any_all_pattern(
        self, node: cst.For, start_line: int, end_line: int
    ) -> None:
        """Check for loops that check conditions (any()/all() candidate)."""
        if not isinstance(node.body, cst.IndentedBlock):
            return

        if len(node.body.body) != 1:
            return

        stmt = node.body.body[0]
        if not isinstance(stmt, cst.If):
            return

        # Check for if <condition>: return True/False pattern
        if_body = stmt.body
        if not isinstance(if_body, cst.IndentedBlock):
            return
        if len(if_body.body) != 1:
            return

        return_stmt = if_body.body[0]
        if not isinstance(return_stmt, cst.SimpleStatementLine):
            return
        if len(return_stmt.body) != 1:
            return

        ret = return_stmt.body[0]
        if not isinstance(ret, cst.Return):
            return

        if not isinstance(ret.value, cst.Name):
            return

        target = self._node_to_code(node.target)
        iter_var = self._node_to_code(node.iter)
        condition = self._node_to_code(stmt.test)
        return_value = ret.value.value

        if return_value == "True":
            # This is an any() pattern
            suggested = f"return any({condition} for {target} in {iter_var})"
            pattern_type = "any_builtin"
        elif return_value == "False":
            # This could be an all() pattern (negated)
            suggested = f"return not all(not ({condition}) for {target} in {iter_var})"
            pattern_type = "all_builtin"
        else:
            return

        original = self._node_to_code(node)
        self.patterns.append(
            LoopPattern(
                pattern_type=pattern_type,
                original_code=original,
                suggested_code=suggested,
                line_number=start_line,
                end_line=end_line,
                confidence=0.85,
            )
        )

    def _check_enumerate_pattern(
        self, node: cst.For, start_line: int, end_line: int
    ) -> None:
        """Check for loops that manually track indices (enumerate() candidate)."""
        # Look for patterns like:
        # i = 0
        # for item in items:
        #     ...use i...
        #     i += 1

        if not isinstance(node.body, cst.IndentedBlock):
            return

        # Check if body ends with i += 1
        if len(node.body.body) < 2:
            return

        last_stmt = node.body.body[-1]
        if not isinstance(last_stmt, cst.SimpleStatementLine):
            return
        if len(last_stmt.body) != 1:
            return

        aug_assign = last_stmt.body[0]
        if not isinstance(aug_assign, cst.AugAssign):
            return
        if not isinstance(aug_assign.operator, cst.AddAssign):
            return

        # Check if incrementing by 1
        if not isinstance(aug_assign.value, cst.Integer):
            return
        if aug_assign.value.value != "1":
            return

        index_var = self._node_to_code(aug_assign.target)
        target = self._node_to_code(node.target)
        iter_var = self._node_to_code(node.iter)

        suggested = f"for {index_var}, {target} in enumerate({iter_var}):"
        original = self._node_to_code(node)

        self.patterns.append(
            LoopPattern(
                pattern_type="enumerate_builtin",
                original_code=original,
                suggested_code=suggested,
                line_number=start_line,
                end_line=end_line,
                confidence=0.9,
            )
        )

    def _check_zip_pattern(
        self, node: cst.For, start_line: int, end_line: int
    ) -> None:
        """Check for nested index loops that could use zip()."""
        # Look for: for i in range(len(list1)): ... list1[i] ... list2[i]
        if not isinstance(node.iter, cst.Call):
            return

        if not isinstance(node.iter.func, cst.Name):
            return
        if node.iter.func.value != "range":
            return
        if len(node.iter.args) != 1:
            return

        # Check if range(len(...))
        range_arg = node.iter.args[0].value
        if not isinstance(range_arg, cst.Call):
            return
        if not isinstance(range_arg.func, cst.Name):
            return
        if range_arg.func.value != "len":
            return

        index_var = self._node_to_code(node.target)
        list_name = self._node_to_code(range_arg.args[0].value) if range_arg.args else ""

        # Suggest using direct iteration or zip
        suggested = f"# Consider: for item in {list_name}: or for item1, item2 in zip(list1, list2):"
        original = self._node_to_code(node)

        self.patterns.append(
            LoopPattern(
                pattern_type="zip_candidate",
                original_code=original,
                suggested_code=suggested,
                line_number=start_line,
                end_line=end_line,
                confidence=0.7,  # Lower confidence as context-dependent
            )
        )

    def _check_map_pattern(
        self, node: cst.For, start_line: int, end_line: int
    ) -> None:
        """Check for loops applying a function to items (map() candidate)."""
        if not isinstance(node.body, cst.IndentedBlock):
            return

        if len(node.body.body) != 1:
            return

        stmt = node.body.body[0]
        if not isinstance(stmt, cst.SimpleStatementLine):
            return
        if len(stmt.body) != 1:
            return

        expr = stmt.body[0]
        if not isinstance(expr, cst.Expr):
            return

        call = expr.value
        if not isinstance(call, cst.Call):
            return

        # Check for list.append(func(item)) pattern
        if not isinstance(call.func, cst.Attribute):
            return
        if call.func.attr.value != "append":
            return
        if len(call.args) != 1:
            return

        # Check if the append value is a function call on the loop target
        append_arg = call.args[0].value
        if not isinstance(append_arg, cst.Call):
            return

        target = self._node_to_code(node.target)
        iter_var = self._node_to_code(node.iter)
        list_name = self._node_to_code(call.func.value)
        func_call = self._node_to_code(append_arg)

        # Extract function name if it's a simple function call
        if isinstance(append_arg.func, cst.Name):
            func_name = append_arg.func.value
            # Check if the argument to the function is just the loop variable
            if (
                len(append_arg.args) == 1
                and isinstance(append_arg.args[0].value, cst.Name)
                and append_arg.args[0].value.value == target
            ):
                suggested = f"{list_name} = list(map({func_name}, {iter_var}))"
            else:
                suggested = f"{list_name} = [{func_call} for {target} in {iter_var}]"
        else:
            suggested = f"{list_name} = [{func_call} for {target} in {iter_var}]"

        original = self._node_to_code(node)
        self.patterns.append(
            LoopPattern(
                pattern_type="map_builtin",
                original_code=original,
                suggested_code=suggested,
                line_number=start_line,
                end_line=end_line,
                confidence=0.85,
            )
        )

    def _check_filter_pattern(
        self, node: cst.For, start_line: int, end_line: int
    ) -> None:
        """Check for loops with conditional append (filter() candidate)."""
        if not isinstance(node.body, cst.IndentedBlock):
            return

        if len(node.body.body) != 1:
            return

        stmt = node.body.body[0]
        if not isinstance(stmt, cst.If):
            return

        # Check for if <condition>: list.append(item) pattern
        if_body = stmt.body
        if not isinstance(if_body, cst.IndentedBlock):
            return
        if len(if_body.body) != 1:
            return

        append_stmt = if_body.body[0]
        if not isinstance(append_stmt, cst.SimpleStatementLine):
            return
        if len(append_stmt.body) != 1:
            return

        expr = append_stmt.body[0]
        if not isinstance(expr, cst.Expr):
            return

        call = expr.value
        if not isinstance(call, cst.Call):
            return

        if not isinstance(call.func, cst.Attribute):
            return
        if call.func.attr.value != "append":
            return

        target = self._node_to_code(node.target)
        iter_var = self._node_to_code(node.iter)
        list_name = self._node_to_code(call.func.value)
        condition = self._node_to_code(stmt.test)
        append_value = self._node_to_code(call.args[0].value) if call.args else target

        if append_value == target:
            # Pure filter pattern
            suggested = f"{list_name} = [x for x in {iter_var} if {condition}]"
            # Or: suggested = f"{list_name} = list(filter(lambda {target}: {condition}, {iter_var}))"
        else:
            # Filter + transform
            suggested = f"{list_name} = [{append_value} for {target} in {iter_var} if {condition}]"

        original = self._node_to_code(node)
        self.patterns.append(
            LoopPattern(
                pattern_type="filter_comprehension",
                original_code=original,
                suggested_code=suggested,
                line_number=start_line,
                end_line=end_line,
                confidence=0.9,
            )
        )


class LoopOptimizer:
    """Analyzer for detecting loop optimization opportunities.

    Detects:
    - Loops that can be replaced with list comprehensions
    - Loops that can be replaced with dict comprehensions
    - Loops that can be replaced with set comprehensions
    - Loops that can be replaced with map()
    - Loops that can be replaced with filter()
    - Loops that can be replaced with any()/all()
    - Loops that can be replaced with sum()
    - Loops that can be replaced with str.join()
    - Loops that should use enumerate()
    - Loops that should use zip()

    Parameters
    ----------
    rejig : Rejig
        The Rejig instance for accessing project files.

    Example
    -------
    >>> from rejig import Rejig
    >>> from rejig.optimize import LoopOptimizer
    >>> rj = Rejig("src/")
    >>> optimizer = LoopOptimizer(rj)
    >>> issues = optimizer.find_all_issues()
    >>> print(issues.summary())
    """

    # Mapping from pattern types to OptimizeType
    PATTERN_TYPE_MAP = {
        "list_comprehension": OptimizeType.SLOW_LOOP_TO_COMPREHENSION,
        "list_conversion": OptimizeType.SLOW_LOOP_TO_COMPREHENSION,
        "dict_comprehension": OptimizeType.SLOW_LOOP_TO_DICT_COMPREHENSION,
        "set_comprehension": OptimizeType.SLOW_LOOP_TO_SET_COMPREHENSION,
        "map_builtin": OptimizeType.SLOW_LOOP_TO_MAP,
        "filter_comprehension": OptimizeType.SLOW_LOOP_TO_FILTER,
        "any_builtin": OptimizeType.SLOW_LOOP_TO_ANY_ALL,
        "all_builtin": OptimizeType.SLOW_LOOP_TO_ANY_ALL,
        "sum_builtin": OptimizeType.SLOW_LOOP_TO_SUM,
        "string_join": OptimizeType.SLOW_LOOP_TO_JOIN,
        "enumerate_builtin": OptimizeType.SLOW_LOOP_TO_ENUMERATE,
        "zip_candidate": OptimizeType.SLOW_LOOP_TO_ZIP,
    }

    PATTERN_MESSAGES = {
        "list_comprehension": "Loop can be replaced with a list comprehension",
        "list_conversion": "Loop can be replaced with list() constructor",
        "dict_comprehension": "Loop can be replaced with a dict comprehension",
        "set_comprehension": "Loop can be replaced with a set comprehension",
        "map_builtin": "Loop can be replaced with map() or list comprehension",
        "filter_comprehension": "Loop with condition can be replaced with filtered comprehension",
        "any_builtin": "Loop can be replaced with any()",
        "all_builtin": "Loop can be replaced with all()",
        "sum_builtin": "Loop can be replaced with sum()",
        "string_join": "String concatenation in loop can be replaced with str.join()",
        "enumerate_builtin": "Manual index tracking can be replaced with enumerate()",
        "zip_candidate": "Index-based iteration may be replaceable with direct iteration or zip()",
    }

    PATTERN_IMPROVEMENTS = {
        "list_comprehension": "Improved readability, more Pythonic, often faster",
        "list_conversion": "Simpler code, more Pythonic",
        "dict_comprehension": "Improved readability, more Pythonic, often faster",
        "set_comprehension": "Improved readability, more Pythonic",
        "map_builtin": "Functional style, can be more efficient for large datasets",
        "filter_comprehension": "Improved readability, more Pythonic",
        "any_builtin": "Cleaner code, short-circuit evaluation, more Pythonic",
        "all_builtin": "Cleaner code, short-circuit evaluation, more Pythonic",
        "sum_builtin": "Cleaner code, optimized implementation",
        "string_join": "Much faster (O(n) vs O(n²)), more Pythonic",
        "enumerate_builtin": "Cleaner code, avoids manual index management",
        "zip_candidate": "Cleaner code, avoids index errors, more Pythonic",
    }

    def __init__(self, rejig: Rejig) -> None:
        self._rejig = rejig

    def _get_python_files(self) -> list[Path]:
        """Get all Python files in the project."""
        return list(self._rejig.root.rglob("*.py"))

    def _analyze_file(self, file_path: Path) -> list[LoopPattern]:
        """Analyze a single file for loop optimization opportunities."""
        try:
            content = file_path.read_text()
            tree = cst.parse_module(content)
            wrapper = MetadataWrapper(tree)

            visitor = LoopPatternVisitor(file_path)
            wrapper.visit(visitor)

            return visitor.patterns
        except Exception:
            return []

    def find_comprehension_opportunities(self) -> OptimizeTargetList:
        """Find loops that can be replaced with comprehensions.

        Returns
        -------
        OptimizeTargetList
            List of comprehension optimization findings.
        """
        return self._find_patterns_by_types([
            "list_comprehension",
            "list_conversion",
            "dict_comprehension",
            "set_comprehension",
        ])

    def find_builtin_opportunities(self) -> OptimizeTargetList:
        """Find loops that can be replaced with built-in functions.

        Returns
        -------
        OptimizeTargetList
            List of builtin function optimization findings.
        """
        return self._find_patterns_by_types([
            "map_builtin",
            "filter_comprehension",
            "any_builtin",
            "all_builtin",
            "sum_builtin",
            "string_join",
        ])

    def find_iterator_opportunities(self) -> OptimizeTargetList:
        """Find loops that should use enumerate() or zip().

        Returns
        -------
        OptimizeTargetList
            List of iterator optimization findings.
        """
        return self._find_patterns_by_types([
            "enumerate_builtin",
            "zip_candidate",
        ])

    def _find_patterns_by_types(
        self, pattern_types: list[str]
    ) -> OptimizeTargetList:
        """Find patterns matching specific types."""
        findings: list[OptimizeTarget] = []
        pattern_set = set(pattern_types)

        for file_path in self._get_python_files():
            patterns = self._analyze_file(file_path)
            for pattern in patterns:
                if pattern.pattern_type in pattern_set:
                    finding = self._pattern_to_finding(file_path, pattern)
                    findings.append(OptimizeTarget(self._rejig, finding))

        return OptimizeTargetList(self._rejig, findings)

    def _pattern_to_finding(
        self, file_path: Path, pattern: LoopPattern
    ) -> OptimizeFinding:
        """Convert a LoopPattern to an OptimizeFinding."""
        optimize_type = self.PATTERN_TYPE_MAP.get(
            pattern.pattern_type, OptimizeType.SLOW_LOOP_TO_COMPREHENSION
        )
        message = self.PATTERN_MESSAGES.get(
            pattern.pattern_type, "Loop can be optimized"
        )
        improvement = self.PATTERN_IMPROVEMENTS.get(
            pattern.pattern_type, "Improved performance and readability"
        )

        return OptimizeFinding(
            type=optimize_type,
            file_path=file_path,
            line_number=pattern.line_number,
            end_line=pattern.end_line,
            message=message,
            severity="suggestion" if pattern.confidence >= 0.85 else "info",
            original_code=pattern.original_code[:300] + "..."
            if len(pattern.original_code) > 300
            else pattern.original_code,
            suggested_code=pattern.suggested_code,
            estimated_improvement=improvement,
            context={
                "pattern_type": pattern.pattern_type,
                "confidence": pattern.confidence,
            },
        )

    def find_all_issues(
        self, min_confidence: float = 0.7
    ) -> OptimizeTargetList:
        """Find all loop optimization opportunities in the codebase.

        Parameters
        ----------
        min_confidence : float
            Minimum confidence level for including a finding (0.0 to 1.0).

        Returns
        -------
        OptimizeTargetList
            Combined list of all loop optimization findings.
        """
        findings: list[OptimizeTarget] = []

        for file_path in self._get_python_files():
            patterns = self._analyze_file(file_path)
            for pattern in patterns:
                if pattern.confidence >= min_confidence:
                    finding = self._pattern_to_finding(file_path, pattern)
                    findings.append(OptimizeTarget(self._rejig, finding))

        return OptimizeTargetList(self._rejig, findings)
