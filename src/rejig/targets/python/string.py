"""StringLiteralTarget for operations on string literals in Python code."""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst

from rejig.targets.base import Result, Target

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


class StringLiteralTarget(Target):
    """Target for a string literal in Python source code.

    Provides operations for reading, modifying, and analyzing string
    literals in Python files. Useful for finding hardcoded strings,
    SQL queries, or extracting strings for internationalization.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    file_path : Path
        Path to the file containing the string.
    line_number : int
        1-based line number where the string starts.
    value : str
        The string value (decoded, without quotes).
    raw_content : str
        The raw string as it appears in source (with quotes).
    is_docstring : bool
        Whether this string is a docstring.

    Examples
    --------
    >>> strings = rj.file("queries.py").find_strings(pattern="SELECT")
    >>> for s in strings:
    ...     print(f"{s.line_number}: {s.value[:50]}")
    """

    def __init__(
        self,
        rejig: Rejig,
        file_path: Path,
        line_number: int,
        value: str,
        raw_content: str,
        is_docstring: bool = False,
    ) -> None:
        super().__init__(rejig)
        self.path = file_path
        self.line_number = line_number
        self.value = value
        self.raw_content = raw_content
        self.is_docstring = is_docstring

    @property
    def file_path(self) -> Path:
        """Path to the file containing this string."""
        return self.path

    @property
    def name(self) -> str:
        """The string value, used by TargetList filtering."""
        return self.value

    def __repr__(self) -> str:
        preview = self.value[:30] + "..." if len(self.value) > 30 else self.value
        doc_marker = " (docstring)" if self.is_docstring else ""
        return f"StringLiteralTarget({self.path}:{self.line_number}, {preview!r}{doc_marker})"

    def exists(self) -> bool:
        """Check if this string literal still exists at the recorded location."""
        if not self.path.exists():
            return False
        try:
            content = self.path.read_text()
            return self.raw_content in content
        except Exception:
            return False

    def get_content(self) -> Result:
        """Get the value of this string literal.

        Returns
        -------
        Result
            Result with string value in `data` field if successful.
        """
        return Result(success=True, message="OK", data=self.value)

    def rewrite(self, new_value: str | None = None, *, new_content: str | None = None) -> Result:
        """Replace this string literal with a new value.

        Parameters
        ----------
        new_value : str
            New string value (preferred parameter name for string literals).
        new_content : str
            Alias for new_value for API consistency with other targets.

        Returns
        -------
        Result
            Result of the operation.
        """
        # Support both new_value and new_content for API consistency
        value = new_value if new_value is not None else new_content
        if value is None:
            return self._operation_failed("rewrite", "Either new_value or new_content must be provided")

        if not self.path.exists():
            return self._operation_failed("rewrite", f"File not found: {self.path}")

        try:
            content = self.path.read_text()

            # Determine the prefix (f, r, b, u, fr, etc.) and quote style
            prefix = ""
            raw = self.raw_content

            # Extract prefix (can be 1-2 chars: f, r, b, u, fr, rf, br, rb)
            for i, char in enumerate(raw[:2]):
                if char in "frbuFRBU":
                    prefix += char
                else:
                    break

            # Get the quote from after the prefix
            quote_start = raw[len(prefix):]
            if quote_start.startswith('"""') or quote_start.startswith("'''"):
                quote = quote_start[:3]
            elif quote_start.startswith('"'):
                quote = '"'
            elif quote_start.startswith("'"):
                quote = "'"
            else:
                quote = '"'

            if len(quote) == 3:
                new_raw = f'{prefix}{quote}{value}{quote}'
            else:
                # Escape quotes in the value
                escaped = value.replace("\\", "\\\\").replace(quote, f"\\{quote}")
                new_raw = f'{prefix}{quote}{escaped}{quote}'

            # Replace in content
            new_content = content.replace(self.raw_content, new_raw, 1)

            if new_content == content:
                return self._operation_failed("rewrite", "Could not find string to replace")

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would rewrite string at line {self.line_number}",
                    files_changed=[self.path],
                )

            self.path.write_text(new_content)
            self.value = value
            self.raw_content = new_raw
            return Result(
                success=True,
                message=f"Rewrote string at line {self.line_number}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("rewrite", f"Failed to rewrite string: {e}", e)

    def delete(self) -> Result:
        """Delete this string literal (replace with empty string or remove assignment).

        Note: This replaces the string with an empty string. For more complex
        deletion (removing the entire statement), use the containing target.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self.rewrite("")

    @property
    def is_multiline(self) -> bool:
        """Check if this is a multiline string (triple-quoted)."""
        return self.raw_content.startswith(('"""', "'''"))

    @property
    def is_fstring(self) -> bool:
        """Check if this is an f-string."""
        return self.raw_content.lower().startswith(("f'", 'f"', "f'''", 'f"""'))

    @property
    def is_raw_string(self) -> bool:
        """Check if this is a raw string."""
        return self.raw_content.lower().startswith(("r'", 'r"', "r'''", 'r"""'))

    @property
    def looks_like_sql(self) -> bool:
        """Check if this string looks like SQL."""
        sql_keywords = ["SELECT", "INSERT", "UPDATE", "DELETE", "FROM", "WHERE", "JOIN"]
        upper_value = self.value.upper()
        return any(kw in upper_value for kw in sql_keywords)

    @property
    def looks_like_url(self) -> bool:
        """Check if this string looks like a URL."""
        return bool(re.match(r"^https?://", self.value, re.IGNORECASE))

    @property
    def looks_like_path(self) -> bool:
        """Check if this string looks like a file path."""
        return "/" in self.value or "\\" in self.value

    @property
    def looks_like_regex(self) -> bool:
        """Check if this string looks like a regex pattern."""
        regex_chars = ["^", "$", "\\d", "\\w", "\\s", "[", "]", "+", "*", "?", "{", "}"]
        return any(char in self.value for char in regex_chars)


def find_strings_in_file(
    rejig,
    file_path: Path,
    pattern: str | None = None,
    include_docstrings: bool = True,
) -> list[StringLiteralTarget]:
    """Find all string literals in a file.

    Parameters
    ----------
    rejig : Rejig
        The Rejig instance.
    file_path : Path
        Path to the file to search.
    pattern : str | None
        Optional regex pattern to filter strings.
    include_docstrings : bool
        Whether to include docstrings.

    Returns
    -------
    list[StringLiteralTarget]
        List of found string literals.
    """
    if not file_path.exists():
        return []

    try:
        content = file_path.read_text()
        tree = cst.parse_module(content)

        strings: list[StringLiteralTarget] = []
        regex = re.compile(pattern) if pattern else None

        class StringFinder(cst.CSTVisitor):
            def __init__(self):
                self.in_docstring_position = False
                self.function_depth = 0

            def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
                self.function_depth += 1
                # Check for docstring
                if node.body and node.body.body:
                    first_stmt = node.body.body[0]
                    if isinstance(first_stmt, cst.SimpleStatementLine):
                        if first_stmt.body and isinstance(first_stmt.body[0], cst.Expr):
                            expr = first_stmt.body[0].value
                            if isinstance(expr, (cst.SimpleString, cst.ConcatenatedString)):
                                self.in_docstring_position = True
                return True

            def leave_FunctionDef(self, node: cst.FunctionDef) -> None:
                self.function_depth -= 1

            def visit_ClassDef(self, node: cst.ClassDef) -> bool:
                # Check for docstring
                if node.body and node.body.body:
                    first_stmt = node.body.body[0]
                    if isinstance(first_stmt, cst.SimpleStatementLine):
                        if first_stmt.body and isinstance(first_stmt.body[0], cst.Expr):
                            expr = first_stmt.body[0].value
                            if isinstance(expr, (cst.SimpleString, cst.ConcatenatedString)):
                                self.in_docstring_position = True
                return True

            def _process_string(self, node: cst.SimpleString, is_docstring: bool = False):
                raw_value = node.value
                # Decode the string value
                try:
                    # Remove quotes and prefixes to get the actual value
                    value = node.evaluated_value
                    if value is None:
                        # For f-strings and other complex cases
                        value = raw_value.strip("\"'").strip("frbFRB")
                except Exception:
                    value = raw_value

                if isinstance(value, bytes):
                    value = value.decode("utf-8", errors="replace")

                # Apply filter
                if regex and not regex.search(str(value)):
                    return

                # Skip docstrings if not wanted
                if is_docstring and not include_docstrings:
                    return

                # Get line number
                code = tree.code_for_node(node)
                start_idx = content.find(code)
                line_num = content[:start_idx].count("\n") + 1 if start_idx >= 0 else 0

                strings.append(
                    StringLiteralTarget(
                        rejig,
                        file_path,
                        line_num,
                        str(value),
                        raw_value,
                        is_docstring,
                    )
                )

            def visit_SimpleString(self, node: cst.SimpleString) -> bool:
                is_doc = self.in_docstring_position
                self.in_docstring_position = False
                self._process_string(node, is_doc)
                return False

        finder = StringFinder()
        wrapper = cst.MetadataWrapper(tree)
        wrapper.visit(finder)

        return strings

    except Exception:
        return []
