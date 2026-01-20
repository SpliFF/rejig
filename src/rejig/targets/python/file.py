"""FileTarget for operations on individual Python files."""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst

from rejig.targets.base import ErrorResult, ErrorTarget, Result, Target, TargetList

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig
    from rejig.imports.targets import ImportTarget, ImportTargetList
    from rejig.targets.python.class_ import ClassTarget
    from rejig.targets.python.code_block import CodeBlockTarget
    from rejig.targets.python.function import FunctionTarget
    from rejig.targets.python.line import LineTarget
    from rejig.targets.python.line_block import LineBlockTarget


class FileTarget(Target):
    """Target for a specific Python file.

    Provides operations for reading, modifying, and navigating within
    a Python source file.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    path : str | Path
        Path to the Python file.

    Examples
    --------
    >>> file = rj.file("mymodule.py")
    >>> file.add_class("NewClass", body="pass")
    >>> file.find_class("MyClass").add_method("process")
    """

    def __init__(self, rejig: Rejig, path: str | Path) -> None:
        super().__init__(rejig)
        self.path = Path(path) if isinstance(path, str) else path

    @property
    def file_path(self) -> Path:
        """The path to this file (alias for consistency with other targets)."""
        return self.path

    def __repr__(self) -> str:
        return f"FileTarget({self.path})"

    def exists(self) -> bool:
        """Check if this file exists."""
        return self.path.exists() and self.path.is_file()

    def get_content(self) -> Result:
        """Get the content of this file.

        Returns
        -------
        Result
            Result with file content in `data` field if successful.
        """
        if not self.exists():
            return self._operation_failed("get_content", f"File not found: {self.path}")
        try:
            content = self.path.read_text()
            return Result(success=True, message="OK", data=content)
        except Exception as e:
            return self._operation_failed("get_content", f"Failed to read file: {e}", e)

    def _write_content(self, content: str) -> Result:
        """Write content to this file (internal helper)."""
        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would modify {self.path}",
                files_changed=[self.path],
            )
        try:
            self.path.write_text(content)
            return Result(
                success=True,
                message=f"Modified {self.path}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("write", f"Failed to write file: {e}", e)

    def _transform(self, transformer: cst.CSTTransformer) -> Result:
        """Apply a LibCST transformer to this file."""
        result = self.get_content()
        if result.is_error():
            return result

        content = result.data
        try:
            tree = cst.parse_module(content)
            new_tree = tree.visit(transformer)
            new_content = new_tree.code

            if new_content == content:
                return Result(success=True, message=f"No changes needed in {self.path}")

            return self._write_content(new_content)
        except Exception as e:
            return self._operation_failed("transform", f"Transformation failed: {e}", e)

    # ===== Navigation methods =====

    def find_class(self, name: str) -> Target:
        """Find a class by name in this file.

        Parameters
        ----------
        name : str
            Name of the class to find.

        Returns
        -------
        ClassTarget | ErrorTarget
            ClassTarget if found, ErrorTarget otherwise.
        """
        from rejig.targets.python.class_ import ClassTarget

        target = ClassTarget(self._rejig, name, file_path=self.path)
        if target.exists():
            return target
        return ErrorTarget(self._rejig, f"Class '{name}' not found in {self.path}")

    def find_function(self, name: str) -> Target:
        """Find a module-level function by name in this file.

        Parameters
        ----------
        name : str
            Name of the function to find.

        Returns
        -------
        FunctionTarget | ErrorTarget
            FunctionTarget if found, ErrorTarget otherwise.
        """
        from rejig.targets.python.function import FunctionTarget

        target = FunctionTarget(self._rejig, name, file_path=self.path)
        if target.exists():
            return target
        return ErrorTarget(self._rejig, f"Function '{name}' not found in {self.path}")

    def find_classes(self, pattern: str | None = None) -> TargetList[Target]:
        """Find all classes in this file, optionally filtered by pattern.

        Parameters
        ----------
        pattern : str | None
            Optional regex pattern to filter class names.

        Returns
        -------
        TargetList[ClassTarget]
            List of matching ClassTarget objects.
        """
        from rejig.targets.python.class_ import ClassTarget

        result = self.get_content()
        if result.is_error():
            return TargetList(self._rejig, [])

        regex = re.compile(pattern) if pattern else None
        targets: list[Target] = []

        try:
            tree = cst.parse_module(result.data)
            for node in tree.body:
                if isinstance(node, cst.ClassDef):
                    name = node.name.value
                    if regex is None or regex.search(name):
                        targets.append(ClassTarget(self._rejig, name, file_path=self.path))
        except Exception:
            pass

        return TargetList(self._rejig, targets)

    def find_functions(self, pattern: str | None = None) -> TargetList[Target]:
        """Find all module-level functions in this file.

        Parameters
        ----------
        pattern : str | None
            Optional regex pattern to filter function names.

        Returns
        -------
        TargetList[FunctionTarget]
            List of matching FunctionTarget objects.
        """
        from rejig.targets.python.function import FunctionTarget

        result = self.get_content()
        if result.is_error():
            return TargetList(self._rejig, [])

        regex = re.compile(pattern) if pattern else None
        targets: list[Target] = []

        try:
            tree = cst.parse_module(result.data)
            for node in tree.body:
                if isinstance(node, cst.FunctionDef):
                    name = node.name.value
                    if regex is None or regex.search(name):
                        targets.append(FunctionTarget(self._rejig, name, file_path=self.path))
        except Exception:
            pass

        return TargetList(self._rejig, targets)

    def line(self, line_number: int) -> Target:
        """Get a specific line of this file.

        Parameters
        ----------
        line_number : int
            1-based line number.

        Returns
        -------
        LineTarget
            Target for the specified line.
        """
        from rejig.targets.python.line import LineTarget

        return LineTarget(self._rejig, self.path, line_number)

    def lines(self, start: int, end: int) -> Target:
        """Get a range of lines from this file.

        Parameters
        ----------
        start : int
            1-based starting line number.
        end : int
            1-based ending line number (inclusive).

        Returns
        -------
        LineBlockTarget
            Target for the specified line range.
        """
        from rejig.targets.python.line_block import LineBlockTarget

        return LineBlockTarget(self._rejig, self.path, start, end)

    def block_at_line(self, line_number: int) -> Target:
        """Get the code block containing the given line.

        Finds the innermost code structure (class, function, if, for, while,
        try, with) that contains the specified line.

        Parameters
        ----------
        line_number : int
            1-based line number.

        Returns
        -------
        CodeBlockTarget | ErrorTarget
            CodeBlockTarget if a block is found, ErrorTarget otherwise.

        Examples
        --------
        >>> block = rj.file("utils.py").block_at_line(42)
        >>> print(block.kind)  # "class", "function", "if", etc.
        >>> block.delete()  # Delete the entire block
        """
        from rejig.targets.python.code_block import CodeBlockTarget

        block = CodeBlockTarget.find_at_line(self._rejig, self.path, line_number)
        if block is None:
            return ErrorTarget(
                self._rejig,
                f"No code block found containing line {line_number} in {self.path}",
            )
        return block

    # ===== Modification operations =====

    def add_import(self, import_statement: str) -> Result:
        """Add an import statement to this file.

        Parameters
        ----------
        import_statement : str
            Import statement to add (without newline).

        Returns
        -------
        Result
            Result of the operation.
        """
        result = self.get_content()
        if result.is_error():
            return result

        content = result.data
        if import_statement in content:
            return Result(success=True, message=f"Import already exists in {self.path}")

        lines = content.splitlines(keepends=True)
        last_import_idx = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")) and not stripped.startswith(
                "from __future__"
            ):
                last_import_idx = i

        if last_import_idx >= 0:
            lines.insert(last_import_idx + 1, import_statement + "\n")
        else:
            insert_idx = 0
            if lines and lines[0].strip().startswith(('"""', "'''")):
                for i, line in enumerate(lines):
                    if i > 0 and (line.strip().endswith('"""') or line.strip().endswith("'''")):
                        insert_idx = i + 1
                        break
            lines.insert(insert_idx, import_statement + "\n")

        new_content = "".join(lines)
        return self._write_content(new_content)

    def add_class(self, name: str, body: str = "pass", **kwargs: str) -> Result:
        """Add a class to this file.

        Parameters
        ----------
        name : str
            Name of the class to add.
        body : str
            Body of the class (default: "pass").
        **kwargs
            Additional options:
            - bases: Base classes (comma-separated string)
            - decorators: Decorators (list of strings without @)

        Returns
        -------
        Result
            Result of the operation.
        """
        result = self.get_content()
        if result.is_error():
            return result

        content = result.data

        # Build class definition
        bases = kwargs.get("bases", "")
        decorators = kwargs.get("decorators", [])

        class_def = ""
        if decorators:
            for dec in decorators:
                class_def += f"@{dec}\n"

        if bases:
            class_def += f"class {name}({bases}):\n"
        else:
            class_def += f"class {name}:\n"

        # Indent body
        for line in body.splitlines():
            class_def += f"    {line}\n"

        # Add to end of file
        if not content.endswith("\n"):
            content += "\n"
        content += "\n\n" + class_def

        return self._write_content(content)

    def add_function(self, name: str, body: str = "pass", **kwargs: str) -> Result:
        """Add a module-level function to this file.

        Parameters
        ----------
        name : str
            Name of the function to add.
        body : str
            Body of the function (default: "pass").
        **kwargs
            Additional options:
            - params: Parameter list (string)
            - return_type: Return type annotation
            - decorators: Decorators (list of strings without @)

        Returns
        -------
        Result
            Result of the operation.
        """
        result = self.get_content()
        if result.is_error():
            return result

        content = result.data

        # Build function definition
        params = kwargs.get("params", "")
        return_type = kwargs.get("return_type", "")
        decorators = kwargs.get("decorators", [])

        func_def = ""
        if decorators:
            for dec in decorators:
                func_def += f"@{dec}\n"

        if return_type:
            func_def += f"def {name}({params}) -> {return_type}:\n"
        else:
            func_def += f"def {name}({params}):\n"

        # Indent body
        for line in body.splitlines():
            func_def += f"    {line}\n"

        # Add to end of file
        if not content.endswith("\n"):
            content += "\n"
        content += "\n\n" + func_def

        return self._write_content(content)

    def rewrite(self, new_content: str) -> Result:
        """Replace the entire content of this file.

        Parameters
        ----------
        new_content : str
            New content for the file.

        Returns
        -------
        Result
            Result of the operation.
        """
        return self._write_content(new_content)

    def delete(self) -> Result:
        """Delete this file.

        Returns
        -------
        Result
            Result of the operation.
        """
        if not self.exists():
            return self._operation_failed("delete", f"File not found: {self.path}")

        if self.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would delete {self.path}",
                files_changed=[self.path],
            )

        try:
            self.path.unlink()
            return Result(
                success=True,
                message=f"Deleted {self.path}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed("delete", f"Failed to delete file: {e}", e)

    # ===== Test operations =====

    def add_pytest_fixture(
        self,
        fixture_name: str,
        body: str,
        scope: str = "function",
        autouse: bool = False,
        params: list[str] | None = None,
    ) -> Result:
        """Add a pytest fixture to this file.

        Typically used with conftest.py files to add shared fixtures.

        Parameters
        ----------
        fixture_name : str
            Name of the fixture function.
        body : str
            Body of the fixture function.
        scope : str
            Fixture scope: "function", "class", "module", or "session".
            Defaults to "function".
        autouse : bool
            If True, fixture is automatically used. Default False.
        params : list[str] | None
            Optional list of fixture parameters for parametrized fixtures.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> conftest = rj.file("tests/conftest.py")
        >>> conftest.add_pytest_fixture(
        ...     "db_session",
        ...     scope="function",
        ...     body="yield get_db()"
        ... )
        """
        from rejig.generation.tests import AddPytestFixtureTransformer

        if not self.exists():
            return self._operation_failed(
                "add_pytest_fixture",
                f"File not found: {self.path}",
            )

        try:
            content = self.path.read_text()

            # Check if fixture already exists
            if f"def {fixture_name}(" in content:
                return Result(
                    success=True,
                    message=f"Fixture '{fixture_name}' already exists in {self.path}",
                )

            tree = cst.parse_module(content)
            transformer = AddPytestFixtureTransformer(
                fixture_name, body, scope, autouse, params
            )
            new_tree = tree.visit(transformer)
            new_content = new_tree.code

            if new_content == content:
                return Result(success=True, message="No changes made")

            # Ensure pytest import exists
            if "import pytest" not in new_content:
                new_content = "import pytest\n\n" + new_content

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would add fixture '{fixture_name}' to {self.path}",
                    data=new_content,
                )

            self.path.write_text(new_content)
            return Result(
                success=True,
                message=f"Added pytest fixture '{fixture_name}' to {self.path}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed(
                "add_pytest_fixture",
                f"Failed to add fixture: {e}",
                e,
            )

    # ===== Import management methods =====

    def find_imports(self) -> ImportTargetList:
        """Find all imports in this file.

        Returns
        -------
        ImportTargetList
            List of ImportTarget objects for all imports in this file.

        Examples
        --------
        >>> file = rj.file("mymodule.py")
        >>> imports = file.find_imports()
        >>> for imp in imports:
        ...     print(f"Line {imp.line_number}: {imp.import_info.import_statement}")
        """
        from rejig.imports.analyzer import ImportAnalyzer
        from rejig.imports.targets import ImportTarget, ImportTargetList

        analyzer = ImportAnalyzer(self._rejig)
        import_infos = analyzer.get_imports(self.path)

        targets = [
            ImportTarget(self._rejig, self.path, info) for info in import_infos
        ]
        return ImportTargetList(self._rejig, targets)

    def find_unused_imports(self) -> ImportTargetList:
        """Find all unused imports in this file.

        Returns
        -------
        ImportTargetList
            List of ImportTarget objects for unused imports.

        Examples
        --------
        >>> file = rj.file("mymodule.py")
        >>> unused = file.find_unused_imports()
        >>> print(f"Found {len(unused)} unused imports")
        >>> unused.delete()  # Remove all unused imports
        """
        from rejig.imports.analyzer import ImportAnalyzer
        from rejig.imports.targets import ImportTarget, ImportTargetList

        analyzer = ImportAnalyzer(self._rejig)
        unused_infos = analyzer.find_unused_imports(self.path)

        targets = [
            ImportTarget(self._rejig, self.path, info) for info in unused_infos
        ]
        return ImportTargetList(self._rejig, targets)

    def organize_imports(
        self, first_party_packages: set[str] | None = None
    ) -> Result:
        """Organize imports in this file (isort-like).

        Groups imports into:
        1. __future__ imports
        2. Standard library imports
        3. Third-party imports
        4. Local/first-party imports

        Within each group, imports are sorted alphabetically.

        Parameters
        ----------
        first_party_packages : set[str] | None
            Set of package names to treat as first-party. If None, will
            try to auto-detect from the project root.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> file = rj.file("mymodule.py")
        >>> file.organize_imports()
        """
        from rejig.imports.organizer import ImportOrganizer

        organizer = ImportOrganizer(self._rejig, first_party_packages)
        return organizer.organize(self.path)

    def remove_unused_imports(self) -> Result:
        """Remove all unused imports from this file.

        Returns
        -------
        Result
            Result of the operation, including count of removed imports.

        Examples
        --------
        >>> file = rj.file("mymodule.py")
        >>> result = file.remove_unused_imports()
        >>> print(result.message)
        """
        unused = self.find_unused_imports()
        if not unused:
            return Result(success=True, message="No unused imports found")

        # Delete in reverse order to avoid line number shifts
        unused_sorted = sorted(
            unused.to_list(),
            key=lambda t: t.line_number,
            reverse=True,
        )

        count = 0
        for imp in unused_sorted:
            result = imp.delete()
            if result.success:
                count += 1

        return Result(
            success=True,
            message=f"Removed {count} unused imports from {self.path}",
            files_changed=[self.path] if count > 0 else [],
        )

    def add_missing_imports(self, import_mapping: dict[str, str] | None = None) -> Result:
        """Add imports for undefined names in this file.

        Note: This is a heuristic operation. It detects names that appear
        to be undefined (not imported or defined locally) and adds imports
        for them if a mapping is provided.

        Parameters
        ----------
        import_mapping : dict[str, str] | None
            Mapping of name to import statement. For example:
            {"Optional": "from typing import Optional"}
            If None, uses a default mapping for common names.

        Returns
        -------
        Result
            Result with the list of potentially missing imports in `data`.

        Examples
        --------
        >>> file = rj.file("mymodule.py")
        >>> result = file.add_missing_imports({
        ...     "Optional": "from typing import Optional",
        ...     "Path": "from pathlib import Path",
        ... })
        """
        from rejig.imports.analyzer import ImportAnalyzer

        analyzer = ImportAnalyzer(self._rejig)
        missing = analyzer.find_potentially_missing_imports(self.path)

        if not missing:
            return Result(
                success=True,
                message="No missing imports detected",
                data=[],
            )

        # Default mapping for common names
        default_mapping = {
            "Optional": "from typing import Optional",
            "List": "from typing import List",
            "Dict": "from typing import Dict",
            "Set": "from typing import Set",
            "Tuple": "from typing import Tuple",
            "Union": "from typing import Union",
            "Any": "from typing import Any",
            "Callable": "from typing import Callable",
            "Iterable": "from typing import Iterable",
            "Iterator": "from typing import Iterator",
            "Generator": "from typing import Generator",
            "Sequence": "from typing import Sequence",
            "Mapping": "from typing import Mapping",
            "TypeVar": "from typing import TypeVar",
            "Generic": "from typing import Generic",
            "Protocol": "from typing import Protocol",
            "TYPE_CHECKING": "from typing import TYPE_CHECKING",
            "Path": "from pathlib import Path",
            "dataclass": "from dataclasses import dataclass",
            "field": "from dataclasses import field",
            "Enum": "from enum import Enum",
            "auto": "from enum import auto",
            "ABC": "from abc import ABC",
            "abstractmethod": "from abc import abstractmethod",
            "contextmanager": "from contextlib import contextmanager",
            "suppress": "from contextlib import suppress",
            "defaultdict": "from collections import defaultdict",
            "Counter": "from collections import Counter",
            "OrderedDict": "from collections import OrderedDict",
            "namedtuple": "from collections import namedtuple",
            "datetime": "from datetime import datetime",
            "date": "from datetime import date",
            "time": "from datetime import time",
            "timedelta": "from datetime import timedelta",
        }

        mapping = {**default_mapping, **(import_mapping or {})}
        added = []
        not_found = []

        for name in missing:
            if name in mapping:
                result = self.add_import(mapping[name])
                if result.success:
                    added.append(name)
            else:
                not_found.append(name)

        message_parts = []
        if added:
            message_parts.append(f"Added imports for: {', '.join(sorted(added))}")
        if not_found:
            message_parts.append(f"No mapping found for: {', '.join(sorted(not_found))}")

        return Result(
            success=True,
            message="; ".join(message_parts) if message_parts else "No changes made",
            files_changed=[self.path] if added else [],
            data={"added": added, "not_found": not_found},
        )

    def convert_relative_to_absolute(self, package_name: str | None = None) -> Result:
        """Convert all relative imports to absolute imports.

        Parameters
        ----------
        package_name : str | None
            The package name to use as the base for absolute imports.
            If None, attempts to detect from project configuration.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> file = rj.file("myapp/utils.py")
        >>> file.convert_relative_to_absolute("myapp")
        """
        imports = self.find_imports()
        relative_imports = imports.filter_relative()

        if not relative_imports:
            return Result(success=True, message="No relative imports found")

        # Auto-detect package name if not provided
        if package_name is None:
            package_name = self._detect_package_name()

        if package_name is None:
            return self._operation_failed(
                "convert_relative_to_absolute",
                "Could not determine package name. Please provide it explicitly.",
            )

        count = 0
        for imp in relative_imports:
            result = imp.convert_to_absolute(package_name)
            if result.success:
                count += 1

        return Result(
            success=True,
            message=f"Converted {count} relative imports to absolute in {self.path}",
            files_changed=[self.path] if count > 0 else [],
        )

    def convert_absolute_to_relative(self) -> Result:
        """Convert all absolute imports to relative imports where possible.

        Only converts imports that are within the same package.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> file = rj.file("myapp/utils.py")
        >>> file.convert_absolute_to_relative()
        """
        imports = self.find_imports()
        absolute_imports = imports.filter_absolute()

        if not absolute_imports:
            return Result(success=True, message="No absolute imports to convert")

        # Get the current package path
        package_name = self._detect_package_name()

        count = 0
        for imp in absolute_imports:
            # Only convert imports that are within the same package
            if imp.module and package_name and imp.module.startswith(package_name + "."):
                result = imp.convert_to_relative()
                if result.success:
                    count += 1

        return Result(
            success=True,
            message=f"Converted {count} absolute imports to relative in {self.path}",
            files_changed=[self.path] if count > 0 else [],
        )

    def _detect_package_name(self) -> str | None:
        """Detect the package name for this file."""
        try:
            # Check pyproject.toml
            root = self._rejig.root
            pyproject = root / "pyproject.toml"

            if pyproject.exists():
                try:
                    import tomllib

                    with open(pyproject, "rb") as f:
                        data = tomllib.load(f)

                    # PEP 621
                    if "project" in data and "name" in data["project"]:
                        return data["project"]["name"].replace("-", "_")

                    # Poetry
                    if "tool" in data and "poetry" in data["tool"]:
                        if "name" in data["tool"]["poetry"]:
                            return data["tool"]["poetry"]["name"].replace("-", "_")
                except Exception:
                    pass

            # Try to infer from directory structure
            rel_path = self.path.relative_to(root)
            parts = list(rel_path.parts)

            # Check for src/ layout
            if parts[0] == "src" and len(parts) > 1:
                return parts[1]

            # Otherwise use the first directory
            if len(parts) > 1:
                return parts[0]

            return None
        except Exception:
            return None

    # ===== Type hint operations =====

    def convert_type_comments_to_annotations(self) -> Result:
        """Convert type comments to inline annotations.

        Converts:
            x = 1  # type: int
        To:
            x: int = 1

        And:
            def f(x):  # type: (int) -> str
        To:
            def f(x: int) -> str:

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> file = rj.file("legacy_module.py")
        >>> file.convert_type_comments_to_annotations()
        """
        from rejig.typehints.modernizer import TypeCommentConverter

        result = self.get_content()
        if result.is_error():
            return result

        content = result.data
        try:
            tree = cst.parse_module(content)
            converter = TypeCommentConverter()
            new_tree = tree.visit(converter)
            new_content = new_tree.code

            if not converter.changed:
                return Result(success=True, message=f"No type comments to convert in {self.path}")

            return self._write_content(new_content)
        except Exception as e:
            return self._operation_failed(
                "convert_type_comments_to_annotations",
                f"Failed to convert type comments: {e}",
                e,
            )

    def modernize_type_hints(self) -> Result:
        """Modernize type hints to Python 3.10+ syntax.

        Converts:
        - List[str] → list[str]
        - Dict[str, int] → dict[str, int]
        - Optional[str] → str | None
        - Union[str, int] → str | int

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> file = rj.file("mymodule.py")
        >>> file.modernize_type_hints()
        """
        from rejig.typehints.modernizer import TypeHintModernizer

        result = self.get_content()
        if result.is_error():
            return result

        content = result.data
        try:
            tree = cst.parse_module(content)
            modernizer = TypeHintModernizer()
            new_tree = tree.visit(modernizer)
            new_content = new_tree.code

            if not modernizer.changed:
                return Result(success=True, message=f"No type hints to modernize in {self.path}")

            return self._write_content(new_content)
        except Exception as e:
            return self._operation_failed(
                "modernize_type_hints",
                f"Failed to modernize type hints: {e}",
                e,
            )

    # ===== Docstring operations =====

    def convert_docstring_style(
        self,
        from_style: str | None,
        to_style: str,
    ) -> Result:
        """Convert all docstrings from one style to another.

        Parameters
        ----------
        from_style : str | None
            Source docstring style ("google", "numpy", "sphinx"),
            or None to auto-detect.
        to_style : str
            Target docstring style ("google", "numpy", "sphinx").

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> file = rj.file("mymodule.py")
        >>> file.convert_docstring_style("sphinx", "google")
        >>> file.convert_docstring_style(None, "numpy")  # auto-detect source
        """
        from rejig.docstrings.updater import ConvertDocstringStyleTransformer

        result = self.get_content()
        if result.is_error():
            return result

        content = result.data
        try:
            tree = cst.parse_module(content)
            transformer = ConvertDocstringStyleTransformer(from_style, to_style)
            new_tree = tree.visit(transformer)
            new_content = new_tree.code

            if transformer.converted_count == 0:
                return Result(
                    success=True,
                    message=f"No docstrings to convert in {self.path}",
                )

            if new_content == content:
                return Result(
                    success=True,
                    message=f"No changes needed in {self.path}",
                )

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would convert {transformer.converted_count} docstrings in {self.path}",
                    files_changed=[self.path],
                )

            self.path.write_text(new_content)
            return Result(
                success=True,
                message=f"Converted {transformer.converted_count} docstrings to {to_style} style in {self.path}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed(
                "convert_docstring_style",
                f"Failed to convert docstrings: {e}",
                e,
            )

    def find_missing_docstrings(self) -> TargetList[Target]:
        """Find all functions, methods, and classes without docstrings.

        Returns
        -------
        TargetList[Target]
            List of FunctionTarget, MethodTarget, and ClassTarget objects
            that don't have docstrings.

        Examples
        --------
        >>> file = rj.file("mymodule.py")
        >>> missing = file.find_missing_docstrings()
        >>> print(f"Found {len(missing)} items without docstrings")
        """
        from rejig.docstrings.updater import find_missing_docstrings
        from rejig.targets.python.class_ import ClassTarget
        from rejig.targets.python.function import FunctionTarget
        from rejig.targets.python.method import MethodTarget

        result = self.get_content()
        if result.is_error():
            return TargetList(self._rejig, [])

        targets: list[Target] = []

        try:
            missing = find_missing_docstrings(result.data)

            for func_name, class_name in missing:
                if class_name is None:
                    # Could be a class or function
                    # Try class first
                    cls = ClassTarget(self._rejig, func_name, file_path=self.path)
                    if cls.exists():
                        targets.append(cls)
                    else:
                        # Must be a function
                        targets.append(FunctionTarget(self._rejig, func_name, file_path=self.path))
                else:
                    # It's a method
                    targets.append(MethodTarget(self._rejig, class_name, func_name, file_path=self.path))
        except Exception:
            pass

        return TargetList(self._rejig, targets)

    def find_outdated_docstrings(self) -> Result:
        """Find functions/methods with outdated docstrings.

        A docstring is considered outdated if:
        - It documents parameters that no longer exist in the signature
        - It's missing documentation for parameters in the signature

        Returns
        -------
        Result
            Result with list of outdated docstrings in `data` field.
            Each entry is a dict with:
            - name: function/method name
            - class_name: class name (or None for functions)
            - stale_params: params documented but not in signature
            - missing_params: params in signature but not documented

        Examples
        --------
        >>> file = rj.file("mymodule.py")
        >>> result = file.find_outdated_docstrings()
        >>> for item in result.data:
        ...     print(f"{item['name']}: stale={item['stale_params']}, missing={item['missing_params']}")
        """
        from rejig.docstrings.updater import find_outdated_docstrings

        result = self.get_content()
        if result.is_error():
            return result

        try:
            outdated = find_outdated_docstrings(result.data)

            data = []
            for func_name, class_name, stale, missing in outdated:
                data.append({
                    "name": func_name,
                    "class_name": class_name,
                    "stale_params": stale,
                    "missing_params": missing,
                })

            return Result(
                success=True,
                message=f"Found {len(data)} outdated docstrings in {self.path}",
                data=data,
            )
        except Exception as e:
            return self._operation_failed(
                "find_outdated_docstrings",
                f"Failed to find outdated docstrings: {e}",
                e,
            )

    def generate_all_docstrings(
        self,
        style: str = "google",
        overwrite: bool = False,
    ) -> Result:
        """Generate docstrings for all functions and methods without them.

        Parameters
        ----------
        style : str
            Docstring style: "google", "numpy", or "sphinx".
            Defaults to "google".
        overwrite : bool
            Whether to overwrite existing docstrings. Default False.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> file = rj.file("mymodule.py")
        >>> file.generate_all_docstrings()
        >>> file.generate_all_docstrings(style="numpy", overwrite=True)
        """
        from rejig.docstrings.updater import AddDocstringTransformer

        result = self.get_content()
        if result.is_error():
            return result

        content = result.data

        try:
            tree = cst.parse_module(content)
            added_count = 0

            # Find all functions and methods that need docstrings
            class AllDocstringAdder(cst.CSTTransformer):
                def __init__(self, docstring_style: str, should_overwrite: bool):
                    self.style = docstring_style
                    self.overwrite = should_overwrite
                    self.current_class: str | None = None
                    self.added = 0

                def visit_ClassDef(self, node: cst.ClassDef) -> bool:
                    self.current_class = node.name.value
                    return True

                def leave_ClassDef(
                    self, original_node: cst.ClassDef, updated_node: cst.ClassDef
                ) -> cst.ClassDef:
                    self.current_class = None
                    return updated_node

                def leave_FunctionDef(
                    self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
                ) -> cst.FunctionDef:
                    from rejig.docstrings.generator import DocstringGenerator
                    from rejig.docstrings.parser import has_docstring

                    # Skip if already has docstring and not overwriting
                    if has_docstring(original_node) and not self.overwrite:
                        return updated_node

                    # Generate docstring
                    generator = DocstringGenerator(self.style)
                    docstring_text = generator.generate(original_node)

                    # Create docstring node
                    docstring_node = cst.SimpleStatementLine(
                        body=[cst.Expr(cst.SimpleString(docstring_text))]
                    )

                    # Update function body
                    body = updated_node.body
                    if isinstance(body, cst.IndentedBlock):
                        new_body_stmts = list(body.body)

                        # Check if first statement is docstring
                        if new_body_stmts and self._is_docstring_stmt(new_body_stmts[0]):
                            if self.overwrite:
                                new_body_stmts[0] = docstring_node
                                self.added += 1
                        else:
                            new_body_stmts.insert(0, docstring_node)
                            self.added += 1

                        new_body = body.with_changes(body=new_body_stmts)
                        return updated_node.with_changes(body=new_body)

                    return updated_node

                def _is_docstring_stmt(self, stmt: cst.BaseStatement) -> bool:
                    if isinstance(stmt, cst.SimpleStatementLine):
                        if stmt.body and isinstance(stmt.body[0], cst.Expr):
                            expr = stmt.body[0].value
                            return isinstance(expr, (cst.SimpleString, cst.ConcatenatedString))
                    return False

            transformer = AllDocstringAdder(style, overwrite)
            new_tree = tree.visit(transformer)
            new_content = new_tree.code

            if transformer.added == 0:
                return Result(
                    success=True,
                    message=f"No docstrings to generate in {self.path}",
                )

            if self.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would generate {transformer.added} docstrings in {self.path}",
                    files_changed=[self.path],
                )

            self.path.write_text(new_content)
            return Result(
                success=True,
                message=f"Generated {transformer.added} docstrings in {self.path}",
                files_changed=[self.path],
            )
        except Exception as e:
            return self._operation_failed(
                "generate_all_docstrings",
                f"Failed to generate docstrings: {e}",
                e,
            )

    # ===== Code modernization operations =====

    def convert_format_strings_to_fstrings(self) -> Result:
        """Convert .format() string formatting to f-strings.

        Converts:
            "Hello {}".format(name) → f"Hello {name}"
            "Hello {0}".format(name) → f"Hello {name}"
            "Hello {name}".format(name=value) → f"Hello {value}"

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> file = rj.file("legacy_module.py")
        >>> file.convert_format_strings_to_fstrings()
        """
        from rejig.modernize.fstrings import FormatToFstringTransformer

        result = self.get_content()
        if result.is_error():
            return result

        content = result.data
        try:
            tree = cst.parse_module(content)
            transformer = FormatToFstringTransformer()
            new_tree = tree.visit(transformer)
            new_content = new_tree.code

            if not transformer.changed:
                return Result(
                    success=True,
                    message=f"No .format() calls to convert in {self.path}",
                )

            return self._write_content(new_content)
        except Exception as e:
            return self._operation_failed(
                "convert_format_strings_to_fstrings",
                f"Failed to convert format strings: {e}",
                e,
            )

    def convert_percent_format_to_fstrings(self) -> Result:
        """Convert % string formatting to f-strings.

        Converts:
            "Hello %s" % name → f"Hello {name}"
            "Hello %s %s" % (a, b) → f"Hello {a} {b}"
            "%(name)s" % {"name": value} → f"{value}"

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> file = rj.file("legacy_module.py")
        >>> file.convert_percent_format_to_fstrings()
        """
        from rejig.modernize.fstrings import PercentToFstringTransformer

        result = self.get_content()
        if result.is_error():
            return result

        content = result.data
        try:
            tree = cst.parse_module(content)
            transformer = PercentToFstringTransformer()
            new_tree = tree.visit(transformer)
            new_content = new_tree.code

            if not transformer.changed:
                return Result(
                    success=True,
                    message=f"No % formatting to convert in {self.path}",
                )

            return self._write_content(new_content)
        except Exception as e:
            return self._operation_failed(
                "convert_percent_format_to_fstrings",
                f"Failed to convert percent formatting: {e}",
                e,
            )

    def add_future_annotations(self) -> Result:
        """Add `from __future__ import annotations` to this file.

        This enables PEP 563 postponed evaluation of annotations, allowing
        forward references and reducing runtime overhead.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> file = rj.file("mymodule.py")
        >>> file.add_future_annotations()
        """
        from rejig.modernize.python2 import AddFutureAnnotationsTransformer

        result = self.get_content()
        if result.is_error():
            return result

        content = result.data
        try:
            tree = cst.parse_module(content)
            transformer = AddFutureAnnotationsTransformer()
            new_tree = tree.visit(transformer)
            new_content = new_tree.code

            if not transformer.added:
                return Result(
                    success=True,
                    message=f"Future annotations already present in {self.path}",
                )

            return self._write_content(new_content)
        except Exception as e:
            return self._operation_failed(
                "add_future_annotations",
                f"Failed to add future annotations: {e}",
                e,
            )

    def remove_python2_compatibility(self) -> Result:
        """Remove Python 2 compatibility code from this file.

        Removes:
        - __future__ imports (except annotations)
        - super(ClassName, self) → super()
        - u"string" prefixes
        - Unnecessary (object) base class

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> file = rj.file("legacy_module.py")
        >>> file.remove_python2_compatibility()
        """
        from rejig.modernize.python2 import RemovePython2CompatTransformer

        result = self.get_content()
        if result.is_error():
            return result

        content = result.data
        try:
            tree = cst.parse_module(content)
            transformer = RemovePython2CompatTransformer()
            new_tree = tree.visit(transformer)
            new_content = new_tree.code

            if not transformer.changed:
                return Result(
                    success=True,
                    message=f"No Python 2 compatibility code in {self.path}",
                )

            return self._write_content(new_content)
        except Exception as e:
            return self._operation_failed(
                "remove_python2_compatibility",
                f"Failed to remove Python 2 compatibility: {e}",
                e,
            )

    def remove_six_usage(self) -> Result:
        """Remove `six` library compatibility usage.

        Converts:
        - six.text_type → str
        - six.binary_type → bytes
        - six.PY2 → False, six.PY3 → True
        - six.moves.range → range

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> file = rj.file("legacy_module.py")
        >>> file.remove_six_usage()
        """
        from rejig.modernize.python2 import RemoveSixUsageTransformer

        result = self.get_content()
        if result.is_error():
            return result

        content = result.data
        try:
            tree = cst.parse_module(content)
            transformer = RemoveSixUsageTransformer()
            new_tree = tree.visit(transformer)
            new_content = new_tree.code

            if not transformer.changed:
                return Result(
                    success=True,
                    message=f"No six library usage in {self.path}",
                )

            return self._write_content(new_content)
        except Exception as e:
            return self._operation_failed(
                "remove_six_usage",
                f"Failed to remove six usage: {e}",
                e,
            )

    def replace_deprecated_code(
        self, replacements: dict[str, str] | None = None
    ) -> Result:
        """Replace deprecated API usage with modern equivalents.

        Replaces common deprecated patterns like:
        - collections.MutableMapping → collections.abc.MutableMapping
        - assertEquals → assertEqual
        - logger.warn → logger.warning

        Parameters
        ----------
        replacements : dict[str, str] | None
            Custom replacement mapping. If None, uses built-in defaults.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> file = rj.file("tests.py")
        >>> file.replace_deprecated_code()
        >>> file.replace_deprecated_code({"oldFunc": "newFunc"})
        """
        from rejig.modernize.deprecated import ReplaceDeprecatedTransformer

        result = self.get_content()
        if result.is_error():
            return result

        content = result.data
        try:
            tree = cst.parse_module(content)
            transformer = ReplaceDeprecatedTransformer(replacements)
            new_tree = tree.visit(transformer)
            new_content = new_tree.code

            if not transformer.changed:
                return Result(
                    success=True,
                    message=f"No deprecated code to replace in {self.path}",
                )

            return self._write_content(new_content)
        except Exception as e:
            return self._operation_failed(
                "replace_deprecated_code",
                f"Failed to replace deprecated code: {e}",
                e,
            )

    def modernize_all(self) -> Result:
        """Apply all modernization transformations to this file.

        This is a convenience method that applies:
        1. F-string conversion (format and percent)
        2. Type hint modernization
        3. Python 2 compatibility removal
        4. Deprecated code replacement

        Returns
        -------
        Result
            Result of the operation with summary of changes.

        Examples
        --------
        >>> file = rj.file("legacy_module.py")
        >>> file.modernize_all()
        """
        changes_made = []

        # Convert format strings to f-strings
        result = self.convert_format_strings_to_fstrings()
        if result.success and result.files_changed:
            changes_made.append("format strings")

        # Convert percent formatting to f-strings
        result = self.convert_percent_format_to_fstrings()
        if result.success and result.files_changed:
            changes_made.append("percent formatting")

        # Modernize type hints
        result = self.modernize_type_hints()
        if result.success and result.files_changed:
            changes_made.append("type hints")

        # Remove Python 2 compatibility
        result = self.remove_python2_compatibility()
        if result.success and result.files_changed:
            changes_made.append("Python 2 compatibility")

        # Replace deprecated code
        result = self.replace_deprecated_code()
        if result.success and result.files_changed:
            changes_made.append("deprecated code")

        if not changes_made:
            return Result(
                success=True,
                message=f"No modernization needed in {self.path}",
            )

        return Result(
            success=True,
            message=f"Modernized {self.path}: {', '.join(changes_made)}",
            files_changed=[self.path],
        )

    # ===== Directive operations =====

    def find_type_ignores(self) -> TargetList[Target]:
        """Find all type: ignore comments in this file.

        Returns
        -------
        TargetList[LineTarget]
            List of LineTarget objects for lines with type: ignore.

        Examples
        --------
        >>> file = rj.file("mymodule.py")
        >>> ignores = file.find_type_ignores()
        >>> print(f"Found {len(ignores)} type: ignore comments")
        """
        from rejig.directives.finder import DirectiveFinder
        from rejig.targets.python.line import LineTarget

        finder = DirectiveFinder(self._rejig)
        directives = finder.find_in_file(self.path).by_type("type_ignore")

        # Convert to LineTargets for easier manipulation
        targets = [
            LineTarget(self._rejig, self.path, d.line_number) for d in directives
        ]
        return TargetList(self._rejig, targets)

    def find_noqa_comments(self) -> TargetList[Target]:
        """Find all noqa comments in this file.

        Returns
        -------
        TargetList[LineTarget]
            List of LineTarget objects for lines with noqa comments.

        Examples
        --------
        >>> file = rj.file("mymodule.py")
        >>> noqa = file.find_noqa_comments()
        >>> print(f"Found {len(noqa)} noqa comments")
        """
        from rejig.directives.finder import DirectiveFinder
        from rejig.targets.python.line import LineTarget

        finder = DirectiveFinder(self._rejig)
        directives = finder.find_in_file(self.path).by_type("noqa")

        targets = [
            LineTarget(self._rejig, self.path, d.line_number) for d in directives
        ]
        return TargetList(self._rejig, targets)

    def find_directives(self):
        """Find all linting directives in this file.

        Returns
        -------
        DirectiveTargetList
            List of DirectiveTarget objects.

        Examples
        --------
        >>> file = rj.file("mymodule.py")
        >>> directives = file.find_directives()
        >>> for d in directives:
        ...     print(f"Line {d.line_number}: {d.directive_type}")
        """
        from rejig.directives.finder import DirectiveFinder

        finder = DirectiveFinder(self._rejig)
        return finder.find_in_file(self.path)

    def remove_all_type_ignores(self) -> Result:
        """Remove all type: ignore comments from this file.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> file = rj.file("mymodule.py")
        >>> file.remove_all_type_ignores()
        """
        from rejig.directives.finder import DirectiveFinder

        finder = DirectiveFinder(self._rejig)
        directives = finder.find_in_file(self.path).by_type("type_ignore")

        if not directives:
            return Result(success=True, message=f"No type: ignore comments found in {self.path}")

        # Remove in reverse order to avoid line number shifts
        sorted_directives = sorted(directives.to_list(), key=lambda d: d.line_number, reverse=True)
        count = 0
        for directive in sorted_directives:
            result = directive.remove()
            if result.success:
                count += 1

        return Result(
            success=True,
            message=f"Removed {count} type: ignore comments from {self.path}",
            files_changed=[self.path] if count > 0 else [],
        )

    def remove_all_noqa(self) -> Result:
        """Remove all noqa comments from this file.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> file = rj.file("mymodule.py")
        >>> file.remove_all_noqa()
        """
        from rejig.directives.finder import DirectiveFinder

        finder = DirectiveFinder(self._rejig)
        directives = finder.find_in_file(self.path).by_type("noqa")

        if not directives:
            return Result(success=True, message=f"No noqa comments found in {self.path}")

        sorted_directives = sorted(directives.to_list(), key=lambda d: d.line_number, reverse=True)
        count = 0
        for directive in sorted_directives:
            result = directive.remove()
            if result.success:
                count += 1

        return Result(
            success=True,
            message=f"Removed {count} noqa comments from {self.path}",
            files_changed=[self.path] if count > 0 else [],
        )

    def remove_all_directives(self) -> Result:
        """Remove all linting directive comments from this file.

        Removes all: type: ignore, noqa, pylint: disable, fmt: skip/off/on,
        pragma: no cover.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> file = rj.file("mymodule.py")
        >>> file.remove_all_directives()
        """
        from rejig.directives.finder import DirectiveFinder

        finder = DirectiveFinder(self._rejig)
        directives = finder.find_in_file(self.path)

        if not directives:
            return Result(success=True, message=f"No directives found in {self.path}")

        # Remove in reverse order to avoid line number shifts
        sorted_directives = sorted(directives.to_list(), key=lambda d: d.line_number, reverse=True)
        count = 0
        for directive in sorted_directives:
            result = directive.remove()
            if result.success:
                count += 1

        return Result(
            success=True,
            message=f"Removed {count} directives from {self.path}",
            files_changed=[self.path] if count > 0 else [],
        )

    # ===== Module operations =====

    def split(
        self,
        by: str = "class",
        output_dir: Path | None = None,
        create_init: bool = True,
    ) -> Result:
        """Split this file into multiple files.

        Parameters
        ----------
        by : str
            What to split by: "class" or "function".
        output_dir : Path | None
            Output directory. Defaults to a package named after the file.
        create_init : bool
            Whether to create an __init__.py with imports.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> file = rj.file("big_module.py")
        >>> file.split(by="class")  # One file per class
        >>> file.split(by="function")  # One file per function
        """
        from rejig.modules.split import ModuleSplitter

        splitter = ModuleSplitter(self._rejig)

        if by == "class":
            return splitter.split_by_class(self.path, output_dir, create_init)
        elif by == "function":
            return splitter.split_by_function(self.path, output_dir, create_init)
        else:
            return self._operation_failed(
                "split",
                f"Invalid split mode: {by}. Use 'class' or 'function'.",
            )

    def convert_to_package(self, keep_original: bool = False) -> Result:
        """Convert this file to a package directory.

        Transforms utils.py into utils/__init__.py.

        Parameters
        ----------
        keep_original : bool
            Whether to keep the original file. Default False.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> file = rj.file("utils.py")
        >>> file.convert_to_package()  # Creates utils/__init__.py
        """
        from rejig.modules.split import ModuleSplitter

        splitter = ModuleSplitter(self._rejig)
        return splitter.convert_to_package(self.path, keep_original)

    # ===== __all__ management operations =====

    def get_all_exports(self) -> list[str]:
        """Get the current __all__ exports from this file.

        Returns
        -------
        list[str]
            List of exported names, or empty list if no __all__.

        Examples
        --------
        >>> file = rj.file("mypackage/__init__.py")
        >>> exports = file.get_all_exports()
        >>> print(exports)  # ['Class1', 'function1', ...]
        """
        from rejig.modules.exports import ExportsManager

        manager = ExportsManager(self._rejig)
        return manager.get_exports(self.path)

    def generate_all_exports(self, include_private: bool = False) -> Result:
        """Generate __all__ from all public definitions in this file.

        Creates an __all__ list containing all public classes, functions,
        and module-level variables.

        Parameters
        ----------
        include_private : bool
            Whether to include private names (starting with _).

        Returns
        -------
        Result
            Result with generated __all__ in data field.

        Examples
        --------
        >>> init_file = rj.file("mypackage/__init__.py")
        >>> init_file.generate_all_exports()
        """
        from rejig.modules.exports import ExportsManager

        manager = ExportsManager(self._rejig)
        return manager.generate_exports(self.path, include_private)

    def update_all_exports(self, include_private: bool = False) -> Result:
        """Update __all__ to sync with actual definitions.

        Adds missing exports and removes stale ones.

        Parameters
        ----------
        include_private : bool
            Whether to include private names (starting with _).

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> init_file = rj.file("mypackage/__init__.py")
        >>> init_file.update_all_exports()
        """
        from rejig.modules.exports import ExportsManager

        manager = ExportsManager(self._rejig)
        return manager.update_exports(self.path, include_private)

    def add_to_all(self, name: str) -> Result:
        """Add a name to __all__.

        Parameters
        ----------
        name : str
            Name to add to __all__.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> init_file = rj.file("mypackage/__init__.py")
        >>> init_file.add_to_all("new_function")
        """
        from rejig.modules.exports import ExportsManager

        manager = ExportsManager(self._rejig)
        return manager.add_export(self.path, name)

    def remove_from_all(self, name: str) -> Result:
        """Remove a name from __all__.

        Parameters
        ----------
        name : str
            Name to remove from __all__.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> init_file = rj.file("mypackage/__init__.py")
        >>> init_file.remove_from_all("old_function")
        """
        from rejig.modules.exports import ExportsManager

        manager = ExportsManager(self._rejig)
        return manager.remove_export(self.path, name)

    # ===== Header management operations =====

    def add_copyright_header(
        self,
        copyright_text: str,
        year: int | None = None,
    ) -> Result:
        """Add a copyright header to this file.

        Parameters
        ----------
        copyright_text : str
            Copyright holder text (e.g., "MyCompany Inc.").
        year : int | None
            Copyright year. Defaults to current year.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> file = rj.file("mymodule.py")
        >>> file.add_copyright_header("Copyright 2024 MyCompany")
        """
        from rejig.modules.headers import HeaderManager

        manager = HeaderManager(self._rejig)
        return manager.add_copyright_header(self.path, copyright_text, year)

    def add_license_header(
        self,
        license_name: str,
        copyright_holder: str | None = None,
        year: int | None = None,
    ) -> Result:
        """Add a license header to this file.

        Parameters
        ----------
        license_name : str
            License identifier: "MIT", "Apache-2.0", "GPL-3.0",
            "BSD-3-Clause", or "Proprietary".
        copyright_holder : str | None
            Copyright holder name. If None, uses a placeholder.
        year : int | None
            Copyright year. Defaults to current year.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> file = rj.file("mymodule.py")
        >>> file.add_license_header("MIT")
        >>> file.add_license_header("Apache-2.0", "MyCompany Inc.")
        """
        from rejig.modules.headers import HeaderManager

        manager = HeaderManager(self._rejig)
        return manager.add_license_header(self.path, license_name, copyright_holder, year)

    def update_copyright_year(self, new_year: int | None = None) -> Result:
        """Update the copyright year in this file's header.

        Updates patterns like:
        - "Copyright 2023" -> "Copyright 2023-2024"
        - "Copyright 2023-2024" -> "Copyright 2023-2025"

        Parameters
        ----------
        new_year : int | None
            Target year. Defaults to current year.

        Returns
        -------
        Result
            Result of the operation.

        Examples
        --------
        >>> file = rj.file("mymodule.py")
        >>> file.update_copyright_year()
        """
        from rejig.modules.headers import HeaderManager

        manager = HeaderManager(self._rejig)
        return manager.update_copyright_year(self.path, new_year)

    def has_header(self) -> bool:
        """Check if this file has a copyright/license header.

        Returns
        -------
        bool
            True if the file has a header.

        Examples
        --------
        >>> file = rj.file("mymodule.py")
        >>> if not file.has_header():
        ...     file.add_license_header("MIT")
        """
        from rejig.modules.headers import HeaderManager

        manager = HeaderManager(self._rejig)
        return manager.has_header(self.path)
