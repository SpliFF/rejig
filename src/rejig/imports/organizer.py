"""Import organization (isort-like functionality).

Organizes imports into groups:
1. __future__ imports
2. Standard library imports
3. Third-party imports
4. Local/first-party imports
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst

from rejig.core.results import Result
from rejig.imports.analyzer import ImportAnalyzer, ImportInfo

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


# Standard library modules (Python 3.10+)
# This is a subset - we also check sys.stdlib_module_names when available
STDLIB_MODULES = {
    "abc",
    "aifc",
    "argparse",
    "array",
    "ast",
    "asynchat",
    "asyncio",
    "asyncore",
    "atexit",
    "audioop",
    "base64",
    "bdb",
    "binascii",
    "binhex",
    "bisect",
    "builtins",
    "bz2",
    "calendar",
    "cgi",
    "cgitb",
    "chunk",
    "cmath",
    "cmd",
    "code",
    "codecs",
    "codeop",
    "collections",
    "colorsys",
    "compileall",
    "concurrent",
    "configparser",
    "contextlib",
    "contextvars",
    "copy",
    "copyreg",
    "cProfile",
    "crypt",
    "csv",
    "ctypes",
    "curses",
    "dataclasses",
    "datetime",
    "dbm",
    "decimal",
    "difflib",
    "dis",
    "distutils",
    "doctest",
    "email",
    "encodings",
    "enum",
    "errno",
    "faulthandler",
    "fcntl",
    "filecmp",
    "fileinput",
    "fnmatch",
    "fractions",
    "ftplib",
    "functools",
    "gc",
    "getopt",
    "getpass",
    "gettext",
    "glob",
    "graphlib",
    "grp",
    "gzip",
    "hashlib",
    "heapq",
    "hmac",
    "html",
    "http",
    "idlelib",
    "imaplib",
    "imghdr",
    "imp",
    "importlib",
    "inspect",
    "io",
    "ipaddress",
    "itertools",
    "json",
    "keyword",
    "lib2to3",
    "linecache",
    "locale",
    "logging",
    "lzma",
    "mailbox",
    "mailcap",
    "marshal",
    "math",
    "mimetypes",
    "mmap",
    "modulefinder",
    "multiprocessing",
    "netrc",
    "nis",
    "nntplib",
    "numbers",
    "operator",
    "optparse",
    "os",
    "ossaudiodev",
    "pathlib",
    "pdb",
    "pickle",
    "pickletools",
    "pipes",
    "pkgutil",
    "platform",
    "plistlib",
    "poplib",
    "posix",
    "posixpath",
    "pprint",
    "profile",
    "pstats",
    "pty",
    "pwd",
    "py_compile",
    "pyclbr",
    "pydoc",
    "queue",
    "quopri",
    "random",
    "re",
    "readline",
    "reprlib",
    "resource",
    "rlcompleter",
    "runpy",
    "sched",
    "secrets",
    "select",
    "selectors",
    "shelve",
    "shlex",
    "shutil",
    "signal",
    "site",
    "smtpd",
    "smtplib",
    "sndhdr",
    "socket",
    "socketserver",
    "spwd",
    "sqlite3",
    "ssl",
    "stat",
    "statistics",
    "string",
    "stringprep",
    "struct",
    "subprocess",
    "sunau",
    "symtable",
    "sys",
    "sysconfig",
    "syslog",
    "tabnanny",
    "tarfile",
    "telnetlib",
    "tempfile",
    "termios",
    "test",
    "textwrap",
    "threading",
    "time",
    "timeit",
    "tkinter",
    "token",
    "tokenize",
    "tomllib",
    "trace",
    "traceback",
    "tracemalloc",
    "tty",
    "turtle",
    "turtledemo",
    "types",
    "typing",
    "typing_extensions",
    "unicodedata",
    "unittest",
    "urllib",
    "uu",
    "uuid",
    "venv",
    "warnings",
    "wave",
    "weakref",
    "webbrowser",
    "winreg",
    "winsound",
    "wsgiref",
    "xdrlib",
    "xml",
    "xmlrpc",
    "zipapp",
    "zipfile",
    "zipimport",
    "zlib",
    "zoneinfo",
    # Private modules often used
    "_thread",
    "__future__",
}


def _get_stdlib_modules() -> set[str]:
    """Get the set of standard library module names."""
    try:
        # Python 3.10+
        return sys.stdlib_module_names | STDLIB_MODULES
    except AttributeError:
        return STDLIB_MODULES


class ImportOrganizer:
    """Organize imports in Python files following isort conventions.

    Import groups (separated by blank lines):
    1. __future__ imports
    2. Standard library imports
    3. Third-party imports
    4. Local/first-party imports (relative imports and project imports)
    5. TYPE_CHECKING imports (inside if TYPE_CHECKING block)
    """

    def __init__(self, rejig: Rejig, first_party_packages: set[str] | None = None) -> None:
        """Initialize the organizer.

        Parameters
        ----------
        rejig : Rejig
            The parent Rejig instance.
        first_party_packages : set[str] | None
            Set of package names to treat as first-party. If None, will try
            to auto-detect from the project root.
        """
        self._rejig = rejig
        self._analyzer = ImportAnalyzer(rejig)
        self._stdlib = _get_stdlib_modules()
        self._first_party = first_party_packages or self._detect_first_party()

    def _detect_first_party(self) -> set[str]:
        """Auto-detect first-party package names from the project root."""
        first_party: set[str] = set()
        root = self._rejig.root

        # Check for src/ layout
        src_dir = root / "src"
        if src_dir.is_dir():
            for p in src_dir.iterdir():
                if p.is_dir() and (p / "__init__.py").exists():
                    first_party.add(p.name)

        # Check for packages at root
        for p in root.iterdir():
            if p.is_dir() and (p / "__init__.py").exists():
                first_party.add(p.name)

        # Check pyproject.toml for package name
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            try:
                import tomllib

                with open(pyproject, "rb") as f:
                    data = tomllib.load(f)

                # PEP 621
                if "project" in data and "name" in data["project"]:
                    first_party.add(data["project"]["name"].replace("-", "_"))

                # Poetry
                if "tool" in data and "poetry" in data["tool"]:
                    if "name" in data["tool"]["poetry"]:
                        first_party.add(data["tool"]["poetry"]["name"].replace("-", "_"))
            except Exception:
                pass

        return first_party

    def _classify_import(self, imp: ImportInfo) -> str:
        """Classify an import into a group.

        Returns one of: 'future', 'stdlib', 'thirdparty', 'firstparty', 'type_checking'
        """
        if imp.is_future:
            return "future"

        if imp.is_type_checking:
            return "type_checking"

        if imp.is_relative:
            return "firstparty"

        # Get the top-level module name
        if imp.is_from_import and imp.module:
            top_level = imp.module.split(".")[0]
        elif imp.names:
            top_level = imp.names[0].split(".")[0]
        else:
            return "thirdparty"

        if top_level in self._stdlib:
            return "stdlib"

        if top_level in self._first_party:
            return "firstparty"

        return "thirdparty"

    def _sort_imports(self, imports: list[ImportInfo]) -> list[ImportInfo]:
        """Sort imports within a group."""
        # Sort by:
        # 1. from imports after regular imports
        # 2. Module name alphabetically
        # 3. Imported names alphabetically
        def sort_key(imp: ImportInfo) -> tuple:
            module = imp.module or ""
            if not imp.is_from_import and imp.names:
                module = imp.names[0]

            return (
                imp.is_from_import,  # Regular imports first
                module.lower(),
                tuple(sorted(n.lower() for n in imp.names)),
            )

        return sorted(imports, key=sort_key)

    def organize(self, path: Path) -> Result:
        """Organize imports in a file.

        Parameters
        ----------
        path : Path
            Path to the Python file.

        Returns
        -------
        Result
            Result of the operation.
        """
        if not path.exists():
            return Result(success=False, message=f"File not found: {path}")

        try:
            content = path.read_text()
            tree = cst.parse_module(content)
        except Exception as e:
            return Result(success=False, message=f"Failed to parse file: {e}")

        # Collect imports
        imports = self._analyzer.get_imports(path)
        if not imports:
            return Result(success=True, message="No imports to organize")

        # Classify imports into groups
        groups: dict[str, list[ImportInfo]] = {
            "future": [],
            "stdlib": [],
            "thirdparty": [],
            "firstparty": [],
            "type_checking": [],
        }

        for imp in imports:
            group = self._classify_import(imp)
            groups[group].append(imp)

        # Sort each group
        for group in groups:
            groups[group] = self._sort_imports(groups[group])

        # Build the organized import block
        organized_lines: list[str] = []
        group_order = ["future", "stdlib", "thirdparty", "firstparty"]

        for group in group_order:
            if groups[group]:
                if organized_lines:
                    organized_lines.append("")  # Blank line between groups
                for imp in groups[group]:
                    organized_lines.append(imp.import_statement)

        # Transform the module
        transformer = ReorganizeImportsTransformer(imports, organized_lines, groups["type_checking"])
        new_tree = tree.visit(transformer)
        new_content = new_tree.code

        if new_content == content:
            return Result(success=True, message="Imports already organized")

        # Write with diff
        from rejig.core.diff import generate_diff

        if self._rejig.current_transaction:
            return self._rejig.current_transaction.add_change(
                path, content, new_content, "organize imports"
            )

        diff = generate_diff(content, new_content, path)

        if self._rejig.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would organize imports in {path}",
                files_changed=[path],
                diff=diff,
                diffs={path: diff},
            )

        path.write_text(new_content)
        return Result(
            success=True,
            message=f"Organized imports in {path}",
            files_changed=[path],
            diff=diff,
            diffs={path: diff},
        )


class ReorganizeImportsTransformer(cst.CSTTransformer):
    """Transform a module to reorganize its imports."""

    def __init__(
        self,
        original_imports: list[ImportInfo],
        organized_lines: list[str],
        type_checking_imports: list[ImportInfo],
    ) -> None:
        self.original_imports = original_imports
        self.organized_lines = organized_lines
        self.type_checking_imports = type_checking_imports
        self._removed_first_import = False
        self._added_organized = False
        self._import_statements = {imp.import_statement for imp in original_imports}
        self._type_checking_statements = {imp.import_statement for imp in type_checking_imports}

    def leave_SimpleStatementLine(
        self,
        original_node: cst.SimpleStatementLine,
        updated_node: cst.SimpleStatementLine,
    ) -> cst.BaseStatement | cst.FlattenSentinel | cst.RemovalSentinel:
        """Process import statements."""
        # Check if this is an import statement
        for stmt in updated_node.body:
            if isinstance(stmt, (cst.Import, cst.ImportFrom)):
                code = cst.Module(body=[cst.SimpleStatementLine(body=[stmt])]).code.strip()

                # Skip TYPE_CHECKING imports - they stay in place
                if code in self._type_checking_statements:
                    return updated_node

                if code in self._import_statements:
                    if not self._added_organized:
                        # Replace first import with all organized imports
                        self._added_organized = True
                        new_statements = []
                        for line in self.organized_lines:
                            if line == "":
                                new_statements.append(cst.EmptyLine(whitespace=cst.SimpleWhitespace("")))
                            else:
                                try:
                                    parsed = cst.parse_statement(line)
                                    new_statements.append(parsed)
                                except Exception:
                                    pass
                        if new_statements:
                            return cst.FlattenSentinel(new_statements)
                    return cst.RemovalSentinel.REMOVE

        return updated_node
