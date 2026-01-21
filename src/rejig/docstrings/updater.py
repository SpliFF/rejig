"""Docstring updater for modifying existing docstrings.

Provides transformers for updating, adding, and converting docstrings.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

import libcst as cst

from rejig.docstrings.generator import DocstringGenerator
from rejig.docstrings.parser import DocstringParser, extract_docstring, has_docstring
from rejig.docstrings.styles import (
    DocstringExample,
    DocstringRaises,
    DocstringStyle,
    DocstringStyleType,
    ParsedDocstring,
    get_formatter,
)

if TYPE_CHECKING:
    from pathlib import Path


class AddDocstringTransformer(cst.CSTTransformer):
    """CST transformer that adds docstrings to functions/methods.

    Parameters
    ----------
    target_class : str | None
        Name of the class (for methods), or None for module-level functions.
    target_func : str
        Name of the function/method.
    style : DocstringStyle | str
        Docstring style to generate.
    summary : str
        Custom summary line.
    overwrite : bool
        Whether to overwrite existing docstrings.
    """

    def __init__(
        self,
        target_class: str | None,
        target_func: str,
        style: DocstringStyle | DocstringStyleType = "google",
        summary: str = "",
        overwrite: bool = False,
    ) -> None:
        self.target_class = target_class
        self.target_func = target_func
        self.style = DocstringStyle(style) if isinstance(style, str) else style
        self.summary = summary
        self.overwrite = overwrite
        self._generator = DocstringGenerator(self.style)
        self._in_target_class = False
        self.added = False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        if self.target_class and node.name.value == self.target_class:
            self._in_target_class = True
        return True

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        if self.target_class and original_node.name.value == self.target_class:
            self._in_target_class = False
        return updated_node

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        # Check if this is the target function
        is_target = original_node.name.value == self.target_func
        if self.target_class:
            is_target = is_target and self._in_target_class
        else:
            is_target = is_target and not self._in_target_class

        if not is_target:
            return updated_node

        # Check if already has docstring
        if has_docstring(original_node) and not self.overwrite:
            return updated_node

        # Generate docstring
        docstring_text = self._generator.generate(original_node, summary=self.summary)

        # Create the docstring node
        docstring_node = cst.SimpleStatementLine(
            body=[cst.Expr(cst.SimpleString(docstring_text))]
        )

        # Update the function body
        body = updated_node.body
        if isinstance(body, cst.IndentedBlock):
            new_body_stmts = list(body.body)

            # Check if first statement is a docstring
            if new_body_stmts and self._is_docstring_stmt(new_body_stmts[0]):
                if self.overwrite:
                    # Replace existing docstring
                    new_body_stmts[0] = docstring_node
                    self.added = True
            else:
                # Add docstring at the beginning
                new_body_stmts.insert(0, docstring_node)
                self.added = True

            new_body = body.with_changes(body=new_body_stmts)
            return updated_node.with_changes(body=new_body)

        return updated_node

    def _is_docstring_stmt(self, stmt: cst.BaseStatement) -> bool:
        """Check if a statement is a docstring."""
        if isinstance(stmt, cst.SimpleStatementLine):
            if stmt.body and isinstance(stmt.body[0], cst.Expr):
                expr = stmt.body[0].value
                return isinstance(expr, (cst.SimpleString, cst.ConcatenatedString))
        return False


class UpdateDocstringTransformer(cst.CSTTransformer):
    """CST transformer that updates specific parts of docstrings.

    Parameters
    ----------
    target_class : str | None
        Name of the class (for methods), or None for module-level functions.
    target_func : str
        Name of the function/method.
    updates : dict
        Dictionary of updates to apply:
        - "param": (name, description) - update parameter description
        - "raises": (exception, description) - add/update raises entry
        - "returns": description - update returns section
        - "example": code - add example
        - "summary": text - update summary
    style : DocstringStyle | str
        Output docstring style (preserves existing style by default).
    """

    def __init__(
        self,
        target_class: str | None,
        target_func: str,
        updates: dict,
        style: DocstringStyle | DocstringStyleType | None = None,
    ) -> None:
        self.target_class = target_class
        self.target_func = target_func
        self.updates = updates
        self.style = DocstringStyle(style) if isinstance(style, str) else style
        self._parser = DocstringParser()
        self._in_target_class = False
        self.updated = False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        if self.target_class and node.name.value == self.target_class:
            self._in_target_class = True
        return True

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        if self.target_class and original_node.name.value == self.target_class:
            self._in_target_class = False
        return updated_node

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        # Check if this is the target function
        is_target = original_node.name.value == self.target_func
        if self.target_class:
            is_target = is_target and self._in_target_class
        else:
            is_target = is_target and not self._in_target_class

        if not is_target:
            return updated_node

        # Extract existing docstring
        existing = extract_docstring(original_node)
        if not existing:
            return updated_node

        # Parse existing docstring
        parsed = self._parser.parse(existing)

        # Detect style if not specified
        style = self.style or self._parser.detect_style(existing)

        # Apply updates
        self._apply_updates(parsed)

        # Generate new docstring
        formatter = get_formatter(style)
        new_docstring_text = formatter.format(parsed)

        # Update the function body
        body = updated_node.body
        if isinstance(body, cst.IndentedBlock):
            new_body_stmts = list(body.body)

            # Find and replace the docstring
            if new_body_stmts and self._is_docstring_stmt(new_body_stmts[0]):
                docstring_node = cst.SimpleStatementLine(
                    body=[cst.Expr(cst.SimpleString(new_docstring_text))]
                )
                new_body_stmts[0] = docstring_node
                self.updated = True

                new_body = body.with_changes(body=new_body_stmts)
                return updated_node.with_changes(body=new_body)

        return updated_node

    def _apply_updates(self, parsed: ParsedDocstring) -> None:
        """Apply the update dictionary to a parsed docstring."""
        for key, value in self.updates.items():
            if key == "param":
                name, description = value
                parsed.add_param(name, description)
            elif key == "raises":
                exception, description = value
                parsed.add_raises(exception, description)
            elif key == "returns":
                if parsed.returns:
                    parsed.returns.description = value
                else:
                    from rejig.docstrings.styles import DocstringReturns
                    parsed.returns = DocstringReturns(description=value)
            elif key == "example":
                parsed.examples.append(DocstringExample(code=value))
            elif key == "summary":
                parsed.summary = value

    def _is_docstring_stmt(self, stmt: cst.BaseStatement) -> bool:
        """Check if a statement is a docstring."""
        if isinstance(stmt, cst.SimpleStatementLine):
            if stmt.body and isinstance(stmt.body[0], cst.Expr):
                expr = stmt.body[0].value
                return isinstance(expr, (cst.SimpleString, cst.ConcatenatedString))
        return False


class ConvertDocstringStyleTransformer(cst.CSTTransformer):
    """CST transformer that converts docstrings from one style to another.

    Parameters
    ----------
    from_style : DocstringStyle | str | None
        Source style (None to auto-detect).
    to_style : DocstringStyle | str
        Target style.
    """

    def __init__(
        self,
        from_style: DocstringStyle | DocstringStyleType | None,
        to_style: DocstringStyle | DocstringStyleType,
    ) -> None:
        self.from_style = DocstringStyle(from_style) if isinstance(from_style, str) else from_style
        self.to_style = DocstringStyle(to_style) if isinstance(to_style, str) else to_style
        self._parser = DocstringParser()
        self._formatter = get_formatter(self.to_style)
        self.converted_count = 0

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        return self._convert_docstring_in_def(original_node, updated_node)

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        return self._convert_docstring_in_def(original_node, updated_node)

    def _convert_docstring_in_def(self, original_node, updated_node):
        """Convert docstring in a function or class definition."""
        existing = extract_docstring(original_node)
        if not existing:
            return updated_node

        # Check if this matches the from_style
        detected_style = self._parser.detect_style(existing)
        if self.from_style and detected_style != self.from_style:
            return updated_node

        # Parse and convert
        parsed = self._parser.parse(existing)
        new_docstring_text = self._formatter.format(parsed)

        # Update the body
        body = updated_node.body
        if isinstance(body, cst.IndentedBlock):
            new_body_stmts = list(body.body)

            if new_body_stmts and self._is_docstring_stmt(new_body_stmts[0]):
                docstring_node = cst.SimpleStatementLine(
                    body=[cst.Expr(cst.SimpleString(new_docstring_text))]
                )
                new_body_stmts[0] = docstring_node
                self.converted_count += 1

                new_body = body.with_changes(body=new_body_stmts)
                return updated_node.with_changes(body=new_body)

        return updated_node

    def _is_docstring_stmt(self, stmt: cst.BaseStatement) -> bool:
        """Check if a statement is a docstring."""
        if isinstance(stmt, cst.SimpleStatementLine):
            if stmt.body and isinstance(stmt.body[0], cst.Expr):
                expr = stmt.body[0].value
                return isinstance(expr, (cst.SimpleString, cst.ConcatenatedString))
        return False


class DocstringValidator:
    """Validate docstrings against function signatures.

    Finds parameters that are documented but not in signature (stale),
    and parameters in signature but not documented (missing).
    """

    def __init__(self) -> None:
        self._parser = DocstringParser()

    def validate(
        self, node: cst.FunctionDef
    ) -> tuple[list[str], list[str]]:
        """Validate a function's docstring against its signature.

        Parameters
        ----------
        node : cst.FunctionDef
            The function to validate.

        Returns
        -------
        tuple[list[str], list[str]]
            (stale_params, missing_params) - params in docstring but not signature,
            and params in signature but not documented.
        """
        docstring = extract_docstring(node)
        if not docstring:
            # No docstring - all params are missing
            sig_params = self._get_signature_params(node)
            return [], sig_params

        parsed = self._parser.parse(docstring)

        # Get params from signature
        sig_params = set(self._get_signature_params(node))

        # Get params from docstring
        doc_params = {p.name for p in parsed.params}

        # Find stale (in docstring but not signature)
        stale = list(doc_params - sig_params)

        # Find missing (in signature but not docstring)
        missing = list(sig_params - doc_params)

        return stale, missing

    def _get_signature_params(self, node: cst.FunctionDef) -> list[str]:
        """Get parameter names from function signature."""
        params: list[str] = []

        for param in node.params.params:
            name = param.name.value
            if name not in ("self", "cls"):
                params.append(name)

        for param in node.params.kwonly_params:
            params.append(param.name.value)

        if node.params.star_arg and isinstance(node.params.star_arg, cst.Param):
            params.append(f"*{node.params.star_arg.name.value}")

        if node.params.star_kwarg:
            params.append(f"**{node.params.star_kwarg.name.value}")

        return params


def find_outdated_docstrings(source: str) -> list[tuple[str, str | None, list[str], list[str]]]:
    """Find functions with outdated docstrings in source code.

    Parameters
    ----------
    source : str
        The source code to analyze.

    Returns
    -------
    list[tuple[str, str | None, list[str], list[str]]]
        List of (func_name, class_name, stale_params, missing_params).
    """
    results: list[tuple[str, str | None, list[str], list[str]]] = []
    validator = DocstringValidator()

    try:
        tree = cst.parse_module(source)

        class OutdatedFinder(cst.CSTVisitor):
            def __init__(self):
                self.current_class: str | None = None

            def visit_ClassDef(self, node: cst.ClassDef) -> bool:
                self.current_class = node.name.value
                return True

            def leave_ClassDef(self, node: cst.ClassDef) -> None:
                self.current_class = None

            def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
                stale, missing = validator.validate(node)
                if stale or missing:
                    results.append((
                        node.name.value,
                        self.current_class,
                        stale,
                        missing,
                    ))
                return False

        finder = OutdatedFinder()
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(finder)

    except Exception:
        pass

    return results


def find_missing_docstrings(source: str) -> list[tuple[str, str | None]]:
    """Find functions/methods without docstrings in source code.

    Parameters
    ----------
    source : str
        The source code to analyze.

    Returns
    -------
    list[tuple[str, str | None]]
        List of (func_name, class_name) for functions without docstrings.
    """
    results: list[tuple[str, str | None]] = []

    try:
        tree = cst.parse_module(source)

        class MissingFinder(cst.CSTVisitor):
            def __init__(self):
                self.current_class: str | None = None

            def visit_ClassDef(self, node: cst.ClassDef) -> bool:
                # Check class docstring
                if not has_docstring(node):
                    results.append((node.name.value, None))
                self.current_class = node.name.value
                return True

            def leave_ClassDef(self, node: cst.ClassDef) -> None:
                self.current_class = None

            def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
                if not has_docstring(node):
                    results.append((node.name.value, self.current_class))
                return False

        finder = MissingFinder()
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(finder)

    except Exception:
        pass

    return results
