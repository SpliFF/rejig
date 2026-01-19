"""FileTarget for operations on individual Python files."""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst

from rejig.targets.base import ErrorResult, ErrorTarget, Result, Target, TargetList

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig
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
